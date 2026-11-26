"""NAVBATCHI — navbatchilikni boshqarish web-dasturi (Flask)."""
import hashlib
import hmac
import io
import logging
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import (Flask, abort, g, jsonify, redirect, render_template, request,
                   send_file, send_from_directory, session, url_for)
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

import db as dbm
import notifications as notif
import utils
from config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=settings.SECRET_KEY,
    DB_PATH=str(settings.DB_PATH),
    SESSION_COOKIE_NAME="navbatchi_session",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=settings.COOKIE_SECURE,
    PERMANENT_SESSION_LIFETIME=timedelta(days=365),
    MAX_CONTENT_LENGTH=256 * 1024,
)
app.json.ensure_ascii = False
if settings.BEHIND_PROXY:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

dbm.init_db(settings.DB_PATH)
app.teardown_appcontext(dbm.close_db)

ASSET_V = int(time.time())
ADMIN_SESSION_SECONDS = 8 * 3600
PHONE_RE = re.compile(r"^[0-9+\-()\s]{0,20}$")
DUMMY_HASH = generate_password_hash("navbatchi-dummy-password")


# --------------------------------------------------------------------------
# Yordamchilar
# --------------------------------------------------------------------------
def db():
    return dbm.get_db()


def sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def base_url() -> str:
    return settings.BASE_URL or request.url_root.rstrip("/")


def personal_link(token: str) -> str:
    return f"{base_url()}/u/{token}"


def api_error(message, code=400):
    return jsonify(ok=False, error=message), code


def clean(value, max_len):
    text = re.sub(r"[\x00-\x1f\x7f]", " ", str(value or "")).strip()
    return re.sub(r"\s+", " ", text)[:max_len]


def utc_str(delta_seconds=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=delta_seconds)).strftime("%Y-%m-%d %H:%M:%S")


def client_ip():
    return request.remote_addr or "unknown"


def rate_blocked(ident, limit, window_seconds):
    row = db().execute(
        "SELECT COUNT(*) c FROM login_attempts WHERE ident = ? AND created_at >= ?",
        (ident, utc_str(-window_seconds)),
    ).fetchone()
    return row["c"] >= limit


def rate_hit(ident):
    conn = db()
    conn.execute("INSERT INTO login_attempts(ident) VALUES (?)", (ident,))
    conn.execute("DELETE FROM login_attempts WHERE created_at < ?", (utc_str(-86400),))
    conn.commit()


def rate_clear(ident):
    db().execute("DELETE FROM login_attempts WHERE ident = ?", (ident,))
    db().commit()


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def start_user_session(user):
    session.clear()
    session["role"] = "user"
    session["uid"] = user["id"]
    session.permanent = True
    db().execute("UPDATE users SET last_login = datetime('now') WHERE id = ?", (user["id"],))
    db().commit()


def wants_json():
    return request.path.startswith("/api/")


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.admin is None:
            if wants_json():
                return api_error("Avval tizimga kiring", 401)
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapper


def user_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user is None:
            if wants_json():
                return api_error("Avval tizimga kiring", 401)
            return redirect(url_for("user_login"))
        return view(*args, **kwargs)
    return wrapper


def parse_range(max_days=70):
    start = utils.parse_date(request.args.get("start"))
    end = utils.parse_date(request.args.get("end"))
    if not start or not end or end < start or (end - start).days > max_days:
        return None, None
    return start.isoformat(), end.isoformat()


def duty_view(row, today):
    d = utils.parse_date(row["duty_date"])
    days = (d - today).days
    return {
        "id": row["id"], "iso": row["duty_date"], "label": utils.fmt_date(d),
        "weekday": utils.weekday(d), "days": days, "when": utils.days_text(days),
        "note": row["note"],
    }


# --------------------------------------------------------------------------
# Sessiya, CSRF, xavfsizlik sarlavhalari
# --------------------------------------------------------------------------
@app.before_request
def load_session():
    g.user = None
    g.admin = None
    if request.endpoint == "static":
        return
    role = session.get("role")
    if role == "admin":
        if session.get("exp", 0) > time.time():
            g.admin = db().execute("SELECT * FROM admins WHERE id = ?", (session.get("aid"),)).fetchone()
        if g.admin is None:
            session.clear()
    elif role == "user":
        g.user = db().execute("SELECT * FROM users WHERE id = ? AND active = 1", (session.get("uid"),)).fetchone()
        if g.user is None:
            session.clear()

    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        expected = session.get("csrf")
        sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token") or ""
        if not expected or not hmac.compare_digest(str(sent), expected):
            if wants_json():
                return api_error("Sessiya eskirgan. Sahifani yangilab qayta urinib ko'ring.", 400)
            abort(400)


@app.after_request
def security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
        "base-uri 'self'; form-action 'self'"
    )
    if settings.COOKIE_SECURE:
        resp.headers["Strict-Transport-Security"] = "max-age=31536000"
    if not request.path.startswith("/static/") and request.endpoint != "service_worker":
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.context_processor
def inject_globals():
    user = g.get("user")
    admin = g.get("admin")
    unread = 0
    if user is not None:
        unread = db().execute(
            "SELECT COUNT(*) c FROM notifications WHERE user_id = ? AND read_at IS NULL", (user["id"],)
        ).fetchone()["c"]
    return dict(
        csrf_token=csrf_token, me=user, admin=admin, unread_count=unread,
        role="admin" if admin else ("user" if user else ""),
        vapid_public_key=settings.VAPID_PUBLIC_KEY, asset_v=ASSET_V, today=utils.today(),
    )


app.jinja_env.filters["fmt_date"] = utils.fmt_date
app.jinja_env.filters["fmt_dt"] = utils.fmt_dt
app.jinja_env.filters["weekday"] = utils.weekday


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(413)
@app.errorhandler(500)
def handle_error(err):
    code = getattr(err, "code", 500) or 500
    if code == 500:
        app.logger.exception("Server xatosi")
    if wants_json():
        return api_error("So'rovni bajarib bo'lmadi", code)
    messages = {
        400: "So'rov noto'g'ri yoki sessiya eskirgan. Sahifani yangilab qayta urinib ko'ring.",
        403: "Bu sahifaga kirish huquqingiz yo'q.",
        404: "Bunday sahifa topilmadi.",
        405: "Bu amalga ruxsat yo'q.",
        413: "Yuborilgan ma'lumot juda katta.",
        500: "Serverda xatolik yuz berdi. Keyinroq qayta urinib ko'ring.",
    }
    return render_template("error.html", title=f"Xatolik {code}", message=messages.get(code, "Xatolik")), code


# --------------------------------------------------------------------------
# Umumiy sahifalar
# --------------------------------------------------------------------------
@app.route("/")
def index():
    if g.admin:
        return redirect(url_for("admin_dashboard"))
    if g.user:
        return redirect(url_for("user_dashboard"))
    return redirect(url_for("user_login"))


@app.route("/sw.js")
def service_worker():
    resp = send_from_directory(app.static_folder, "sw.js", mimetype="application/javascript")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


@app.route("/manifest.webmanifest")
def manifest():
    data = {
        "name": "NAVBATCHI", "short_name": "Navbatchi", "lang": "uz",
        "start_url": "/app", "scope": "/", "display": "standalone",
        "background_color": "#0f1220", "theme_color": "#5b6cff",
        "icons": [
            {"src": "/static/img/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/img/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }
    resp = jsonify(data)
    resp.mimetype = "application/manifest+json"
    return resp


@app.route("/healthz")
def healthz():
    return "ok"


@app.route("/logout", methods=["POST"])
def logout():
    was_admin = g.admin is not None
    session.clear()
    return redirect(url_for("admin_login" if was_admin else "user_login"))


# --------------------------------------------------------------------------
# Foydalanuvchi: kirish va ro'yxatdan o'tish
# --------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def user_login():
    if g.user:
        return redirect(url_for("user_dashboard"))
    error = None
    if request.method == "POST":
        ident = "login:" + client_ip()
        if rate_blocked(ident, 10, 900):
            error = "Juda ko'p urinish bo'ldi. 15 daqiqadan keyin qayta urinib ko'ring."
        else:
            code = request.form.get("code", "").strip().rstrip("/").split("/")[-1]
            user = None
            if code:
                user = db().execute(
                    "SELECT * FROM users WHERE token_hash = ? AND active = 1", (sha(code),)
                ).fetchone()
            if user:
                rate_clear(ident)
                start_user_session(user)
                return redirect(url_for("user_dashboard"))
            rate_hit(ident)
            error = "Kod yoki havola noto'g'ri."
    return render_template("login.html", error=error)


@app.route("/u/<token>")
def user_link_login(token):
    ident = "login:" + client_ip()
    if rate_blocked(ident, 10, 900):
        return render_template("error.html", title="Biroz kuting",
                               message="Juda ko'p urinish bo'ldi. 15 daqiqadan keyin qayta urinib ko'ring."), 429
    user = db().execute("SELECT * FROM users WHERE token_hash = ? AND active = 1", (sha(token),)).fetchone()
    if not user:
        rate_hit(ident)
        return render_template("error.html", title="Havola yaroqsiz",
                               message="Bu shaxsiy havola noto'g'ri yoki bekor qilingan. Administratordan yangi havola so'rang."), 404
    start_user_session(user)
    return redirect(url_for("user_dashboard"))


def get_valid_qr(token):
    qr = db().execute("SELECT * FROM qr_tokens WHERE token = ?", (token,)).fetchone()
    if not qr or not qr["active"]:
        return None
    if qr["expires_at"] and qr["expires_at"] < utc_str():
        return None
    return qr


@app.route("/join/<token>", methods=["GET", "POST"])
def join(token):
    qr = get_valid_qr(token)
    if not qr:
        return render_template("error.html", title="QR-kod yaroqsiz",
                               message="Bu QR-kod faol emas yoki muddati tugagan. Administratordan yangisini so'rang."), 404
    if g.admin:
        return render_template("error.html", title="Administrator sessiyasi",
                               message="Siz administrator sifatida kirgansiz. Ro'yxatdan o'tish uchun havolani boshqa brauzerda yoki telefonda oching."), 403
    if g.user:
        db().execute("INSERT INTO qr_scans(qr_id, user_id, kind) VALUES (?, ?, 'login')", (qr["id"], g.user["id"]))
        db().commit()
        return redirect(url_for("user_dashboard"))

    values = {"first_name": "", "last_name": "", "phone": "", "note": ""}
    error = None
    if request.method == "POST":
        values = {
            "first_name": clean(request.form.get("first_name"), 50),
            "last_name": clean(request.form.get("last_name"), 50),
            "phone": clean(request.form.get("phone"), 20),
            "note": clean(request.form.get("note"), 100),
        }
        ident = "join:" + client_ip()
        if rate_blocked(ident, 15, 3600):
            error = "Juda ko'p urinish bo'ldi. Keyinroq qayta urinib ko'ring."
        elif len(values["first_name"]) < 2 or len(values["last_name"]) < 2:
            error = "Ism va familiyani to'liq kiriting (kamida 2 ta belgi)."
        elif not PHONE_RE.match(values["phone"]):
            error = "Telefon raqami noto'g'ri kiritilgan."
        else:
            rate_hit(ident)
            conn = db()
            cur = conn.execute(
                "INSERT INTO users(first_name, last_name, phone, note, token_hash, qr_id) VALUES (?, ?, ?, ?, ?, ?)",
                (values["first_name"], values["last_name"], values["phone"], values["note"],
                 sha(new_token()), qr["id"]),
            )
            uid = cur.lastrowid
            conn.execute("INSERT INTO qr_scans(qr_id, user_id, kind) VALUES (?, ?, 'register')", (qr["id"], uid))
            conn.commit()
            user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
            start_user_session(user)
            return redirect(url_for("user_dashboard"))
    return render_template("join.html", values=values, error=error, qr=qr)


# --------------------------------------------------------------------------
# Foydalanuvchi paneli
# --------------------------------------------------------------------------
@app.route("/app")
@user_required
def user_dashboard():
    today = utils.today()
    uid = g.user["id"]
    upcoming = db().execute(
        "SELECT * FROM duties WHERE user_id = ? AND duty_date >= ? ORDER BY duty_date LIMIT 8",
        (uid, today.isoformat())).fetchall()
    past = db().execute(
        "SELECT * FROM duties WHERE user_id = ? AND duty_date < ? ORDER BY duty_date DESC LIMIT 8",
        (uid, today.isoformat())).fetchall()
    upcoming = [duty_view(r, today) for r in upcoming]
    past = [duty_view(r, today) for r in past]
    return render_template(
        "user/dashboard.html", today_label=utils.fmt_date(today), today_weekday=utils.weekday(today),
        next_duty=upcoming[0] if upcoming else None, upcoming=upcoming, past=past,
        on_duty_today=bool(upcoming and upcoming[0]["days"] == 0),
    )


@app.route("/app/notifications")
@user_required
def user_notifications():
    rows = db().execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT 60", (g.user["id"],)
    ).fetchall()
    return render_template("user/notifications.html", items=rows)


@app.route("/app/profile")
@user_required
def user_profile():
    subs = db().execute("SELECT COUNT(*) c FROM push_subscriptions WHERE user_id = ?", (g.user["id"],)).fetchone()["c"]
    return render_template("user/profile.html", push_count=subs)


@app.route("/api/me/duties")
@user_required
def api_me_duties():
    start, end = parse_range()
    if not start:
        return api_error("Sana oralig'i noto'g'ri")
    rows = db().execute(
        "SELECT id, duty_date, note FROM duties WHERE user_id = ? AND duty_date BETWEEN ? AND ? ORDER BY duty_date",
        (g.user["id"], start, end)).fetchall()
    items = [{"id": r["id"], "date": r["duty_date"], "note": r["note"], "name": "Navbatchilik"} for r in rows]
    return jsonify(ok=True, items=items)


@app.route("/api/me/profile", methods=["POST"])
@user_required
def api_me_profile():
    d = request.get_json(silent=True) or {}
    first, last = clean(d.get("first_name"), 50), clean(d.get("last_name"), 50)
    phone, note = clean(d.get("phone"), 20), clean(d.get("note"), 100)
    if len(first) < 2 or len(last) < 2:
        return api_error("Ism va familiya kamida 2 ta belgidan iborat bo'lsin")
    if not PHONE_RE.match(phone):
        return api_error("Telefon raqami noto'g'ri")
    db().execute("UPDATE users SET first_name=?, last_name=?, phone=?, note=? WHERE id=?",
                 (first, last, phone, note, g.user["id"]))
    db().commit()
    return jsonify(ok=True)


@app.route("/api/me/link", methods=["POST"])
@user_required
def api_me_link():
    token = new_token()
    db().execute("UPDATE users SET token_hash = ? WHERE id = ?", (sha(token), g.user["id"]))
    db().commit()
    return jsonify(ok=True, link=personal_link(token))


@app.route("/api/me/notifications/read", methods=["POST"])
@user_required
def api_me_read():
    db().execute("UPDATE notifications SET read_at = datetime('now') WHERE user_id = ? AND read_at IS NULL",
                 (g.user["id"],))
    db().commit()
    return jsonify(ok=True)


@app.route("/api/me/test-push", methods=["POST"])
@user_required
def api_me_test_push():
    sent = notif.send_push_to_user(db(), g.user["id"], "NAVBATCHI",
                                   "Bu sinov bildirishnomasi. Hammasi ishlayapti!", url="/app", tag="test")
    if sent == 0:
        return api_error("Bu qurilmada bildirishnoma yoqilmagan yoki yuborib bo'lmadi.")
    return jsonify(ok=True, sent=sent)


@app.route("/api/push/subscribe", methods=["POST"])
@user_required
def api_push_subscribe():
    d = request.get_json(silent=True) or {}
    sub = d.get("subscription") or {}
    keys = sub.get("keys") or {}
    endpoint, p256dh, auth = sub.get("endpoint"), keys.get("p256dh"), keys.get("auth")
    if not (isinstance(endpoint, str) and endpoint.startswith("https://") and len(endpoint) < 1000
            and isinstance(p256dh, str) and isinstance(auth, str) and len(p256dh) < 200 and len(auth) < 100):
        return api_error("Obuna ma'lumotlari noto'g'ri")
    conn = db()
    conn.execute(
        "INSERT INTO push_subscriptions(user_id, endpoint, p256dh, auth, user_agent) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(endpoint) DO UPDATE SET user_id=excluded.user_id, p256dh=excluded.p256dh, "
        "auth=excluded.auth, user_agent=excluded.user_agent",
        (g.user["id"], endpoint, p256dh, auth, clean(request.headers.get("User-Agent"), 200)))
    conn.execute("UPDATE users SET notify_enabled = 1, notify_asked = 1 WHERE id = ?", (g.user["id"],))
    conn.commit()
    return jsonify(ok=True)


@app.route("/api/push/unsubscribe", methods=["POST"])
@user_required
def api_push_unsubscribe():
    d = request.get_json(silent=True) or {}
    endpoint = d.get("endpoint")
    conn = db()
    if endpoint:
        conn.execute("DELETE FROM push_subscriptions WHERE user_id = ? AND endpoint = ?", (g.user["id"], endpoint))
    else:
        conn.execute("DELETE FROM push_subscriptions WHERE user_id = ?", (g.user["id"],))
    left = conn.execute("SELECT COUNT(*) c FROM push_subscriptions WHERE user_id = ?", (g.user["id"],)).fetchone()["c"]
    if left == 0:
        conn.execute("UPDATE users SET notify_enabled = 0 WHERE id = ?", (g.user["id"],))
    conn.commit()
    return jsonify(ok=True)


@app.route("/api/push/decline", methods=["POST"])
@user_required
def api_push_decline():
    db().execute("UPDATE users SET notify_asked = 1 WHERE id = ?", (g.user["id"],))
    db().commit()
    return jsonify(ok=True)


# --------------------------------------------------------------------------
# Administrator: kirish
# --------------------------------------------------------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if g.admin:
        return redirect(url_for("admin_dashboard"))
    error = None
    if request.method == "POST":
        username = clean(request.form.get("username"), 64).lower()
        password = request.form.get("password", "")
        ident_ip, ident_user = "alogin:" + client_ip(), "alogin:u:" + username
        if rate_blocked(ident_ip, 10, 900) or rate_blocked(ident_user, 5, 900):
            error = "Juda ko'p urinish bo'ldi. 15 daqiqadan keyin qayta urinib ko'ring."
        else:
            row = db().execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
            ok = check_password_hash(row["password_hash"] if row else DUMMY_HASH, password) and row is not None
            if ok:
                rate_clear(ident_ip)
                rate_clear(ident_user)
                session.clear()
                session["role"] = "admin"
                session["aid"] = row["id"]
                session["exp"] = time.time() + ADMIN_SESSION_SECONDS
                return redirect(url_for("admin_dashboard"))
            rate_hit(ident_ip)
            rate_hit(ident_user)
            error = "Login yoki parol noto'g'ri."
    return render_template("admin/login.html", error=error)


# --------------------------------------------------------------------------
# Administrator: sahifalar
# --------------------------------------------------------------------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = db()
    today = utils.today()
    month_start = today.replace(day=1)
    next_month = (month_start + timedelta(days=32)).replace(day=1)
    t_iso = today.isoformat()

    def one(sql, *args):
        return conn.execute(sql, args).fetchone()[0]

    stats = {
        "users": one("SELECT COUNT(*) FROM users WHERE active = 1"),
        "month_duties": one("SELECT COUNT(*) FROM duties WHERE duty_date >= ? AND duty_date < ?",
                            month_start.isoformat(), next_month.isoformat()),
        "push_users": one("SELECT COUNT(DISTINCT user_id) FROM push_subscriptions"),
        "qr_users": one("SELECT COUNT(*) FROM users WHERE qr_id IS NOT NULL"),
    }

    def names_on(day):
        rows = conn.execute(
            "SELECT u.first_name, u.last_name FROM duties d JOIN users u ON u.id = d.user_id "
            "WHERE d.duty_date = ? ORDER BY u.first_name", (day.isoformat(),)).fetchall()
        return [f"{r['first_name']} {r['last_name']}" for r in rows]

    upcoming = []
    for i in range(0, 7):
        day = today + timedelta(days=i)
        upcoming.append({"day": day, "names": names_on(day), "when": utils.days_text(i)})

    per_user = conn.execute(
        "SELECT u.first_name, u.last_name, COUNT(d.id) c FROM users u "
        "JOIN duties d ON d.user_id = u.id AND d.duty_date >= ? AND d.duty_date < ? "
        "GROUP BY u.id ORDER BY c DESC, u.first_name LIMIT 8",
        (month_start.isoformat(), next_month.isoformat())).fetchall()
    recent_users = conn.execute(
        "SELECT u.*, q.label AS qr_label FROM users u LEFT JOIN qr_tokens q ON q.id = u.qr_id "
        "ORDER BY u.id DESC LIMIT 6").fetchall()
    return render_template("admin/dashboard.html", stats=stats, upcoming=upcoming, per_user=per_user,
                           recent_users=recent_users, month_label=f"{utils.UZ_MONTHS[today.month - 1]} {today.year}",
                           max_count=max([r["c"] for r in per_user], default=1), today_iso=t_iso)


@app.route("/admin/users")
@admin_required
def admin_users():
    rows = db().execute(
        "SELECT u.*, q.label AS qr_label, "
        "(SELECT COUNT(*) FROM push_subscriptions p WHERE p.user_id = u.id) AS push_count, "
        "(SELECT COUNT(*) FROM duties d WHERE d.user_id = u.id) AS duty_total, "
        "(SELECT MIN(duty_date) FROM duties d WHERE d.user_id = u.id AND d.duty_date >= ?) AS next_duty "
        "FROM users u LEFT JOIN qr_tokens q ON q.id = u.qr_id ORDER BY u.first_name, u.last_name",
        (utils.today().isoformat(),)).fetchall()
    return render_template("admin/users.html", users=rows)


@app.route("/admin/calendar")
@admin_required
def admin_calendar():
    users = db().execute("SELECT id, first_name, last_name FROM users WHERE active = 1 ORDER BY first_name, last_name").fetchall()
    return render_template("admin/calendar.html",
                           users=[{"id": u["id"], "name": f"{u['first_name']} {u['last_name']}"} for u in users])


@app.route("/admin/qr")
@admin_required
def admin_qr():
    conn = db()
    tokens = conn.execute(
        "SELECT q.*, (SELECT COUNT(*) FROM users u WHERE u.qr_id = q.id) AS joined "
        "FROM qr_tokens q ORDER BY q.id DESC").fetchall()
    items = [dict(t, link=f"{base_url()}/join/{t['token']}",
                  expired=bool(t["expires_at"] and t["expires_at"] < utc_str())) for t in tokens]
    scans = conn.execute(
        "SELECT s.created_at, s.kind, q.label, u.first_name, u.last_name FROM qr_scans s "
        "JOIN qr_tokens q ON q.id = s.qr_id LEFT JOIN users u ON u.id = s.user_id "
        "ORDER BY s.id DESC LIMIT 60").fetchall()
    return render_template("admin/qr.html", items=items, scans=scans)


@app.route("/admin/qr/<int:qid>.png")
@admin_required
def admin_qr_png(qid):
    qr = db().execute("SELECT * FROM qr_tokens WHERE id = ?", (qid,)).fetchone()
    if not qr:
        abort(404)
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_M
    except ImportError:
        return "qrcode kutubxonasi o'rnatilmagan (pip install -r requirements.txt)", 500
    img = qrcode.make(f"{base_url()}/join/{qr['token']}", box_size=10, border=3, error_correction=ERROR_CORRECT_M)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", download_name=f"navbatchi-qr-{qid}.png",
                     as_attachment=request.args.get("download") == "1")


@app.route("/admin/notifications")
@admin_required
def admin_notifications():
    users = db().execute("SELECT id, first_name, last_name, notify_enabled FROM users WHERE active = 1 "
                         "ORDER BY first_name, last_name").fetchall()
    history = db().execute(
        "SELECT title, body, created_at, COUNT(*) AS total, SUM(pushed) AS pushed FROM notifications "
        "WHERE kind = 'admin' GROUP BY created_at, title, body ORDER BY created_at DESC LIMIT 30").fetchall()
    return render_template("admin/notify.html", users=users, history=history)


@app.route("/admin/stats")
@admin_required
def admin_stats():
    conn = db()
    today = utils.today()
    try:
        year = int(request.args.get("year", today.year))
    except ValueError:
        year = today.year
    year = min(max(year, 2000), 2100)
    ys = str(year)

    months = [0] * 12
    for r in conn.execute("SELECT CAST(substr(duty_date, 6, 2) AS INTEGER) m, COUNT(*) c FROM duties "
                          "WHERE substr(duty_date, 1, 4) = ? GROUP BY m", (ys,)):
        months[r["m"] - 1] = r["c"]
    weekdays = [0] * 7
    for r in conn.execute("SELECT strftime('%w', duty_date) w, COUNT(*) c FROM duties "
                          "WHERE substr(duty_date, 1, 4) = ? GROUP BY w", (ys,)):
        weekdays[(int(r["w"]) + 6) % 7] = r["c"]  # 0=yakshanba -> oxiriga
    t_iso = today.isoformat()
    per_user = conn.execute(
        "SELECT u.id, u.first_name, u.last_name, COUNT(d.id) AS total, "
        "COALESCE(SUM(d.duty_date >= ?), 0) AS upcoming, COALESCE(SUM(d.duty_date < ?), 0) AS past, "
        "MIN(CASE WHEN d.duty_date >= ? THEN d.duty_date END) AS next_duty "
        "FROM users u LEFT JOIN duties d ON d.user_id = u.id AND substr(d.duty_date, 1, 4) = ? "
        "WHERE u.active = 1 GROUP BY u.id ORDER BY total DESC, u.first_name",
        (t_iso, t_iso, t_iso, ys)).fetchall()
    return render_template(
        "admin/stats.html", year=year, months=months, month_names=utils.UZ_MONTHS,
        weekdays=weekdays, weekday_names=utils.UZ_DAYS, per_user=per_user,
        max_month=max(months) or 1, max_weekday=max(weekdays) or 1,
        total=sum(months), max_user=max([r["total"] for r in per_user], default=1) or 1)


@app.route("/admin/account")
@admin_required
def admin_account():
    return render_template("admin/account.html")


# --------------------------------------------------------------------------
# Administrator: API
# --------------------------------------------------------------------------
def read_user_fields(d):
    first, last = clean(d.get("first_name"), 50), clean(d.get("last_name"), 50)
    phone, note = clean(d.get("phone"), 20), clean(d.get("note"), 100)
    if len(first) < 2 or len(last) < 2:
        return None, "Ism va familiya kamida 2 ta belgidan iborat bo'lsin"
    if not PHONE_RE.match(phone):
        return None, "Telefon raqami noto'g'ri"
    return (first, last, phone, note), None


@app.route("/api/admin/users", methods=["POST"])
@admin_required
def api_users_create():
    fields, err = read_user_fields(request.get_json(silent=True) or {})
    if err:
        return api_error(err)
    token = new_token()
    cur = db().execute(
        "INSERT INTO users(first_name, last_name, phone, note, token_hash) VALUES (?, ?, ?, ?, ?)",
        (*fields, sha(token)))
    db().commit()
    return jsonify(ok=True, id=cur.lastrowid, link=personal_link(token))


@app.route("/api/admin/users/<int:uid>", methods=["PUT"])
@admin_required
def api_users_update(uid):
    d = request.get_json(silent=True) or {}
    fields, err = read_user_fields(d)
    if err:
        return api_error(err)
    active = 1 if d.get("active", True) else 0
    cur = db().execute("UPDATE users SET first_name=?, last_name=?, phone=?, note=?, active=? WHERE id=?",
                       (*fields, active, uid))
    db().commit()
    if cur.rowcount == 0:
        return api_error("Foydalanuvchi topilmadi", 404)
    return jsonify(ok=True)


@app.route("/api/admin/users/<int:uid>", methods=["DELETE"])
@admin_required
def api_users_delete(uid):
    cur = db().execute("DELETE FROM users WHERE id = ?", (uid,))
    db().commit()
    if cur.rowcount == 0:
        return api_error("Foydalanuvchi topilmadi", 404)
    return jsonify(ok=True)


@app.route("/api/admin/users/<int:uid>/link", methods=["POST"])
@admin_required
def api_users_link(uid):
    token = new_token()
    cur = db().execute("UPDATE users SET token_hash = ? WHERE id = ?", (sha(token), uid))
    db().commit()
    if cur.rowcount == 0:
        return api_error("Foydalanuvchi topilmadi", 404)
    return jsonify(ok=True, link=personal_link(token))


@app.route("/api/admin/duties", methods=["GET"])
@admin_required
def api_duties_list():
    start, end = parse_range()
    if not start:
        return api_error("Sana oralig'i noto'g'ri")
    rows = db().execute(
        "SELECT d.id, d.user_id, d.duty_date, d.note, u.first_name, u.last_name FROM duties d "
        "JOIN users u ON u.id = d.user_id WHERE d.duty_date BETWEEN ? AND ? "
        "ORDER BY d.duty_date, u.first_name", (start, end)).fetchall()
    items = [{"id": r["id"], "user_id": r["user_id"], "date": r["duty_date"], "note": r["note"],
              "name": f"{r['first_name']} {r['last_name']}"} for r in rows]
    return jsonify(ok=True, items=items)


@app.route("/api/admin/duties", methods=["POST"])
@admin_required
def api_duties_create():
    d = request.get_json(silent=True) or {}
    raw_users, raw_dates = d.get("user_ids"), d.get("dates")
    if not isinstance(raw_users, list) or not isinstance(raw_dates, list) or not raw_users or not raw_dates:
        return api_error("Foydalanuvchi va sanani tanlang")
    if len(raw_dates) > 366 or len(raw_users) > 200:
        return api_error("Bir vaqtda juda ko'p ma'lumot yuborildi")
    dates = []
    for value in raw_dates:
        parsed = utils.parse_date(value)
        if not parsed:
            return api_error("Sana noto'g'ri")
        dates.append(parsed.isoformat())
    user_ids = []
    for value in raw_users:
        if not isinstance(value, int) or isinstance(value, bool):
            return api_error("Foydalanuvchi noto'g'ri")
        user_ids.append(value)
    conn = db()
    existing = {r["id"] for r in conn.execute(
        f"SELECT id FROM users WHERE id IN ({','.join('?' * len(user_ids))})", user_ids)}
    if existing != set(user_ids):
        return api_error("Foydalanuvchi topilmadi", 404)
    note = clean(d.get("note"), 100)
    added = 0
    for uid in user_ids:
        for ds in dates:
            added += conn.execute("INSERT OR IGNORE INTO duties(user_id, duty_date, note) VALUES (?, ?, ?)",
                                  (uid, ds, note)).rowcount
    conn.commit()
    total = len(user_ids) * len(dates)
    return jsonify(ok=True, added=added, skipped=total - added)


@app.route("/api/admin/duties/<int:did>", methods=["PUT"])
@admin_required
def api_duties_update(did):
    d = request.get_json(silent=True) or {}
    conn = db()
    row = conn.execute("SELECT * FROM duties WHERE id = ?", (did,)).fetchone()
    if not row:
        return api_error("Navbatchilik topilmadi", 404)
    duty_date, user_id, note = row["duty_date"], row["user_id"], row["note"]
    if "duty_date" in d:
        parsed = utils.parse_date(d["duty_date"])
        if not parsed:
            return api_error("Sana noto'g'ri")
        duty_date = parsed.isoformat()
    if "user_id" in d:
        if not isinstance(d["user_id"], int) or not conn.execute(
                "SELECT 1 FROM users WHERE id = ?", (d["user_id"],)).fetchone():
            return api_error("Foydalanuvchi topilmadi", 404)
        user_id = d["user_id"]
    if "note" in d:
        note = clean(d["note"], 100)
    try:
        conn.execute("UPDATE duties SET duty_date=?, user_id=?, note=? WHERE id=?", (duty_date, user_id, note, did))
        conn.commit()
    except Exception:
        conn.rollback()
        return api_error("Bu foydalanuvchi o'sha kunga allaqachon biriktirilgan", 409)
    return jsonify(ok=True)


@app.route("/api/admin/duties/<int:did>", methods=["DELETE"])
@admin_required
def api_duties_delete(did):
    cur = db().execute("DELETE FROM duties WHERE id = ?", (did,))
    db().commit()
    if cur.rowcount == 0:
        return api_error("Navbatchilik topilmadi", 404)
    return jsonify(ok=True)


@app.route("/api/admin/qr", methods=["POST"])
@admin_required
def api_qr_create():
    d = request.get_json(silent=True) or {}
    label = clean(d.get("label"), 60) or "Asosiy QR-kod"
    expires = None
    try:
        days = int(d.get("valid_days") or 0)
    except (TypeError, ValueError):
        return api_error("Amal qilish muddati noto'g'ri")
    if days < 0 or days > 3650:
        return api_error("Amal qilish muddati noto'g'ri")
    if days:
        expires = utc_str(days * 86400)
    cur = db().execute("INSERT INTO qr_tokens(token, label, expires_at) VALUES (?, ?, ?)",
                       (new_token(), label, expires))
    db().commit()
    return jsonify(ok=True, id=cur.lastrowid)


@app.route("/api/admin/qr/<int:qid>", methods=["PATCH"])
@admin_required
def api_qr_toggle(qid):
    d = request.get_json(silent=True) or {}
    cur = db().execute("UPDATE qr_tokens SET active = ? WHERE id = ?", (1 if d.get("active") else 0, qid))
    db().commit()
    if cur.rowcount == 0:
        return api_error("QR-kod topilmadi", 404)
    return jsonify(ok=True)


@app.route("/api/admin/qr/<int:qid>", methods=["DELETE"])
@admin_required
def api_qr_delete(qid):
    cur = db().execute("DELETE FROM qr_tokens WHERE id = ?", (qid,))
    db().commit()
    if cur.rowcount == 0:
        return api_error("QR-kod topilmadi", 404)
    return jsonify(ok=True)


@app.route("/api/admin/notify", methods=["POST"])
@admin_required
def api_notify():
    d = request.get_json(silent=True) or {}
    title, body = clean(d.get("title"), 80), clean(d.get("body"), 300)
    if not title or not body:
        return api_error("Sarlavha va xabar matnini kiriting")
    conn = db()
    if d.get("all"):
        ids = [r["id"] for r in conn.execute("SELECT id FROM users WHERE active = 1")]
    else:
        raw = d.get("user_ids")
        if not isinstance(raw, list) or not raw or not all(isinstance(i, int) for i in raw):
            return api_error("Qabul qiluvchilarni tanlang")
        ids = [r["id"] for r in conn.execute(
            f"SELECT id FROM users WHERE active = 1 AND id IN ({','.join('?' * len(raw))})", raw)]
    if not ids:
        return api_error("Qabul qiluvchi topilmadi")
    stamp = utc_str()
    pushed = 0
    for uid in ids:
        _nid, sent = notif.create_notification(conn, uid, "admin", title, body, None, created_at=stamp)
        pushed += 1 if sent else 0
    return jsonify(ok=True, total=len(ids), pushed=pushed)


@app.route("/api/admin/account/password", methods=["POST"])
@admin_required
def api_admin_password():
    d = request.get_json(silent=True) or {}
    current, new = d.get("current", ""), d.get("new", "")
    if not check_password_hash(g.admin["password_hash"], current):
        return api_error("Joriy parol noto'g'ri")
    if len(new) < 8:
        return api_error("Yangi parol kamida 8 ta belgidan iborat bo'lsin")
    db().execute("UPDATE admins SET password_hash = ? WHERE id = ?", (generate_password_hash(new), g.admin["id"]))
    db().commit()
    return jsonify(ok=True)


# --------------------------------------------------------------------------
# Ishga tushirish
# --------------------------------------------------------------------------
def bootstrap_admin():
    """ADMIN_USERNAME / ADMIN_PASSWORD berilgan va admin yo'q bo'lsa, birinchi adminni yaratadi."""
    if not (settings.ADMIN_USERNAME and settings.ADMIN_PASSWORD):
        return
    conn = dbm.connect(settings.DB_PATH)
    try:
        if conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0] == 0:
            if len(settings.ADMIN_PASSWORD) < 8:
                app.logger.error("ADMIN_PASSWORD kamida 8 ta belgi bo'lishi kerak")
                return
            conn.execute("INSERT INTO admins(username, password_hash) VALUES (?, ?)",
                         (settings.ADMIN_USERNAME, generate_password_hash(settings.ADMIN_PASSWORD)))
            conn.commit()
            app.logger.info("Administrator yaratildi: %s", settings.ADMIN_USERNAME)
    finally:
        conn.close()


bootstrap_admin()

if not settings.DISABLE_SCHEDULER and os.environ.get("NAVBATCHI_NO_SCHEDULER") != "1":
    notif.start_scheduler(app)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)

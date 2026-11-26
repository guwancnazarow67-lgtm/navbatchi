"""Web Push yuborish va avtomatik eslatmalar."""
import json
import logging
import threading
import time
from datetime import timedelta

import db as dbm
import utils
from config import settings

log = logging.getLogger("navbatchi.push")


def _webpush():
    try:
        from pywebpush import WebPushException, webpush

        return webpush, WebPushException
    except ImportError:
        return None, None


def send_push_to_user(conn, user_id, title, body, url="/app", tag=None):
    """Foydalanuvchining barcha qurilmalariga push yuboradi. Yuborilganlar sonini qaytaradi."""
    webpush, WebPushException = _webpush()
    if webpush is None:
        log.warning("pywebpush o'rnatilmagan: push yuborilmadi")
        return 0
    subs = conn.execute(
        "SELECT id, endpoint, p256dh, auth FROM push_subscriptions WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    if not subs:
        return 0
    payload = json.dumps(
        {"title": title, "body": body, "url": url, "tag": tag or "navbatchi"},
        ensure_ascii=False,
    )
    sent = 0
    for s in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": s["endpoint"],
                    "keys": {"p256dh": s["p256dh"], "auth": s["auth"]},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_SUBJECT},
                ttl=86400,
                timeout=10,
            )
            sent += 1
        except WebPushException as exc:
            code = getattr(getattr(exc, "response", None), "status_code", None)
            if code in (404, 410):
                conn.execute("DELETE FROM push_subscriptions WHERE id = ?", (s["id"],))
            else:
                log.warning("Push xatosi (%s): %s", code, exc)
        except Exception:  # tarmoq xatosi va h.k.
            log.exception("Push yuborishda kutilmagan xato")
    left = conn.execute(
        "SELECT COUNT(*) c FROM push_subscriptions WHERE user_id = ?", (user_id,)
    ).fetchone()["c"]
    if left == 0:
        conn.execute("UPDATE users SET notify_enabled = 0 WHERE id = ?", (user_id,))
    conn.commit()
    return sent


def create_notification(conn, user_id, kind, title, body, ref_date=None,
                        created_at=None, url="/app/notifications"):
    """Bildirishnomani bazaga yozadi va push yuboradi.

    ref_date berilgan bo'lsa, (user, kind, ref_date) bo'yicha takrorlanmaydi.
    (notification_id, sent) qaytaradi; takror bo'lsa (None, 0).
    """
    cur = conn.execute(
        "INSERT OR IGNORE INTO notifications(user_id, kind, title, body, ref_date, created_at) "
        "VALUES (?, ?, ?, ?, ?, COALESCE(?, datetime('now')))",
        (user_id, kind, title, body, ref_date, created_at),
    )
    if cur.rowcount == 0:
        conn.commit()
        return None, 0
    nid = cur.lastrowid
    conn.commit()
    sent = send_push_to_user(conn, user_id, title, body, url=url, tag=f"{kind}-{ref_date or nid}")
    if sent:
        conn.execute("UPDATE notifications SET pushed = 1 WHERE id = ?", (nid,))
        conn.commit()
    return nid, sent


def run_reminders(db_path):
    """Bugungi va ertangi navbatchilar uchun eslatma yuboradi (kuniga bir marta)."""
    conn = dbm.connect(db_path)
    try:
        now = utils.now()
        if now.hour < settings.NOTIFY_HOUR:
            return
        today = now.date()
        plans = (
            ("today", today, "Bugun navbatchilik kuningiz",
             "{name}, bugun ({date}) sizning navbatchilik kuningiz."),
            ("before", today + timedelta(days=1), "Ertaga navbatchilik",
             "{name}, ertaga ({date}, {wd}) navbatchilikka chiqasiz."),
        )
        for kind, day, title, template in plans:
            rows = conn.execute(
                "SELECT d.user_id, u.first_name FROM duties d "
                "JOIN users u ON u.id = d.user_id WHERE d.duty_date = ? AND u.active = 1",
                (day.isoformat(),),
            ).fetchall()
            for r in rows:
                body = template.format(name=r["first_name"], date=utils.fmt_date(day),
                                       wd=utils.weekday(day))
                create_notification(conn, r["user_id"], kind, title, body,
                                    ref_date=day.isoformat(), url="/app")
    finally:
        conn.close()


def start_scheduler(app):
    def loop():
        time.sleep(5)
        while True:
            try:
                run_reminders(app.config["DB_PATH"])
            except Exception:
                app.logger.exception("Eslatmalar xatosi")
            time.sleep(60)

    threading.Thread(target=loop, name="navbatchi-scheduler", daemon=True).start()

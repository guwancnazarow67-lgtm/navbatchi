"""SQLite bilan ishlash."""
import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS admins (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS qr_tokens (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    token      TEXT NOT NULL UNIQUE,
    label      TEXT NOT NULL,
    active     INTEGER NOT NULL DEFAULT 1,
    expires_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name     TEXT NOT NULL,
    last_name      TEXT NOT NULL,
    phone          TEXT NOT NULL DEFAULT '',
    note           TEXT NOT NULL DEFAULT '',
    token_hash     TEXT UNIQUE,
    qr_id          INTEGER REFERENCES qr_tokens(id) ON DELETE SET NULL,
    notify_enabled INTEGER NOT NULL DEFAULT 0,
    notify_asked   INTEGER NOT NULL DEFAULT 0,
    active         INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    last_login     TEXT
);

CREATE TABLE IF NOT EXISTS qr_scans (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    qr_id      INTEGER NOT NULL REFERENCES qr_tokens(id) ON DELETE CASCADE,
    user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
    kind       TEXT NOT NULL DEFAULT 'register',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS duties (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    duty_date  TEXT NOT NULL,
    note       TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id, duty_date)
);
CREATE INDEX IF NOT EXISTS idx_duties_date ON duties(duty_date);

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint   TEXT NOT NULL UNIQUE,
    p256dh     TEXT NOT NULL,
    auth       TEXT NOT NULL,
    user_agent TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS notifications (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind       TEXT NOT NULL,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    ref_date   TEXT,
    pushed     INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    read_at    TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_notif_ref
    ON notifications(user_id, kind, ref_date) WHERE ref_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id, created_at);

CREATE TABLE IF NOT EXISTS login_attempts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ident      TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_attempts ON login_attempts(ident, created_at);
"""


def connect(path):
    conn = sqlite3.connect(str(path), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DB_PATH"])
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(path):
    conn = connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
from werkzeug.security import generate_password_hash
from config import settings


def ensure_default_admin():
    username = (settings.ADMIN_USERNAME or "admin").strip().lower()
    password = settings.ADMIN_PASSWORD
    if len(username) < 3 or not password or len(password) < 8:
        return

    init_db(settings.DB_PATH)
    conn = connect(settings.DB_PATH)
    try:
        row = conn.execute("SELECT id FROM admins WHERE username = ?", (username,)).fetchone()
        hashed = generate_password_hash(password)
        if row:
            conn.execute("UPDATE admins SET password_hash = ? WHERE id = ?", (hashed, row["id"]))
        else:
            conn.execute("INSERT INTO admins(username, password_hash) VALUES (?, ?)", (username, hashed))
        conn.commit()
    finally:
        conn.close()

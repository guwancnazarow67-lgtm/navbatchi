"""NAVBATCHI sozlamalari.

Sozlamalar .env faylidan yoki muhit o'zgaruvchilaridan o'qiladi.
SECRET_KEY va VAPID kalitlari ko'rsatilmasa, birinchi ishga tushishda
avtomatik yaratilib, data/secrets.json fayliga saqlanadi.
"""
import base64
import json
import os
import secrets
from datetime import timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _generate_vapid():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    key = ec.generate_private_key(ec.SECP256R1())
    private_raw = key.private_numbers().private_value.to_bytes(32, "big")
    public_raw = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return _b64url(private_raw), _b64url(public_raw)


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(int(default))).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    def __init__(self):
        self.DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.DB_PATH = self.DATA_DIR / "navbatchi.db"

        self.BASE_URL = os.getenv("BASE_URL", "").strip().rstrip("/")
        self.COOKIE_SECURE = _env_bool("COOKIE_SECURE", self.BASE_URL.startswith("https://"))
        self.BEHIND_PROXY = _env_bool("BEHIND_PROXY", False)
        self.NOTIFY_HOUR = int(os.getenv("NOTIFY_HOUR", "8"))
        self.DISABLE_SCHEDULER = _env_bool("DISABLE_SCHEDULER", False)
        self.VAPID_SUBJECT = os.getenv("VAPID_SUBJECT", "mailto:admin@example.com")
        self.ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "").strip().lower()
        self.ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

        # --- avtomatik yaratiladigan maxfiy qiymatlar ---
        store_path = self.DATA_DIR / "secrets.json"
        store = {}
        if store_path.exists():
            try:
                store = json.loads(store_path.read_text(encoding="utf-8"))
            except Exception:
                store = {}
        changed = False

        self.SECRET_KEY = os.getenv("SECRET_KEY") or store.get("SECRET_KEY")
        if not self.SECRET_KEY:
            self.SECRET_KEY = secrets.token_hex(32)
            store["SECRET_KEY"] = self.SECRET_KEY
            changed = True

        priv = os.getenv("VAPID_PRIVATE_KEY") or store.get("VAPID_PRIVATE_KEY")
        pub = os.getenv("VAPID_PUBLIC_KEY") or store.get("VAPID_PUBLIC_KEY")
        if not priv or not pub:
            priv, pub = _generate_vapid()
            store["VAPID_PRIVATE_KEY"], store["VAPID_PUBLIC_KEY"] = priv, pub
            changed = True
        self.VAPID_PRIVATE_KEY, self.VAPID_PUBLIC_KEY = priv, pub

        if changed:
            store_path.write_text(json.dumps(store, indent=2), encoding="utf-8")
            try:
                os.chmod(store_path, 0o600)
            except OSError:
                pass

        # --- vaqt zonasi ---
        tz_name = os.getenv("TIMEZONE", "Asia/Tashkent")
        try:
            from zoneinfo import ZoneInfo

            self.TZ = ZoneInfo(tz_name)
        except Exception:
            self.TZ = timezone(timedelta(hours=5))  # Toshkent (UTC+5)


settings = Settings()

from app import app  # gunicorn wsgi:app
from db import ensure_default_admin

ensure_default_admin()

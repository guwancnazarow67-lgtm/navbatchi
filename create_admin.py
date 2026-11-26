"""Administrator hisobini yaratish yoki parolini almashtirish.

Ishlatish:  python create_admin.py
"""
import getpass
import sys

from werkzeug.security import generate_password_hash

import db as dbm
from config import settings


def main():
    dbm.init_db(settings.DB_PATH)
    username = input("Administrator logini: ").strip().lower()
    if len(username) < 3:
        sys.exit("Login kamida 3 ta belgidan iborat bo'lsin.")
    password = getpass.getpass("Parol (kamida 8 ta belgi): ")
    if len(password) < 8:
        sys.exit("Parol kamida 8 ta belgidan iborat bo'lsin.")
    if password != getpass.getpass("Parolni qayta kiriting: "):
        sys.exit("Parollar mos kelmadi.")

    conn = dbm.connect(settings.DB_PATH)
    try:
        hashed = generate_password_hash(password)
        row = conn.execute("SELECT id FROM admins WHERE username = ?", (username,)).fetchone()
        if row:
            conn.execute("UPDATE admins SET password_hash = ? WHERE id = ?", (hashed, row["id"]))
            print(f"'{username}' administratorining paroli yangilandi.")
        else:
            conn.execute("INSERT INTO admins(username, password_hash) VALUES (?, ?)", (username, hashed))
            print(f"Administrator '{username}' yaratildi.")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()

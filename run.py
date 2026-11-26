"""Dasturni ishga tushirish (Windows va Linux uchun)."""
import os

from app import app

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    try:
        from waitress import serve

        print(f"NAVBATCHI ishga tushdi: http://{host}:{port}")
        serve(app, host=host, port=port, threads=4)
    except ImportError:
        app.run(host=host, port=port, debug=False)

"""Yordamchi funksiyalar: sana va vaqt (o'zbekcha)."""
from datetime import date, datetime, timezone

from config import settings

UZ_MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul",
             "avgust", "sentyabr", "oktyabr", "noyabr", "dekabr"]
UZ_DAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]


def now():
    return datetime.now(settings.TZ)


def today() -> date:
    return now().date()


def parse_date(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def fmt_date(d) -> str:
    if isinstance(d, str):
        d = parse_date(d)
    if not d:
        return ""
    return f"{d.day}-{UZ_MONTHS[d.month - 1]}, {d.year}"


def weekday(d) -> str:
    if isinstance(d, str):
        d = parse_date(d)
    return UZ_DAYS[d.weekday()] if d else ""


def fmt_dt(value) -> str:
    """Bazadagi UTC vaqtni (YYYY-MM-DD HH:MM:SS) mahalliy vaqtga o'tkazadi."""
    if not value:
        return ""
    try:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return str(value)
    dt = dt.astimezone(settings.TZ)
    return f"{dt.day}-{UZ_MONTHS[dt.month - 1]} {dt.year}, {dt:%H:%M}"


def days_text(n: int) -> str:
    if n == 0:
        return "Bugun"
    if n == 1:
        return "Ertaga"
    if n > 1:
        return f"{n} kundan keyin"
    if n == -1:
        return "Kecha"
    return f"{-n} kun oldin"

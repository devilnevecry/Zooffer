from __future__ import annotations

import re
import unicodedata
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s\-()]{8,}\d)")
_URL_RE = re.compile(
    r"(?:https?://|www\.|t\.me/|telegram\.me/|vk\.com/|wa\.me/|viber://|@[A-Za-z0-9_]{4,})",
    re.IGNORECASE,
)
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
_NAME_ALLOWED_RE = re.compile(r"^[А-Яа-яЁёA-Za-z][А-Яа-яЁёA-Za-z '\-]{0,39}$")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

TRANSLIT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def utcnow() -> datetime:
    return datetime.now(UTC)


def quota_date(now: datetime | None = None, tz: str = "Europe/Moscow") -> date:
    current = now or utcnow()
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(ZoneInfo(tz)).date()


def next_quota_reset(now: datetime | None = None, tz: str = "Europe/Moscow") -> datetime:
    current = now or utcnow()
    local = current.astimezone(ZoneInfo(tz))
    next_day = local.date() + timedelta(days=1)
    local_midnight = datetime.combine(next_day, time(0, 0), tzinfo=ZoneInfo(tz))
    return local_midnight.astimezone(UTC)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_whitespace(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    value = _CONTROL_RE.sub("", value)
    return re.sub(r"\s+", " ", value).strip()


def validate_display_name(value: str, *, field: str = "Имя") -> str:
    cleaned = normalize_whitespace(value)
    if not cleaned:
        raise ValueError(f"{field}: укажите имя")
    if not _NAME_ALLOWED_RE.match(cleaned):
        raise ValueError(
            f"{field}: используйте только буквы, пробел, дефис или апостроф (до 40 символов)"
        )
    if contains_contact_info(cleaned):
        raise ValueError(f"{field}: контакты нельзя указывать в имени")
    return cleaned


def contains_contact_info(text: str) -> bool:
    if not text:
        return False
    if _EMAIL_RE.search(text) or _PHONE_RE.search(text) or _URL_RE.search(text):
        return True
    return bool(_IBAN_RE.search(text))


def find_contact_matches(text: str) -> list[str]:
    found: list[str] = []
    if _EMAIL_RE.search(text):
        found.append("email")
    if _PHONE_RE.search(text):
        found.append("phone")
    if _URL_RE.search(text):
        found.append("link")
    return found


def strip_control_chars(value: str) -> str:
    return _CONTROL_RE.sub("", value)


def slugify(value: str, *, max_length: int = 120) -> str:
    lowered = value.strip().lower()
    transliterated = "".join(TRANSLIT.get(ch, ch) for ch in lowered)
    ascii_value = unicodedata.normalize("NFKD", transliterated).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    if not slug:
        slug = "listing"
    return slug[:max_length].strip("-")


def age_years(birth_date: date | None, today: date | None = None) -> int | None:
    if not birth_date:
        return None
    current = today or utcnow().date()
    years = current.year - birth_date.year
    if (current.month, current.day) < (birth_date.month, birth_date.day):
        years -= 1
    return max(years, 0)

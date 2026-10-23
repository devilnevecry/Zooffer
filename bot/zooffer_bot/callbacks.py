from __future__ import annotations

import base64
import hashlib
import hmac

from zooffer.config import settings

VERSION = "v1"
SIGNATURE_BYTES = 9
MAX_CALLBACK_BYTES = 64


def _secret() -> bytes:
    return settings.session_secret.encode("utf-8")


def _sign(payload: str) -> str:
    digest = hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest[:SIGNATURE_BYTES]).decode().rstrip("=")


def pack(*parts: str) -> str:
    """Build a signed, versioned callback payload.

    Telegram rejects callback data longer than 64 bytes. Raise early instead of
    silently producing a keyboard that the API will reject at runtime.
    """
    payload = ":".join(parts)
    value = f"{VERSION}:{payload}:{_sign(payload)}"
    if len(value.encode("utf-8")) > MAX_CALLBACK_BYTES:
        raise ValueError("callback data exceeds Telegram's 64-byte limit")
    return value


def unpack(value: str | None, expected_parts: int) -> tuple[str, ...] | None:
    if not value or len(value.encode("utf-8")) > MAX_CALLBACK_BYTES:
        return None
    pieces = value.split(":")
    if len(pieces) != expected_parts + 2 or pieces[0] != VERSION:
        return None
    payload = ":".join(pieces[1:-1])
    if not hmac.compare_digest(pieces[-1], _sign(payload)):
        return None
    return tuple(pieces[1:-1])


def prefix(name: str) -> str:
    """Return the signed-data prefix used by aiogram ``F.data.startswith`` filters."""
    return f"{VERSION}:{name}"

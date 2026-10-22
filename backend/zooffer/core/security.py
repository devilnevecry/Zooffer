"""Cryptographic primitives: password hashing, tokens, encryption, Telegram signatures."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from zooffer.config import settings

# OWASP-recommended argon2id parameters (19 MiB, t=2, p=1) with a 32-byte salt.
_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1, hash_len=32, salt_len=16)

ARGON2_NEEDS_REHASH = _hasher.check_needs_rehash


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def generate_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def hmac_sha256(secret: str, value: str) -> str:
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def hash_session_token(token: str) -> str:
    return hmac_sha256(settings.secret_pepper, f"session:{token}")


def hash_link_token(token: str) -> str:
    return hmac_sha256(settings.secret_pepper, f"link:{token}")


def hash_email(email: str) -> str:
    return hmac_sha256(settings.secret_pepper, f"email:{email.strip().lower()}")


def hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    return hmac_sha256(settings.secret_pepper, f"ip:{ip}")[:32]


def constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def csrf_token_for(session_token: str) -> str:
    """Deterministic per-session CSRF token; the session cookie is already secret and HttpOnly."""
    digest = hmac_sha256(settings.secret_pepper, f"csrf:{session_token}")
    return base64.urlsafe_b64encode(bytes.fromhex(digest)).decode().rstrip("=")


def verify_csrf(session_token: str, submitted: str | None) -> bool:
    if not submitted:
        return False
    return constant_time_compare(csrf_token_for(session_token), submitted)


# --- Application-level field encryption -------------------------------------------------------


def _encryption_key() -> bytes:
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"zooffer-field-encryption",
        info=b"v1",
    )
    return hkdf.derive(settings.secret_pepper.encode("utf-8"))


def encrypt_value(plaintext: str) -> str:
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(_encryption_key()).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_value(token: str) -> str:
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    nonce, ciphertext = raw[:12], raw[12:]
    return AESGCM(_encryption_key()).decrypt(nonce, ciphertext, None).decode("utf-8")


# --- Telegram validation ----------------------------------------------------------------------
# Sources (checked 2026-10-22):
# https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
# https://core.telegram.org/widgets/login#checking-authorization
# Telegram Login:   secret_key = SHA256(bot_token); HMAC_SHA256(data_check_string, secret_key)
# Mini App initData: secret_key = HMAC_SHA256(bot_token, "WebAppData")


class TelegramAuthError(ValueError):
    pass


def _data_check_string(fields: dict[str, str]) -> str:
    return "\n".join(f"{k}={fields[k]}" for k in sorted(fields) if k != "hash")


def verify_telegram_login(
    payload: dict[str, Any], bot_token: str, *, max_age_seconds: int = 300, now: int | None = None
) -> dict[str, Any]:
    """Validate a Telegram Login Widget payload. Returns the parsed payload on success."""
    if not bot_token:
        raise TelegramAuthError("telegram login is not configured")
    fields = {k: str(v) for k, v in payload.items() if v is not None}
    received_hash = fields.pop("hash", "")
    if not received_hash:
        raise TelegramAuthError("missing hash")
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    expected = hmac.new(
        secret_key, _data_check_string(fields).encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise TelegramAuthError("invalid signature")
    auth_date = int(fields.get("auth_date", "0"))
    current = int(time.time()) if now is None else now
    if auth_date <= 0 or abs(current - auth_date) > max_age_seconds:
        raise TelegramAuthError("stale authentication data")
    if not fields.get("id", "").isdigit():
        raise TelegramAuthError("invalid telegram id")
    return fields


def verify_telegram_init_data(
    init_data: str, bot_token: str, *, max_age_seconds: int = 300, now: int | None = None
) -> dict[str, Any]:
    """Validate Mini App initData query string. Never trust initDataUnsafe."""
    if not bot_token:
        raise TelegramAuthError("telegram mini app is not configured")
    from urllib.parse import parse_qsl

    pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    received_hash = pairs.pop("hash", "")
    if not received_hash:
        raise TelegramAuthError("missing hash")
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    expected = hmac.new(
        secret_key, _data_check_string(pairs).encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise TelegramAuthError("invalid signature")
    auth_date = int(pairs.get("auth_date", "0"))
    current = int(time.time()) if now is None else now
    if auth_date <= 0 or abs(current - auth_date) > max_age_seconds:
        raise TelegramAuthError("stale authentication data")
    try:
        user = json.loads(pairs.get("user", "{}"))
    except json.JSONDecodeError as exc:
        raise TelegramAuthError("invalid user payload") from exc
    if not isinstance(user, dict) or not str(user.get("id", "")).isdigit():
        raise TelegramAuthError("invalid telegram user")
    return {"user": user, "auth_date": auth_date, "query_id": pairs.get("query_id")}

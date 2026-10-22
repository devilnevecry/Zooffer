"""Encrypted column type for sensitive personal fields."""

from __future__ import annotations

from typing import Any

from sqlalchemy import String, Text
from sqlalchemy.types import TypeDecorator

from zooffer.core.security import decrypt_value, encrypt_value


class EncryptedText(TypeDecorator[str]):
    """Application-level AES-GCM encryption with authenticated ciphertext.

    Values are stored as base64 text and are never searchable by content; lookups use a
    separate blind index (HMAC) where equality is required (e.g. email).
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        return encrypt_value(str(value))

    def process_result_value(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        return decrypt_value(str(value))


class BlindIndex(String):
    """Marker type documenting that a column is an HMAC blind index, not raw data."""

    cache_ok = True

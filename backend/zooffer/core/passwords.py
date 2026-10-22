from __future__ import annotations

import hashlib

import httpx

from zooffer.config import settings

# Small offline baseline. The authoritative check is the k-anonymity HIBP range API.
_COMMON = {
    "1234567890",
    "12345678",
    "qwerty123",
    "password",
    "password1",
    "qwertyuiop",
    "123456789",
    "iloveyou",
    "admin123",
    "welcome1",
    "letmein123",
    "qwerty12345",
    "1111111111",
    "0000000000",
    "superman",
    "sunshine",
    "princess",
    "football",
    "charlie1",
    "aa123456",
    "qwerty1234",
    "1q2w3e4r5t",
    "qazwsxedc",
    "password123",
    "zooffer123",
    "pochemuchka",
}


async def is_breached_password(password: str) -> bool:
    if password.lower() in _COMMON:
        return True
    if not settings.hibp_enabled:
        return False
    digest = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()  # noqa: S324 (HIBP protocol)
    prefix, suffix = digest[:5], digest[5:]
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                headers={"Add-Padding": "true", "User-Agent": "Zooffer password check"},
            )
            response.raise_for_status()
    except httpx.HTTPError:
        # Availability over strictness: never block registration because HIBP is down.
        return False
    for line in response.text.splitlines():
        candidate, _, count = line.partition(":")
        if candidate == suffix and count.strip().isdigit() and int(count) > 0:
            return True
    return False

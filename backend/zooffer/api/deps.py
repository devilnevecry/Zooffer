from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated
from urllib.parse import urlparse

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from zooffer.config import settings
from zooffer.core.enums import UserRole
from zooffer.core.errors import ForbiddenError, UnauthorizedError
from zooffer.core.security import csrf_token_for, hash_ip, verify_csrf
from zooffer.db.session import get_db
from zooffer.services.auth_service import AuthContext, resolve_session

DbSession = Annotated[AsyncSession, Depends(get_db)]

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def client_ip(request: Request) -> str | None:
    if settings.environment in {"dev", "test"} and request.client:
        return request.client.host
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def request_ip_hash(request: Request) -> str | None:
    return hash_ip(client_ip(request))


async def get_auth_optional(request: Request, db: DbSession) -> AuthContext | None:
    token = request.cookies.get(settings.cookie_name)
    if not token:
        return None
    return await resolve_session(db, token)


async def require_user(
    request: Request, auth: Annotated[AuthContext | None, Depends(get_auth_optional)]
) -> AuthContext:
    if auth is None:
        raise UnauthorizedError("Требуется вход в аккаунт", code="authentication_required")
    return auth


def check_origin(request: Request) -> None:
    if request.method not in MUTATING_METHODS:
        return
    origin = request.headers.get("Origin")
    if not origin:
        return
    allowed = {
        urlparse(settings.app_base_url).netloc,
        urlparse(settings.api_base_url).netloc,
        "localhost:3000",
        "localhost:8000",
        "127.0.0.1:3000",
        "127.0.0.1:8000",
        "testserver",
    }
    if urlparse(origin).netloc not in allowed:
        raise ForbiddenError("Запрос отклонён: неверный источник", code="origin_rejected")


async def require_csrf(request: Request, auth: AuthContext) -> None:
    check_origin(request)
    if request.method not in MUTATING_METHODS:
        return
    submitted = request.headers.get(settings.csrf_header)
    if not verify_csrf(auth.token, submitted):
        raise ForbiddenError(
            "Не удалось проверить защитный токен. Обновите страницу и попробуйте снова.",
            code="csrf_failed",
        )


async def require_user_csrf(
    request: Request, auth: Annotated[AuthContext, Depends(require_user)]
) -> AuthContext:
    await require_csrf(request, auth)
    return auth


def permission_required(permission: str) -> Callable[..., Awaitable[AuthContext]]:
    """Central RBAC dependency. Every admin endpoint declares a permission here."""

    async def dependency(auth: Annotated[AuthContext, Depends(require_user_csrf)]) -> AuthContext:
        roles = {
            "admin:dashboard": {UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUPERADMIN},
            "moderation:read": {UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUPERADMIN},
            "moderation:write": {UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUPERADMIN},
            "users:read": {UserRole.ADMIN, UserRole.SUPERADMIN},
            "users:write": {UserRole.ADMIN, UserRole.SUPERADMIN},
            "payments:read": {UserRole.ADMIN, UserRole.SUPERADMIN},
            "payments:write": {UserRole.SUPERADMIN},
            "settings:write": {UserRole.SUPERADMIN},
            "partners:write": {UserRole.ADMIN, UserRole.SUPERADMIN},
            "legal:write": {UserRole.SUPERADMIN},
        }
        allowed = roles.get(permission, {UserRole.SUPERADMIN})
        if auth.user.role not in {role.value for role in allowed}:
            raise ForbiddenError("Недостаточно прав", code="permission_denied")
        if not (auth.user.mfa_enabled and auth.session.mfa_verified_at):
            raise ForbiddenError(
                "Для доступа к панели включите двухфакторную аутентификацию", code="mfa_required"
            )
        return auth

    return dependency


def auth_csrf_token(auth: AuthContext) -> str:
    return csrf_token_for(auth.token)


CurrentAuth = Annotated[AuthContext, Depends(require_user_csrf)]
OptionalAuth = Annotated[AuthContext | None, Depends(get_auth_optional)]

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select

from zooffer.api.cookies import clear_session_cookie, set_session_cookie
from zooffer.api.deps import (
    DbSession,
    auth_csrf_token,
    request_ip_hash,
    require_user,
    require_user_csrf,
)
from zooffer.config import settings
from zooffer.core.errors import UnauthorizedError
from zooffer.core.logging import get_logger
from zooffer.core.rate_limit import limiter
from zooffer.core.security import hash_email
from zooffer.db.models import UserSession
from zooffer.schemas.auth import (
    AuthResponse,
    EmailVerifyRequest,
    LinkTokenResponse,
    LoginRequest,
    MeResponse,
    MessageResponse,
    MfaConfirmRequest,
    MfaSetupResponse,
    MiniAppAuthRequest,
    OkResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    SessionListResponse,
    SessionView,
    TelegramLoginRequest,
    UserSelfView,
)
from zooffer.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger("zooffer.auth")


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    payload: RegisterRequest, request: Request, response: Response, db: DbSession
) -> AuthResponse:
    ip_hash = request_ip_hash(request)
    await limiter.hit(f"register:{ip_hash}", limit=5, window_seconds=3600)
    user = await auth_service.create_user_with_password(
        db,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        city_id=payload.city_id,
        accepted_terms=payload.accepted_terms,
        accepted_privacy=payload.accepted_privacy,
        marketing_opt_in=payload.marketing_opt_in,
        ip_hash=ip_hash,
    )
    bundle = await auth_service.create_session(
        db, user, ip_hash=ip_hash, user_agent=request.headers.get("User-Agent")
    )
    set_session_cookie(response, bundle.token)
    try:
        await auth_service.issue_email_verification(db, user, payload.email)
    except Exception:
        logger.exception("email_verification_send_failed")
    view = await auth_service.get_self_view(db, user)
    return AuthResponse(user=view, csrf_token=bundle.csrf_token)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest, request: Request, response: Response, db: DbSession
) -> AuthResponse:
    ip_hash = request_ip_hash(request)
    await limiter.hit(f"login:ip:{ip_hash}", limit=15, window_seconds=300)
    await limiter.hit(f"login:email:{hash_email(payload.email)}", limit=8, window_seconds=300)
    user = await auth_service.authenticate_password(
        db, email=payload.email, password=payload.password, mfa_code=payload.mfa_code
    )
    bundle = await auth_service.create_session(
        db, user, ip_hash=ip_hash, user_agent=request.headers.get("User-Agent")
    )
    set_session_cookie(response, bundle.token)
    view = await auth_service.get_self_view(db, user)
    return AuthResponse(user=view, csrf_token=bundle.csrf_token)


@router.post("/logout", response_model=OkResponse)
async def logout(
    response: Response,
    auth: Annotated[auth_service.AuthContext, Depends(require_user_csrf)],
    db: DbSession,
) -> OkResponse:
    await auth_service.revoke_session(db, auth.session)
    clear_session_cookie(response)
    return OkResponse()


@router.get("/me", response_model=MeResponse)
async def me(
    auth: Annotated[auth_service.AuthContext, Depends(require_user)], db: DbSession
) -> MeResponse:
    view = await auth_service.get_self_view(db, auth.user)
    return MeResponse(user=view, csrf_token=auth_csrf_token(auth))


@router.post("/telegram", response_model=AuthResponse)
async def telegram_login(
    payload: TelegramLoginRequest, request: Request, response: Response, db: DbSession
) -> AuthResponse:
    ip_hash = request_ip_hash(request)
    await limiter.hit(f"tglogin:{ip_hash}", limit=20, window_seconds=300)
    user = await auth_service.authenticate_telegram_login(
        db,
        {
            key: value
            for key, value in payload.model_dump().items()
            if value not in ("", None) or key in {"id", "auth_date", "hash"}
        },
    )
    bundle = await auth_service.create_session(db, user, ip_hash=ip_hash)
    set_session_cookie(response, bundle.token)
    view = await auth_service.get_self_view(db, user)
    return AuthResponse(user=view, csrf_token=bundle.csrf_token)


@router.post("/telegram/miniapp", response_model=AuthResponse)
async def telegram_miniapp_login(
    payload: MiniAppAuthRequest, request: Request, response: Response, db: DbSession
) -> AuthResponse:
    ip_hash = request_ip_hash(request)
    await limiter.hit(f"tgapp:{ip_hash}", limit=30, window_seconds=300)
    user = await auth_service.authenticate_telegram_init_data(db, payload.init_data)
    bundle = await auth_service.create_session(db, user, ip_hash=ip_hash)
    set_session_cookie(response, bundle.token)
    view = await auth_service.get_self_view(db, user)
    return AuthResponse(user=view, csrf_token=bundle.csrf_token)


@router.post("/telegram/link-token", response_model=LinkTokenResponse)
async def create_link_token(
    auth: Annotated[auth_service.AuthContext, Depends(require_user_csrf)], db: DbSession
) -> LinkTokenResponse:
    raw, expires_at = await auth_service.create_link_token(db, auth.user.id)
    username = settings.telegram_bot_username
    return LinkTokenResponse(
        token=raw,
        expires_at=expires_at,
        deep_link=f"https://t.me/{username}?start=link_{raw}" if username else f"link_{raw}",
    )


@router.post("/password/reset/request", response_model=MessageResponse)
async def password_reset_request(
    payload: PasswordResetRequest, request: Request, db: DbSession
) -> MessageResponse:
    ip_hash = request_ip_hash(request)
    await limiter.hit(f"reset:{ip_hash}", limit=5, window_seconds=3600)
    await auth_service.request_password_reset(db, payload.email)
    return MessageResponse(
        message="Если такой адрес зарегистрирован, мы отправили письмо с инструкцией."
    )


@router.post("/password/reset/confirm", response_model=OkResponse)
async def password_reset_confirm(payload: PasswordResetConfirm, db: DbSession) -> OkResponse:
    await auth_service.reset_password(
        db, raw_token=payload.token, new_password=payload.new_password
    )
    return OkResponse()


@router.post("/email/verify", response_model=OkResponse)
async def email_verify(payload: EmailVerifyRequest, db: DbSession) -> OkResponse:
    await auth_service.verify_email(db, payload.token)
    return OkResponse()


@router.post("/email/resend", response_model=MessageResponse)
async def email_resend(
    auth: Annotated[auth_service.AuthContext, Depends(require_user_csrf)], db: DbSession
) -> MessageResponse:
    if auth.user.email_verified_at is not None:
        return MessageResponse(message="Почта уже подтверждена")
    from zooffer.db.models import UserPrivateData

    private = await db.get(UserPrivateData, auth.user.id)
    if private and private.email_encrypted:
        await auth_service.issue_email_verification(db, auth.user, private.email_encrypted)
    return MessageResponse(message="Письмо отправлено")


@router.patch("/profile", response_model=UserSelfView)
async def update_profile(
    payload: ProfileUpdateRequest,
    auth: Annotated[auth_service.AuthContext, Depends(require_user_csrf)],
    db: DbSession,
) -> UserSelfView:
    user = await auth_service.update_profile(
        db,
        auth.user,
        first_name=payload.first_name,
        last_name=payload.last_name,
        city_id=payload.city_id,
    )
    return await auth_service.get_self_view(db, user)


@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def mfa_setup(
    auth: Annotated[auth_service.AuthContext, Depends(require_user_csrf)], db: DbSession
) -> MfaSetupResponse:
    await limiter.hit(f"mfa-setup:{auth.user.id}", limit=5, window_seconds=3600)
    secret, uri = await auth_service.setup_totp(db, auth.user)
    return MfaSetupResponse(secret=secret, otpauth_url=uri)


@router.post("/mfa/confirm", response_model=OkResponse)
async def mfa_confirm(
    payload: MfaConfirmRequest,
    auth: Annotated[auth_service.AuthContext, Depends(require_user_csrf)],
    db: DbSession,
) -> OkResponse:
    await limiter.hit(f"mfa-confirm:{auth.user.id}", limit=10, window_seconds=3600)
    await auth_service.confirm_totp(db, auth.user, payload.code)
    auth.session.mfa_verified_at = auth_service.utcnow()
    await db.commit()
    return OkResponse()


@router.post("/mfa/disable", response_model=OkResponse)
async def mfa_disable(
    payload: MfaConfirmRequest,
    auth: Annotated[auth_service.AuthContext, Depends(require_user_csrf)],
    db: DbSession,
) -> OkResponse:
    await limiter.hit(f"mfa-disable:{auth.user.id}", limit=10, window_seconds=3600)
    await auth_service.disable_totp(db, auth.user, payload.code)
    return OkResponse()


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    auth: Annotated[auth_service.AuthContext, Depends(require_user)], db: DbSession
) -> SessionListResponse:
    rows = (
        await db.scalars(
            select(UserSession)
            .where(UserSession.user_id == auth.user.id, UserSession.revoked_at.is_(None))
            .order_by(UserSession.last_seen_at.desc())
        )
    ).all()
    return SessionListResponse(
        items=[
            SessionView(
                id=s.id,
                device_label=s.device_label,
                user_agent=s.user_agent,
                created_at=s.created_at,
                last_seen_at=s.last_seen_at,
                is_current=s.id == auth.session.id,
            )
            for s in rows
        ]
    )


@router.delete("/sessions/{session_id}", response_model=OkResponse)
async def revoke_session_by_id(
    session_id: str,
    auth: Annotated[auth_service.AuthContext, Depends(require_user_csrf)],
    db: DbSession,
) -> OkResponse:
    session = await db.get(UserSession, session_id)
    if session is None or session.user_id != auth.user.id:
        raise UnauthorizedError("Сессия не найдена", code="session_not_found")
    await auth_service.revoke_session(db, session, "user_revoked")
    return OkResponse()


@router.post("/sessions/revoke-all", response_model=OkResponse)
async def revoke_all(
    response: Response,
    auth: Annotated[auth_service.AuthContext, Depends(require_user_csrf)],
    db: DbSession,
) -> OkResponse:
    await auth_service.revoke_all_sessions(db, auth.user.id, "user_revoked_all")
    clear_session_cookie(response)
    return OkResponse()

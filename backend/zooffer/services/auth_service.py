from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pyotp
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from zooffer.config import settings
from zooffer.core.enums import AuthProvider, UserRole, UserStatus
from zooffer.core.errors import ConflictError, ForbiddenError, UnauthorizedError, ValidationAppError
from zooffer.core.passwords import is_breached_password
from zooffer.core.security import (
    TelegramAuthError,
    csrf_token_for,
    generate_token,
    hash_email,
    hash_link_token,
    hash_password,
    hash_session_token,
    verify_password,
    verify_telegram_init_data,
    verify_telegram_login,
)
from zooffer.core.utils import normalize_email, utcnow
from zooffer.db.models import (
    AccountLinkToken,
    AuthIdentity,
    AuthToken,
    Consent,
    Credential,
    MfaFactor,
    Profile,
    User,
    UserPrivateData,
    UserSession,
)
from zooffer.schemas.auth import UserSelfView
from zooffer.services.email import get_email_sender

TERMS_VERSION = "2026-10-22"
PRIVACY_VERSION = "2026-10-22"
CONSENT_VERSION = "2026-10-22"
STAFF_ROLES = {UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUPERADMIN}


@dataclass(slots=True)
class SessionBundle:
    user: User
    token: str
    csrf_token: str
    session: UserSession


@dataclass(slots=True)
class AuthContext:
    user: User
    session: UserSession
    token: str


class DummyHash:
    """Constant-ish work factor for login with unknown emails to reduce timing leakage."""

    _hash: str | None = None

    @classmethod
    def get(cls) -> str:
        if cls._hash is None:
            cls._hash = hash_password(generate_token(24))
        return cls._hash


async def _ensure_email_available(db: AsyncSession, email: str) -> None:
    exists = await db.scalar(
        select(UserPrivateData.user_id).where(UserPrivateData.email_hash == hash_email(email))
    )
    if exists:
        raise ConflictError(
            "Не удалось создать аккаунт. Войдите или восстановите пароль.",
            code="registration_unavailable",
        )


async def create_user_with_password(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    first_name: str,
    last_name: str | None,
    city_id: int | None,
    accepted_terms: bool,
    accepted_privacy: bool,
    marketing_opt_in: bool,
    channel: str = "web",
    ip_hash: str | None = None,
) -> User:
    if not accepted_terms or not accepted_privacy:
        raise ValidationAppError("Для регистрации примите условия и политику конфиденциальности")
    if await is_breached_password(password):
        raise ValidationAppError(
            "Этот пароль встречался в утечках. Выберите другой пароль.", code="weak_password"
        )
    email = normalize_email(email)
    await _ensure_email_available(db, email)

    user = User(public_id=uuid4(), status=UserStatus.ACTIVE, role=UserRole.USER)
    db.add(user)
    await db.flush()
    db.add(
        Profile(
            user_id=user.id,
            public_first_name=first_name,
            public_last_name=last_name,
            city_id=city_id,
        )
    )
    db.add(
        UserPrivateData(
            user_id=user.id,
            email_encrypted=email,
            email_hash=hash_email(email),
        )
    )
    db.add(Credential(user_id=user.id, password_hash=hash_password(password)))
    db.add(
        Consent(
            user_id=user.id,
            document="terms",
            version=TERMS_VERSION,
            channel=channel,
            ip_hash=ip_hash,
        )
    )
    db.add(
        Consent(
            user_id=user.id,
            document="privacy",
            version=PRIVACY_VERSION,
            channel=channel,
            ip_hash=ip_hash,
        )
    )
    if marketing_opt_in:
        db.add(
            Consent(
                user_id=user.id,
                document="marketing",
                version=CONSENT_VERSION,
                channel=channel,
                ip_hash=ip_hash,
            )
        )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(
            "Не удалось создать аккаунт. Войдите или восстановите пароль.",
            code="registration_unavailable",
        ) from exc
    await db.refresh(user)
    return user


async def find_user_by_email(db: AsyncSession, email: str) -> User | None:
    row = await db.execute(
        select(User)
        .join(UserPrivateData, UserPrivateData.user_id == User.id)
        .where(UserPrivateData.email_hash == hash_email(email))
    )
    return row.scalar_one_or_none()


async def authenticate_password(
    db: AsyncSession, *, email: str, password: str, mfa_code: str | None = None
) -> User:
    user = await find_user_by_email(db, email)
    if user is None:
        verify_password(password, DummyHash.get())
        raise UnauthorizedError("Неверная почта или пароль", code="invalid_credentials")
    credential = await db.get(Credential, user.id)
    if credential is None or not verify_password(password, credential.password_hash):
        raise UnauthorizedError("Неверная почта или пароль", code="invalid_credentials")
    if user.status != UserStatus.ACTIVE:
        raise ForbiddenError("Аккаунт недоступен. Обратитесь в поддержку.", code="account_inactive")
    if user.mfa_enabled:
        if not mfa_code:
            raise UnauthorizedError("Введите код двухфакторной аутентификации", code="mfa_required")
        if not await verify_totp(db, user.id, mfa_code):
            raise UnauthorizedError("Неверный код подтверждения", code="invalid_mfa")
    return user


async def verify_totp(db: AsyncSession, user_id: UUID, code: str) -> bool:
    factor = await db.scalar(
        select(MfaFactor).where(MfaFactor.user_id == user_id, MfaFactor.confirmed_at.is_not(None))
    )
    if factor is None:
        return False
    totp = pyotp.TOTP(factor.secret_encrypted)
    counter = int(datetime.now(UTC).timestamp()) // 30
    if factor.last_used_counter is not None and counter <= factor.last_used_counter:
        return False
    if not totp.verify(code, valid_window=1):
        return False
    factor.last_used_counter = counter
    await db.commit()
    return True


async def setup_totp(db: AsyncSession, user: User) -> tuple[str, str]:
    """Create (or replace an unconfirmed) TOTP factor and return its provisioning URI."""
    confirmed = await db.scalar(
        select(MfaFactor).where(MfaFactor.user_id == user.id, MfaFactor.confirmed_at.is_not(None))
    )
    if confirmed is not None:
        raise ConflictError("Двухфакторная аутентификация уже включена", code="mfa_already_enabled")
    factor = await db.scalar(
        select(MfaFactor).where(MfaFactor.user_id == user.id, MfaFactor.factor_type == "totp")
    )
    secret = pyotp.random_base32()
    if factor is None:
        factor = MfaFactor(
            id=uuid4(),
            user_id=user.id,
            factor_type="totp",
            secret_encrypted=secret,
        )
        db.add(factor)
    else:
        factor.secret_encrypted = secret
        factor.confirmed_at = None
        factor.last_used_counter = None
    await db.commit()
    private = await db.get(UserPrivateData, user.id)
    account_name = (
        private.email_encrypted if private and private.email_encrypted else str(user.public_id)
    )
    uri = pyotp.TOTP(secret).provisioning_uri(name=account_name, issuer_name="Zooffer")
    return secret, uri


async def confirm_totp(db: AsyncSession, user: User, code: str) -> None:
    factor = await db.scalar(
        select(MfaFactor).where(
            MfaFactor.user_id == user.id,
            MfaFactor.factor_type == "totp",
            MfaFactor.confirmed_at.is_(None),
        )
    )
    if factor is None:
        raise ValidationAppError(
            "Сначала создайте секрет двухфакторной аутентификации", code="mfa_not_started"
        )
    if not pyotp.TOTP(factor.secret_encrypted).verify(code.strip(), valid_window=1):
        raise ValidationAppError("Неверный код подтверждения", code="invalid_mfa")
    factor.confirmed_at = utcnow()
    factor.last_used_counter = int(datetime.now(UTC).timestamp()) // 30
    user.mfa_enabled = True
    await db.commit()


async def disable_totp(db: AsyncSession, user: User, code: str) -> None:
    factor = await db.scalar(
        select(MfaFactor).where(
            MfaFactor.user_id == user.id,
            MfaFactor.factor_type == "totp",
            MfaFactor.confirmed_at.is_not(None),
        )
    )
    if factor is None:
        raise ValidationAppError("Двухфакторная аутентификация не включена", code="mfa_not_enabled")
    if not await verify_totp(db, user.id, code):
        raise ValidationAppError("Неверный код подтверждения", code="invalid_mfa")
    await db.delete(factor)
    user.mfa_enabled = False
    await db.commit()


async def create_session(
    db: AsyncSession,
    user: User,
    *,
    ip_hash: str | None = None,
    user_agent: str | None = None,
    device_label: str | None = None,
) -> SessionBundle:
    token = generate_token(32)
    now = utcnow()
    session = UserSession(
        id=uuid4(),
        user_id=user.id,
        token_hash=hash_session_token(token),
        ip_hash=ip_hash,
        user_agent=(user_agent or "")[:255] or None,
        device_label=(device_label or "")[:120] or None,
        last_seen_at=now,
        idle_expires_at=now + timedelta(days=settings.session_idle_days),
        absolute_expires_at=now + timedelta(days=settings.session_absolute_days),
        mfa_verified_at=now if user.mfa_enabled else None,
    )
    db.add(session)
    await db.commit()
    return SessionBundle(user=user, token=token, csrf_token=csrf_token_for(token), session=session)


async def resolve_session(db: AsyncSession, token: str) -> AuthContext | None:
    if not token or len(token) > 200:
        return None
    now = utcnow()
    row = await db.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(
            UserSession.token_hash == hash_session_token(token),
            UserSession.revoked_at.is_(None),
            UserSession.idle_expires_at > now,
            UserSession.absolute_expires_at > now,
            User.status == UserStatus.ACTIVE,
        )
    )
    found = row.first()
    if not found:
        return None
    session, user = found
    if (now - session.last_seen_at).total_seconds() > 60:
        session.last_seen_at = now
        session.idle_expires_at = now + timedelta(days=settings.session_idle_days)
        await db.commit()
    return AuthContext(user=user, session=session, token=token)


async def revoke_session(db: AsyncSession, session: UserSession, reason: str = "logout") -> None:
    session.revoked_at = utcnow()
    session.revoked_reason = reason
    await db.commit()


async def revoke_all_sessions(db: AsyncSession, user_id: UUID, reason: str) -> None:
    await db.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=utcnow(), revoked_reason=reason)
    )
    await db.commit()


async def _get_identity(
    db: AsyncSession, provider: str, provider_user_id: str
) -> AuthIdentity | None:
    return await db.scalar(
        select(AuthIdentity).where(
            AuthIdentity.provider == provider,
            AuthIdentity.provider_user_id == provider_user_id,
        )
    )


async def authenticate_telegram_login(db: AsyncSession, payload: dict[str, object]) -> User:
    try:
        data = verify_telegram_login(
            payload,
            settings.telegram_bot_token,
            max_age_seconds=settings.telegram_auth_max_age_seconds,
        )
    except TelegramAuthError as exc:
        raise UnauthorizedError(
            "Не удалось подтвердить вход через Telegram", code="telegram_invalid"
        ) from exc
    telegram_id = str(data["id"])
    identity = await _get_identity(db, AuthProvider.TELEGRAM, telegram_id)
    if identity:
        user = await db.get(User, identity.user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            raise ForbiddenError("Аккаунт недоступен", code="account_inactive")
        return user
    return await _create_telegram_user(db, telegram_id)


async def authenticate_telegram_init_data(db: AsyncSession, init_data: str) -> User:
    try:
        data = verify_telegram_init_data(
            init_data,
            settings.telegram_bot_token,
            max_age_seconds=settings.telegram_auth_max_age_seconds,
        )
    except TelegramAuthError as exc:
        raise UnauthorizedError(
            "Не удалось подтвердить данные Telegram", code="telegram_invalid"
        ) from exc
    tg_user = data["user"]
    telegram_id = str(tg_user["id"])
    identity = await _get_identity(db, AuthProvider.TELEGRAM, telegram_id)
    if identity:
        user = await db.get(User, identity.user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            raise ForbiddenError("Аккаунт недоступен", code="account_inactive")
        return user
    return await _create_telegram_user(db, telegram_id)


async def _create_telegram_user(db: AsyncSession, telegram_id: str) -> User:
    user = User(public_id=uuid4(), status=UserStatus.ACTIVE, role=UserRole.USER)
    db.add(user)
    await db.flush()
    db.add(Profile(user_id=user.id))
    db.add(UserPrivateData(user_id=user.id))
    db.add(
        AuthIdentity(
            id=uuid4(),
            user_id=user.id,
            provider=AuthProvider.TELEGRAM,
            provider_user_id=telegram_id,
        )
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Не удалось создать аккаунт", code="telegram_conflict") from exc
    await db.refresh(user)
    return user


async def create_telegram_bot_user(
    db: AsyncSession,
    *,
    telegram_id: str,
    public_first_name: str,
    accepted_terms: bool,
    accepted_privacy: bool,
    channel: str = "telegram",
) -> User:
    """Resolve a Telegram identity or create a consented bot-first account.

    Telegram usernames, photos and numeric IDs are never copied into public fields.
    """
    identity = await _get_identity(db, AuthProvider.TELEGRAM, telegram_id)
    if identity is not None:
        user = await db.get(User, identity.user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            raise ForbiddenError("Аккаунт недоступен", code="account_inactive")
        return user
    if not accepted_terms or not accepted_privacy:
        raise ValidationAppError(
            "Для создания аккаунта примите условия и политику конфиденциальности",
            code="consent_required",
        )
    name = public_first_name.strip()
    if not name or len(name) > 60:
        raise ValidationAppError("Укажите имя до 60 символов", code="invalid_name")
    user = User(public_id=uuid4(), status=UserStatus.ACTIVE, role=UserRole.USER)
    db.add(user)
    await db.flush()
    db.add(Profile(user_id=user.id, public_first_name=name))
    db.add(UserPrivateData(user_id=user.id))
    db.add(
        AuthIdentity(
            id=uuid4(),
            user_id=user.id,
            provider=AuthProvider.TELEGRAM,
            provider_user_id=telegram_id,
        )
    )
    db.add(
        Consent(
            user_id=user.id,
            document="terms",
            version=TERMS_VERSION,
            channel=channel,
        )
    )
    db.add(
        Consent(
            user_id=user.id,
            document="privacy",
            version=PRIVACY_VERSION,
            channel=channel,
        )
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Не удалось создать аккаунт", code="telegram_conflict") from exc
    await db.refresh(user)
    return user


async def find_telegram_user(db: AsyncSession, telegram_id: str) -> User | None:
    identity = await _get_identity(db, AuthProvider.TELEGRAM, telegram_id)
    if identity is None:
        return None
    return await db.get(User, identity.user_id)


async def create_link_token(db: AsyncSession, user_id: UUID) -> tuple[str, datetime]:
    raw = generate_token(24)
    expires_at = utcnow() + timedelta(minutes=15)
    db.add(
        AccountLinkToken(
            id=uuid4(),
            user_id=user_id,
            token_hash=hash_link_token(raw),
            expires_at=expires_at,
        )
    )
    await db.commit()
    return raw, expires_at


async def confirm_link_token(db: AsyncSession, *, raw_token: str, telegram_id: str) -> User:
    token = await db.scalar(
        select(AccountLinkToken).where(
            AccountLinkToken.token_hash == hash_link_token(raw_token),
            AccountLinkToken.used_at.is_(None),
            AccountLinkToken.expires_at > utcnow(),
        )
    )
    if token is None:
        raise ValidationAppError(
            "Ссылка для привязки недействительна или истекла", code="link_token_invalid"
        )
    existing = await _get_identity(db, AuthProvider.TELEGRAM, telegram_id)
    if existing and existing.user_id != token.user_id:
        raise ConflictError(
            "Этот Telegram уже привязан к другому аккаунту. "
            "Обратитесь в поддержку для объединения.",
            code="telegram_already_linked",
        )
    if existing is None:
        db.add(
            AuthIdentity(
                id=uuid4(),
                user_id=token.user_id,
                provider=AuthProvider.TELEGRAM,
                provider_user_id=telegram_id,
            )
        )
    token.used_at = utcnow()
    await db.commit()
    user = await db.get(User, token.user_id)
    if user is None:
        raise ValidationAppError("Аккаунт не найден", code="account_missing")
    return user


async def request_password_reset(db: AsyncSession, email: str) -> None:
    """Always succeeds from the caller's perspective (enumeration-resistant)."""
    user = await find_user_by_email(db, email)
    if user is None:
        return
    raw = generate_token(32)
    db.add(
        AuthToken(
            id=uuid4(),
            user_id=user.id,
            purpose="password_reset",
            token_hash=hash_link_token(raw),
            expires_at=utcnow() + timedelta(hours=1),
        )
    )
    await db.commit()
    sender = get_email_sender()
    await sender.send(
        to=email,
        subject="Zooffer — восстановление пароля",
        body=(
            "Чтобы задать новый пароль, откройте ссылку (действует 1 час):\n"
            f"{settings.app_base_url}/auth/reset-password?token={raw}\n\n"
            "Если вы не запрашивали восстановление, просто проигнорируйте письмо."
        ),
    )


async def reset_password(db: AsyncSession, *, raw_token: str, new_password: str) -> None:
    if await is_breached_password(new_password):
        raise ValidationAppError(
            "Этот пароль встречался в утечках. Выберите другой пароль.", code="weak_password"
        )
    token = await db.scalar(
        select(AuthToken).where(
            AuthToken.token_hash == hash_link_token(raw_token),
            AuthToken.purpose == "password_reset",
            AuthToken.used_at.is_(None),
            AuthToken.expires_at > utcnow(),
        )
    )
    if token is None:
        raise ValidationAppError("Ссылка недействительна или истекла", code="token_invalid")
    credential = await db.get(Credential, token.user_id)
    if credential is None:
        raise ValidationAppError("Для аккаунта не настроен пароль", code="password_not_set")
    credential.password_hash = hash_password(new_password)
    credential.password_changed_at = utcnow()
    token.used_at = utcnow()
    await revoke_all_sessions(db, token.user_id, "password_reset")
    await db.commit()


async def issue_email_verification(db: AsyncSession, user: User, email: str) -> None:
    raw = generate_token(32)
    db.add(
        AuthToken(
            id=uuid4(),
            user_id=user.id,
            purpose="email_verify",
            token_hash=hash_link_token(raw),
            expires_at=utcnow() + timedelta(days=2),
        )
    )
    await db.commit()
    sender = get_email_sender()
    await sender.send(
        to=email,
        subject="Zooffer — подтвердите почту",
        body=(
            "Подтвердите адрес электронной почты (ссылка действует 2 дня):\n"
            f"{settings.app_base_url}/auth/verify-email?token={raw}"
        ),
    )


async def verify_email(db: AsyncSession, raw_token: str) -> User:
    token = await db.scalar(
        select(AuthToken).where(
            AuthToken.token_hash == hash_link_token(raw_token),
            AuthToken.purpose == "email_verify",
            AuthToken.used_at.is_(None),
            AuthToken.expires_at > utcnow(),
        )
    )
    if token is None:
        raise ValidationAppError("Ссылка недействительна или истекла", code="token_invalid")
    user = await db.get(User, token.user_id)
    if user is None:
        raise ValidationAppError("Аккаунт не найден", code="account_missing")
    user.email_verified_at = utcnow()
    token.used_at = utcnow()
    await db.commit()
    return user


async def get_self_view(db: AsyncSession, user: User) -> UserSelfView:
    profile = await db.get(Profile, user.id)
    private = await db.get(UserPrivateData, user.id)
    return UserSelfView(
        public_id=user.public_id,
        email=private.email_encrypted if private else None,
        role=user.role,
        first_name=profile.public_first_name if profile else None,
        last_name=profile.public_last_name if profile else None,
        city_id=profile.city_id if profile else None,
        onboarding_completed=user.onboarding_completed_at is not None,
        mfa_enabled=user.mfa_enabled,
        created_at=user.created_at,
    )


async def update_profile(
    db: AsyncSession,
    user: User,
    *,
    first_name: str,
    last_name: str | None,
    city_id: int | None,
) -> User:
    profile = await db.get(Profile, user.id)
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
    profile.public_first_name = first_name
    profile.public_last_name = last_name
    profile.city_id = city_id
    user.onboarding_completed_at = user.onboarding_completed_at or utcnow()
    await db.commit()
    return user


async def change_password(db: AsyncSession, user: User, current: str, new: str) -> None:
    credential = await db.get(Credential, user.id)
    if credential is None or not verify_password(current, credential.password_hash):
        raise UnauthorizedError("Текущий пароль указан неверно", code="invalid_password")
    if await is_breached_password(new):
        raise ValidationAppError("Выберите более надёжный пароль", code="weak_password")
    credential.password_hash = hash_password(new)
    credential.password_changed_at = utcnow()
    await db.commit()


def is_staff(user: User) -> bool:
    return user.role in {role.value for role in STAFF_ROLES}


async def ensure_email_verification_allowed(db: AsyncSession, user: User) -> None:
    private = await db.get(UserPrivateData, user.id)
    if private is None or not private.email_hash:
        return
    if user.email_verified_at is None:
        raise ForbiddenError(
            "Подтвердите электронную почту, чтобы продолжить", code="email_not_verified"
        )

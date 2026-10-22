from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from zooffer.core.utils import normalize_email, validate_display_name


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    first_name: str = Field(min_length=1, max_length=40)
    last_name: str | None = Field(default=None, max_length=40)
    city_id: int | None = None
    accepted_terms: bool
    accepted_privacy: bool
    marketing_opt_in: bool = False
    invite_code: str | None = Field(default=None, max_length=32)

    @field_validator("email")
    @classmethod
    def email_normalized(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("first_name")
    @classmethod
    def name_valid(cls, value: str) -> str:
        return validate_display_name(value, field="Имя")

    @field_validator("last_name")
    @classmethod
    def surname_valid(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return validate_display_name(value, field="Фамилия")


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    mfa_code: str | None = Field(default=None, min_length=6, max_length=8)

    @field_validator("email")
    @classmethod
    def email_normalized(cls, value: str) -> str:
        return normalize_email(value)


class TelegramLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    photo_url: str = ""
    auth_date: int
    hash: str


class MiniAppAuthRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    init_data: str = Field(min_length=10, max_length=8192)


class LinkTokenResponse(BaseModel):
    token: str
    expires_at: datetime
    deep_link: str


class UserSelfView(BaseModel):
    public_id: UUID
    email: str | None
    role: str
    first_name: str | None
    last_name: str | None
    city_id: int | None
    onboarding_completed: bool
    mfa_enabled: bool
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserSelfView
    csrf_token: str


class MeResponse(BaseModel):
    user: UserSelfView
    csrf_token: str


class OkResponse(BaseModel):
    ok: bool = True


class MessageResponse(BaseModel):
    message: str


class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr

    @field_validator("email")
    @classmethod
    def email_normalized(cls, value: str) -> str:
        return normalize_email(value)


class PasswordResetConfirm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=10, max_length=128)


class EmailVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=20, max_length=200)


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(min_length=1, max_length=40)
    last_name: str | None = Field(default=None, max_length=40)
    city_id: int | None = None

    @field_validator("first_name")
    @classmethod
    def name_valid(cls, value: str) -> str:
        return validate_display_name(value, field="Имя")

    @field_validator("last_name")
    @classmethod
    def surname_valid(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return validate_display_name(value, field="Фамилия")


class MfaConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=6, max_length=8)


class MfaSetupResponse(BaseModel):
    secret: str
    otpauth_url: str


class SessionView(BaseModel):
    id: UUID
    device_label: str | None
    user_agent: str | None
    created_at: datetime
    last_seen_at: datetime
    is_current: bool = False


class SessionListResponse(BaseModel):
    items: list[SessionView]

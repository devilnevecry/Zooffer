from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration.

    Production fails fast on weak/missing secrets. Development has safe local defaults,
    but never production credentials.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: Literal["dev", "test", "staging", "prod"] = "dev"
    log_level: str = "INFO"
    app_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"
    public_api_url: str = "http://localhost:8000"

    database_url: str = "postgresql+asyncpg://zooffer:zooffer_dev_password@localhost:5432/zooffer"
    test_database_url: str = (
        "postgresql+asyncpg://zooffer:zooffer_dev_password@localhost:5432/zooffer_test"
    )
    redis_url: str = "redis://:zooffer_dev_redis@localhost:6379/0"

    session_secret: str = "dev-only-session-secret-not-for-production"
    secret_pepper: str = "dev-only-pepper-not-for-production"
    cookie_secure: bool = False
    cookie_domain: str | None = None
    session_idle_days: int = 14
    session_absolute_days: int = 60
    csrf_header: str = "X-CSRF-Token"

    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    telegram_webhook_secret: str = ""
    telegram_login_bot_id: int = 0
    telegram_login_bot_username: str = ""
    telegram_admin_chat_id: int = 0
    telegram_auth_max_age_seconds: int = 300

    payment_provider: Literal["fake", "yookassa"] = "fake"
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    yookassa_return_url: str = "http://localhost:3000/account/subscription"

    media_backend: Literal["local"] = "local"  # S3 adapter is not implemented (B9)
    media_local_path: str = "./data/media"
    media_public_base_url: str = "http://localhost:8000"
    max_upload_bytes: int = 8 * 1024 * 1024
    max_image_pixels: int = 40_000_000

    email_backend: Literal["console", "smtp"] = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-reply@example.invalid"

    free_daily_swipes: int = 20
    quota_timezone: str = "Europe/Moscow"

    metrics_token: str = "dev-metrics-token"
    sentry_dsn: str = ""
    hibp_enabled: bool = False

    enable_telegram: bool = False
    enable_glass: bool = True
    admin_bootstrap_token: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment in {"staging", "prod"}

    @property
    def cookie_name(self) -> str:
        return "__Host-zooffer_session" if self.cookie_secure else "zooffer_session"

    @property
    def csrf_cookie_name(self) -> str:
        return "__Host-zooffer_csrf" if self.cookie_secure else "zooffer_csrf"

    @model_validator(mode="after")
    def validate_production(self) -> Settings:
        if not self.is_production:
            return self
        problems: list[str] = []
        if len(self.session_secret) < 32 or self.session_secret.startswith("dev-only"):
            problems.append("SESSION_SECRET must be a strong value (>=32 chars)")
        if len(self.secret_pepper) < 32 or self.secret_pepper.startswith("dev-only"):
            problems.append("SECRET_PEPPER must be a strong value (>=32 chars)")
        if not self.cookie_secure:
            problems.append("COOKIE_SECURE must be true in production")
        if self.payment_provider == "fake":
            problems.append("PAYMENT_PROVIDER=fake is not allowed in production")
        if self.enable_telegram and (
            not self.telegram_bot_token or not self.telegram_webhook_secret
        ):
            problems.append("TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET are required")
        if "zooffer_dev_password" in self.database_url:
            problems.append("DATABASE_URL uses the development password")
        if problems:
            raise ValueError("Invalid production configuration: " + "; ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

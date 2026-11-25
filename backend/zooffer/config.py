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

    # Telegram Stars is the primary subscription path. Robokassa and YooKassa are
    # optional website providers and are never offered inside Telegram.
    payment_provider: Literal["fake", "yookassa", "robokassa", "telegram_stars"] = "fake"
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    yookassa_return_url: str = "http://localhost:3000/account/subscription"

    robokassa_merchant_login: str = ""
    robokassa_password1: str = ""
    robokassa_password2: str = ""
    robokassa_is_test: bool = True
    robokassa_hash_algo: Literal["md5", "sha256"] = "md5"

    telegram_stars_enabled: bool = False
    """Expose Telegram Stars purchase in the bot and Mini App.

    Usually implied by ``PAYMENT_PROVIDER=telegram_stars`` but kept as a separate
    switch so a deployment can beta-test Stars while another provider is selected
    for the website.
    """

    crypto_payment_enabled: bool = False
    """Additional purchase path: crypto wallet payments (for example a Telegram wallet).

    When enabled, the bot creates crypto wallet payment orders instead of Telegram
    Stars invoices. The wallet address / asset are configured below. This is an
    additional method and does not remove the Telegram Stars path.
    """

    crypto_payment_wallet_address: str = ""
    crypto_payment_asset: str = "USDT"
    crypto_payment_network: str = "TON"

    email_auth_enabled: bool = False
    """Email/password login. Always disabled in production for the Telegram-only launch.

    Development and test keep the legacy endpoints so the existing suite can run.
    """

    media_backend: Literal["local", "s3"] = "local"
    media_local_path: str = "./data/media"
    media_public_base_url: str = "http://localhost:8000"
    media_cdn_base_url: str = ""
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_signed_url_ttl: int = 3600
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
    def stars_enabled(self) -> bool:
        """Telegram Stars are usable when enabled and a bot token exists."""
        return (self.telegram_stars_enabled or self.payment_provider == "telegram_stars") and bool(
            self.telegram_bot_token
        )

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
        if self.payment_provider == "robokassa" and not (
            self.robokassa_merchant_login and self.robokassa_password1 and self.robokassa_password2
        ):
            problems.append(
                "ROBOKASSA_MERCHANT_LOGIN, ROBOKASSA_PASSWORD1 and ROBOKASSA_PASSWORD2 "
                "are required for PAYMENT_PROVIDER=robokassa"
            )
        if self.payment_provider == "telegram_stars" and not self.telegram_bot_token:
            problems.append("TELEGRAM_BOT_TOKEN is required for Telegram Stars")
        if self.enable_telegram and (
            not self.telegram_bot_token or not self.telegram_webhook_secret
        ):
            problems.append("TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET are required")
        if self.cookie_secure and self.cookie_domain:
            problems.append("COOKIE_DOMAIN must be empty when COOKIE_SECURE=true (__Host- cookies)")
        if not self.metrics_token or self.metrics_token == "dev-metrics-token":
            problems.append("METRICS_TOKEN must be a strong non-default value")
        if "zooffer_dev_password" in self.database_url:
            problems.append("DATABASE_URL uses the development password")
        if problems:
            raise ValueError("Invalid production configuration: " + "; ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

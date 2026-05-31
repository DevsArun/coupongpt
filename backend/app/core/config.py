"""Central application configuration.

All infrastructure endpoints and secrets are read from the environment so the
same image can run on Hugging Face Spaces, a VPS, or a dedicated server without
code changes. See ``.env.example`` for the full list of knobs.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- App ----
    app_name: str = "CouponGPT"
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me"
    api_v1_prefix: str = "/api/v1"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:8080"

    # ---- MySQL ----
    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_user: str = "coupongpt"
    mysql_password: str = "coupongpt_pw"
    mysql_database: str = "coupongpt"
    database_url: str | None = None

    # ---- Redis ----
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_url: str | None = None

    # ---- Meilisearch ----
    meili_host: str = "http://meilisearch:7700"
    meili_master_key: str = "change-me-meili-master-key"
    meili_index_coupons: str = "coupons"

    # ---- JWT / auth ----
    jwt_secret: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    password_bcrypt_rounds: int = 12

    # ---- AI providers ----
    ai_provider_priority: str = "groq,gemini,openai"
    ai_request_timeout: int = 8
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # ---- Billing ----
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # ---- Rate limiting ----
    rate_limit_per_minute: int = 120
    rate_limit_search_per_minute: int = 30

    # ---- Observability ----
    log_level: str = "INFO"
    log_json: bool = True
    sentry_dsn: str = ""

    # -----------------------------------------------------------------
    # Derived values
    # -----------------------------------------------------------------
    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"mysql+asyncmy://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_uri(self) -> str:
        if self.redis_url:
            return self.redis_url
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ai_priority_list(self) -> list[str]:
        return [p.strip().lower() for p in self.ai_provider_priority.split(",") if p.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()

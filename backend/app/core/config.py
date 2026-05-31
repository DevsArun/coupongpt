"""Central application configuration.

All infrastructure endpoints and secrets are read from the environment so the
same image can run on Hugging Face Spaces, a VPS, or a dedicated server without
code changes. See ``.env.example`` for the full list of knobs.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Default secret placeholders that must never survive into a production deploy.
_INSECURE_DEFAULTS = {
    "app_secret_key": "change-me",
    "jwt_secret": "change-me-jwt-secret",
    "meili_master_key": "change-me-meili-master-key",
}


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
    # Async driver: aiomysql (pure-Python, no build step — ideal for HF Spaces)
    # or asyncmy (faster at runtime, requires compilation).
    mysql_driver: str = "aiomysql"
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

    # ---- Production / serving ----
    web_concurrency: int = 1
    trust_proxy_headers: bool = False
    allowed_hosts: str = "*"
    app_base_url: str = "http://localhost:8080"  # used for links (e.g. password reset)

    # ---- Email (password reset, notifications) ----
    email_backend: str = "console"  # console | smtp
    email_from: str = "CouponGPT <no-reply@coupongpt.local>"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True

    # ---- Background scheduler (seconds; 0 disables a task) ----
    scheduler_enabled: bool = False
    ingest_interval_seconds: int = 21600  # 6h
    expire_interval_seconds: int = 3600  # 1h
    payment_retry_interval_seconds: int = 3600  # 1h

    # -----------------------------------------------------------------
    # Derived values
    # -----------------------------------------------------------------
    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"mysql+{self.mysql_driver}://{self.mysql_user}:{self.mysql_password}"
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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()] or ["*"]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    # -----------------------------------------------------------------
    # Fail-fast production validation
    # -----------------------------------------------------------------
    def production_problems(self) -> list[str]:
        """Return a list of misconfigurations that are unsafe in production."""
        problems: list[str] = []
        for field, insecure in _INSECURE_DEFAULTS.items():
            value = getattr(self, field, "")
            if not value or value == insecure or len(str(value)) < 16:
                problems.append(f"{field.upper()} must be set to a strong (>=16 char) secret")
        if self.app_debug:
            problems.append("APP_DEBUG must be false in production")
        if "*" in self.cors_origin_list:
            problems.append("CORS_ORIGINS must not be '*' in production")
        if not self.cors_origin_list:
            problems.append("CORS_ORIGINS must list your frontend origin(s)")
        return problems

    def validate_production(self) -> None:
        """Raise if running in production with an unsafe configuration."""
        if not self.is_production:
            return
        problems = self.production_problems()
        if problems:
            raise RuntimeError(
                "Refusing to start in production with insecure configuration:\n  - "
                + "\n  - ".join(problems)
            )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()

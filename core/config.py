"""Application configuration management using Pydantic Settings."""

from typing import Optional
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration settings for TelegramWarden."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram Bot
    BOT_TOKEN: str = Field(default="123456789:ABCDefghIJKlmnoPQRstuvWXYZ_1234567")
    BOT_USERNAME: str = Field(default="TelegramWardenBot")

    # Primary AI (DeepSeek)
    DEEPSEEK_API_KEY: str = Field(default="sk-dummy-deepseek-key")
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com")
    DEEPSEEK_MODEL: str = Field(default="deepseek-chat")

    # Fallback AI (Groq / OpenRouter / OpenAI)
    FALLBACK_AI_ENABLED: bool = Field(default=True)
    FALLBACK_API_KEY: Optional[str] = Field(default=None)
    FALLBACK_BASE_URL: str = Field(default="https://api.groq.com/openai/v1")
    FALLBACK_MODEL: str = Field(default="llama-3.3-70b-versatile")

    # Tier-1 fast triage (TypeSafe Jev, System One). Off unless explicitly
    # enabled with a key: without it the dispatcher calls DeepSeek directly.
    JEV_ENABLED: bool = Field(default=False)
    TYPESAFE_API_KEY: Optional[str] = Field(default=None)
    JEV_BASE_URL: str = Field(default="https://api.typesafe.ai")
    JEV_MODEL: str = Field(default="jev-1.13.0")
    JEV_FAST_PASS_THRESHOLD: float = Field(default=0.03, ge=0.0, le=1.0)
    JEV_TIMEOUT_SECONDS: float = Field(default=2.5, ge=0.5, le=10.0)
    JEV_MAX_CONCURRENT: int = Field(default=10, ge=1, le=50)

    # PostgreSQL Database
    POSTGRES_USER: str = Field(default="warden_user")
    POSTGRES_PASSWORD: str = Field(default="warden_secure_password")
    POSTGRES_DB: str = Field(default="warden_db")
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    DATABASE_URL: Optional[str] = Field(default=None)

    @computed_field
    @property
    def async_database_url(self) -> str:
        """Get async PostgreSQL connection string."""
        if self.DATABASE_URL:
            # Ensure asyncpg driver prefix
            if self.DATABASE_URL.startswith("postgresql://"):
                return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    REDIS_DB: int = Field(default=0)
    REDIS_URL: Optional[str] = Field(default=None)

    @computed_field
    @property
    def redis_connection_url(self) -> str:
        """Get Redis connection URL."""
        if self.REDIS_URL:
            return self.REDIS_URL
        auth_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # API & WebApp
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=2009)
    SECRET_KEY: str = Field(default="warden_super_secret_session_key_32_bytes_long!")
    WEBAPP_URL: str = Field(default="https://localhost:3000")

    # Global SuperAdmin Configuration
    SUPERADMIN_IDS: str = Field(default="")
    DEFAULT_LOG_CHANNEL_ID: Optional[int] = Field(default=None)

    @computed_field
    @property
    def superadmin_id_list(self) -> list[int]:
        """Parse comma-separated superadmin IDs from environment (empty if unset)."""
        ids = []
        for part in self.SUPERADMIN_IDS.split(","):
            cleaned = part.strip()
            if cleaned.isdigit():
                ids.append(int(cleaned))
        return ids

    def validate_runtime_secrets(self) -> None:
        """Fail fast on startup when production secrets are left at defaults."""
        problems = []
        fields = type(self).model_fields
        if self.BOT_TOKEN == fields["BOT_TOKEN"].default:
            problems.append("BOT_TOKEN is not configured (still default)")
        if self.SECRET_KEY == fields["SECRET_KEY"].default:
            problems.append("SECRET_KEY is not configured (still default)")
        if self.DEEPSEEK_API_KEY == fields["DEEPSEEK_API_KEY"].default:
            problems.append("DEEPSEEK_API_KEY is not configured (still default)")
        db_password_default = self.POSTGRES_PASSWORD == fields["POSTGRES_PASSWORD"].default
        db_url_leaks_default = bool(
            self.DATABASE_URL and "warden_secure_password" in self.DATABASE_URL
        )
        if db_password_default or db_url_leaks_default:
            problems.append("POSTGRES_PASSWORD is not configured (still default)")
        if problems:
            raise RuntimeError(
                "Refusing to start TelegramWarden with insecure defaults: "
                + "; ".join(problems)
                + ". Set them via environment variables or .env"
            )


    # Data Retention Policies (in days/hours)
    # Fallback only: per-chat Chat.warn_expiration_days is the single source
    # of truth applied by SanctionsExecutor.
    WARN_EXPIRATION_DAYS: int = Field(default=7)
    LOGS_RETENTION_DAYS: int = Field(default=30)
    MESSAGE_CACHE_HOURS: int = Field(default=24)

    # Logging
    LOG_LEVEL: str = Field(default="INFO")

    # Optional SHA-256 pin for the auto-downloaded OpenNSFW ONNX model
    NSFW_MODEL_SHA256: str = Field(default="")
    NSFW_THRESHOLD: float = Field(default=0.70)


# Singleton instance
settings = Settings()

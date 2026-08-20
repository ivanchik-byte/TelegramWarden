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
        """Parse comma-separated superadmin IDs from environment."""
        if not self.SUPERADMIN_IDS:
            return [8667615215, 123456789]
        ids = []
        for part in self.SUPERADMIN_IDS.split(","):
            cleaned = part.strip()
            if cleaned.isdigit():
                ids.append(int(cleaned))
        return ids if ids else [8667615215, 123456789]


    # Data Retention Policies (in days/hours)
    WARN_EXPIRATION_DAYS: int = Field(default=14)
    LOGS_RETENTION_DAYS: int = Field(default=30)
    MESSAGE_CACHE_HOURS: int = Field(default=24)

    # Logging
    LOG_LEVEL: str = Field(default="INFO")


# Singleton instance
settings = Settings()

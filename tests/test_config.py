"""Unit tests for configuration validation and settings."""

from core.config import Settings


def test_default_settings_instantiation():
    """Verify that default settings instantiate with proper values and typing."""
    cfg = Settings(
        BOT_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        POSTGRES_USER="test_user",
        POSTGRES_PASSWORD="test_password",
        POSTGRES_DB="test_db",
    )

    assert cfg.BOT_TOKEN.startswith("123456:")
    assert cfg.POSTGRES_USER == "test_user"
    assert cfg.WARN_EXPIRATION_DAYS == 14
    assert cfg.LOGS_RETENTION_DAYS == 30
    assert "postgresql+asyncpg://" in cfg.async_database_url
    assert "redis://" in cfg.redis_connection_url


def test_custom_database_url_override():
    """Verify that a custom DATABASE_URL is properly normalized with asyncpg."""
    cfg = Settings(
        DATABASE_URL="postgresql://custom_user:custom_pass@dbhost:5432/custom_db"
    )
    assert cfg.async_database_url.startswith("postgresql+asyncpg://")

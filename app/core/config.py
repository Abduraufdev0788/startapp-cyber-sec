"""
Core application configuration management using Pydantic Settings.
Validates environment variables at application startup (Fail-Fast principle).
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with strict validation."""

    # Application Mode & Logging
    ENVIRONMENT: Literal["development", "staging", "production", "testing"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    PROJECT_NAME: str = "Telegram Phishing & Scam Detection Platform"

    # Security & Cryptography
    APP_MASTER_KEY: str = Field(
        ...,
        description="32-byte hexadecimal AES-256 master key (64 hex characters)",
    )
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # Database Infrastructure
    DATABASE_URL: str = Field(
        ...,
        description="Async PostgreSQL connection string (postgresql+asyncpg://...)",
    )
    SYNC_DATABASE_URL: str | None = None

    # Redis Infrastructure
    REDIS_URL: str = Field(
        "redis://localhost:6379/0",
        description="Redis connection URL for caching and Celery broker",
    )

    # Telegram Credentials
    TELEGRAM_API_ID: int = Field(..., description="Telegram App API ID")
    TELEGRAM_API_HASH: str = Field(..., description="Telegram App API Hash")
    TELEGRAM_BOT_TOKEN: str = Field(..., description="Official Bot Token from @BotFather")

    # AI Provider (Google Gemini)
    GEMINI_API_KEY: str = Field(..., description="Google Gemini API Key")
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Scanner & Network Constraints (SSRF & DoS mitigation)
    SCANNER_CONNECT_TIMEOUT_SECONDS: int = 5
    SCANNER_TOTAL_TIMEOUT_SECONDS: int = 10
    SCANNER_MAX_RESPONSE_BYTES: int = 2097152  # 2 MB limit
    SCANNER_MAX_REDIRECTS: int = 5

    @field_validator("APP_MASTER_KEY")
    @classmethod
    def validate_master_key(cls, v: str) -> str:
        clean_key = v.strip()
        try:
            key_bytes = bytes.fromhex(clean_key)
            if len(key_bytes) != 32:
                raise ValueError(
                    f"APP_MASTER_KEY must be exactly 32 bytes (64 hex chars), got {len(key_bytes)} bytes."
                )
        except ValueError as err:
            raise ValueError(f"Invalid APP_MASTER_KEY format: {err}") from err
        return clean_key

    @property
    def master_key_bytes(self) -> bytes:
        """Returns the decoded 32-byte master key for AES-256."""
        return bytes.fromhex(self.APP_MASTER_KEY)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Singleton getter for application settings."""
    return Settings()

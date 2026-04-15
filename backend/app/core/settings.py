"""Application settings and configuration."""
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # =========================
    # API
    # =========================
    API_TITLE: str = "BlockScope API"
    API_VERSION: str = "0.1.0"
    APP_VERSION: str = "0.1.0"
    API_DESCRIPTION: str = "Smart Contract Vulnerability Scanner"
    APP_NAME: str = "BlockScope API"

    # =========================
    # Server
    # =========================
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # =========================
    # Debug / Docs
    # =========================
    DEBUG: bool = True
    ENABLE_API_DOCS: bool = True

    # =========================
    # Environment
    # =========================
    ENVIRONMENT: str = "development"

    # =========================
    # CORS
    # =========================
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    CORS_MAX_AGE: int = 3600

    # =========================
    # Database
    # =========================
    DATABASE_URL: str = "postgresql://postgres:CHANGE_ME@localhost:5432/blockscope"
    SQLALCHEMY_ECHO: bool = True
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    # =========================
    # Redis
    # =========================
    REDIS_URL: str = "redis://localhost:6379/0"

    # =========================
    # Security
    # =========================
    SECRET_KEY: str = ""  # Must be set in .env
    JWT_SECRET_KEY: str = ""  # Must be set in .env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SECURITY_ENABLED: bool = True
    RATE_LIMIT_ENABLED: bool = False

    # =========================
    # API Key
    # =========================
    API_KEY_HEADER_NAME: str = "X-API-Key"
    API_KEY_LENGTH: int = 32
    API_KEY_PREFIX: str = "bsc_"

    # =========================
    # Rate Limiting
    # =========================
    RATE_LIMIT_PER_MINUTE: int = 20
    RATE_LIMIT_PER_HOUR: int = 100
    RATE_LIMIT_PER_DAY: int = 1000
    API_KEY_RATE_LIMIT_PER_MINUTE: int = 60
    API_KEY_RATE_LIMIT_PER_HOUR: int = 500
    API_KEY_RATE_LIMIT_PER_DAY: int = 5000

    # =========================
    # File Upload
    # =========================
    MAX_UPLOAD_SIZE: int = 5242880  # 5 MB
    ALLOWED_EXTENSIONS: List[str] = [".sol"]
    MAX_FILENAME_LENGTH: int = 255

    # =========================
    # Logging
    # =========================
    LOG_LEVEL: str = "INFO"
    LOG_REQUESTS: bool = True

    model_config = SettingsConfigDict(
        env_file=(".env.development", ".env"),
        extra="ignore",  # cleanly ignore anything not defined above
    )


settings = Settings()
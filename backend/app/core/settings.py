"""Application settings and configuration."""
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
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # =========================
    # Database
    # =========================
    DATABASE_URL: str = "postgresql://postgres:joker@localhost:5432/blockscope"
    SQLALCHEMY_ECHO: bool = True

    # =========================
    # Redis
    # =========================
    REDIS_URL: str = "redis://localhost:6379/0"

    # =========================
    # Security
    # =========================
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    JWT_SECRET_KEY: str = "your-jwt-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SECURITY_ENABLED: bool = True
    RATE_LIMIT_ENABLED: bool = False

    model_config = SettingsConfigDict(
        env_file=(".env.development", ".env"),
        extra="ignore",  # cleanly ignore anything not defined above
    )


settings = Settings()
"""Application settings and configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # API
    API_TITLE: str = "BlockScope API"
    API_VERSION: str = "0.1.0"
    API_DESCRIPTION: str = "Smart Contract Vulnerability Scanner"
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/blockscope"
    SQLALCHEMY_ECHO: bool = True
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"


settings = Settings()

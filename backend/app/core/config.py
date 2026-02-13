"""
BlockScope Configuration Module
Handles all environment variables with validation using Pydantic Settings
"""

import secrets
from functools import lru_cache
from typing import List, Optional

from pydantic import EmailStr, Field, HttpUrl, PostgresDsn, RedisDsn, conint, constr, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings with environment variable validation.
    All settings are loaded from environment variables.
    """

    # ==================== Application Settings ====================
    APP_NAME: str = Field(default="BlockScope", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    ENVIRONMENT: str = Field(
        default="development", description="Environment: development, staging, production"
    )
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(
        default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )

    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        """Ensure environment is one of allowed values"""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Ensure log level is valid"""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v.upper()

    # ==================== Server Configuration ====================
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: conint(gt=0, lt=65536) = Field(default=8000, description="Server port")
    WORKERS: conint(gt=0) = Field(default=4, description="Number of worker processes")
    RELOAD: bool = Field(default=False, description="Auto-reload on code changes")

    # ==================== Database Configuration ====================
    DATABASE_URL: PostgresDsn = Field(
        ..., description="PostgreSQL connection string"  # Required field
    )
    DB_POOL_SIZE: conint(gt=0) = Field(default=20, description="Database pool size")
    DB_MAX_OVERFLOW: conint(ge=0) = Field(default=10, description="Max overflow connections")
    DB_POOL_TIMEOUT: conint(gt=0) = Field(default=30, description="Pool timeout in seconds")
    DB_POOL_RECYCLE: conint(gt=0) = Field(
        default=3600, description="Recycle connections after seconds"
    )
    DB_ECHO: bool = Field(default=False, description="Log SQL statements")

    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v):
        """Ensure database URL is properly formatted"""
        if not v:
            raise ValueError("DATABASE_URL is required")
        if not v.startswith("postgresql://"):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v

    # ==================== Redis Configuration ====================
    REDIS_URL: RedisDsn = Field(
        default="redis://localhost:6379/0", description="Redis connection string"
    )
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")
    REDIS_MAX_CONNECTIONS: conint(gt=0) = Field(default=50, description="Max Redis connections")
    REDIS_SOCKET_TIMEOUT: conint(gt=0) = Field(default=5, description="Socket timeout")
    REDIS_SOCKET_CONNECT_TIMEOUT: conint(gt=0) = Field(default=5, description="Connection timeout")

    # ==================== Security Configuration ====================
    SECRET_KEY: constr(min_length=32) = Field(
        ..., description="Secret key for signing tokens"  # Required field
    )
    JWT_SECRET_KEY: constr(min_length=32) = Field(
        ..., description="JWT secret key"  # Required field
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: conint(gt=0) = Field(
        default=60, description="Access token expiration in minutes"
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: conint(gt=0) = Field(
        default=30, description="Refresh token expiration in days"
    )

    @validator("SECRET_KEY", "JWT_SECRET_KEY")
    def validate_secret_keys(cls, v):
        """Ensure secret keys are strong"""
        if v in [
            "changeme",
            "secret",
            "password",
            "dev_secret_key_DO_NOT_USE_IN_PRODUCTION_abc123xyz789",
        ]:
            raise ValueError("Please change the default secret key to a secure random value")
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v

    @validator("JWT_ALGORITHM")
    def validate_jwt_algorithm(cls, v):
        """Ensure JWT algorithm is secure"""
        allowed = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if v not in allowed:
            raise ValueError(f"JWT_ALGORITHM must be one of {allowed}")
        return v

    # API Key Configuration
    API_KEY_HEADER_NAME: str = Field(default="X-API-Key", description="API key header name")
    API_KEY_LENGTH: conint(ge=16, le=64) = Field(default=32, description="API key length")
    API_KEY_PREFIX: str = Field(default="bsc_", description="API key prefix")

    # Password hashing
    BCRYPT_ROUNDS: conint(ge=10, le=16) = Field(default=12, description="BCrypt hashing rounds")

    # ==================== CORS Configuration ====================
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:5173"], description="Allowed CORS origins"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="Allow credentials")
    CORS_ALLOW_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"], description="Allowed HTTP methods"
    )
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"], description="Allowed headers")
    CORS_MAX_AGE: conint(gt=0) = Field(default=3600, description="Preflight cache time")

    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @validator("CORS_ORIGINS")
    def validate_cors_origins(cls, v, values):
        """Warn if CORS is too permissive in production"""
        if values.get("ENVIRONMENT") == "production" and "*" in v:
            raise ValueError("CORS_ORIGINS should not contain '*' in production")
        return v

    # ==================== Rate Limiting Configuration ====================
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_PER_MINUTE: conint(gt=0) = Field(
        default=20, description="Rate limit per minute per IP"
    )
    RATE_LIMIT_PER_HOUR: conint(gt=0) = Field(default=100, description="Rate limit per hour per IP")
    RATE_LIMIT_PER_DAY: conint(gt=0) = Field(default=1000, description="Rate limit per day per IP")

    # API Key tier limits
    API_KEY_RATE_LIMIT_PER_MINUTE: conint(gt=0) = Field(
        default=60, description="API key rate limit per minute"
    )
    API_KEY_RATE_LIMIT_PER_HOUR: conint(gt=0) = Field(
        default=500, description="API key rate limit per hour"
    )
    API_KEY_RATE_LIMIT_PER_DAY: conint(gt=0) = Field(
        default=5000, description="API key rate limit per day"
    )
    RATE_LIMIT_BURST: conint(ge=0) = Field(default=10, description="Burst allowance")

    # ==================== File Upload Configuration ====================
    MAX_UPLOAD_SIZE: conint(gt=0) = Field(
        default=5242880, description="Maximum file upload size in bytes"  # 5MB
    )
    ALLOWED_EXTENSIONS: List[str] = Field(default=[".sol"], description="Allowed file extensions")
    UPLOAD_FOLDER: str = Field(default="/tmp/blockscope_uploads", description="Upload folder path")
    MAX_FILENAME_LENGTH: conint(gt=0, le=255) = Field(
        default=255, description="Maximum filename length"
    )

    @validator("ALLOWED_EXTENSIONS", pre=True)
    def parse_allowed_extensions(cls, v):
        """Parse allowed extensions from comma-separated string or list"""
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v

    @validator("ALLOWED_EXTENSIONS")
    def validate_allowed_extensions(cls, v):
        """Ensure extensions start with dot"""
        validated = []
        for ext in v:
            if not ext.startswith("."):
                ext = f".{ext}"
            validated.append(ext.lower())
        return validated

    # ==================== Slither Configuration ====================
    SLITHER_TIMEOUT: conint(gt=0) = Field(
        default=300, description="Slither analysis timeout in seconds"
    )
    SLITHER_MAX_CONCURRENT: conint(gt=0) = Field(
        default=3, description="Maximum concurrent Slither analyses"
    )
    SLITHER_PATH: str = Field(default="slither", description="Path to Slither binary")
    SOLC_VERSION: str = Field(default="0.8.20", description="Default Solidity compiler version")

    # ==================== Analysis Configuration ====================
    CRITICAL_WEIGHT: conint(ge=0) = Field(default=100, description="Critical issue weight")
    HIGH_WEIGHT: conint(ge=0) = Field(default=50, description="High issue weight")
    MEDIUM_WEIGHT: conint(ge=0) = Field(default=20, description="Medium issue weight")
    LOW_WEIGHT: conint(ge=0) = Field(default=5, description="Low issue weight")

    # Caching
    CACHE_SCAN_RESULTS: bool = Field(default=True, description="Enable result caching")
    CACHE_TTL: conint(gt=0) = Field(default=86400, description="Cache TTL in seconds")
    CACHE_PREFIX: str = Field(default="scan:", description="Cache key prefix")

    # ==================== Email Configuration ====================
    SMTP_ENABLED: bool = Field(default=False, description="Enable SMTP")
    SMTP_HOST: Optional[str] = Field(default=None, description="SMTP host")
    SMTP_PORT: Optional[conint(gt=0, lt=65536)] = Field(default=587, description="SMTP port")
    SMTP_USER: Optional[str] = Field(default=None, description="SMTP username")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP password")
    SMTP_FROM_EMAIL: Optional[EmailStr] = Field(default=None, description="From email address")
    SMTP_FROM_NAME: Optional[str] = Field(default="BlockScope", description="From name")
    SMTP_TLS: bool = Field(default=True, description="Use TLS")
    SMTP_SSL: bool = Field(default=False, description="Use SSL")

    @validator("SMTP_FROM_EMAIL")
    def validate_smtp_config(cls, v, values):
        """If SMTP is enabled, ensure required fields are set"""
        if values.get("SMTP_ENABLED"):
            if not all([values.get("SMTP_HOST"), values.get("SMTP_USER"), v]):
                raise ValueError(
                    "SMTP_HOST, SMTP_USER, and SMTP_FROM_EMAIL required when SMTP_ENABLED=True"
                )
        return v

    # ==================== Monitoring & Logging ====================
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN")
    SENTRY_TRACES_SAMPLE_RATE: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Sentry traces sample rate"
    )
    SENTRY_ENVIRONMENT: str = Field(default="development", description="Sentry environment")

    # Logging
    LOG_FILE_ENABLED: bool = Field(default=True, description="Enable log file")
    LOG_FILE_PATH: str = Field(default="/var/log/blockscope/app.log", description="Log file path")
    LOG_FILE_MAX_BYTES: conint(gt=0) = Field(default=10485760, description="Max log file size")
    LOG_FILE_BACKUP_COUNT: conint(ge=0) = Field(default=5, description="Number of backup logs")
    LOG_JSON_FORMAT: bool = Field(default=True, description="Use JSON log format")
    LOG_REQUESTS: bool = Field(default=True, description="Log HTTP requests")
    LOG_RESPONSES: bool = Field(default=False, description="Log HTTP responses")
    LOG_REQUEST_BODY: bool = Field(default=False, description="Log request bodies")

    # ==================== Performance Configuration ====================
    GZIP_MINIMUM_SIZE: conint(ge=0) = Field(
        default=1000, description="Minimum response size to compress"
    )
    GZIP_COMPRESSION_LEVEL: conint(ge=1, le=9) = Field(
        default=6, description="GZIP compression level"
    )
    DB_STATEMENT_TIMEOUT: conint(gt=0) = Field(
        default=30000, description="Database statement timeout in milliseconds"
    )

    # ==================== Background Tasks (Celery) ====================
    CELERY_BROKER_URL: Optional[str] = Field(default=None, description="Celery broker URL")
    CELERY_RESULT_BACKEND: Optional[str] = Field(default=None, description="Celery result backend")
    CELERY_TASK_TRACK_STARTED: bool = Field(default=True, description="Track task start")
    CELERY_TASK_TIME_LIMIT: conint(gt=0) = Field(
        default=600, description="Task time limit in seconds"
    )
    CELERY_TASK_SOFT_TIME_LIMIT: conint(gt=0) = Field(
        default=540, description="Task soft time limit in seconds"
    )

    # ==================== Feature Flags ====================
    ENABLE_REGISTRATION: bool = Field(default=True, description="Enable user registration")
    ENABLE_SOCIAL_LOGIN: bool = Field(default=False, description="Enable social login")
    ENABLE_EMAIL_VERIFICATION: bool = Field(default=False, description="Enable email verification")
    ENABLE_TWO_FACTOR_AUTH: bool = Field(default=False, description="Enable 2FA")
    ENABLE_API_DOCS: bool = Field(default=True, description="Enable API documentation")
    ENABLE_METRICS: bool = Field(default=True, description="Enable Prometheus metrics")

    # ==================== Admin Configuration ====================
    ADMIN_EMAIL: EmailStr = Field(default="admin@blockscope.io", description="Admin email address")
    ADMIN_USERNAME: str = Field(default="admin", description="Admin username")
    ADMIN_PASSWORD: constr(min_length=8) = Field(default="changeme", description="Admin password")

    @validator("ADMIN_PASSWORD")
    def validate_admin_password(cls, v, values):
        """Warn about weak admin password in production"""
        if values.get("ENVIRONMENT") == "production":
            if v in ["admin", "password", "changeme", "admin123"]:
                raise ValueError("ADMIN_PASSWORD must be changed from default in production!")
        return v

    # ==================== External Services ====================
    ETH_RPC_URL: Optional[HttpUrl] = Field(default=None, description="Ethereum RPC URL")
    POLYGON_RPC_URL: Optional[HttpUrl] = Field(default=None, description="Polygon RPC URL")
    BSC_RPC_URL: Optional[HttpUrl] = Field(default=None, description="BSC RPC URL")

    # Analytics
    GOOGLE_ANALYTICS_ID: Optional[str] = Field(default=None, description="Google Analytics ID")
    MIXPANEL_TOKEN: Optional[str] = Field(default=None, description="Mixpanel token")

    # ==================== Development Tools ====================
    AUTO_RELOAD: bool = Field(default=False, description="Auto-reload on changes")
    ENABLE_PROFILER: bool = Field(default=False, description="Enable profiler")
    PROFILER_OUTPUT_DIR: str = Field(
        default="/tmp/blockscope_profiles", description="Profiler output directory"
    )

    # ==================== Testing ====================
    TESTING: bool = Field(default=False, description="Testing mode")
    TEST_DATABASE_URL: Optional[PostgresDsn] = Field(default=None, description="Test database URL")

    # ==================== Config Class ====================
    class Config:
        """Pydantic config"""

        env_file = (".env.development", ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True

        # Allow extra fields from environment
        extra = "ignore"

    # ==================== Computed Properties ====================
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"

    @property
    def database_url_sync(self) -> str:
        """Get sync database URL"""
        return str(self.DATABASE_URL)

    @property
    def database_url_async(self) -> str:
        """Get async database URL"""
        return str(self.DATABASE_URL).replace("postgresql://", "postgresql+asyncpg://")

    @property
    def redis_url_str(self) -> str:
        """Get Redis URL as string"""
        return str(self.REDIS_URL)

    def generate_secret_key(self) -> str:
        """Generate a secure secret key"""
        return secrets.token_urlsafe(64)

    def validate_all(self) -> None:
        """Perform additional validation checks"""
        # Check production-specific requirements
        if self.is_production:
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production")
            if self.ENABLE_API_DOCS:
                print("WARNING: API docs are enabled in production")
            if "*" in self.CORS_ORIGINS:
                raise ValueError("CORS_ORIGINS should not contain '*' in production")


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    This function uses lru_cache to ensure settings are loaded only once.

    Returns:
        Settings: Validated settings object

    Raises:
        ValueError: If required environment variables are missing or invalid
    """
    try:
        settings = Settings()
        settings.validate_all()
        return settings
    except Exception as e:
        print(f"❌ Configuration Error: {str(e)}")
        print("\nPlease check your environment variables.")
        print("Required variables: DATABASE_URL, SECRET_KEY, JWT_SECRET_KEY")
        print(
            f"\nCurrent ENVIRONMENT: {Settings().ENVIRONMENT if hasattr(Settings(), 'ENVIRONMENT') else 'unknown'}"
        )
        raise


# Export settings instance
settings = get_settings()


# ==================== Helper Functions ====================


def generate_secure_key(length: int = 64) -> str:
    """
    Generate a secure random key.

    Args:
        length: Length of the key

    Returns:
        str: Secure random key
    """
    return secrets.token_urlsafe(length)


def print_config_summary():
    """Print configuration summary (for debugging)"""
    s = settings
    print("\n" + "=" * 60)
    print("BLOCKSCOPE CONFIGURATION SUMMARY")
    print("=" * 60)
    print(f"Environment:      {s.ENVIRONMENT}")
    print(f"Debug Mode:       {s.DEBUG}")
    print(f"API Docs:         {s.ENABLE_API_DOCS}")
    print(
        f"Database:         {s.DATABASE_URL.split('@')[1] if '@' in str(s.DATABASE_URL) else 'configured'}"
    )
    print(
        f"Redis:            {s.REDIS_URL.split('@')[1] if '@' in str(s.REDIS_URL) else 'configured'}"
    )
    print(
        f"CORS Origins:     {', '.join(s.CORS_ORIGINS[:3])}{'...' if len(s.CORS_ORIGINS) > 3 else ''}"
    )
    print(f"Rate Limiting:    {'Enabled' if s.RATE_LIMIT_ENABLED else 'Disabled'}")
    print(f"Log Level:        {s.LOG_LEVEL}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Test configuration loading
    try:
        settings = get_settings()
        print("✅ Configuration loaded successfully!")
        print_config_summary()
    except Exception as e:
        print(f"❌ Configuration failed: {e}")

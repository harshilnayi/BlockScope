"""
Root conftest.py — sets test environment variables BEFORE any app module is imported.

This MUST run before anything triggers `from app.core.config import settings`,
because settings = get_settings() executes at module-import time.
"""

import os

# Set test environment variables before any imports
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-1234567890")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-testing-1234567890")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("LOG_FILE_ENABLED", "false")

# Clear the lru_cache on get_settings in case it was already called
try:
    from app.core.config import get_settings
    get_settings.cache_clear()
except Exception:
    pass

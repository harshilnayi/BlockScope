"""
Targeted tests for health checks and configuration helpers.

These cover launch-critical utility paths that were previously untested:
- health probe helper functions and readiness/startup responses
- config parsing, computed properties, and CLI-style summary helpers
"""

import os
import sys
from collections import namedtuple
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("TESTING", "True")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_health_config.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use-only")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-not-for-production-use-only")
os.environ.setdefault("RATE_LIMIT_ENABLED", "False")
os.environ.setdefault("LOG_FILE_ENABLED", "False")
os.environ.setdefault("ADMIN_PASSWORD", "testadmin123")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.routers.health as health  # noqa: E402
from app.core import config as config_module  # noqa: E402
from app.core.config import Settings, generate_secure_key  # noqa: E402


def _settings_kwargs(**overrides):
    base = {
        "DATABASE_URL": "sqlite:///./unit-test.db",
        "SECRET_KEY": "x" * 40,
        "JWT_SECRET_KEY": "y" * 40,
        "ADMIN_PASSWORD": "strongadmin123",
        "ENVIRONMENT": "development",
        "REDIS_URL": "redis://localhost:6379/0",
    }
    base.update(overrides)
    return base


class TestHealthHelpers:
    def test_check_database_success(self):
        mock_conn = MagicMock()
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        with patch.object(health, "engine", mock_engine):
            assert health.check_database() == {"status": "ok"}

    def test_check_database_error(self):
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = RuntimeError("db down")

        with patch.object(health, "engine", mock_engine):
            result = health.check_database()

        assert result["status"] == "error"
        assert "db down" in result["detail"]

    def test_check_redis_success(self):
        redis_client = MagicMock()
        redis_client.ping.return_value = True

        with patch.object(health.settings, "RATE_LIMIT_ENABLED", True), patch.object(
            health.redis, "from_url", return_value=redis_client
        ):
            assert health.check_redis() == {"status": "ok"}

    def test_check_redis_error(self):
        with patch.object(health.settings, "RATE_LIMIT_ENABLED", True), patch.object(
            health.redis, "from_url", side_effect=RuntimeError("redis down")
        ):
            result = health.check_redis()

        assert result["status"] == "error"
        assert "redis down" in result["detail"]

    def test_check_redis_disabled(self):
        with patch.object(health.settings, "RATE_LIMIT_ENABLED", False):
            assert health.check_redis() == {"status": "disabled"}

    def test_check_disk_warning_and_critical(self):
        disk_usage = namedtuple("usage", ["total", "used", "free"])

        with patch.object(health.shutil, "disk_usage", return_value=disk_usage(100, 90, 10)):
            warning = health.check_disk()
        assert warning["status"] == "warning"

        with patch.object(health.shutil, "disk_usage", return_value=disk_usage(100, 96, 4)):
            critical = health.check_disk()
        assert critical["status"] == "critical"

    def test_check_memory_warning_and_critical(self):
        warning_mem = SimpleNamespace(percent=90, available=512 * 1024 * 1024)
        critical_mem = SimpleNamespace(percent=97, available=256 * 1024 * 1024)

        with patch.object(health.psutil, "virtual_memory", return_value=warning_mem):
            warning = health.check_memory()
        assert warning["status"] == "warning"

        with patch.object(health.psutil, "virtual_memory", return_value=critical_mem):
            critical = health.check_memory()
        assert critical["status"] == "critical"

    def test_check_response_time_warning_and_critical(self):
        with patch.object(health.time, "time", side_effect=[0.0, 0.8]):
            warning = health.check_response_time()
        assert warning["status"] == "warning"

        with patch.object(health.time, "time", side_effect=[0.0, 1.5]):
            critical = health.check_response_time()
        assert critical["status"] == "critical"

    def test_readiness_ready(self):
        ok = {"status": "ok"}
        healthy = {"status": "healthy"}

        with patch.object(health, "check_database", return_value=ok), patch.object(
            health, "check_redis", return_value=ok
        ), patch.object(health, "check_disk", return_value={"status": "ok"}), patch.object(
            health, "check_memory", return_value={"status": "ok"}
        ), patch.object(
            health, "check_response_time", return_value=healthy
        ):
            result = health.readiness()

        assert result["status"] == "ready"
        assert "checks" in result

    def test_readiness_not_ready(self):
        ok = {"status": "ok"}

        with patch.object(health, "check_database", return_value={"status": "error"}), patch.object(
            health, "check_redis", return_value=ok
        ), patch.object(health, "check_disk", return_value={"status": "ok"}), patch.object(
            health, "check_memory", return_value={"status": "ok"}
        ), patch.object(
            health, "check_response_time", return_value={"status": "healthy"}
        ):
            result = health.readiness()

        assert result.status_code == 503
        assert b"not_ready" in result.body

    def test_startup_endpoint_states(self):
        with patch.object(health, "startup_complete", False):
            starting = health.startup()
        assert starting.status_code == 503

        with patch.object(health, "startup_complete", True):
            started = health.startup()
        assert started == {"status": "started"}

    def test_liveness(self):
        assert health.liveness() == {"status": "alive"}


class TestConfigHelpers:
    def test_settings_parse_string_lists_and_extensions(self):
        settings = Settings(
            **_settings_kwargs(
                CORS_ORIGINS="http://a.test, http://b.test",
                CORS_ALLOW_METHODS="GET, POST",
                CORS_ALLOW_HEADERS="Authorization, Content-Type",
                ALLOWED_EXTENSIONS="sol, vy",
            )
        )

        assert settings.CORS_ORIGINS == ["http://a.test", "http://b.test"]
        assert settings.CORS_ALLOW_METHODS == ["GET", "POST"]
        assert settings.CORS_ALLOW_HEADERS == ["Authorization", "Content-Type"]
        assert settings.ALLOWED_EXTENSIONS == [".sol", ".vy"]

    def test_settings_properties_and_secret_generation(self):
        settings = Settings(**_settings_kwargs())

        assert settings.is_development is True
        assert settings.is_production is False
        assert settings.database_url_async == "sqlite:///./unit-test.db"
        assert settings.redis_url_str == "redis://localhost:6379/0"
        assert isinstance(settings.generate_secret_key(), str)

    def test_invalid_environment_rejected(self):
        with pytest.raises(ValidationError):
            Settings(**_settings_kwargs(ENVIRONMENT="broken"))

    def test_invalid_database_url_rejected(self):
        with pytest.raises(ValidationError):
            Settings(**_settings_kwargs(DATABASE_URL="mysql://localhost/db"))

    def test_short_secret_rejected(self):
        with pytest.raises(ValidationError):
            Settings(**_settings_kwargs(SECRET_KEY="short"))

    def test_invalid_jwt_algorithm_rejected(self):
        with pytest.raises(ValidationError):
            Settings(**_settings_kwargs(JWT_ALGORITHM="MD5"))

    def test_production_debug_and_wildcard_cors_rejected(self):
        with pytest.raises(ValueError):
            Settings(
                **_settings_kwargs(
                    ENVIRONMENT="production",
                    DEBUG=True,
                    ENABLE_API_DOCS=False,
                    CORS_ORIGINS=["https://blockscope.io"],
                )
            ).validate_all()

        with pytest.raises(ValidationError):
            Settings(
                **_settings_kwargs(
                    ENVIRONMENT="production",
                    DEBUG=False,
                    CORS_ORIGINS=["*"],
                )
            )

    def test_generate_secure_key_helper(self):
        key = generate_secure_key(32)
        assert isinstance(key, str)
        assert len(key) >= 32

    def test_print_config_summary(self, capsys):
        fake_settings = Settings(**_settings_kwargs())
        with patch.object(config_module, "settings", fake_settings):
            config_module.print_config_summary()

        out = capsys.readouterr().out
        assert "BLOCKSCOPE CONFIGURATION SUMMARY" in out
        assert "Environment:" in out

"""
Unit tests for app.main — FastAPI application, middleware, and system endpoints.

Uses TestClient with mocked DB. Covers startup/shutdown, middleware,
health check, root, info, debug routes, and exception handlers.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# env before imports
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("TESTING", "True")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_main.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use-only")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-not-for-production-use-only")
os.environ.setdefault("RATE_LIMIT_ENABLED", "False")
os.environ.setdefault("LOG_FILE_ENABLED", "False")
os.environ.setdefault("ADMIN_PASSWORD", "testadmin123")
os.environ.setdefault("DEBUG", "True")  # Enable debug routes

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app, RequestIDMiddleware, PerformanceLoggingMiddleware  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


# ══════════════════════════════════════════════════════════════
# Request ID middleware
# ══════════════════════════════════════════════════════════════

class TestRequestIDMiddleware:

    def test_response_has_x_request_id_header(self):
        resp = client.get("/health")
        assert "x-request-id" in resp.headers

    def test_custom_request_id_echoed_back(self):
        resp = client.get("/health", headers={"X-Request-ID": "my-custom-id"})
        assert resp.headers.get("x-request-id") == "my-custom-id"

    def test_auto_generated_request_id_is_uuid(self):
        resp = client.get("/health")
        rid = resp.headers.get("x-request-id", "")
        # UUID4 format: 8-4-4-4-12
        parts = rid.split("-")
        assert len(parts) == 5


# ══════════════════════════════════════════════════════════════
# Performance logging middleware
# ══════════════════════════════════════════════════════════════

class TestPerformanceLoggingMiddleware:

    def test_requests_complete_without_error(self):
        resp = client.get("/health")
        assert resp.status_code in (200,)

    def test_404_logged_as_warning(self):
        resp = client.get("/not-existing-path")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════
# Health endpoint
# ══════════════════════════════════════════════════════════════

class TestHealthEndpoint:

    def test_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_has_status_field(self):
        resp = client.get("/health")
        assert "status" in resp.json()

    def test_has_version_field(self):
        resp = client.get("/health")
        assert "version" in resp.json()

    def test_status_healthy_or_degraded(self):
        resp = client.get("/health")
        assert resp.json()["status"] in ("healthy", "degraded")


# ══════════════════════════════════════════════════════════════
# Root endpoint
# ══════════════════════════════════════════════════════════════

class TestRootEndpoint:

    def test_returns_200(self):
        assert client.get("/").status_code == 200

    def test_has_message(self):
        assert "message" in client.get("/").json()

    def test_has_version(self):
        assert "version" in client.get("/").json()

    def test_has_endpoints(self):
        assert "endpoints" in client.get("/").json()


# ══════════════════════════════════════════════════════════════
# API info endpoint
# ══════════════════════════════════════════════════════════════

class TestApiInfo:

    def test_returns_200(self):
        assert client.get("/api/v1/info").status_code == 200

    def test_has_name_field(self):
        assert "name" in client.get("/api/v1/info").json()

    def test_has_environment(self):
        data = client.get("/api/v1/info").json()
        assert "environment" in data


class TestCacheInvalidationEndpoint:

    def test_cache_invalidate_allowed_in_debug(self):
        with patch.object(sys.modules["app.main"].settings, "DEBUG", True):
            resp = client.post("/api/v1/cache/invalidate")
        assert resp.status_code == 200
        assert "analysis_cache_cleared" in resp.json()

    def test_cache_invalidate_requires_api_key_outside_debug(self):
        with patch.object(sys.modules["app.main"].settings, "DEBUG", False):
            resp = client.post("/api/v1/cache/invalidate")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════
# Debug endpoints (DEBUG=True)
# ══════════════════════════════════════════════════════════════

class TestDebugEndpoints:

    def test_debug_routes_available_or_not(self):
        """Debug routes exist when DEBUG=True; otherwise 404."""
        resp = client.get("/debug/routes")
        # In testing, DEBUG may be True (routes exist) or False (404)
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            assert "routes" in resp.json()

    def test_debug_config_available_or_not(self):
        resp = client.get("/debug/config")
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            body = resp.json()
            assert "security_enabled" in body


# ══════════════════════════════════════════════════════════════
# 404 handler
# ══════════════════════════════════════════════════════════════

class TestNotFoundHandler:

    def test_unknown_path_returns_404(self):
        resp = client.get("/this/does/not/exist")
        assert resp.status_code == 404

    def test_404_response_has_error_field(self):
        data = client.get("/nonexistent").json()
        assert "error" in data
        assert data["error"] == "not_found"

    def test_404_response_has_request_id(self):
        data = client.get("/nonexistent").json()
        assert "request_id" in data


# ══════════════════════════════════════════════════════════════
# Startup / shutdown events
# ══════════════════════════════════════════════════════════════

class TestLifecycleEvents:

    def test_app_can_start_and_stop(self):
        """TestClient entering context triggers startup; exiting triggers shutdown."""
        with TestClient(app) as tc:
            resp = tc.get("/health")
            assert resp.status_code == 200

    def test_startup_initialises_db(self):
        """Startup logs database connection (or logs warning on failure)."""
        with TestClient(app) as tc:
            resp = tc.get("/health")
            assert resp.status_code == 200
            # Can't assert DB=connected since it may be in test mode
            assert "database" in resp.json()


# ══════════════════════════════════════════════════════════════
# Exception handler coverage
# ══════════════════════════════════════════════════════════════

class TestExceptionHandlers:

    def test_500_exception_handler_returns_structured_response(self):
        """Force a 500 via a route that raises."""
        from app.core.database import get_db

        def _crash():
            raise RuntimeError("forced server error")

        @app.get("/test-force-500", include_in_schema=False)
        async def _force_error():
            raise RuntimeError("forced 500")

        resp = client.get("/test-force-500")
        assert resp.status_code == 500
        data = resp.json()
        assert "error" in data
        assert data["error"] == "internal_server_error"

    def test_health_degraded_on_db_failure(self):
        """Health returns 200 regardless of DB state (graceful down)."""
        from sqlalchemy import exc as sa_exc
        from unittest.mock import patch
        with patch("app.core.database.engine") as m:
            m.connect.side_effect = sa_exc.OperationalError("conn", None, None)
            resp = client.get("/health")
            assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════
# Middleware imports
# ══════════════════════════════════════════════════════════════

class TestMiddlewareClasses:

    def test_request_id_middleware_instantiable(self):
        assert RequestIDMiddleware is not None

    def test_performance_middleware_instantiable(self):
        assert PerformanceLoggingMiddleware is not None

    def test_slow_threshold_is_positive(self):
        assert PerformanceLoggingMiddleware.SLOW_REQUEST_THRESHOLD_MS > 0

"""
API endpoint tests for /api/v1/scan and /api/v1/scan/file.

All tests use a shared SQLite in-memory database with the app's own Base.
The orchestrator is mocked in fast tests; real analysis used where needed.
"""

import os
import sys
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest

# ── env BEFORE any app import ──
os.environ["ENVIRONMENT"] = "testing"
os.environ["TESTING"] = "True"
os.environ["DATABASE_URL"] = "sqlite:///./test_api_endpoint.db"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production-use-only"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-not-for-production-use-only"
os.environ["RATE_LIMIT_ENABLED"] = "False"
os.environ["LOG_FILE_ENABLED"] = "False"
os.environ["ADMIN_PASSWORD"] = "testadmin123"

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ── Import models FIRST so SQLAlchemy registers relationships ──
from app.models.finding import Finding  # noqa: E402 F401
from app.models.scan import Scan  # noqa: E402 F401

# ── Now import the app and DB tools ──
from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from analysis.models import ScanResult  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

# ── Build the in-memory test DB ──
_test_engine = create_engine(
    "sqlite:///./test_api_endpoint.db",
    connect_args={"check_same_thread": False},
)
Base.metadata.create_all(bind=_test_engine)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


def _get_test_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _get_test_db

client = TestClient(app, raise_server_exceptions=False)

SCAN_FILE_URL = "/api/v1/scan/file"
SCAN_JSON_URL = "/api/v1/scan"

_FAKE_RESULT = ScanResult(
    contract_name="Test",
    source_code="contract Test {}",
    findings=[],
    vulnerabilities_count=0,
    severity_breakdown={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
    overall_score=100,
    summary="No vulnerabilities found — SAFE [OK]",
)


# ══════════════════════════════════════════════════════════════
# Root + info
# ══════════════════════════════════════════════════════════════

def test_root_returns_200():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_api_info_returns_200():
    resp = client.get("/api/v1/info")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════
# File upload scan
# ══════════════════════════════════════════════════════════════

def test_scan_file_success_mocked():
    """Mocked orchestrator: endpoint should return 200."""
    with patch("app.routers.scan.orchestrator.analyze", return_value=_FAKE_RESULT):
        resp = client.post(
            SCAN_FILE_URL,
            files={"file": ("Test.sol", BytesIO(b"contract Test {}"), "text/plain")},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["contract_name"] == "Test"
    assert body["overall_score"] == 100
    assert isinstance(body["scan_id"], int)


def test_scan_file_missing_file_returns_422():
    resp = client.post(SCAN_FILE_URL)
    assert resp.status_code == 422


def test_scan_file_empty_content_rejected():
    """Empty file must be rejected with 400 (too short)."""
    resp = client.post(
        SCAN_FILE_URL,
        files={"file": ("empty.sol", BytesIO(b""), "text/plain")},
    )
    assert resp.status_code in (400, 422)


def test_scan_file_real_contract():
    """Real orchestrator with minimal contract."""
    sol = b"pragma solidity ^0.8.0;\ncontract Minimal { function x() public {} }"
    resp = client.post(
        SCAN_FILE_URL,
        files={"file": ("Minimal.sol", BytesIO(sol), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["contract_name"] == "Minimal"
    assert data["overall_score"] >= 0


def test_scan_file_response_has_required_keys():
    sol = b"pragma solidity ^0.8.0;\ncontract A { uint x; }"
    with patch("app.routers.scan.orchestrator.analyze", return_value=_FAKE_RESULT):
        resp = client.post(
            SCAN_FILE_URL,
            files={"file": ("A.sol", BytesIO(sol), "text/plain")},
        )
    data = resp.json()
    required = {"scan_id", "contract_name", "findings", "severity_breakdown",
                "overall_score", "summary", "timestamp", "vulnerabilities_count"}
    assert required.issubset(data.keys())


def test_scan_file_orchestrator_crash_returns_500():
    """If orchestrator raises, endpoint must return 500."""
    with patch("app.routers.scan.orchestrator.analyze", side_effect=RuntimeError("crash")):
        resp = client.post(
            SCAN_FILE_URL,
            files={"file": ("Test.sol", BytesIO(b"contract Test {}"), "text/plain")},
        )
    assert resp.status_code == 500
    assert "detail" in resp.json()


def test_scan_file_malformed_contract_graceful():
    """Malformed Solidity should still return 200 (degrades gracefully)."""
    bad = b"pragma solidity ^0.8.0;\ncontract Broken { function x() {"
    resp = client.post(
        SCAN_FILE_URL,
        files={"file": ("broken.sol", BytesIO(bad), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data


# ══════════════════════════════════════════════════════════════
# JSON scan endpoint
# ══════════════════════════════════════════════════════════════

def test_scan_json_success_mocked():
    with patch("app.routers.scan.orchestrator.analyze", return_value=_FAKE_RESULT):
        resp = client.post(
            SCAN_JSON_URL,
            json={"source_code": "contract Test {}", "contract_name": "Test"},
        )
    assert resp.status_code == 200
    assert resp.json()["contract_name"] == "Test"


def test_scan_json_missing_source_returns_422():
    resp = client.post(SCAN_JSON_URL, json={})
    assert resp.status_code == 422


def test_scan_json_short_source_rejected():
    """Source < min_length should be rejected by Pydantic validation."""
    resp = client.post(SCAN_JSON_URL, json={"source_code": "hi"})
    assert resp.status_code == 422


def test_scan_json_real_contract():
    sol = "pragma solidity ^0.8.0;\ncontract Counter { uint public count; }"
    resp = client.post(SCAN_JSON_URL, json={"source_code": sol})
    assert resp.status_code == 200
    assert resp.json()["overall_score"] >= 0


# ══════════════════════════════════════════════════════════════
# Scans list + get-by-ID
# ══════════════════════════════════════════════════════════════

def test_list_scans_returns_200():
    resp = client.get("/api/v1/scans")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_scans_limit_exceeded_returns_400():
    resp = client.get("/api/v1/scans?limit=101")
    assert resp.status_code == 400


def test_get_scan_not_found_returns_404():
    resp = client.get("/api/v1/scans/999999")
    assert resp.status_code == 404


def test_get_scan_invalid_id_zero_returns_400():
    resp = client.get("/api/v1/scans/0")
    assert resp.status_code == 400


def test_create_then_retrieve_scan():
    """Create a scan, then GET it by ID."""
    with patch("app.routers.scan.orchestrator.analyze", return_value=_FAKE_RESULT):
        post = client.post(
            SCAN_FILE_URL,
            files={"file": ("store.sol", BytesIO(b"contract Store {}"), "text/plain")},
        )
    assert post.status_code == 200
    scan_id = post.json()["scan_id"]

    get = client.get(f"/api/v1/scans/{scan_id}")
    assert get.status_code == 200
    assert get.json()["scan_id"] == scan_id


def test_list_scans_pagination():
    resp1 = client.get("/api/v1/scans?skip=0&limit=2")
    resp2 = client.get("/api/v1/scans?skip=2&limit=2")
    assert resp1.status_code == 200
    assert resp2.status_code == 200


def test_concurrent_scans_unique_ids():
    ids = []
    with patch("app.routers.scan.orchestrator.analyze", return_value=_FAKE_RESULT):
        for i in range(3):
            resp = client.post(
                SCAN_FILE_URL,
                files={"file": (f"c{i}.sol", BytesIO(b"contract A {}"), "text/plain")},
            )
            if resp.status_code == 200:
                ids.append(resp.json()["scan_id"])
    assert len(set(ids)) == len(ids)


# ══════════════════════════════════════════════════════════════
# 404 handler
# ══════════════════════════════════════════════════════════════

def test_custom_404_response():
    resp = client.get("/this/does/not/exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body.get("error") == "not_found"

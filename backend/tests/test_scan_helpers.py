"""
Unit tests for app.routers.scan helper functions.

Tests the pure helper utilities directly without going through HTTP.
These cover branches that the integration tests miss.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("TESTING", "True")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use-only")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-not-for-production-use-only")
os.environ.setdefault("LOG_FILE_ENABLED", "False")
os.environ.setdefault("ADMIN_PASSWORD", "testadmin123")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import HTTPException  # noqa: E402
from app.routers.scan import (  # noqa: E402
    _validate_source_length,
    _findings_to_json,
    _build_scan_record,
    _scan_record_to_response,
    _sanitize_source,
    _api_key_dep,
    _conditional_rate_limit,
    SECURITY_ENABLED,
)
from analysis.models import Finding as PydanticFinding, ScanResult  # noqa: E402
from app.schemas.scan_schema import ScanResponse  # noqa: E402


def _finding(**kwargs) -> PydanticFinding:
    defaults = dict(
        title="Issue",
        severity="high",
        description="Some issue",
        line_number=10,
        code_snippet=None,
        recommendation="Fix it",
    )
    defaults.update(kwargs)
    return PydanticFinding(**defaults)


def _result(**kwargs):
    defaults = dict(
        contract_name="TestContract",
        source_code="contract TestContract {}",
        findings=[],
        vulnerabilities_count=0,
        severity_breakdown={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        overall_score=100,
        summary="No issues",
    )
    defaults.update(kwargs)
    return ScanResult(**defaults)


# ══════════════════════════════════════════════════════════════
# _validate_source_length
# ══════════════════════════════════════════════════════════════

class TestValidateSourceLength:

    def test_valid_source_does_not_raise(self):
        _validate_source_length("contract A {}")  # ~13 chars

    def test_too_short_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_source_length("short")
        assert exc_info.value.status_code == 400
        assert "minimum 10 characters" in exc_info.value.detail

    def test_empty_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_source_length("")
        assert exc_info.value.status_code == 400

    def test_exactly_10_chars_is_valid(self):
        _validate_source_length("x" * 10)  # Should not raise

    def test_too_long_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_source_length("x" * 500_001)
        assert exc_info.value.status_code == 400
        assert "500 KB" in exc_info.value.detail

    def test_exactly_500k_is_valid(self):
        _validate_source_length("x" * 500_000)  # Exactly at limit, should not raise


# ══════════════════════════════════════════════════════════════
# _findings_to_json
# ══════════════════════════════════════════════════════════════

class TestFindingsToJson:

    def test_empty_findings_returns_empty_list(self):
        result = _result(findings=[])
        assert _findings_to_json(result) == []

    def test_converts_finding_to_dict(self):
        f = _finding(title="Reentrancy", severity="critical", line_number=42)
        result = _result(findings=[f])
        json_list = _findings_to_json(result)
        assert len(json_list) == 1
        assert json_list[0]["title"] == "Reentrancy"
        assert json_list[0]["severity"] == "critical"
        assert json_list[0]["line_number"] == 42

    def test_finding_without_line_number(self):
        f = _finding(line_number=None)
        result = _result(findings=[f])
        json_list = _findings_to_json(result)
        assert json_list[0]["line_number"] is None

    def test_multiple_findings(self):
        findings = [_finding(severity=s) for s in ("critical", "high", "low")]
        result = _result(findings=findings)
        json_list = _findings_to_json(result)
        assert len(json_list) == 3


# ══════════════════════════════════════════════════════════════
# _build_scan_record
# ══════════════════════════════════════════════════════════════

class TestBuildScanRecord:

    def test_returns_scan_instance(self):
        from app.models.scan import Scan
        result = _result()
        findings_json = _findings_to_json(result)
        scan = _build_scan_record(result, findings_json)
        assert isinstance(scan, Scan)

    def test_contract_name_set(self):
        result = _result(contract_name="MyToken")
        scan = _build_scan_record(result, [])
        assert scan.contract_name == "MyToken"

    def test_overall_score_set(self):
        result = _result(overall_score=85)
        scan = _build_scan_record(result, [])
        assert scan.overall_score == 85

    def test_findings_json_stored(self):
        f = _finding(title="Bug")
        result = _result(findings=[f])
        json_list = _findings_to_json(result)
        scan = _build_scan_record(result, json_list)
        assert scan.findings == json_list


# ══════════════════════════════════════════════════════════════
# _scan_record_to_response
# ══════════════════════════════════════════════════════════════

class TestScanRecordToResponse:

    def _make_scan(self) -> "app.models.scan.Scan":
        from app.models.scan import Scan
        from datetime import datetime, timezone
        s = Scan(
            id=7,
            contract_name="Test",
            source_code="contract Test {}",
            vulnerabilities_count=0,
            severity_breakdown={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
            overall_score=100,
            summary="No issues",
            findings=[],
            scanned_at=datetime.now(timezone.utc),
        )
        return s

    def test_returns_scan_response(self):
        scan = self._make_scan()
        resp = _scan_record_to_response(scan)
        assert isinstance(resp, ScanResponse)

    def test_scan_id_mapped(self):
        scan = self._make_scan()
        resp = _scan_record_to_response(scan)
        assert resp.scan_id == 7

    def test_findings_empty_list_when_none(self):
        scan = self._make_scan()
        scan.findings = None
        resp = _scan_record_to_response(scan)
        assert resp.findings == []


# ══════════════════════════════════════════════════════════════
# _sanitize_source (no-security path)
# ══════════════════════════════════════════════════════════════

class TestSanitizeSource:

    def test_returns_unchanged_without_security(self):
        if SECURITY_ENABLED:
            pytest.skip("Security is enabled — this tests the no-security path")
        src, name = _sanitize_source("contract A {}", "MyContract")
        assert src == "contract A {}"
        assert name == "MyContract"


# ══════════════════════════════════════════════════════════════
# _api_key_dep / _conditional_rate_limit
# ══════════════════════════════════════════════════════════════

class TestHelperFunctions:

    def test_api_key_dep_returns_callable(self):
        dep = _api_key_dep()
        assert callable(dep)

    def test_conditional_rate_limit_returns_callable(self):
        decorator = _conditional_rate_limit(per_minute=5)
        # Should return a callable (decorator or lambda)
        assert callable(decorator)

    def test_conditional_rate_limit_decorator_passes_through(self):
        decorator = _conditional_rate_limit(per_minute=5)
        def my_func():
            return "hello"
        result = decorator(my_func)
        assert callable(result)

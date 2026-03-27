"""
Extended unit tests for analysis.orchestrator — covers mocked Slither,
rule execution, deduplication edge cases, scoring, summary generation,
and repr.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional
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

from analysis.models import Finding as PydanticFinding, ScanRequest, ScanResult  # noqa: E402
from analysis.orchestrator import AnalysisOrchestrator, _remove_temp_file  # noqa: E402
from analysis.rules.base import Finding as RuleFinding, Severity, VulnerabilityRule  # noqa: E402


# ── Helpers ──────────────────────────────────────────────────

def _finding(title="Issue", severity="high", line=10, desc="description") -> PydanticFinding:
    return PydanticFinding(
        title=title,
        severity=severity,
        description=desc,
        line_number=line,
        code_snippet=None,
        recommendation="Fix it.",
    )


def _request(source="contract A {}", contract_name="A") -> ScanRequest:
    return ScanRequest(source_code=source, contract_name=contract_name, file_path="A.sol")


class _AlwaysFindsRule(VulnerabilityRule):
    """Dummy rule that always returns one finding."""

    def __init__(self):
        super().__init__(rule_id="ALWAYS_FINDS", name="Always finds", severity=Severity.HIGH)

    def detect(self, ast_node) -> List[RuleFinding]:
        return [
            RuleFinding(
                rule_id="ALWAYS_FINDS",
                name="Always Found",
                title="Always Found",
                severity=Severity.HIGH,
                description="Found every time",
                line_number=42,
                code_snippet="...",
                remediation="N/A",
            )
        ]


class _CrashingRule(VulnerabilityRule):
    """Dummy rule that always raises an exception."""

    def __init__(self):
        super().__init__(rule_id="CRASHER", name="Crasher", severity=Severity.LOW)

    def detect(self, ast_node) -> List[RuleFinding]:
        raise RuntimeError("rule crash")


# ══════════════════════════════════════════════════════════════
# Core analyze() function
# ══════════════════════════════════════════════════════════════

class TestAnalyzeCore:

    def test_returns_scan_result(self):
        orc = AnalysisOrchestrator(rules=[])
        result = orc.analyze(_request())
        assert isinstance(result, ScanResult)

    def test_contract_name_used(self):
        orc = AnalysisOrchestrator(rules=[])
        result = orc.analyze(_request(contract_name="MyToken"))
        assert result.contract_name == "MyToken"

    def test_contract_name_extracted_from_source(self):
        orc = AnalysisOrchestrator(rules=[])
        result = orc.analyze(ScanRequest(
            source_code="contract MyDefi {}",
            contract_name=None,
            file_path="x.sol",
        ))
        assert result.contract_name == "MyDefi"

    def test_no_findings_gives_100_score(self):
        orc = AnalysisOrchestrator(rules=[])
        result = orc.analyze(_request())
        assert result.overall_score == 100

    def test_score_decreases_with_findings(self):
        orc = AnalysisOrchestrator(rules=[])
        # Directly inject findings to test scoring
        findings = [_finding(severity="high")]
        score = orc._calculate_score(findings)
        assert score == 95

    def test_summary_safe_when_no_findings(self):
        orc = AnalysisOrchestrator(rules=[])
        result = orc.analyze(_request())
        assert "SAFE" in result.summary or "No vulnerabilities" in result.summary


# ══════════════════════════════════════════════════════════════
# Slither paths (mocked)
# ══════════════════════════════════════════════════════════════

class TestSlitherIntegration:

    def test_slither_unavailable_returns_no_findings(self):
        orc = AnalysisOrchestrator(rules=[])
        with patch.object(orc.slither_wrapper, "available", False):
            result = orc.analyze(_request())
        assert result.vulnerabilities_count == 0

    def test_slither_available_but_parse_fails_gracefully(self):
        orc = AnalysisOrchestrator(rules=[])
        with patch.object(orc.slither_wrapper, "available", True), \
             patch.object(orc.slither_wrapper, "parse_contract", side_effect=RuntimeError("no sol")):
            result = orc.analyze(_request())
        assert isinstance(result, ScanResult)

    def test_slither_available_returns_findings(self):
        orc = AnalysisOrchestrator(rules=[])
        mock_slither = MagicMock()
        mock_slither.detectors_results = [
            {
                "check": "reentrancy",
                "impact": "High",
                "description": "Reentrancy detected",
                "recommendation": "Use checks-effects-interactions",
                "elements": [{"source_mapping": {"lines": [10]}}],
            }
        ]
        with patch.object(orc.slither_wrapper, "available", True), \
             patch.object(orc.slither_wrapper, "parse_contract", return_value=mock_slither):
            slither_findings = orc._run_slither_analysis(_request())
        assert len(slither_findings) >= 1
        assert slither_findings[0].severity in ("critical", "high", "medium", "low")

    def test_slither_finding_without_lines(self):
        orc = AnalysisOrchestrator(rules=[])
        mock_slither = MagicMock()
        mock_slither.detectors_results = [
            {
                "check": "weak",
                "impact": "Low",
                "description": "Weak check",
                "recommendation": "Fix",
                "elements": [],
            }
        ]
        with patch.object(orc.slither_wrapper, "available", True), \
             patch.object(orc.slither_wrapper, "parse_contract", return_value=mock_slither):
            findings = orc._run_slither_analysis(_request())
        assert len(findings) == 1
        assert findings[0].line_number is None

    def test_slither_result_without_detectors_results_attr(self):
        orc = AnalysisOrchestrator(rules=[])
        mock_slither = MagicMock(spec=[])  # no attributes
        with patch.object(orc.slither_wrapper, "available", True), \
             patch.object(orc.slither_wrapper, "parse_contract", return_value=mock_slither):
            findings = orc._run_slither_analysis(_request())
        assert findings == []


# ══════════════════════════════════════════════════════════════
# Rule analysis paths
# ══════════════════════════════════════════════════════════════

class TestRuleAnalysis:

    def test_no_rules_returns_empty(self):
        orc = AnalysisOrchestrator(rules=[])
        findings = orc._run_rule_analysis(_request())
        assert findings == []

    def test_rule_with_available_slither_returns_findings(self):
        orc = AnalysisOrchestrator(rules=[_AlwaysFindsRule()])
        mock_slither_obj = MagicMock()
        with patch.object(orc.slither_wrapper, "available", True), \
             patch.object(orc.slither_wrapper, "parse_contract", return_value=mock_slither_obj), \
             patch.object(orc.slither_wrapper, "get_ast_nodes", return_value=MagicMock()):
            findings = orc._run_rule_analysis(_request())
        assert len(findings) == 1

    def test_crashing_rule_skipped_gracefully(self):
        orc = AnalysisOrchestrator(rules=[_CrashingRule()])
        mock_slither_obj = MagicMock()
        with patch.object(orc.slither_wrapper, "available", True), \
             patch.object(orc.slither_wrapper, "parse_contract", return_value=mock_slither_obj), \
             patch.object(orc.slither_wrapper, "get_ast_nodes", return_value=MagicMock()):
            findings = orc._run_rule_analysis(_request())
        assert findings == []

    def test_rule_analysis_slither_unavailable_skips_rules(self):
        orc = AnalysisOrchestrator(rules=[_AlwaysFindsRule()])
        with patch.object(orc.slither_wrapper, "available", False):
            findings = orc._run_rule_analysis(_request())
        assert findings == []


# ══════════════════════════════════════════════════════════════
# Deduplication
# ══════════════════════════════════════════════════════════════

class TestDeduplication:

    def _orc(self):
        return AnalysisOrchestrator(rules=[])

    def test_identical_findings_deduplicated(self):
        orc = self._orc()
        f1 = _finding(desc="short")
        f2 = _finding(desc="longer description wins")
        result = orc._merge_and_deduplicate([f1], [f2])
        assert len(result) == 1
        assert result[0].description == "longer description wins"

    def test_different_severities_not_deduplicated(self):
        orc = self._orc()
        f1 = _finding(severity="high", line=1)
        f2 = _finding(severity="low", line=2)
        result = orc._merge_and_deduplicate([f1], [f2])
        assert len(result) == 2

    def test_sorted_critical_first(self):
        orc = self._orc()
        f_low = _finding(severity="low", line=100)
        f_critical = _finding(severity="critical", line=200)
        result = orc._merge_and_deduplicate([f_low], [f_critical])
        assert result[0].severity == "critical"

    def test_no_findings_returns_empty(self):
        orc = self._orc()
        assert orc._merge_and_deduplicate([], []) == []


# ══════════════════════════════════════════════════════════════
# Severity breakdown + scoring
# ══════════════════════════════════════════════════════════════

class TestScoringAndBreakdown:

    def _orc(self):
        return AnalysisOrchestrator(rules=[])

    def test_breakdown_all_zeros_for_no_findings(self):
        orc = self._orc()
        breakdown = orc._calculate_severity_breakdown([])
        assert all(v == 0 for v in breakdown.values())

    def test_breakdown_counts_correctly(self):
        orc = self._orc()
        findings = [_finding(severity="critical"), _finding(severity="critical"), _finding(severity="low")]
        bd = orc._calculate_severity_breakdown(findings)
        assert bd["critical"] == 2
        assert bd["low"] == 1

    def test_score_max_100_no_findings(self):
        assert self._orc()._calculate_score([]) == 100

    def test_score_capped_at_zero(self):
        orc = self._orc()
        findings = [_finding(severity="critical")] * 20
        assert orc._calculate_score(findings) == 0

    def test_score_decrements_by_severity(self):
        orc = self._orc()
        findings = [_finding(severity="high")]  # -5
        assert orc._calculate_score(findings) == 95


# ══════════════════════════════════════════════════════════════
# Summary generation
# ══════════════════════════════════════════════════════════════

class TestSummaryGeneration:

    def _orc(self):
        return AnalysisOrchestrator(rules=[])

    def test_summary_safe_when_no_issues(self):
        orc = self._orc()
        s = orc._generate_summary({"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}, 100)
        assert "SAFE" in s or "No vulnerabilities" in s

    def test_summary_unsafe_when_many_criticals(self):
        orc = self._orc()
        bd = {"critical": 5, "high": 3, "medium": 0, "low": 0, "info": 0}
        s = orc._generate_summary(bd, 5)
        assert "FAIL" in s or "UNSAFE" in s

    def test_summary_moderate_score(self):
        orc = self._orc()
        bd = {"critical": 0, "high": 2, "medium": 1, "low": 0, "info": 0}
        s = orc._generate_summary(bd, 90)
        assert s

    def test_summary_risky_score(self):
        orc = self._orc()
        bd = {"critical": 1, "high": 2, "medium": 0, "low": 0, "info": 0}
        s = orc._generate_summary(bd, 50)
        assert s


# ══════════════════════════════════════════════════════════════
# Contract name extraction
# ══════════════════════════════════════════════════════════════

class TestContractNameExtraction:

    def test_extracts_name(self):
        orc = AnalysisOrchestrator(rules=[])
        name = orc._extract_contract_name("pragma solidity ^0.8.0;\ncontract MyContract {}")
        assert name == "MyContract"

    def test_unknown_when_no_contract_keyword(self):
        orc = AnalysisOrchestrator(rules=[])
        name = orc._extract_contract_name("// just a comment")
        assert name == "Unknown"


# ══════════════════════════════════════════════════════════════
# _remove_temp_file utility
# ══════════════════════════════════════════════════════════════

class TestRemoveTempFile:

    def test_none_path_is_safe(self):
        _remove_temp_file(None)  # Must not raise

    def test_missing_file_is_safe(self):
        _remove_temp_file("/nonexistent/path/file.sol")

    def test_removes_existing_file(self, tmp_path):
        f = tmp_path / "test.sol"
        f.write_text("contract A {}")
        _remove_temp_file(str(f))
        assert not f.exists()


# ══════════════════════════════════════════════════════════════
# Repr
# ══════════════════════════════════════════════════════════════

class TestRepr:

    def test_repr_contains_rule_count(self):
        orc = AnalysisOrchestrator(rules=[_AlwaysFindsRule()])
        r = repr(orc)
        assert "rules=1" in r

    def test_repr_is_string(self):
        orc = AnalysisOrchestrator(rules=[])
        assert isinstance(repr(orc), str)

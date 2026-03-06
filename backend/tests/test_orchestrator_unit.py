import pytest
from unittest.mock import patch

from backend.analysis.orchestrator import AnalysisOrchestrator
from backend.analysis.models import ScanRequest
from backend.analysis.rules.base import VulnerabilityRule, Finding as RuleFinding, Severity


# --------------------
# Fixtures
# --------------------

@pytest.fixture
def slither_available(monkeypatch):
    monkeypatch.setattr(
        "backend.analysis.orchestrator.SlitherWrapper.available",
        True,
        raising=False
    )
    monkeypatch.setattr(
        "backend.analysis.orchestrator.SlitherWrapper.parse_contract",
        lambda self, path: object()
    )
    monkeypatch.setattr(
        "backend.analysis.orchestrator.SlitherWrapper.get_ast_nodes",
        lambda self, obj: {"dummy": "ast"}
    )


@pytest.fixture
def scan_request():
    return ScanRequest(
        source_code="contract Test { function foo() public {} }",
        file_path="Test.sol",
        contract_name="Test"
    )


# --------------------
# Dummy Rules
# --------------------

class DummyRule(VulnerabilityRule):
    def __init__(self):
        super().__init__("R001", "Dummy Rule", Severity.LOW)

    def detect(self, ast):
        return [
            RuleFinding(
                rule_id="R001",
                title="Dummy Issue",
                name="Dummy Issue",          # ✅ FIX
                description="Test issue",
                severity=Severity.LOW,
                line_number=10,
                code_snippet="foo()",
                remediation="Fix foo",
            )
        ]



class FailingRule(VulnerabilityRule):
    def __init__(self):
        super().__init__("FAIL", "Failing Rule", Severity.HIGH)

    def detect(self, ast):
        raise RuntimeError("Boom")


class MixedRule(VulnerabilityRule):
    def __init__(self):
        super().__init__("MIX", "Mixed Rule", Severity.CRITICAL)

    def detect(self, ast):
        return [
            RuleFinding(
                rule_id="CRIT",
                title="Critical issue",
                name="Critical issue",       # ✅ FIX
                description="critical issue",
                severity=Severity.CRITICAL,
                line_number=1,
                code_snippet=None,
                remediation="fix",
            ),
            RuleFinding(
                rule_id="HIGH",
                title="High issue",
                name="High issue",           # ✅ FIX
                description="high issue",
                severity=Severity.HIGH,
                line_number=2,
                code_snippet=None,
                remediation="fix",
            ),
            RuleFinding(
                rule_id="LOW",
                title="Low issue",
                name="Low issue",            # ✅ FIX
                description="low issue",
                severity=Severity.LOW,
                line_number=3,
                code_snippet=None,
                remediation="fix",
            ),
        ]



# --------------------
# Tests
# --------------------

def test_analyze_returns_scan_result(slither_available):
    orchestrator = AnalysisOrchestrator(rules=[DummyRule()])
    request = ScanRequest(
        file_path="Test.sol",
        source_code="contract Test { function foo() public {} }",
        contract_name="Test",
    )

    result = orchestrator.analyze(request)

    assert result.contract_name == "Test"
    assert result.vulnerabilities_count == 1
    assert result.findings[0].title == "Dummy Issue"
    assert result.severity_breakdown["low"] == 1
    assert result.overall_score == 99


def test_analyze_with_no_rules_and_no_slither(scan_request):
    orchestrator = AnalysisOrchestrator(rules=[])

    with patch.object(orchestrator.slither_wrapper, "available", False):
        result = orchestrator.analyze(scan_request)

    assert result.vulnerabilities_count == 0
    assert result.overall_score == 100
    assert result.summary.startswith("No vulnerabilities")


def test_rule_failure_does_not_break_analysis(scan_request):
    orchestrator = AnalysisOrchestrator(rules=[FailingRule()])

    with patch.object(orchestrator.slither_wrapper, "available", False):
        result = orchestrator.analyze(scan_request)

    assert result.vulnerabilities_count == 0
    assert result.overall_score == 100


def test_score_calculation_multiple_severities(slither_available):
    orchestrator = AnalysisOrchestrator(rules=[MixedRule()])
    request = ScanRequest(
        file_path="Test.sol",
        source_code="contract Test { function foo() public {} }",
        contract_name="Test",
    )

    result = orchestrator.analyze(request)

    assert result.severity_breakdown == {
        "critical": 1,
        "high": 1,
        "medium": 0,
        "low": 1,
        "info": 0,
    }
    assert result.overall_score == 84  # 100 - 10 - 5 - 1


def test_orchestrator_repr():
    orch = AnalysisOrchestrator(rules=[])
    text = repr(orch)

    assert "AnalysisOrchestrator" in text
    assert "rules=0" in text

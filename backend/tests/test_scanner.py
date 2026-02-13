import pytest

from backend.analysis.scanner import SmartContractScanner
from backend.analysis.rules.base import Finding, VulnerabilityRule


# ----------------------------
# Test helpers
# ----------------------------

class FakeSeverity:
    """Minimal severity object with numeric ordering."""
    def __init__(self, value: int):
        self.value = value


LOW = FakeSeverity(1)
MEDIUM = FakeSeverity(2)
HIGH = FakeSeverity(3)
CRITICAL = FakeSeverity(4)


class DummyRule(VulnerabilityRule):
    rule_id = "DUMMY"

    def __init__(self, findings):
        self._findings = findings

    def detect(self, ast):
        return self._findings


class FailingRule(VulnerabilityRule):
    def __init__(self):
        super().__init__(
            rule_id="FAIL",
            name="Failing Rule",
            severity=MEDIUM,
        )

    def detect(self, ast):
        raise RuntimeError("rule failed")


# ----------------------------
# Scanner tests
# ----------------------------
def make_finding(
    *,
    rule_id="R1",
    title="Test title",
    name="Test Finding",
    description="Test description",
    severity=None,
    line_number=1,
    code_snippet="uint x = 1;",
    remediation="Fix it",
):
    return Finding(
        rule_id=rule_id,
        title=title,
        name=name,
        description=description,
        severity=severity,
        line_number=line_number,
        code_snippet=code_snippet,
        remediation=remediation,
    )

def test_scanner_starts_with_no_rules():
    scanner = SmartContractScanner()
    assert scanner.rules == []


def test_register_rule_adds_rule():
    scanner = SmartContractScanner()
    rule = DummyRule([])

    scanner.register_rule(rule)

    assert scanner.rules == [rule]


def test_scan_runs_registered_rules():
    scanner = SmartContractScanner()

    finding = make_finding(
    rule_id="R1",
    severity=LOW,
)


    scanner.register_rule(DummyRule([finding]))

    results = scanner.scan(ast={})

    assert results == [finding]


def test_scan_combines_findings_from_multiple_rules():
    scanner = SmartContractScanner()

    f1 = make_finding(rule_id="R1", severity=LOW)
    f2 = make_finding(rule_id="R2", severity=HIGH)

    scanner.register_rule(DummyRule([f1]))
    scanner.register_rule(DummyRule([f2]))

    results = scanner.scan(ast={})

    assert len(results) == 2
    assert f1 in results
    assert f2 in results


def test_scan_sorts_findings_by_severity():
    scanner = SmartContractScanner()

    low = make_finding(rule_id="LOW", severity=LOW)
    critical = make_finding(rule_id="CRIT", severity=CRITICAL)

    scanner.register_rule(DummyRule([critical, low]))

    results = scanner.scan(ast={})

    assert results[0].severity.value <= results[1].severity.value


def test_scan_continues_when_rule_raises_exception(capsys):
    scanner = SmartContractScanner()

    good_finding = make_finding(rule_id="OK", severity=MEDIUM)

    scanner.register_rule(FailingRule())
    scanner.register_rule(DummyRule([good_finding]))

    results = scanner.scan(ast={})

    assert results == [good_finding]

    captured = capsys.readouterr()
    assert "Error in FAIL" in captured.out

"""Tests for base rule classes."""

import pytest

from backend.analysis.rules.base import Finding, Severity, VulnerabilityRule


def test_finding_creation():
    """Test creating a Finding object."""
    finding = Finding(
        rule_id="TEST_001",
        name="Test Vulnerability",
        title="Test Vulnerability",
        severity=Severity.CRITICAL,
        description="Test description",
        line_number=42,
        code_snippet="vulnerable code",
        remediation="fix it",
    )

    assert finding.rule_id == "TEST_001"
    assert finding.severity == Severity.CRITICAL
    assert finding.line_number == 42


def test_finding_repr():
    """Test Finding string representation."""
    finding = Finding(
        rule_id="TEST_001",
        name="Test Vulnerability",
        title="Test Vulnerability",
        severity=Severity.HIGH,
        description="Test",
        line_number=10,
        code_snippet="code",
        remediation="fix",
    )

    assert "Test Vulnerability" in repr(finding)
    assert "high" in repr(finding).lower()
    assert "10" in repr(finding)


def test_rule_base_not_implemented():
    """Test that base Rule requires implementation."""

    class IncompleteRule(VulnerabilityRule):
        pass

    rule = IncompleteRule("TEST", "Test", Severity.MEDIUM)

    with pytest.raises(NotImplementedError):
        rule.detect(None)

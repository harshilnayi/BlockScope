"""Smart contract scanner that runs all vulnerability rules."""

from typing import List

from .rules.base import Finding, VulnerabilityRule


class SmartContractScanner:
    """Scanner that orchestrates vulnerability detection rules."""

    def __init__(self):
        self.rules: List[VulnerabilityRule] = []

    def register_rule(self, rule: VulnerabilityRule) -> None:
        """Register a vulnerability rule."""
        self.rules.append(rule)

    def scan(self, ast) -> List[Finding]:
        """
        Scan contract AST against all registered rules.

        Args:
            ast: Abstract syntax tree from Slither

        Returns:
            All findings from all rules
        """
        findings = []
        for rule in self.rules:
            try:
                findings.extend(rule.detect(ast))
            except Exception as e:
                print(f"Error in {rule.rule_id}: {e}")

        return sorted(findings, key=lambda f: f.severity.value)

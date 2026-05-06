"""
Source-based fallback rules for Solidity security scanning.

These rules operate directly on Solidity source code so BlockScope can still
surface meaningful findings when Slither or the local compiler toolchain is
unavailable.
"""

from __future__ import annotations

import re
from typing import Iterable, List

from .models import Finding


def _line_number_for_offset(source_code: str, offset: int) -> int:
    """Convert a string offset into a 1-based line number."""
    return source_code.count("\n", 0, offset) + 1


def _make_finding(
    *,
    title: str,
    severity: str,
    description: str,
    recommendation: str,
    source_code: str,
    match: re.Match[str],
) -> Finding:
    """Build a finding from a regex match."""
    return Finding(
        title=title,
        severity=severity,
        description=description,
        line_number=_line_number_for_offset(source_code, match.start()),
        code_snippet=match.group(0).strip(),
        recommendation=recommendation,
    )


def _find_reentrancy(source_code: str) -> Iterable[Finding]:
    lines = source_code.splitlines()
    state_write_pattern = re.compile(
        r"(?:balances|mapping|owner|admins?|allowance|locked|status|withdrawn)\b[^\n;]*=",
        re.IGNORECASE,
    )
    call_pattern = re.compile(r"\.\s*call\s*(?:\{[^}]*\})?\s*\(", re.IGNORECASE)

    for index, line in enumerate(lines):
        if call_pattern.search(line) is None:
            continue

        lookahead = "\n".join(lines[index + 1 : index + 9])
        if state_write_pattern.search(lookahead) is None:
            continue

        yield Finding(
            title="Potential Reentrancy",
            severity="critical",
            description=(
                "A low-level external call appears before a later state update in the same "
                "function, which is a classic reentrancy risk pattern."
            ),
            line_number=index + 1,
            code_snippet="\n".join(lines[index : index + 4]).strip(),
            recommendation=(
                "Apply checks-effects-interactions, update state before the external call, "
                "or add a reentrancy guard."
            ),
        )


def _find_tx_origin(source_code: str) -> Iterable[Finding]:
    pattern = re.compile(r"\btx\.origin\b")
    for match in pattern.finditer(source_code):
        yield _make_finding(
            title="tx.origin Authentication",
            severity="high",
            description=(
                "Using tx.origin for authorization is unsafe because malicious intermediary "
                "contracts can preserve the original EOA and bypass intended trust boundaries."
            ),
            recommendation="Use msg.sender for authorization checks instead of tx.origin.",
            source_code=source_code,
            match=match,
        )


def _find_selfdestruct(source_code: str) -> Iterable[Finding]:
    pattern = re.compile(r"\b(?:selfdestruct|suicide)\s*\(", re.IGNORECASE)
    for match in pattern.finditer(source_code):
        yield _make_finding(
            title="Dangerous Self-Destruct",
            severity="high",
            description=(
                "Contract destruction primitives are highly sensitive and can permanently "
                "disable functionality or redirect funds if exposed incorrectly."
            ),
            recommendation="Restrict destructive operations to a well-audited admin path or remove them.",
            source_code=source_code,
            match=match,
        )


def _find_delegatecall(source_code: str) -> Iterable[Finding]:
    pattern = re.compile(r"\.\s*delegatecall\s*\(", re.IGNORECASE)
    for match in pattern.finditer(source_code):
        yield _make_finding(
            title="Delegatecall Usage",
            severity="high",
            description=(
                "delegatecall executes external code in the current contract context and can "
                "corrupt storage or bypass security invariants if the target is not strictly trusted."
            ),
            recommendation="Avoid delegatecall where possible, or tightly control the target and storage layout.",
            source_code=source_code,
            match=match,
        )


def _find_unchecked_low_level_calls(source_code: str) -> Iterable[Finding]:
    for index, line in enumerate(source_code.splitlines(), start=1):
        normalized = line.strip()
        if ".call" not in normalized or "delegatecall" in normalized.lower():
            continue
        if "=" in normalized or "require(" in normalized or "if (" in normalized:
            continue

        yield Finding(
            title="Unchecked Low-Level Call",
            severity="medium",
            description=(
                "Low-level calls can fail silently if their return value is ignored, leaving "
                "the contract in an unexpected state."
            ),
            line_number=index,
            code_snippet=normalized,
            recommendation="Capture the success value and handle failures explicitly.",
        )


def run_source_rules(source_code: str) -> List[Finding]:
    """Run all source-based fallback rules against Solidity source code."""
    findings: List[Finding] = []
    rules = (
        _find_reentrancy,
        _find_tx_origin,
        _find_selfdestruct,
        _find_delegatecall,
        _find_unchecked_low_level_calls,
    )
    for rule in rules:
        findings.extend(rule(source_code))
    return findings

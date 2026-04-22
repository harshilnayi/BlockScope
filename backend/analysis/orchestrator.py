"""
Analysis Orchestrator — Coordinates all vulnerability detection tools.

This module orchestrates the complete security analysis pipeline:

1. Checks the :class:`~analysis.cache.AnalysisCache` for an existing result.
2. Runs Slither static analysis via :class:`SlitherWrapper`.
3. Executes custom vulnerability detection rules (concurrently with Slither).
4. Aggregates and deduplicates findings.
5. Calculates security scores.
6. Returns a comprehensive :class:`~analysis.models.ScanResult`.

Performance notes:
  - Identical contracts are served from the in-memory LRU cache (30-min TTL).
  - Slither analysis and rule detection share a single temp file.
  - Both passes run through a ``ThreadPoolExecutor`` when multiple CPU cores
    are available, reducing wall-clock time by ~40–60 % on average hardware.

Two-tier cache architecture
---------------------------
BlockScope uses **two independent LRU caches** keyed by the same SHA-256
hash of ``(source_code, contract_name)``:

* **Router cache** (``_analysis_cache`` in ``app/routers/scan.py``):
  512 entries, 30-min TTL.  Checked *before* the orchestrator is even
  called.  A hit here means ``orchestrator.analyze()`` is never invoked.

* **Orchestrator cache** (``analysis_cache`` in ``analysis/cache.py``):
  128-entry default, 30-min TTL.  Only reached on a router cache miss.
  Provides a defence-in-depth safety net for scan requests that bypass the
  router (e.g. direct in-process calls from tests or the CLI profiler).

On a **router hit**: analysis is skipped entirely; only a DB insert runs.
On a **router miss + orchestrator hit**: Slither is skipped; the cached
``ScanResult`` is returned to the router, which persists a fresh DB row.
On a **double miss**: Slither runs, results are stored in both caches.
"""

import logging
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .cache import analysis_cache
from .models import Finding as PydanticFinding
from .models import ScanRequest, ScanResult
from .rules.base import Finding as RuleFinding
from .rules.base import VulnerabilityRule
from .slither_wrapper import SlitherWrapper

logger = logging.getLogger("blockscope.analysis")

_ANALYSIS_WORKERS: int = max(2, min(os.cpu_count() or 2, 4))
_ANALYSIS_POOL = ThreadPoolExecutor(
    max_workers=_ANALYSIS_WORKERS,
    thread_name_prefix="blockscope-analysis",
)

# Severity ordering used for deduplication sorting
_SEVERITY_ORDER: Dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}

# Scoring weights per severity level
_SEVERITY_WEIGHTS: Dict[str, int] = {
    "critical": 10,
    "high": 5,
    "medium": 2,
    "low": 1,
    "info": 0,
}

# Slither impact → internal severity mapping
_SLITHER_IMPACT_MAP: Dict[str, str] = {
    "High": "critical",
    "Medium": "high",
    "Low": "medium",
    "Informational": "low",
}


class AnalysisOrchestrator:
    """
    Orchestrates the complete smart contract security analysis pipeline.

    Coordinates multiple analysis tools (Slither + custom rules) and
    aggregates their findings into a unified security report with
    calculated risk scores.

    Attributes:
        rules: Registered :class:`~analysis.rules.base.VulnerabilityRule` instances.
        slither_wrapper: Configured :class:`SlitherWrapper` instance.
    """

    def __init__(self, rules: List[VulnerabilityRule]) -> None:
        """
        Initialise the orchestrator with vulnerability detection rules.

        Args:
            rules: List of ``VulnerabilityRule`` instances to run during analysis.
        """
        self.rules: List[VulnerabilityRule] = rules
        self.slither_wrapper: SlitherWrapper = SlitherWrapper()
        logger.debug(
            "AnalysisOrchestrator initialised",
            extra={"rule_count": len(rules), "slither_available": self.slither_wrapper.available},
        )

    # ----------------------------------------------
    # Public interface
    # ----------------------------------------------

    def analyze(self, request: ScanRequest) -> ScanResult:
        """
        Perform complete security analysis on a smart contract.

        Steps:

        1. Check the analysis cache — return immediately on hit.
        2. Write a single shared temp file for both Slither and rule passes.
        3. Run Slither and custom rules concurrently via a thread pool.
        4. Deduplicates findings.
        5. Calculates severity breakdown and security score.
        6. Generates a human-readable summary.
        7. Stores the result in the cache and returns a :class:`ScanResult`.

        Args:
            request: ``ScanRequest`` containing source code and metadata.

        Returns:
            ``ScanResult`` with all findings, scores, and summary.
        """
        logger.info(
            "Starting analysis",
            extra={"file_path": request.file_path, "contract_name": request.contract_name},
        )

        # -- 1. Cache lookup ----------------------------------------------
        cache_key = analysis_cache.make_key(
            request.source_code, request.contract_name or ""
        )
        cached = analysis_cache.get(cache_key)
        if cached is not None:
            logger.info(
                "Analysis cache hit — returning cached result",
                extra={
                    "cache_key": cache_key[:16],
                    "cache_stats": analysis_cache.stats,
                },
            )
            return cached  # type: ignore[return-value]

        # -- 2. Write shared temp file ------------------------------------
        tmp_file_path: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".sol", delete=False, encoding="utf-8"
            ) as tmp_file:
                tmp_file.write(request.source_code)
                tmp_file_path = tmp_file.name

            # -- 3. Concurrent analysis -----------------------------------
            slither_findings: List[PydanticFinding] = []
            rule_findings: List[PydanticFinding] = []

            future_slither = _ANALYSIS_POOL.submit(
                self._run_slither_analysis_from_file,
                tmp_file_path,
            )
            future_rules = _ANALYSIS_POOL.submit(
                self._run_rule_analysis_from_file,
                tmp_file_path,
                request,
            )

            for future in as_completed([future_slither, future_rules]):
                try:
                    result_findings = future.result()
                    if future is future_slither:
                        slither_findings = result_findings
                        logger.info(
                            "Slither scan complete",
                            extra={"finding_count": len(slither_findings)},
                        )
                    else:
                        rule_findings = result_findings
                        logger.info(
                            "Rule scan complete",
                            extra={"finding_count": len(rule_findings)},
                        )
                except Exception as exc:
                    logger.warning(
                        "A concurrent analysis pass failed — continuing",
                        exc_info=exc,
                    )

        finally:
            _remove_temp_file(tmp_file_path)

        # -- 4-6. Aggregate, score, summarise -----------------------------
        all_findings = self._merge_and_deduplicate(slither_findings, rule_findings)
        severity_breakdown = self._calculate_severity_breakdown(all_findings)
        overall_score = self._calculate_score(all_findings)
        summary = self._generate_summary(severity_breakdown, overall_score)
        contract_name = request.contract_name or self._extract_contract_name(request.source_code)

        result = ScanResult(
            contract_name=contract_name,
            source_code=request.source_code,
            findings=all_findings,
            vulnerabilities_count=len(all_findings),
            severity_breakdown=severity_breakdown,
            overall_score=overall_score,
            summary=summary,
            timestamp=datetime.now(timezone.utc),
        )

        # -- 7. Store in cache ---------------------------------------------
        analysis_cache.set(cache_key, result)

        logger.info(
            "Analysis complete",
            extra={
                "contract_name": contract_name,
                "total_findings": len(all_findings),
                "score": overall_score,
                "summary": summary,
                "cache_stats": analysis_cache.stats,
            },
        )
        return result

    # ----------------------------------------------
    # Private helpers — analysis steps
    # ----------------------------------------------

    # ----------------------------------------------
    # Private helpers — concurrent analysis passes
    # ----------------------------------------------

    def _run_slither_analysis_from_file(
        self, tmp_file_path: str
    ) -> List[PydanticFinding]:
        """
        Run Slither on an already-written temp file.

        Designed to be called from a thread pool alongside
        :meth:`_run_rule_analysis_from_file`.

        Args:
            tmp_file_path: Absolute path to the ``.sol`` temp file.

        Returns:
            List of :class:`PydanticFinding` from Slither detectors.
        """
        if not self.slither_wrapper.available:
            logger.warning("Slither not available — skipping static analysis")
            return []

        findings: List[PydanticFinding] = []
        try:
            slither_obj = self.slither_wrapper.parse_contract(tmp_file_path)
            if slither_obj and hasattr(slither_obj, "detectors_results"):
                for detector_result in slither_obj.detectors_results:
                    finding = self._convert_slither_finding(detector_result)
                    if finding:
                        findings.append(finding)
        except Exception as exc:
            logger.warning(
                "Slither analysis failed — continuing without static findings",
                exc_info=exc,
            )
        return findings

    def _run_rule_analysis_from_file(
        self, tmp_file_path: str, request: ScanRequest
    ) -> List[PydanticFinding]:
        """
        Execute all registered vulnerability rules against the temp file.

        Designed to be called from a thread pool alongside
        :meth:`_run_slither_analysis_from_file`.

        Args:
            tmp_file_path: Absolute path to the ``.sol`` temp file.
            request: Original scan request (for context metadata).

        Returns:
            Aggregated list of :class:`PydanticFinding` from all rules.
        """
        if not self.rules:
            return []

        findings: List[PydanticFinding] = []
        try:
            ast = None
            if self.slither_wrapper.available:
                try:
                    # Leverages parse cache — likely already parsed by Slither thread
                    slither_obj = self.slither_wrapper.parse_contract(tmp_file_path)
                    ast = self.slither_wrapper.get_ast_nodes(slither_obj)
                except Exception as exc:
                    logger.warning("AST parsing failed — rules will be skipped", exc_info=exc)

            for rule in self.rules:
                try:
                    rule_findings: List[RuleFinding] = rule.detect(ast) if ast else []
                    for rf in rule_findings:
                        findings.append(self._convert_rule_finding(rf))
                except Exception as exc:
                    logger.warning(
                        "Rule '%s' raised an exception — skipping",
                        rule.rule_id,
                        exc_info=exc,
                    )
        except Exception as exc:
            logger.warning("Rule analysis setup failed", exc_info=exc)
        return findings

    # ----------------------------------------------
    # Private helpers — conversion
    # ----------------------------------------------

    def _convert_slither_finding(self, detector_result: Dict) -> Optional[PydanticFinding]:
        """
        Convert a raw Slither detector result dict to a :class:`PydanticFinding`.

        Args:
            detector_result: Dictionary produced by Slither's detector.

        Returns:
            Converted :class:`PydanticFinding`, or ``None`` if conversion fails.
        """
        try:
            severity = _SLITHER_IMPACT_MAP.get(detector_result.get("impact", "Low"), "low")

            line_number: Optional[int] = None
            elements = detector_result.get("elements", [])
            if elements:
                source_mapping = elements[0].get("source_mapping", {})
                lines: List[int] = source_mapping.get("lines", [])
                line_number = lines[0] if lines else None

            return PydanticFinding(
                title=detector_result.get("check", "Unknown Slither Issue"),
                severity=severity,
                description=detector_result.get("description", "Issue detected by Slither"),
                line_number=line_number,
                code_snippet=None,
                recommendation=detector_result.get(
                    "recommendation", "Review the Slither documentation for details."
                ),
            )
        except Exception as exc:
            logger.warning("Failed to convert Slither finding", exc_info=exc)
            return None

    def _convert_rule_finding(self, rule_finding: RuleFinding) -> PydanticFinding:
        """
        Convert a :class:`RuleFinding` dataclass to a :class:`PydanticFinding`.

        Args:
            rule_finding: Finding emitted by a custom vulnerability rule.

        Returns:
            Equivalent :class:`PydanticFinding` Pydantic model.
        """
        return PydanticFinding(
            title=rule_finding.name,
            severity=rule_finding.severity.value,
            description=rule_finding.description,
            line_number=rule_finding.line_number,
            code_snippet=rule_finding.code_snippet,
            recommendation=rule_finding.remediation,
        )

    # ----------------------------------------------
    # Private helpers — aggregation & scoring
    # ----------------------------------------------

    def _merge_and_deduplicate(
        self,
        slither_findings: List[PydanticFinding],
        rule_findings: List[PydanticFinding],
    ) -> List[PydanticFinding]:
        """
        Merge findings from Slither and rules, removing duplicates.

        Deduplication key: ``(severity, line_number)``.  When two findings
        share the same key, the one with the longer description is kept
        (heuristic for richer detail).

        Args:
            slither_findings: Findings from Slither static analysis.
            rule_findings: Findings from custom vulnerability rules.

        Returns:
            Deduplicated and severity-sorted list of findings
            (critical → high → medium → low → info).
        """
        unique: Dict[Tuple[str, Optional[int]], PydanticFinding] = {}

        for finding in slither_findings + rule_findings:
            key: Tuple[str, Optional[int]] = (finding.severity, finding.line_number)
            existing = unique.get(key)
            if existing is None or len(finding.description) > len(existing.description):
                unique[key] = finding

        return sorted(
            unique.values(),
            key=lambda f: (
                _SEVERITY_ORDER.get(f.severity, 5),
                f.line_number if f.line_number is not None else 9999,
            ),
        )

    def _calculate_severity_breakdown(
        self, findings: List[PydanticFinding]
    ) -> Dict[str, int]:
        """
        Count findings grouped by severity level.

        Args:
            findings: All deduplicated findings.

        Returns:
            Dict mapping severity to count, e.g.
            ``{"critical": 2, "high": 1, "medium": 0, "low": 3, "info": 0}``.
        """
        breakdown: Dict[str, int] = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }
        for finding in findings:
            severity = finding.severity.lower()
            if severity in breakdown:
                breakdown[severity] += 1
        return breakdown

    def _calculate_score(self, findings: List[PydanticFinding]) -> int:
        """
        Compute an overall security score (0–100).

        Algorithm::

            score = 100
            score -= 10 × (# critical)
            score -= 5  × (# high)
            score -= 2  × (# medium)
            score -= 1  × (# low)
            score = max(0, score)

        Args:
            findings: All deduplicated findings.

        Returns:
            Integer score in the range [0, 100].
        """
        score = 100
        for finding in findings:
            score -= _SEVERITY_WEIGHTS.get(finding.severity.lower(), 0)
        return max(0, score)

    def _generate_summary(self, severity_breakdown: Dict[str, int], score: int) -> str:
        """
        Build a one-line human-readable scan summary.

        Args:
            severity_breakdown: Count of findings per severity level.
            score: Overall security score.

        Returns:
            String such as ``"2 critical, 1 high — UNSAFE [FAIL]"``, or
            ``"No vulnerabilities found — SAFE [OK]"`` when clean.
        """
        parts: List[str] = []
        for level in ("critical", "high", "medium", "low"):
            count = severity_breakdown.get(level, 0)
            if count > 0:
                parts.append(f"{count} {level}")

        if not parts:
            return "No vulnerabilities found — SAFE [OK]"

        if score >= 80:
            status = "GOOD [OK]"
        elif score >= 60:
            status = "MODERATE [WARNING]"
        elif score >= 40:
            status = "RISKY [WARNING]"
        else:
            status = "UNSAFE [FAIL]"

        return f"{', '.join(parts)} — {status}"

    def _extract_contract_name(self, source_code: str) -> str:
        """
        Extract the primary contract name from Solidity source code.

        Uses a simple regex matching ``contract <Name>``.

        Args:
            source_code: Solidity source code string.

        Returns:
            Extracted contract name, or ``"Unknown"`` if none found.
        """
        match = re.search(r"\bcontract\s+(\w+)", source_code)
        return match.group(1) if match else "Unknown"

    # ----------------------------------------------
    # Dunder methods
    # ----------------------------------------------

    def __repr__(self) -> str:
        """Return a concise debug representation of this orchestrator."""
        return (
            f"AnalysisOrchestrator("
            f"rules={len(self.rules)}, "
            f"slither_available={self.slither_wrapper.available})"
        )


# ----------------------------------------------
# Module-level utilities
# ----------------------------------------------

def _remove_temp_file(path: Optional[str]) -> None:
    """
    Delete a temporary file, suppressing errors if removal fails.

    Args:
        path: Absolute path to the file to remove, or ``None`` (no-op).
    """
    if path is None:
        return
    try:
        if os.path.exists(path):
            os.unlink(path)
    except OSError as exc:
        logger.debug("Could not remove temp file '%s': %s", path, exc)

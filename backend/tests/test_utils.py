from backend.analysis.orchestrator import AnalysisOrchestrator
from backend.analysis.models import Finding


def test_score_calculation_basic():
    orch = AnalysisOrchestrator([])
    score = orch._calculate_score([])
    assert score == 100


def test_score_never_negative():
    orch = AnalysisOrchestrator([])

    fake = [
        Finding(
            rule_id="R",
            title="Test",
            name="x",
            severity="critical",
            description="x",
            line_number=1,
            code_snippet="x",
            remediation="x"
        )
    ] * 50

    score = orch._calculate_score(fake)
    assert score >= 0


def test_summary_generation():
    orch = AnalysisOrchestrator([])
    s = orch._generate_summary({"high": 1}, 70)
    assert isinstance(s, str)


def test_merge_deduplication():
    orch = AnalysisOrchestrator([])

    a = [
        Finding(
            rule_id="1",
            title="Test",
            name="x",
            severity="low",
            description="x",
            line_number=1,
            code_snippet="x",
            remediation="x"
        )
    ]

    b = [
        Finding(
            rule_id="1",
            title="Test",
            name="x",
            severity="low",
            description="x",
            line_number=1,
            code_snippet="x",
            remediation="x"
        )
    ]

    r = orch._merge_and_deduplicate(a, b)
    assert len(r) == 1

import pytest
from backend.app.models.base import Base

@pytest.fixture(autouse=True)
def clear_metadata():
    """
    Prevent SQLAlchemy table re-definition errors during test collection.
    """
    Base.metadata.clear()

def test_scan_model_creation():
    from backend.app.models import Scan
    scan = Scan(
        contract_name="A",
        source_code="code",
        status="completed",
        overall_score=90,
        summary="ok",
        vulnerabilities_count=0,
        severity_breakdown={},
        findings=[],
        scanned_at=None,
    )
    assert scan.contract_name == "A"


def test_vulnerability_model():
    from backend.app.models import Finding
    f = Finding(
        scan_id=1,
        rule_id="R1",
        name="Test",
        severity="high",
        description="d",
        line_number=1,
        code_snippet="x",
        remediation="fix",
    )
    assert f.severity == "high"


def test_relationships():
    from backend.app.models import Scan, Finding
    scan = Scan.__table__.name
    finding = Finding.__table__.name
    assert scan == "scans"
    assert finding == "findings"


def test_constraints():
    from backend.app.models import Finding
    assert Finding.rule_id.property.columns[0].nullable is False


def test_data_validation():
    from backend.app.models import Finding
    assert isinstance(Finding.severity.type.length, int)

from app.models.scan import Scan, Finding

def test_scan_model_creation():
    scan = Scan(
        contract_name="A",
        source_code="code",
        status="completed",
        overall_score=90,
        summary="ok",
        vulnerabilities_count=0,
        severity_breakdown={},
        findings=[],
        scanned_at=None
    )
    assert scan.contract_name == "A"

def test_vulnerability_model():
    f = Finding(
        scan_id=1,
        rule_id="R1",
        name="Test",
        severity="high",
        description="d",
        line_number=1,
        code_snippet="x",
        remediation="fix"
    )
    assert f.severity == "high"

def test_relationships():
    scan = Scan.__table__.name
    finding = Finding.__table__.name
    assert scan == "scans"
    assert finding == "findings"

def test_constraints():
    assert Finding.rule_id.property.columns[0].nullable is False

def test_data_validation():
    assert isinstance(Finding.severity.type.length, int)

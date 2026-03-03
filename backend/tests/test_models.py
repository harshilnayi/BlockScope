import pytest
from app.models.finding import Finding
from app.models.scan import Scan
from sqlalchemy.orm import configure_mappers


def test_scan_table_definition():
    assert Scan.__tablename__ == "scans"
    assert Scan.contract_name.property.columns[0].nullable is False


def test_finding_table_definition():
    assert Finding.__tablename__ == "findings"
    assert Finding.severity.property.columns[0].nullable is False


def test_constraints():
    assert Finding.rule_id.property.columns[0].nullable is False


def test_data_validation():
    assert isinstance(Finding.severity.type.length, int)

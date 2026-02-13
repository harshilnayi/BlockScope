from urllib import response
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from io import BytesIO

from backend.app.main import app
from backend.analysis.models import ScanResult

client = TestClient(app)
SCAN_URL = "/api/v1/scan"


def test_scan_endpoint_success():
    fake_result = ScanResult(
        contract_name="Test",
        source_code="contract Test {}",
        findings=[],
        vulnerabilities_count=0,
        severity_breakdown={
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        },
        overall_score=100,
        summary="No vulnerabilities found - SAFE ✅",
    )

    with patch(
        "backend.app.routers.scan.orchestrator.analyze",
        return_value=fake_result,
    ):
        response = client.post(
            SCAN_URL,
            files={
                "file": (
                    "Test.sol",
                    BytesIO(b"contract Test {}"),
                    "text/plain",
                )
            },
        )

    assert response.status_code == 200
    body = response.json()

    assert body["contract_name"] == "Test"
    assert body["overall_score"] == 100
    assert body["summary"].startswith("No vulnerabilities")


def test_scan_endpoint_validation_error():
    # Missing file → API explicitly raises 400
    response = client.post(SCAN_URL)

    assert response.status_code == 400
    assert response.json()["detail"] == "file is required"


def test_scan_endpoint_internal_error():
    """
    Orchestrator failures are handled internally and
    should NOT crash the API.
    """

    with patch(
        "backend.app.routers.scan.orchestrator.analyze",
        side_effect=RuntimeError("boom"),
    ):
        response = client.post(
            SCAN_URL,
            files={
                "file": (
                    "Test.sol",
                    BytesIO(b"contract Test {}"),
                    "text/plain",
                )
            },
        )

    assert response.status_code == 200
    body = response.json()

    assert body["overall_score"] == 100
    assert body["summary"].startswith("No vulnerabilities")



def test_successful_scan(client):
    file_content = b"""
    pragma solidity ^0.8.0;
    contract Test {
        function x() public {}
    }
    """

    response = client.post(
        "/api/v1/scan",
        files={"file": ("test.sol", file_content, "text/plain")},
    )

    assert response.status_code == 200
    data = response.json()

    assert "scan_id" in data
    assert isinstance(data["scan_id"], int)
    assert data["contract_name"] == "test"
    assert "scan_id" in data
    assert data["overall_score"] >= 0


def test_invalid_file_type(client):
    response = client.post(
        "/api/v1/scan",
        files={"file": ("bad.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400
    assert response.status_code == 400
    assert "only .sol files allowed" in response.text.lower()


def test_malformed_contract(client):
    bad_contract = b"""
    pragma solidity ^0.8.0;
    contract Broken {
        function x() public {
    """

    response = client.post(
        "/api/v1/scan",
        files={"file": ("broken.sol", bad_contract, "text/plain")},
    )

    assert response.status_code == 200
    data = response.json()

    # Scan still created, but analysis should fail gracefully
    assert "summary" in data
    assert "severity_breakdown" in data


def test_empty_file(client):
    response = client.post(
        "/api/v1/scan",
        files={"file": ("empty.sol", b"", "text/plain")},
    )

    assert response.status_code == 400

def test_response_format(client):
    response = client.post(
        "/api/v1/scan",
        files={"file": ("test.sol", b"contract A {}", "text/plain")},
    )

    data = response.json()

    required_keys = {
    "scan_id",
    "contract_name",
    "vulnerabilities",
    "severity_breakdown",
    "overall_score",
    "summary",
    "scan_timestamp",
}

    assert required_keys.issubset(data.keys())

def test_scan_status_updates(client):
    response = client.post(
        "/api/v1/scan",
        files={"file": ("test.sol", b"contract A {}", "text/plain")},
    )

    scan_id = response.json()["scan_id"]
    assert isinstance(scan_id, int)

    get_resp = client.get(f"/api/v1/scans/{scan_id}")
    assert get_resp.status_code == 200

    data = get_resp.json()
    assert data["scan_id"] == scan_id
    assert "summary" in data
    
def test_concurrent_scans(client):
    responses = []

    for i in range(3):
        resp = client.post(
            "/api/v1/scan",
            files={"file": (f"c{i}.sol", b"contract A {}", "text/plain")},
        )
        responses.append(resp)

    ids = [r.json()["scan_id"] for r in responses]
    assert len(ids) == len(set(ids))
    assert len(set(ids)) == 3


import time
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


# -----------------------------
# Test contracts (5 types)
# -----------------------------
CONTRACTS = {
    "clean": (
        "Clean.sol",
        """
        pragma solidity ^0.8.0;
        contract Clean {
            uint256 public x;
        }
        """,
        200,
    ),
    "broken": (
        "Broken.sol",
        """
        pragma solidity ^0.8.0;
        contract Broken {
            uint256 public x
        """,
        200,  # system should recover safely
    ),
    "empty": (
        "Empty.sol",
        "",
        400,
    ),
    "large": (
        "Large.sol",
        "pragma solidity ^0.8.0;\ncontract Large {" + "uint x;\n" * 20000 + "}",
        200,
    ),
    "invalid_ext": (
        "Invalid.txt",
        "not solidity",
        400,
    ),
}


def upload_contract(filename: str, content: str):
    """Helper to upload contract as multipart/form-data"""
    return client.post(
        "/api/v1/scan",
        files={"file": (filename, content, "text/plain")},
    )


def get_scan(scan_id: int):
    return client.get(f"/api/v1/scans/{scan_id}")


# -----------------------------
# FULL END-TO-END FLOW
# -----------------------------
@pytest.mark.integration
def test_full_scan_flow():
    """
    End-to-End integration test:
    Upload → Analyze → Store → Retrieve
    Covers 5 contract types
    Verifies correctness + performance
    """

    for name, (filename, source, expected_status) in CONTRACTS.items():
        start_time = time.time()

        response = upload_contract(filename, source)

        duration = time.time() - start_time

        # -------- Status check --------
        assert response.status_code == expected_status, f"{name} failed"

        if expected_status != 200:
            continue

        data = response.json()

        # -------- Basic response integrity --------
        assert "scan_id" in data
        assert data["scan_id"] is not None
        assert data["contract_name"] == filename.replace(".sol", "")
        assert "overall_score" in data
        assert "summary" in data
        assert "severity_breakdown" in data
        assert "vulnerabilities" in data

        # -------- Data consistency --------
        assert data["overall_score"] >= 0
        assert isinstance(data["severity_breakdown"], dict)
        assert isinstance(data["vulnerabilities"], list)

        vuln_count = len(data["vulnerabilities"])
        breakdown_total = sum(data["severity_breakdown"].values())
        assert vuln_count == breakdown_total

        # -------- Stored & retrievable --------
        scan_id = data["scan_id"]
        stored = get_scan(scan_id)

        assert stored.status_code == 200
        stored_data = stored.json()

        assert stored_data["scan_id"] == scan_id
        assert stored_data["overall_score"] == data["overall_score"]
        assert stored_data["summary"] == data["summary"]

        # -------- Performance benchmark --------
        assert duration < 2.0, f"Scan too slow: {duration}s"

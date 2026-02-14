import time
import pytest
from datetime import datetime, timezone



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
        200,
    ),
    "empty": (
        "Empty.sol",
        "",
        400,
    ),
    "large": (
        "Large.sol",
        None,
        200,
    ),
    "invalid_ext": (
        "Invalid.txt",
        "not solidity",
        400,
    ),
}


# -----------------------------
# FULL END-TO-END FLOW
# -----------------------------
@pytest.mark.integration
@pytest.mark.parametrize(
    "name,filename,source,expected_status",
    [(k, *v) for k, v in CONTRACTS.items()],
)
def test_full_scan_flow(client, name, filename, source, expected_status):
    
    if name == "large":
        source = (
        "pragma solidity ^0.8.0;\n"
        "contract Large {\n" +
        ("uint x;\n" * 20_000) +
        "}"
    )
    start_time = time.time()

    response = client.post(
        "/api/v1/scan",
        files={"file": (filename, source, "text/plain")},
    )

    duration = time.time() - start_time

    # -------- Status check --------
    assert response.status_code == expected_status, f"{name} failed"

    if expected_status != 200:
        return

    data = response.json()

    # -------- Large payload validation --------
    if name == "large":
        assert len(source.encode()) > 100_000  # ~100 KB

    # -------- Basic response integrity --------
    assert data["scan_id"] is not None
    assert data["contract_name"] == filename.replace(".sol", "")
    assert "overall_score" in data
    assert "summary" in data
    assert "severity_breakdown" in data
    assert "vulnerabilities" in data

    # -------- Data consistency --------
    vuln_count = len(data["vulnerabilities"])
    breakdown_total = sum(data["severity_breakdown"].values())
    assert vuln_count == breakdown_total

    # -------- Stored & retrievable --------
    scan_id = data["scan_id"]
    stored = client.get(f"/api/v1/scans/{scan_id}")
    assert stored.status_code == 200

    stored_data = stored.json()
    assert stored_data["scan_id"] == scan_id
    assert stored_data["overall_score"] == data["overall_score"]
    assert stored_data["summary"] == data["summary"]
    assert stored_data["contract_name"] == filename.replace(".sol", "")
    assert isinstance(stored_data["scan_timestamp"], str)
    assert stored_data["vulnerabilities"] == data["vulnerabilities"]
    assert isinstance(stored_data["scan_timestamp"], str)

    # -------- Timestamp validation --------
    scan_time = datetime.fromisoformat(stored_data["scan_timestamp"])
    assert scan_time.tzinfo is None or scan_time.tzinfo == timezone.utc
    assert abs((datetime.utcnow() - scan_time).total_seconds()) < 60

    # -------- Performance benchmark --------
    assert duration < 2.0, f"Scan too slow: {duration}s"

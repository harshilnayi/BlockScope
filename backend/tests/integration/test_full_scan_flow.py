import time
from datetime import datetime, timezone

import pytest

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
        400,  # Empty file is rejected: source too short
    ),
    "large": (
        "Large.sol",
        None,
        200,
    ),
    "invalid_ext": (
        "Invalid.txt",
        "not solidity",
        None,  # 400 with security module, 200/400 without — checked in test body
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
        source = "pragma solidity ^0.8.0;\n" "contract Large {\n" + ("uint x;\n" * 20_000) + "}"
    start_time = time.time()

    response = client.post(
        "/api/v1/scan/file",
        files={"file": (filename, source, "text/plain")},
    )

    duration = time.time() - start_time

    # -------- Status check --------
    if expected_status is None:
        # dynamic: security-dependent, just check it's a recognized status
        assert response.status_code in (200, 400, 422), f"{name} returned unexpected status"
        return

    assert response.status_code == expected_status, (
        f"{name} failed: expected {expected_status}, got {response.status_code}\n"
        f"Response: {response.text[:200]}"
    )

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
    assert "findings" in data

    # -------- Data consistency --------
    vuln_count = len(data["findings"])
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
    assert isinstance(stored_data["timestamp"], str)
    assert stored_data["findings"] == data["findings"]
    assert isinstance(stored_data["timestamp"], str)

    # -------- Timestamp validation --------
    scan_time = datetime.fromisoformat(stored_data["timestamp"])
    assert scan_time.tzinfo is None or scan_time.tzinfo == timezone.utc
    assert abs((datetime.now(timezone.utc).replace(tzinfo=None) - scan_time.replace(tzinfo=None)).total_seconds()) < 60

    # -------- Performance benchmark --------
    assert duration < 5.0, f"Scan too slow: {duration}s"

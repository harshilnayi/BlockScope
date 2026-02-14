import pytest

def test_slither_execution_path(client, tmp_path):
    """
    Integration test for Slither execution path.

    This test verifies:
    - API works when Slither is available
    - API degrades gracefully when Slither is NOT available
    - We can clearly detect which path was taken
    """

    sol_file = tmp_path / "Test.sol"
    sol_file.write_text(
        "pragma solidity ^0.8.0; contract Test { uint256 public x; }"
    )

    with open(sol_file, "rb") as f:
        res = client.post(
            "/api/v1/scan",
            files={"file": ("Test.sol", f, "text/plain")},
        )

    # -------- Slither AVAILABLE path --------
    if res.status_code == 200:
        data = res.json()

        # Core response must exist
        assert "overall_score" in data
        assert "summary" in data
        assert "severity_breakdown" in data
        assert "vulnerabilities" in data

        # Slither-specific expectation:
        # Even if no vulns found, structure must be correct
        assert isinstance(data["vulnerabilities"], list)
        assert isinstance(data["severity_breakdown"], dict)

        # Explicitly document which path ran
        print("✔ Slither available: analysis executed")

    # -------- Slither NOT AVAILABLE path --------
    elif res.status_code == 400:
        error = res.json()

        # API must fail gracefully, not crash
        assert "detail" in error
        assert "file" not in error["detail"].lower()

        print("⚠ Slither not available: graceful degradation")

    # -------- Anything else is a real failure --------
    else:
        pytest.fail(f"Unexpected status code: {res.status_code}")

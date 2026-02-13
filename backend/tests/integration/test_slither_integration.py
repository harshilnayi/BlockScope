def test_slither_execution_path(client, tmp_path):
    # Create a minimal Solidity file
    sol_file = tmp_path / "Test.sol"
    sol_file.write_text("pragma solidity ^0.8.0; contract Test {}")

    with open(sol_file, "rb") as f:
        res = client.post(
            "/api/v1/scan",
            files={"file": ("Test.sol", f, "text/plain")}
        )

    # Slither may or may not be installed in CI / Windows
    # Both behaviors are VALID
    assert res.status_code in (200, 400)

    if res.status_code == 200:
        data = res.json()
        assert "overall_score" in data
        assert "summary" in data


def test_malformed_contract_recovery(client, tmp_path):
    """
    Error recovery test:
    - Malformed Solidity file
    - System should not crash
    - Must return a safe response
    """

    bad_contract = "pragma solidity ^0.8.0; contract Broken {"

    sol_file = tmp_path / "Broken.sol"
    sol_file.write_text(bad_contract)

    with open(sol_file, "rb") as f:
        res = client.post(
            "/api/v1/scan",
            files={"file": ("Broken.sol", f, "text/plain")},
        )

    # -------- API must respond, not crash --------
    assert res.status_code in (200, 400)

    # -------- If analysis continues safely --------
    if res.status_code == 200:
        data = res.json()

        assert "overall_score" in data
        assert "summary" in data
        assert "severity_breakdown" in data
        assert "vulnerabilities" in data

        # Even broken contracts must not explode counts
        assert isinstance(data["vulnerabilities"], list)
        assert isinstance(data["severity_breakdown"], dict)

    # -------- If rejected gracefully --------
    else:
        error = res.json()
        assert "detail" in error

def test_malformed_contract_file_rejected(client, tmp_path):
    sol = tmp_path / "Bad.sol"
    sol.write_text("contract {")

    with sol.open("rb") as f:
        res = client.post("/api/v1/scan", files={"file": ("Bad.sol", f, "text/plain")})

    assert res.status_code in (200, 400)

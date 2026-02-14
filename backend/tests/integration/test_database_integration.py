from http import client


def test_scan_persisted_and_retrievable(client, tmp_path):
    # --- create temp solidity file ---
    sol_file = tmp_path / "A.sol"
    sol_file.write_text("pragma solidity ^0.8.0; contract A {}")

    # --- call scan endpoint (multipart) ---
    with open(sol_file, "rb") as f:
        res = client.post(
            "/api/v1/scan",
            files={"file": ("A.sol", f, "text/plain")}
        )

    assert res.status_code == 200
    data = res.json()

    # --- basic response validation ---
    assert "overall_score" in data
    assert "severity_breakdown" in data
    assert isinstance(data["severity_breakdown"], dict)

    # --- DB persistence is OPTIONAL ---
    assert "scan_id" in data

    assert data["scan_id"] is not None, "Scan was not persisted to DB"

    scan_id = data["scan_id"]

    res2 = client.get(f"/api/v1/scans/{scan_id}")
    assert res2.status_code == 200

    stored = res2.json()

    assert stored["scan_id"] == scan_id
    assert isinstance(stored["severity_breakdown"], dict)
    assert isinstance(stored["overall_score"], (int, float))
    assert isinstance(stored["scan_timestamp"], str)


def test_scan_list_contains_persisted_scan(client, tmp_path):
    sol = tmp_path / "ListDB.sol"
    sol.write_text("pragma solidity ^0.8.0; contract ListDB {}")

    with sol.open("rb") as f:
        res = client.post("/api/v1/scan", files={"file": ("ListDB.sol", f, "text/plain")})

    assert res.status_code == 200

    res2 = client.get("/api/v1/scans")
    assert res2.status_code == 200

    scans = res2.json()
    assert isinstance(scans, list)
    assert any(s["contract_name"] == "ListDB" for s in scans)

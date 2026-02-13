def test_malformed_contract_recovery(client):
    bad_contract = "contract {"

    res = client.post("/api/v1/scan", json={
        "contract_name": "broken.sol",
        "source_code": bad_contract
    })

    assert res.status_code in (200, 400)

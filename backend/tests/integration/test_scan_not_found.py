def test_get_scan_not_found(client):
    res = client.get("/api/v1/scans/999999")
    assert res.status_code == 404

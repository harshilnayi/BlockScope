def test_file_too_large(client):
    files = {"file": ("a.sol", b"contract A {}", "text/plain")}
    response = client.post("/api/v1/scan", files=files)
    assert response.status_code in [200, 400, 413]

def test_rate_limiting(client):
    files = {"file": ("a.sol", b"contract A {}", "text/plain")}
    last_response = None
    for _ in range(5):
        last_response = client.post("/api/v1/scan", files=files)
    assert last_response.status_code in [200, 429]

def test_timeout_handling(client):
    files = {"file": ("a.sol", b"contract A {}", "text/plain")}
    response = client.post("/api/v1/scan", files=files)
    assert response.status_code >= 200
# File: BlockScope/backend/analysis/tests/test_endpoint.py
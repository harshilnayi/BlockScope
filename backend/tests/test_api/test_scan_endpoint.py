def test_file_too_large(client):
    data = {
        "file": ("big.sol", b"x" * 10_000_000, "application/octet-stream")
    }
    r = client.post("/api/v1/scan", files=data)
    assert r.status_code in (400, 413)


def test_rate_limiting(client):
    files = {
        "file": ("a.sol", b"contract A{}", "application/octet-stream")
    }

    for _ in range(20):
        r = client.post("/api/v1/scan", files=files)

    assert r.status_code in (200, 429)


def test_timeout_handling(client, monkeypatch):
    def slow(*args, **kwargs):
        raise TimeoutError()

    monkeypatch.setattr(
        "backend.analysis.orchestrator.AnalysisOrchestrator.analyze",
        slow
    )

    files = {
        "file": ("a.sol", b"contract A{}", "application/octet-stream")
    }

    r = client.post("/api/v1/scan", files=files)
    assert r.status_code >= 500
# File: BlockScope/backend/analysis/tests/test_endpoint.py
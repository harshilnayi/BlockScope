import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_health_endpoint_returns_200(client):
    """
    Health endpoint should always be reachable.
    This confirms FastAPI app boots correctly.
    """
    response = client.get("/health")

    assert response.status_code == 200


def test_health_endpoint_response_schema(client):
    """
    Health endpoint should return a predictable schema
    so monitoring systems can rely on it.
    """
    response = client.get("/health")
    data = response.json()

    assert isinstance(data, dict)
    assert "status" in data


def test_health_endpoint_status_is_ok(client):
    """
    Explicitly verify semantic meaning of health.
    """
    response = client.get("/health")

    assert response.json()["status"] in {"ok", "healthy", "up"}


def test_health_endpoint_is_fast(client):
    """
    Health checks must be lightweight.
    This indirectly ensures no heavy dependencies
    (DB, scanner, Slither) are triggered.
    """
    response = client.get("/health")

    # If this endpoint starts doing heavy work,
    # this test will start failing in CI.
    assert response.elapsed.total_seconds() < 1

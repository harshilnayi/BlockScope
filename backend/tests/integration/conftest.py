import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import engine
from app.models.base import Base


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """
    Create tables once for integration tests.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    """
    FastAPI test client for integration tests.
    """
    return TestClient(app)

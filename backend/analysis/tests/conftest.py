import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine
from app import models

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)

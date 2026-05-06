"""
BlockScope Test Configuration
Provides fixtures for database, API client, mock services, and test data.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Environment setup — must run BEFORE any app imports
# ---------------------------------------------------------------------------
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("TESTING", "True")
os.environ.setdefault("DEBUG", "False")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use-only")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-not-for-production-use-only")
os.environ.setdefault("RATE_LIMIT_ENABLED", "False")
os.environ.setdefault("LOG_FILE_ENABLED", "False")
os.environ.setdefault("ADMIN_PASSWORD", "testadmin123")

# Ensure the backend directory is on the import path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ── Import ALL models so SQLAlchemy resolves relationships before tables are created ──
# app.models.__init__ imports Finding before Scan (correct order for back_populates).
import app.models  # noqa: F401, E402


# ==================== Database Fixtures ====================


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine using SQLite in-memory."""
    from sqlalchemy import create_engine

    engine = create_engine(
        "sqlite:///./test.db",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    yield engine
    engine.dispose()
    # Cleanup test database file
    db_path = Path("./test.db")
    if db_path.exists():
        try:
            db_path.unlink()
        except PermissionError:
            pass


@pytest.fixture(scope="session")
def test_tables(test_engine):
    """Create all database tables for testing."""
    from sqlalchemy.orm import declarative_base

    try:
        from app.core.database import Base

        Base.metadata.create_all(bind=test_engine)
        yield
        Base.metadata.drop_all(bind=test_engine)
    except Exception:
        # If Base isn't available, create a minimal schema
        base = declarative_base()
        base.metadata.create_all(bind=test_engine)
        yield
        base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(test_engine, test_tables):
    """Provide a transactional database session for each test."""
    from sqlalchemy.orm import sessionmaker

    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ==================== FastAPI Client Fixtures ====================


@pytest.fixture
def app():
    """Create a FastAPI test application instance."""
    try:
        from app.main import app as fastapi_app

        return fastapi_app
    except Exception:
        from fastapi import FastAPI

        return FastAPI(title="BlockScope Test")


@pytest.fixture
def client(app, db_session):
    """Provide a FastAPI TestClient with database session override."""
    from fastapi.testclient import TestClient

    try:
        from app.core.database import get_db

        app.dependency_overrides[get_db] = lambda: db_session
    except ImportError:
        pass

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ==================== Mock Redis Fixture ====================


@pytest.fixture
def mock_redis():
    """Provide a mock Redis client for testing without Redis server."""
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.exists = AsyncMock(return_value=0)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.incr = AsyncMock(return_value=1)
    redis_mock.zadd = AsyncMock(return_value=1)
    redis_mock.zrangebyscore = AsyncMock(return_value=[])
    redis_mock.zremrangebyscore = AsyncMock(return_value=0)
    redis_mock.zcard = AsyncMock(return_value=0)
    redis_mock.pipeline = MagicMock(return_value=redis_mock)
    redis_mock.execute = AsyncMock(return_value=[])
    return redis_mock


# ==================== File Fixtures ====================


@pytest.fixture
def sample_sol_content():
    """Return sample Solidity contract source code."""
    return """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SimpleStorage {
    uint256 private storedData;
    address public owner;

    event DataStored(uint256 data);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function set(uint256 x) public onlyOwner {
        storedData = x;
        emit DataStored(x);
    }

    function get() public view returns (uint256) {
        return storedData;
    }
}
"""


@pytest.fixture
def sample_sol_file(sample_sol_content, tmp_path):
    """Create a temporary .sol file for upload testing."""
    sol_file = tmp_path / "TestContract.sol"
    sol_file.write_text(sample_sol_content)
    return sol_file


@pytest.fixture
def sample_upload_file(sample_sol_content):
    """Create an in-memory file-like object for upload testing."""
    import io

    return io.BytesIO(sample_sol_content.encode("utf-8"))


@pytest.fixture
def vulnerable_sol_content():
    """Return a Solidity contract with known vulnerabilities for testing."""
    return """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Vulnerable {
    mapping(address => uint256) public balances;

    // Reentrancy vulnerability
    function withdraw() public {
        uint256 balance = balances[msg.sender];
        (bool success, ) = msg.sender.call{value: balance}("");
        require(success, "Transfer failed");
        balances[msg.sender] = 0;
    }

    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }
}
"""


# ==================== API Key Fixtures ====================


@pytest.fixture
def test_api_key_raw():
    """Return a raw API key string for testing."""
    return "bsc_dev_test1234567890abcdef1234567890ab"


@pytest.fixture
def test_api_key_hash(test_api_key_raw):
    """Return a hashed version of the test API key."""
    import hashlib

    return hashlib.sha256(test_api_key_raw.encode()).hexdigest()


# ==================== Cleanup Fixtures ====================


@pytest.fixture(autouse=True)
def cleanup_uploads():
    """Clean up any uploaded files after each test."""
    yield
    upload_dir = Path("./uploads/test")
    if upload_dir.exists():
        import shutil

        shutil.rmtree(upload_dir, ignore_errors=True)


# ==================== Markers ====================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, no external deps)")
    config.addinivalue_line("markers", "integration: Integration tests (needs DB/Redis)")
    config.addinivalue_line("markers", "slow: Slow tests (Slither analysis, etc.)")
    config.addinivalue_line("markers", "security: Security-related tests")
    config.addinivalue_line("markers", "edge_case: Edge-case and boundary-value tests")

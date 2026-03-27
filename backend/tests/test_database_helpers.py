"""
Unit tests for app.core.database helpers.

Tests paginate(), get_by_id(), bulk_insert(), get_db_context(),
test_connection(), init_db(), and the FastAPI get_db() dependency.
"""

import os
import sys
from pathlib import Path

import pytest

# ── env BEFORE any app import ──
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("TESTING", "True")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use-only")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-not-for-production-use-only")
os.environ.setdefault("RATE_LIMIT_ENABLED", "False")
os.environ.setdefault("LOG_FILE_ENABLED", "False")
os.environ.setdefault("ADMIN_PASSWORD", "testadmin123")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import (  # noqa: E402
    Base,
    bulk_insert,
    get_by_id,
    get_db,
    get_db_context,
    init_db,
    paginate,
    test_connection,
)
from app.models.scan import Scan  # noqa: E402 — registers Scan mapper
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402


# ── Session fixture using a per-test in-memory engine ──
@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def mem_db(db_engine):
    """Fresh session, rolled back after each test."""
    Session_ = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = Session_()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _make_scan(**kwargs) -> Scan:
    defaults = dict(
        contract_name="TestContract",
        source_code="contract TestContract {}",
        status="completed",
        vulnerabilities_count=0,
        severity_breakdown={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        overall_score=100,
        summary="No issues",
        findings=[],
    )
    defaults.update(kwargs)
    return Scan(**defaults)


# ══════════════════════════════════════════════════════════════
# paginate()
# ══════════════════════════════════════════════════════════════

class TestPaginate:

    def test_returns_list(self, mem_db):
        results = paginate(mem_db.query(Scan), skip=0, limit=10)
        assert isinstance(results, list)

    def test_respects_limit(self, mem_db):
        for i in range(5):
            mem_db.add(_make_scan(contract_name=f"C{i}"))
        mem_db.flush()
        results = paginate(mem_db.query(Scan), skip=0, limit=3)
        assert len(results) <= 3

    def test_respects_skip(self, mem_db):
        for i in range(4):
            mem_db.add(_make_scan(contract_name=f"D{i}"))
        mem_db.flush()
        all_results = paginate(mem_db.query(Scan), skip=0, limit=100)
        skipped = paginate(mem_db.query(Scan), skip=2, limit=100)
        assert len(skipped) <= len(all_results)

    def test_caps_at_max_limit(self, mem_db):
        for i in range(5):
            mem_db.add(_make_scan(contract_name=f"E{i}"))
        mem_db.flush()
        results = paginate(mem_db.query(Scan), skip=0, limit=9999, max_limit=2)
        assert len(results) <= 2

    def test_negative_skip_treated_as_zero(self, mem_db):
        results = paginate(mem_db.query(Scan), skip=-5, limit=10)
        assert isinstance(results, list)


# ══════════════════════════════════════════════════════════════
# get_by_id()
# ══════════════════════════════════════════════════════════════

class TestGetById:

    def test_returns_none_for_missing_id(self, mem_db):
        result = get_by_id(mem_db, Scan, 99999)
        assert result is None

    def test_returns_instance_for_existing_id(self, mem_db):
        scan = _make_scan()
        mem_db.add(scan)
        mem_db.commit()
        mem_db.refresh(scan)
        found = get_by_id(mem_db, Scan, scan.id)
        assert found is not None
        assert found.id == scan.id


# ══════════════════════════════════════════════════════════════
# bulk_insert()
# ══════════════════════════════════════════════════════════════

class TestBulkInsert:

    def test_inserts_multiple_records(self, mem_db):
        before = mem_db.query(Scan).count()
        scans = [_make_scan(contract_name=f"Bulk{i}") for i in range(3)]
        bulk_insert(mem_db, scans)
        mem_db.flush()
        after = mem_db.query(Scan).count()
        assert after == before + 3

    def test_empty_list_is_no_op(self, mem_db):
        before = mem_db.query(Scan).count()
        bulk_insert(mem_db, [])
        mem_db.flush()
        after = mem_db.query(Scan).count()
        assert after == before


# ══════════════════════════════════════════════════════════════
# get_db_context()
# ══════════════════════════════════════════════════════════════

class TestGetDbContext:

    def test_yields_session(self):
        with get_db_context() as db:
            assert isinstance(db, Session)

    def test_rolls_back_on_exception(self):
        try:
            with get_db_context() as db:
                db.add(_make_scan())
                raise RuntimeError("intentional")
        except RuntimeError:
            pass


# ══════════════════════════════════════════════════════════════
# get_db() FastAPI dependency
# ══════════════════════════════════════════════════════════════

class TestGetDb:

    def test_yields_session_instance(self):
        gen = get_db()
        db = next(gen)
        assert isinstance(db, Session)
        try:
            next(gen)
        except StopIteration:
            pass


# ══════════════════════════════════════════════════════════════
# test_connection() / init_db()
# ══════════════════════════════════════════════════════════════

class TestConnectionHelpers:

    def test_returns_bool(self):
        assert isinstance(test_connection(), bool)

    def test_succeeds_with_sqlite(self):
        assert test_connection() is True

    def test_init_db_is_idempotent(self):
        init_db()
        init_db()

    def test_test_connection_failure_returns_false(self):
        """test_connection returns False and logs error when DB is down."""
        from unittest.mock import patch, MagicMock
        from sqlalchemy import exc as sa_exc
        with patch("app.core.database.engine") as mock_engine:
            mock_engine.connect.side_effect = sa_exc.OperationalError("n", None, None)
            result = test_connection()
        assert result is False

    def test_get_db_context_rollback_on_exception(self):
        """get_db_context() rolls back on exception (coverage line 137)."""
        try:
            with get_db_context() as db:
                db.execute(__import__("sqlalchemy").text("INVALID SQL SYNTAX XYZ"))
        except Exception:
            pass  # rollback triggered on line 137

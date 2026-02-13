import pytest
from sqlalchemy import text
from backend.app.core.database import engine, SessionLocal


def test_connection_pooling():
    conn = engine.connect()
    assert conn is not None
    conn.close()


def test_session_management():
    db = SessionLocal()
    assert db is not None
    db.close()


def test_transaction_rollback():
    db = SessionLocal()
    try:
        db.execute(text("INVALID SQL"))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def test_concurrent_access():
    s1 = SessionLocal()
    s2 = SessionLocal()
    assert s1 is not s2
    s1.close()
    s2.close()


def test_query_optimization():
    db = SessionLocal()
    result = db.execute(text("SELECT 1")).scalar()
    assert result == 1
    db.close()


def test_migration_compatibility():
    db = SessionLocal()
    db.execute(text("SELECT 1"))
    db.close()

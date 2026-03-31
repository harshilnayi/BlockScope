"""
BlockScope Database Configuration.

Provides:
- SQLAlchemy engine creation (PostgreSQL + SQLite support)
- Session factory with proper lifecycle management
- FastAPI dependency for injecting DB sessions
- Connection health-check and table initialisation helpers
- Optimised query helpers (pagination, bulk operations)
"""

import logging
from contextlib import contextmanager
from typing import Any, Generator, Optional, Type, TypeVar

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# ──────────────────────────────────────────────
# Configuration loading
# ──────────────────────────────────────────────
try:
    from app.core.settings import settings

    DATABASE_URL: str = settings.database_url_sync
    DB_POOL_SIZE: int = settings.DB_POOL_SIZE
    DB_MAX_OVERFLOW: int = settings.DB_MAX_OVERFLOW
    DB_POOL_TIMEOUT: int = settings.DB_POOL_TIMEOUT
    DB_POOL_RECYCLE: int = settings.DB_POOL_RECYCLE
    DB_ECHO: bool = settings.DB_ECHO

except ImportError:
    import os

    from dotenv import load_dotenv

    load_dotenv()

    DATABASE_URL = os.getenv("DATABASE_URL", "")
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL environment variable is required but not set.\n"
            "Set it in your .env file, e.g.:\n"
            "  DATABASE_URL=postgresql://user:password@localhost:5432/blockscope_dev\n"
            "or for local development:\n"
            "  DATABASE_URL=sqlite:///./blockscope.db"
        )
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))
    DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

logger = logging.getLogger("blockscope.database")

# ──────────────────────────────────────────────
# Engine creation
# ──────────────────────────────────────────────
_IS_SQLITE: bool = DATABASE_URL.startswith("sqlite://")

if _IS_SQLITE:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=DB_ECHO,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_timeout=DB_POOL_TIMEOUT,
        pool_recycle=DB_POOL_RECYCLE,
        pool_pre_ping=True,   # Detect stale connections before use
        echo=DB_ECHO,
    )

# ──────────────────────────────────────────────
# Session factory
# ──────────────────────────────────────────────
SessionLocal: sessionmaker = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ──────────────────────────────────────────────
# Declarative base
# ──────────────────────────────────────────────
Base = declarative_base()

# Generic model type for query helpers
_ModelT = TypeVar("_ModelT")


# ──────────────────────────────────────────────
# FastAPI dependency
# ──────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session and guarantee cleanup.

    Intended for use as a FastAPI ``Depends`` dependency::

        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            return db.query(Item).all()

    Yields:
        Active SQLAlchemy ``Session``.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context-manager wrapper around :func:`get_db` for non-FastAPI code.

    Usage::

        with get_db_context() as db:
            scan = db.query(Scan).first()

    Yields:
        Active SQLAlchemy ``Session``.
    """
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ──────────────────────────────────────────────
# Optimised query helpers
# ──────────────────────────────────────────────
def paginate(
    query: Any,
    skip: int = 0,
    limit: int = 20,
    max_limit: int = 100,
) -> list:
    """
    Apply safe pagination to any SQLAlchemy query.

    Caps ``limit`` at ``max_limit`` to prevent unbounded result sets.

    Args:
        query: An existing SQLAlchemy ORM query object.
        skip: Number of records to skip (offset).
        limit: Maximum records to return.
        max_limit: Hard ceiling for ``limit`` (default 100).

    Returns:
        List of model instances.
    """
    effective_limit = min(max(1, limit), max_limit)
    effective_skip = max(0, skip)
    return query.offset(effective_skip).limit(effective_limit).all()


def get_by_id(
    db: Session,
    model: Type[_ModelT],
    record_id: int,
) -> Optional[_ModelT]:
    """
    Fetch a single record by primary key.

    Prefer this over ``db.query(M).filter(M.id == id).first()``
    because SQLAlchemy's ``Session.get()`` uses the identity map
    (no extra round-trip if the object is already loaded).

    Args:
        db: Active database session.
        model: SQLAlchemy model class.
        record_id: Primary-key value to look up.

    Returns:
        Model instance if found, otherwise ``None``.
    """
    return db.get(model, record_id)


def bulk_insert(db: Session, instances: list) -> None:
    """
    Insert multiple model instances in a single transaction.

    Args:
        db: Active database session.
        instances: List of model instances to persist.
    """
    db.add_all(instances)
    db.flush()


# ──────────────────────────────────────────────
# Health and lifecycle helpers
# ──────────────────────────────────────────────
def test_connection() -> bool:
    """
    Verify the database is reachable with a lightweight query.

    Returns:
        ``True`` if the connection succeeded, ``False`` otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
        return True
    except Exception as exc:
        logger.error(
            "Database connection check failed",
            exc_info=exc,
            extra={"database_url": DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "local"},
        )
        return False


def init_db() -> None:
    """
    Create all tables defined by SQLAlchemy models.

    Safe to call on every startup — existing tables are not modified.
    """
    logger.info("Initialising database tables …")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready")


if __name__ == "__main__":  # pragma: no cover
    print("Testing database connection …")
    status = "OK" if test_connection() else "FAILED"
    print(f"Connection: {status}")

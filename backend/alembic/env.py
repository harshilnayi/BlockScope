"""
Alembic environment configuration for BlockScope.

Reads DATABASE_URL from the application's Settings object (which in turn
reads from environment variables / .env files).  This avoids duplicating
connection strings in ``alembic.ini``.

Usage::

    cd backend
    alembic upgrade head       # Apply all pending migrations
    alembic downgrade -1       # Roll back the last migration
    alembic revision --autogenerate -m "description"  # Generate migration
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Ensure the backend package is importable when running from backend/.
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ---------------------------------------------------------------------------
# Import models so Alembic can detect them for --autogenerate.
# Explicit imports (rather than wildcard) keep the namespace clean and
# make it obvious which models participate in migrations.
# ---------------------------------------------------------------------------
from app.core.database import Base  # noqa: E402
from app.models import Scan, Finding  # noqa: E402, F401

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to alembic.ini values.
# ---------------------------------------------------------------------------
config = context.config

# Override sqlalchemy.url from environment so credentials are never in .ini.
_db_url = os.getenv("DATABASE_URL", "")
if not _db_url:
    try:
        from app.core.config import settings

        _db_url = settings.database_url_sync
    except Exception:
        pass

if _db_url:
    config.set_main_option("sqlalchemy.url", _db_url)

# Set up Python logging from the .ini file.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for --autogenerate support.
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Migration runners
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL scripts without requiring a live database connection.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an engine, connects, and runs each migration inside a
    transaction.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

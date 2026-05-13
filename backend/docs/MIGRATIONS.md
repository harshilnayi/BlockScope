# Database Migrations

BlockScope uses [Alembic](https://alembic.sqlalchemy.org/) for database schema management.

## Directory Structure

```
backend/
├── alembic.ini              # Alembic configuration (no credentials!)
├── alembic/
│   ├── env.py               # Runtime configuration (reads DATABASE_URL)
│   ├── script.py.mako       # Template for new migrations
│   └── versions/
│       ├── 0001_baseline_create_tables.py
│       └── 0002_add_indexes.py
```

> **Note:** `backend/migrations/` is deprecated. All new work goes in `backend/alembic/`.

## Prerequisites

Set `DATABASE_URL` in your environment or `.env` file:

```bash
# PostgreSQL (production / staging)
DATABASE_URL=postgresql://user:password@localhost:5432/blockscope

# SQLite (local development)
DATABASE_URL=sqlite:///./blockscope.db
```

## Common Commands

All commands should be run from the `backend/` directory.

### Apply all migrations

```bash
alembic upgrade head
```

### Roll back the last migration

```bash
alembic downgrade -1
```

### Roll back to a specific revision

```bash
alembic downgrade 0001_baseline
```

### Check current revision

```bash
alembic current
```

### View migration history

```bash
alembic history --verbose
```

### Generate SQL without executing (dry run)

```bash
alembic upgrade head --sql
```

## Creating New Migrations

### Auto-generate from model changes

After modifying SQLAlchemy models in `app/models/`:

```bash
alembic revision --autogenerate -m "add_column_x_to_scans"
```

> Always review the generated migration! Auto-generate can miss some changes
> (e.g., index renames, data migrations, CHECK constraints).

### Create an empty migration (manual)

```bash
alembic revision -m "backfill_severity_scores"
```

Then edit the generated file to add your `upgrade()` and `downgrade()` logic.

## Existing Database Setup

If your database already has tables from `Base.metadata.create_all()`:

```bash
# 1. Stamp the database as being at the baseline revision
alembic stamp 0001_baseline

# 2. Apply any new migrations (e.g., performance indexes)
alembic upgrade head
```

## Troubleshooting

### "Target database is not up to date"

Run `alembic upgrade head` to apply pending migrations.

### "Can't locate revision"

The `alembic_version` table may reference a deleted revision. Fix with:

```bash
alembic stamp head  # Reset to latest
```

### Model not detected by --autogenerate

Ensure the model is imported in `app/models/__init__.py`. Alembic's `env.py`
does `from app.models import *` to register all models with the mapper.

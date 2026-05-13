# ⚠️ DEPRECATED — Do Not Use

This migrations directory is **deprecated** as of May 2026.

All Alembic migrations have been consolidated into `backend/alembic/`.

## If you have an existing database

```bash
cd backend
alembic stamp 0001_baseline    # Mark as already at baseline
alembic upgrade head           # Apply any new migrations (e.g. indexes)
```

## For new databases

```bash
cd backend
alembic upgrade head           # Creates tables + indexes from scratch
```

See `backend/docs/MIGRATIONS.md` for full documentation.

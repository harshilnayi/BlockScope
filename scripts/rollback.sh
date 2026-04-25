#!/bin/bash
# =============================================================================
# BlockScope — Rollback Script
# =============================================================================
# Rolls back the application by restoring a database backup and restarting services.
#
# Usage:
#   ./scripts/rollback.sh <backup-file>
# =============================================================================

set -euo pipefail

BACKUP_FILE="${1:-}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./rollback.sh <backup-file>"
    echo ""
    echo "Available backups:"
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    ls -lh "$SCRIPT_DIR/../backups"/backup_*.sql.gz 2>/dev/null || echo "  No backups found."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.prod.yml"

# Resolve backup path
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_PATH="$BACKUP_FILE"
elif [ -f "$PROJECT_ROOT/backups/$BACKUP_FILE" ]; then
    BACKUP_PATH="$PROJECT_ROOT/backups/$BACKUP_FILE"
else
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "[$(date)] Starting rollback from: $BACKUP_PATH"

echo "[$(date)] Stopping backend and frontend..."
docker compose -f "$COMPOSE_FILE" stop backend frontend

echo "[$(date)] Restoring database..."
gunzip -c "$BACKUP_PATH" | docker exec -i blockscope-postgres psql -U blockscope blockscope

echo "[$(date)] Restarting services..."
docker compose -f "$COMPOSE_FILE" start backend frontend

echo "[$(date)] Rollback completed successfully."

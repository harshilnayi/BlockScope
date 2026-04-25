#!/bin/bash
# =============================================================================
# BlockScope — PostgreSQL Restore Script
# =============================================================================
# Restores a database from a compressed backup file.
#
# Usage:
#   ./restore.sh backups/backup_blockscope_2026-04-23_02-00-00.sql.gz
# =============================================================================

set -euo pipefail

BACKUP_FILE="${1:-}"
DB_USER="${DB_USER:-blockscope}"
DB_NAME="${DB_NAME:-blockscope}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
CONTAINER_NAME="${CONTAINER_NAME:-blockscope-postgres}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file.sql.gz>"
    echo ""
    echo "Available backups:"
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    ls -lh "$SCRIPT_DIR/../backups"/backup_*.sql.gz 2>/dev/null || echo "  No backups found."
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "=== BlockScope Database Restore ==="
echo "  Backup file: $BACKUP_FILE"
echo "  Database:    $DB_NAME"
echo "  User:        $DB_USER"
echo ""
read -p "WARNING: This will overwrite the current database. Continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 0
fi

echo "[$(date)] Starting restore..."

if command -v docker &> /dev/null && docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "[$(date)] Restoring via Docker container '${CONTAINER_NAME}'..."
    gunzip -c "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" "$DB_NAME"
else
    echo "[$(date)] Restoring via local psql..."
    gunzip -c "$BACKUP_FILE" | PGPASSWORD="${DB_PASSWORD:-}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"
fi

echo "[$(date)] Restore completed successfully from: $BACKUP_FILE"

#!/bin/bash
# =============================================================================
# BlockScope — PostgreSQL Backup Script
# =============================================================================
# Performs a compressed database dump, verifies the backup, and rotates
# old backups to prevent disk exhaustion.
#
# Usage:
#   ./backup.sh                     # Uses defaults
#   DB_USER=myuser DB_NAME=mydb ./backup.sh
#
# Cron (daily at 2 AM):
#   crontab -e
#   0 2 * * * /path/to/scripts/backup.sh >> /var/log/blockscope-backup.log 2>&1
# =============================================================================

set -euo pipefail

# ── Configuration ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$SCRIPT_DIR/../backups}"
DB_USER="${DB_USER:-blockscope}"
DB_NAME="${DB_NAME:-blockscope}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
CONTAINER_NAME="${CONTAINER_NAME:-blockscope-postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
MIN_BACKUP_SIZE=100   # bytes — minimum valid backup size

DATE=$(date +%F_%H-%M-%S)
BACKUP_FILE="$BACKUP_DIR/backup_${DB_NAME}_${DATE}.sql.gz"

# ── Setup ──
mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting PostgreSQL backup for database '$DB_NAME'..."

# ── Dump ──
# If running inside Docker, use docker exec; otherwise, use pg_dump directly.
if command -v docker &> /dev/null && docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "[$(date)] Dumping via Docker container '${CONTAINER_NAME}'..."
    docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"
else
    echo "[$(date)] Dumping via local pg_dump..."
    PGPASSWORD="${DB_PASSWORD:-}" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"
fi

# ── Verify ──
if [ ! -f "$BACKUP_FILE" ]; then
    echo "[$(date)] ERROR: Backup file was not created!"
    exit 1
fi

FILE_SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE" 2>/dev/null)
if [ "$FILE_SIZE" -lt "$MIN_BACKUP_SIZE" ]; then
    echo "[$(date)] ERROR: Backup file is too small (${FILE_SIZE} bytes). Possible failure."
    exit 1
fi

echo "[$(date)] Backup successful: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# ── Rotation: delete backups older than RETENTION_DAYS ──
DELETED=$(find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
    echo "[$(date)] Rotated $DELETED old backup(s) (older than ${RETENTION_DAYS} days)"
fi

# ── Summary ──
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "backup_*.sql.gz" | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "[$(date)] Backup complete. Total backups: $TOTAL_BACKUPS, Total size: $TOTAL_SIZE"

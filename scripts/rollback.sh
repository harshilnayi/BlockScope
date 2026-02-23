#!/bin/bash
set -e

echo "Starting rollback..."

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: ./rollback.sh <backup-file>"
  exit 1
fi

# Resolve script directory safely
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOCKER_DIR="$SCRIPT_DIR/../docker"
BACKUP_PATH="$SCRIPT_DIR/$BACKUP_FILE"

if [ ! -f "$BACKUP_PATH" ]; then
  echo "Backup file not found: $BACKUP_PATH"
  exit 1
fi

cd "$DOCKER_DIR" || { echo "Failed to enter docker directory"; exit 1; }

echo "Stopping backend and frontend..."
docker compose -f docker-compose.prod.yml stop backend frontend

echo "Restoring database from $BACKUP_FILE..."
gunzip -c "$BACKUP_PATH" | docker exec -i blockscope-postgres psql -U blockscope blockscope

echo "Restarting services..."
docker compose -f docker-compose.prod.yml start backend frontend

echo "Rollback completed successfully."
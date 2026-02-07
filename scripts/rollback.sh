#!/bin/bash
set -e

echo "Starting rollback..."

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: ./rollback.sh <backup-file>"
  exit 1
fi

echo "Stopping services..."
cd ../docker
docker compose -f docker-compose.prod.yml stop backend frontend

echo "Restoring database..."
gunzip -c "../scripts/$BACKUP_FILE" | docker exec -i blockscope-postgres psql -U blockscope blockscope

echo "Restarting services..."
docker compose -f docker-compose.prod.yml start backend frontend

echo "Rollback completed successfully."

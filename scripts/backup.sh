#!/bin/bash
set -e

DATE=$(date +%F-%H-%M)
BACKUP_FILE="backup-$DATE.sql.gz"

echo "Creating PostgreSQL compressed backup..."

docker exec blockscope-postgres pg_dump -U blockscope blockscope | gzip > "$BACKUP_FILE"

echo "Backup saved as $BACKUP_FILE"

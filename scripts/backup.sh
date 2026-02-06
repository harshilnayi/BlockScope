#!/bin/bash

DATE=$(date +%F-%H-%M)
BACKUP_FILE="backup-$DATE.sql"

echo "Creating PostgreSQL backup..."

docker exec blockscope-postgres pg_dump -U blockscope blockscope > $BACKUP_FILE

echo "Backup saved as $BACKUP_FILE"

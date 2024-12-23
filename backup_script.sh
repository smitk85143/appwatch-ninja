#!/bin/bash

# Define variables
BACKUP_DIR=path/to/backups
BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y-%m-%d).sql"

# Run pg_dump inside PostgreSQL container
docker exec postgres pg_dump -U postgres -d appwatch-test -F c > "$BACKUP_FILE"

# Upload the backup to Dropbox (optional step)
python3 upload_to_dropbox.py "$BACKUP_FILE"
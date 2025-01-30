#!/bin/bash

# Define variables
BACKUP_DIR=/path/to/appwatch-ninja/db
BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y-%m-%d).sql"

# Run pg_dump inside PostgreSQL container
docker exec postgres pg_dump -U postgres -d appwatch -F c > "$BACKUP_FILE"

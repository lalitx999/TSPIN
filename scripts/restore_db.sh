#!/bin/bash
# ==============================================================================
# TSPI Clinic - Database Restore Script (Disaster Recovery)
# Usage: ./scripts/restore_db.sh path/to/backup.sql.gz
# ==============================================================================

set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <path_to_backup_file.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: Backup file '${BACKUP_FILE}' does not exist!"
    exit 1
fi

echo "=================================================================="
echo "⚠️  WARNING: Restoring database will OVERWRITE current data!  ⚠️"
echo "Target file: ${BACKUP_FILE}"
echo "=================================================================="
read -p "Are you sure you want to proceed? (yes/no): " CONFIRM

if [ "${CONFIRM}" != "yes" ]; then
    echo "Restore aborted by user."
    exit 0
fi

echo "[TSPI Restore] Decompressing and restoring database..."

if command -v docker &> /dev/null && docker ps | grep -q tspi_postgres; then
    echo "[TSPI Restore] Importing into Docker container tspi_postgres..."
    gunzip -c "${BACKUP_FILE}" | docker exec -i tspi_postgres psql -U "${DB_USER:-postgres}" "${DB_NAME:-drpatrcl_sys}"
else
    echo "[TSPI Restore] Importing via local psql..."
    PGPASSWORD="${DB_PASSWORD:-postgres}" gunzip -c "${BACKUP_FILE}" | psql -h "${DB_HOST:-127.0.0.1}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}" "${DB_NAME:-drpatrcl_sys}"
fi

echo "[TSPI Restore] Database restoration completed successfully!"

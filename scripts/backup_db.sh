#!/bin/bash
# ==============================================================================
# TSPI Clinic - Automated Database Backup Script (Pillars 5, 8)
# Performs encrypted/compressed PostgreSQL backup with 7-day retention rotation.
# ==============================================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/tspi_db_backup_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=7

mkdir -p "${BACKUP_DIR}"

echo "[TSPI Backup] Starting database backup at $(date)..."

if command -v docker &> /dev/null && docker ps | grep -q tspi_postgres; then
    echo "[TSPI Backup] Exporting via Docker container tspi_postgres..."
    docker exec tspi_postgres pg_dump -U "${DB_USER:-postgres}" "${DB_NAME:-drpatrcl_sys}" | gzip -9 > "${BACKUP_FILE}"
else
    echo "[TSPI Backup] Exporting via local pg_dump..."
    PGPASSWORD="${DB_PASSWORD:-postgres}" pg_dump -h "${DB_HOST:-127.0.0.1}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}" "${DB_NAME:-drpatrcl_sys}" | gzip -9 > "${BACKUP_FILE}"
fi

BACKUP_SIZE=$(ls -lh "${BACKUP_FILE}" | awk '{print $5}')
echo "[TSPI Backup] Backup successful: ${BACKUP_FILE} (${BACKUP_SIZE})"

# Encrypted clinical media (LINE/web images, audio). Files are already Fernet-encrypted,
# so the archive is safe at rest; it still needs the same FERNET_KEY/SECRET_KEY to restore.
PRIVATE_MEDIA_ROOT="${PRIVATE_MEDIA_ROOT:-./private_media}"
if [ -d "${PRIVATE_MEDIA_ROOT}" ]; then
    MEDIA_FILE="${BACKUP_DIR}/tspi_media_backup_${TIMESTAMP}.tar.gz"
    tar -czf "${MEDIA_FILE}" -C "$(dirname "${PRIVATE_MEDIA_ROOT}")" "$(basename "${PRIVATE_MEDIA_ROOT}")"
    echo "[TSPI Backup] Media backup: ${MEDIA_FILE} ($(ls -lh "${MEDIA_FILE}" | awk '{print $5}'))"
fi

# Retention Rotation: Remove backups older than 7 days
echo "[TSPI Backup] Cleaning up backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "tspi_db_backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}" -name "tspi_media_backup_*.tar.gz" -type f -mtime +${RETENTION_DAYS} -delete

echo "[TSPI Backup] Completed successfully."

#!/usr/bin/env bash
set -Eeuo pipefail

MONGODB_URI="${MONGODB_URI:-}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/aborodesk/mongodb}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
[[ -n "${MONGODB_URI}" ]] || { echo "MONGODB_URI fehlt." >&2; exit 1; }
command -v mongodump >/dev/null || { echo "mongodump fehlt. Bitte MongoDB Database Tools installieren." >&2; exit 1; }
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="${BACKUP_DIR}/${timestamp}"
install -d -m 0700 "${target}"
mongodump --uri="${MONGODB_URI}" --archive="${target}/aborodesk.archive.gz" --gzip --quiet
find "${BACKUP_DIR}" -mindepth 1 -maxdepth 1 -type d -mtime "+${RETENTION_DAYS}" -exec rm -rf -- {} +
echo "Backup erstellt: ${target}/aborodesk.archive.gz"

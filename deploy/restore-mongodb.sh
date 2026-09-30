#!/usr/bin/env bash
set -Eeuo pipefail

MONGODB_URI="${MONGODB_URI:-}"
ARCHIVE="${ARCHIVE:-}"
[[ -n "${MONGODB_URI}" ]] || { echo "MONGODB_URI fehlt." >&2; exit 1; }
[[ -f "${ARCHIVE}" ]] || { echo "ARCHIVE fehlt oder nicht gefunden: ${ARCHIVE}" >&2; exit 1; }
command -v mongorestore >/dev/null || { echo "mongorestore fehlt. Bitte MongoDB Database Tools installieren." >&2; exit 1; }
echo "WARNUNG: Der Datenbestand wird mit dem Backup überschrieben."
read -r -p "Zum Fortfahren RESTORE eingeben: " confirmation
[[ "${confirmation}" == "RESTORE" ]] || { echo "Abgebrochen."; exit 1; }
mongorestore --uri="${MONGODB_URI}" --archive="${ARCHIVE}" --gzip --drop
echo "Wiederherstellung abgeschlossen."

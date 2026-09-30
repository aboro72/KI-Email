#!/usr/bin/env bash
set -Eeuo pipefail

CONFIG_FILE="${UPDATE_CONFIG:-/etc/aborodesk/update.env}"
[[ -f "${CONFIG_FILE}" ]] || { echo "Update-Konfiguration fehlt: ${CONFIG_FILE}" >&2; exit 1; }
source "${CONFIG_FILE}"

APP_DIR="${APP_DIR:-/opt/aborodesk}"
SOURCE_DIR="${SOURCE_DIR:-/var/lib/aborodesk-updater/source}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/aborodesk}"
SERVICE_NAME="${SERVICE_NAME:-aborodesk}"
GIT_BRANCH="${GIT_BRANCH:-master}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8001/health}"
LOCK_FILE="${LOCK_FILE:-/run/lock/aborodesk-update.lock}"
UPDATE_STATUS_FILE="${UPDATE_STATUS_FILE:-/var/lib/aborodesk-updater/status.json}"

log() { echo "[$(date --iso-8601=seconds)] [AboroDesk-Update] $*"; }
die() { log "FEHLER: $*"; exit 1; }
write_status() {
  local state="$1" commit="$2" message="$3" temporary
  temporary="${UPDATE_STATUS_FILE}.tmp"
  install -d -m 0755 "$(dirname "${UPDATE_STATUS_FILE}")"
  printf '{"state":"%s","commit":"%s","message":"%s","checked_at":"%s"}\n' \
    "$state" "$commit" "$message" "$(date --iso-8601=seconds)" > "${temporary}"
  chmod 0644 "${temporary}"
  mv -f "${temporary}" "${UPDATE_STATUS_FILE}"
}

[[ "${EUID}" -eq 0 ]] || die "Bitte als root ausführen."
command -v git >/dev/null || die "git ist nicht installiert."
command -v rsync >/dev/null || die "rsync ist nicht installiert."
[[ -n "${REPOSITORY_URL:-}" ]] || die "REPOSITORY_URL fehlt in ${CONFIG_FILE}."
[[ -d "${APP_DIR}" ]] || die "APP_DIR fehlt: ${APP_DIR}"

install -d -m 0750 "$(dirname "${LOCK_FILE}")" "${SOURCE_DIR}" "${BACKUP_DIR}"
exec 9>"${LOCK_FILE}"
flock -n 9 || { log "Ein anderes Update läuft bereits."; exit 0; }

if [[ ! -d "${SOURCE_DIR}/.git" ]]; then
  log "Initialisiere Update-Repository …"
  rm -rf "${SOURCE_DIR}"
  git clone --branch "${GIT_BRANCH}" --depth 20 "${REPOSITORY_URL}" "${SOURCE_DIR}"
else
  git -C "${SOURCE_DIR}" remote set-url origin "${REPOSITORY_URL}"
  git -C "${SOURCE_DIR}" fetch --prune origin "${GIT_BRANCH}"
fi

git -C "${SOURCE_DIR}" checkout --quiet "${GIT_BRANCH}" 2>/dev/null || true
git -C "${SOURCE_DIR}" reset --quiet --hard "origin/${GIT_BRANCH}"
new_commit="$(git -C "${SOURCE_DIR}" rev-parse HEAD)"
old_commit=""
if [[ -f "${APP_DIR}/.deployed-commit" ]]; then
  old_commit="$(cat "${APP_DIR}/.deployed-commit")"
fi

if [[ "${new_commit}" == "${old_commit}" ]]; then
  write_status "current" "${new_commit}" "Keine neuen Updates"
  log "Keine Änderung (${new_commit:0:12})."
  exit 0
fi

timestamp="$(date +%Y%m%d-%H%M%S)"
backup_path="${BACKUP_DIR}/${timestamp}"
log "Neuer Commit erkannt: ${new_commit:0:12}; sichere aktuellen Stand …"
install -d -m 0750 "${backup_path}"
rsync -a --exclude '.venv/' --exclude '.deployed-commit' "${APP_DIR}/" "${backup_path}/"

log "Installiere neuen Quellstand …"
rsync -a --delete --exclude '.venv/' --exclude '.env' --exclude '*.db' --exclude 'bedrock-long-term-api-key.csv' --exclude '.deployed-commit' "${SOURCE_DIR}/" "${APP_DIR}/"

if [[ -x "${APP_DIR}/.venv/bin/pip" ]]; then
  "${APP_DIR}/.venv/bin/pip" install --quiet -r "${APP_DIR}/requirements.txt"
fi
printf '%s\n' "${new_commit}" > "${APP_DIR}/.deployed-commit"
systemctl restart "${SERVICE_NAME}.service"
sleep 3

if ! curl --fail --silent --show-error "${HEALTH_URL}" >/dev/null; then
  write_status "rollback" "${old_commit:-}" "Update fehlgeschlagen; vorheriger Stand wiederhergestellt"
  log "Healthcheck fehlgeschlagen; stelle vorherigen Quellstand wieder her."
  systemctl stop "${SERVICE_NAME}.service" || true
  rsync -a --delete --exclude '.venv/' --exclude '.env' --exclude '*.db' --exclude 'bedrock-long-term-api-key.csv' --exclude '.deployed-commit' "${backup_path}/" "${APP_DIR}/"
  printf '%s\n' "${old_commit:-rollback}" > "${APP_DIR}/.deployed-commit"
  systemctl start "${SERVICE_NAME}.service"
  die "Rollback durchgeführt."
fi

find "${BACKUP_DIR}" -mindepth 1 -maxdepth 1 -type d -mtime +14 -exec rm -rf -- {} +
write_status "updated" "${new_commit}" "Neues Update wurde installiert"
log "Update erfolgreich: ${new_commit:0:12}."

#!/usr/bin/env bash
set -Eeuo pipefail

# Installation für einen vorhandenen ISPConfig3-Server.
# Der ISPConfig-Webserver wird nicht automatisch verändert. Die Anwendung
# lauscht nur lokal; die Domain wird in ISPConfig als Reverse Proxy eingerichtet.

APP_NAME="${APP_NAME:-AboroDesk Developer}"
APP_DIR="${APP_DIR:-/opt/aborodesk}"
DATA_DIR="${DATA_DIR:-/var/lib/aborodesk}"
ETC_DIR="${ETC_DIR:-/etc/aborodesk}"
SERVICE_NAME="${SERVICE_NAME:-aborodesk}"
SERVICE_USER="${SERVICE_USER:-www-data}"
SERVICE_GROUP="${SERVICE_GROUP:-${SERVICE_USER}}"
APP_PORT="${APP_PORT:-8001}"
MONGODB_URI="${MONGODB_URI:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# FTP-Layout des ISPConfig-Projekts: /web/app enthält app/, requirements.txt usw.
# SOURCE_DIR kann für ein anderes Layout weiterhin überschrieben werden.
SOURCE_DIR="${SOURCE_DIR:-/web/app}"
if [[ ! -d "${SOURCE_DIR}/app" && -d "${SCRIPT_DIR}/../.."/app ]]; then
  SOURCE_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
fi

die() { echo "FEHLER: $*" >&2; exit 1; }
log() { echo "[AboroDesk] $*"; }

[[ "${EUID}" -eq 0 ]] || die "Bitte als root ausführen."
command -v apt-get >/dev/null || die "Dieses Skript erwartet Debian/Ubuntu mit apt-get."
[[ -d "${SOURCE_DIR}/app" ]] || die "Quellverzeichnis nicht gefunden: ${SOURCE_DIR}"
[[ -n "${MONGODB_URI}" ]] || die "MONGODB_URI muss auf mongodb://.../aborodesk gesetzt werden."
id "${SERVICE_USER}" >/dev/null 2>&1 || die "SERVICE_USER existiert nicht: ${SERVICE_USER}. In ISPConfig den Web-Benutzer angeben."
getent group "${SERVICE_GROUP}" >/dev/null || die "SERVICE_GROUP existiert nicht: ${SERVICE_GROUP}."
log "Verwende Projektstamm: ${SOURCE_DIR}"

log "Installiere Python-Laufzeit und rsync …"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends python3 python3-venv python3-pip rsync curl ca-certificates openssl

install -d -m 0750 -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" "${APP_DIR}" "${DATA_DIR}"
install -d -m 0750 -o root -g "${SERVICE_GROUP}" "${ETC_DIR}"

log "Kopiere Anwendung nach ${APP_DIR} …"
rsync -a \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude '*.db' \
  --exclude '.env' \
  --exclude 'bedrock-long-term-api-key.csv' \
  "${SOURCE_DIR}/" "${APP_DIR}/"
chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${APP_DIR}"

log "Erstelle virtuelle Python-Umgebung …"
runuser -u "${SERVICE_USER}" -- python3 -m venv "${APP_DIR}/.venv"
runuser -u "${SERVICE_USER}" -- "${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip
runuser -u "${SERVICE_USER}" -- "${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

if [[ ! -f "${ETC_DIR}/${SERVICE_NAME}.env" ]]; then
  SECRET_KEY="$(openssl rand -hex 32 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(32))')"
  install -m 0640 -o root -g "${SERVICE_GROUP}" /dev/null "${ETC_DIR}/${SERVICE_NAME}.env"
  cat > "${ETC_DIR}/${SERVICE_NAME}.env" <<EOF
APP_NAME=${APP_NAME}
ENVIRONMENT=production
DATABASE_URL=${MONGODB_URI}
SECRET_KEY=${SECRET_KEY}
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me-now
SESSION_COOKIE_SECURE=true
BEDROCK_REGION=eu-central-1
BEDROCK_MODEL_ID=eu.anthropic.claude-sonnet-4-6
BEDROCK_API_KEY_FILE=${ETC_DIR}/bedrock-long-term-api-key.csv
EOF
  chmod 0640 "${ETC_DIR}/${SERVICE_NAME}.env"
  log "Environment-Datei angelegt: ${ETC_DIR}/${SERVICE_NAME}.env"
fi

cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=${APP_NAME}
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ETC_DIR}/${SERVICE_NAME}.env
ExecStart=${APP_DIR}/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${APP_PORT} --workers 1
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ReadWritePaths=${DATA_DIR}

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}.service"
sleep 2
systemctl --no-pager --full status "${SERVICE_NAME}.service" || true
curl --fail --silent "http://127.0.0.1:${APP_PORT}/health" >/dev/null || die "Healthcheck fehlgeschlagen. Logs: journalctl -u ${SERVICE_NAME} -e"

cat <<EOF

Installation abgeschlossen.

Lokaler Dienst: http://127.0.0.1:${APP_PORT}
Environment:    ${ETC_DIR}/${SERVICE_NAME}.env
Datenbank:      ${DATA_DIR}/ki_email.db
Logs:           journalctl -u ${SERVICE_NAME} -f

Nächste Schritte in ISPConfig:
1. Website/Domain anlegen oder die gewünschte Domain auswählen.
2. Reverse Proxy auf http://127.0.0.1:${APP_PORT} konfigurieren.
3. SSL/Let's Encrypt in ISPConfig aktivieren.
4. ADMIN_EMAIL und ADMIN_PASSWORD in ${ETC_DIR}/${SERVICE_NAME}.env setzen.
5. Danach: systemctl restart ${SERVICE_NAME}

Der Bedrock-Key wird nicht automatisch kopiert. Falls verwendet, als root nach
${ETC_DIR}/bedrock-long-term-api-key.csv legen und mit 0640 sowie Gruppe ${SERVICE_GROUP} schützen.
EOF

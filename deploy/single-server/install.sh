#!/usr/bin/env bash
set -Eeuo pipefail

# Vollständige Installation auf einem einzelnen Debian/Ubuntu-Server.
# Nginx dient als Reverse Proxy; die Anwendung selbst läuft als systemd-Dienst.

APP_NAME="${APP_NAME:-AboroDesk Developer}"
APP_DIR="${APP_DIR:-/opt/aborodesk}"
DATA_DIR="${DATA_DIR:-/var/lib/aborodesk}"
ETC_DIR="${ETC_DIR:-/etc/aborodesk}"
SERVICE_NAME="${SERVICE_NAME:-aborodesk}"
SERVICE_USER="${SERVICE_USER:-aborodesk}"
APP_PORT="${APP_PORT:-8000}"
DOMAIN="${DOMAIN:-_}"
ENABLE_TLS="${ENABLE_TLS:-0}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"
SOURCE_DIR="${SOURCE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

die() { echo "FEHLER: $*" >&2; exit 1; }
log() { echo "[AboroDesk] $*"; }

[[ "${EUID}" -eq 0 ]] || die "Bitte als root ausführen."
command -v apt-get >/dev/null || die "Dieses Skript erwartet Debian/Ubuntu mit apt-get."
[[ -d "${SOURCE_DIR}/app" ]] || die "Quellverzeichnis nicht gefunden: ${SOURCE_DIR}"
[[ "${ENABLE_TLS}" != "1" || "${DOMAIN}" != "_" ]] || die "ENABLE_TLS=1 benötigt DOMAIN=deine-domain.tld."
[[ "${ENABLE_TLS}" != "1" || -n "${CERTBOT_EMAIL}" ]] || die "ENABLE_TLS=1 benötigt CERTBOT_EMAIL."

log "Installiere Systempakete …"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends python3 python3-venv python3-pip rsync curl ca-certificates nginx openssl
if [[ "${ENABLE_TLS}" == "1" ]]; then
  apt-get install -y --no-install-recommends certbot python3-certbot-nginx
fi

if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --home-dir "${APP_DIR}" --create-home --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

install -d -m 0750 -o "${SERVICE_USER}" -g "${SERVICE_USER}" "${APP_DIR}" "${DATA_DIR}"
install -d -m 0750 -o root -g "${SERVICE_USER}" "${ETC_DIR}"

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
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${APP_DIR}"

log "Installiere Python-Abhängigkeiten …"
runuser -u "${SERVICE_USER}" -- python3 -m venv "${APP_DIR}/.venv"
runuser -u "${SERVICE_USER}" -- "${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip
runuser -u "${SERVICE_USER}" -- "${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

if [[ ! -f "${ETC_DIR}/${SERVICE_NAME}.env" ]]; then
  SECRET_KEY="$(openssl rand -hex 32)"
  install -m 0640 -o root -g "${SERVICE_USER}" /dev/null "${ETC_DIR}/${SERVICE_NAME}.env"
  cat > "${ETC_DIR}/${SERVICE_NAME}.env" <<EOF
APP_NAME=${APP_NAME}
ENVIRONMENT=production
DATABASE_URL=sqlite:////var/lib/aborodesk/ki_email.db
SECRET_KEY=${SECRET_KEY}
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me-now
SESSION_COOKIE_SECURE=true
BEDROCK_REGION=eu-central-1
BEDROCK_MODEL_ID=eu.anthropic.claude-sonnet-4-6
BEDROCK_API_KEY_FILE=${ETC_DIR}/bedrock-long-term-api-key.csv
EOF
  chmod 0640 "${ETC_DIR}/${SERVICE_NAME}.env"
fi

cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=${APP_NAME}
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
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

cat > "/etc/nginx/sites-available/${SERVICE_NAME}" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};
    client_max_body_size 25m;

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
ln -sfn "/etc/nginx/sites-available/${SERVICE_NAME}" "/etc/nginx/sites-enabled/${SERVICE_NAME}"
rm -f /etc/nginx/sites-enabled/default
nginx -t

systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}.service"
systemctl reload nginx
sleep 2
curl --fail --silent "http://127.0.0.1:${APP_PORT}/health" >/dev/null || die "Healthcheck fehlgeschlagen. Logs: journalctl -u ${SERVICE_NAME} -e"

if [[ "${ENABLE_TLS}" == "1" ]]; then
  log "Fordere Let's-Encrypt-Zertifikat an …"
  certbot --nginx --non-interactive --agree-tos --redirect --email "${CERTBOT_EMAIL}" -d "${DOMAIN}"
fi

cat <<EOF

Installation abgeschlossen.

Adresse:         http://${DOMAIN}
Lokaler Dienst:  http://127.0.0.1:${APP_PORT}
Environment:     ${ETC_DIR}/${SERVICE_NAME}.env
Datenbank:       ${DATA_DIR}/ki_email.db
Logs:            journalctl -u ${SERVICE_NAME} -f

Vor dem produktiven Login ADMIN_EMAIL und ADMIN_PASSWORD in der Environment-Datei setzen:
  ${ETC_DIR}/${SERVICE_NAME}.env
Danach: systemctl restart ${SERVICE_NAME}

Der Bedrock-Key wird nicht automatisch kopiert. Falls verwendet, als root nach
${ETC_DIR}/bedrock-long-term-api-key.csv legen und mit 0640 sowie Gruppe ${SERVICE_USER} schützen.
EOF

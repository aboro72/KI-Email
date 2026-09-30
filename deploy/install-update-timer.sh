#!/usr/bin/env bash
set -Eeuo pipefail

REPOSITORY_URL="${REPOSITORY_URL:-}"
GIT_BRANCH="${GIT_BRANCH:-master}"
SERVICE_NAME="${SERVICE_NAME:-aborodesk}"
APP_PORT="${APP_PORT:-8001}"
APP_DIR="${APP_DIR:-/opt/aborodesk}"
SOURCE_DIR="${SOURCE_DIR:-/var/lib/aborodesk-updater/source}"
CONFIG_DIR="${CONFIG_DIR:-/etc/aborodesk}"
CONFIG_FILE="${CONFIG_DIR}/update.env"

[[ "${EUID}" -eq 0 ]] || { echo "Bitte als root ausführen." >&2; exit 1; }
[[ -n "${REPOSITORY_URL}" ]] || { echo "REPOSITORY_URL muss gesetzt werden." >&2; exit 1; }
command -v systemctl >/dev/null || { echo "systemd ist erforderlich." >&2; exit 1; }
[[ -x "${APP_DIR}/deploy/update.sh" ]] || { echo "${APP_DIR}/deploy/update.sh fehlt." >&2; exit 1; }

install -d -m 0750 -o root -g root "${CONFIG_DIR}"
cat > "${CONFIG_FILE}" <<EOF
REPOSITORY_URL=${REPOSITORY_URL}
GIT_BRANCH=${GIT_BRANCH}
APP_DIR=${APP_DIR}
SOURCE_DIR=${SOURCE_DIR}
SERVICE_NAME=${SERVICE_NAME}
HEALTH_URL=http://127.0.0.1:${APP_PORT}/health
EOF
chmod 0600 "${CONFIG_FILE}"

cat > /etc/systemd/system/aborodesk-update.service <<EOF
[Unit]
Description=AboroDesk auf neue Git-Version prüfen
After=network-online.target ${SERVICE_NAME}.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=${APP_DIR}/deploy/update.sh
EOF

cat > /etc/systemd/system/aborodesk-update.timer <<'EOF'
[Unit]
Description=AboroDesk alle 20 Minuten auf Updates prüfen

[Timer]
OnBootSec=5min
OnUnitActiveSec=20min
AccuracySec=1min
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now aborodesk-update.timer
systemctl start --no-block aborodesk-update.service

echo "Update-Timer eingerichtet."
echo "Prüfung: systemctl list-timers aborodesk-update.timer"
echo "Logs:    journalctl -u aborodesk-update.service"

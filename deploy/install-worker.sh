#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/aborodesk}"
ETC_DIR="${ETC_DIR:-/etc/aborodesk}"
SERVICE_NAME="${SERVICE_NAME:-aborodesk}"
SERVICE_USER="${SERVICE_USER:-aborodesk}"
SERVICE_GROUP="${SERVICE_GROUP:-${SERVICE_USER}}"
WORKER_INTERVAL_SECONDS="${WORKER_INTERVAL_SECONDS:-10}"

[[ "${EUID}" -eq 0 ]] || { echo "Bitte als root ausführen." >&2; exit 1; }
[[ -x "${APP_DIR}/.venv/bin/python" ]] || { echo "Python-Umgebung fehlt: ${APP_DIR}/.venv" >&2; exit 1; }
cat > "/etc/systemd/system/${SERVICE_NAME}-worker.service" <<EOF
[Unit]
Description=${SERVICE_NAME} Hintergrundaufgaben
After=network-online.target ${SERVICE_NAME}.service
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ETC_DIR}/${SERVICE_NAME}.env
Environment=WORKER_INTERVAL_SECONDS=${WORKER_INTERVAL_SECONDS}
ExecStart=${APP_DIR}/.venv/bin/python -m app.worker
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ReadWritePaths=/var/lib/aborodesk

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}-worker.service"
systemctl --no-pager --full status "${SERVICE_NAME}-worker.service" || true
echo "Worker aktiv: journalctl -u ${SERVICE_NAME}-worker -f"

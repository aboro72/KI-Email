#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/aborodesk}"
SERVICE_NAME="${SERVICE_NAME:-aborodesk}"
SERVICE_USER="${SERVICE_USER:-web29}"
SERVICE_GROUP="${SERVICE_GROUP:-client2}"
INTERVAL="${INTERVAL:-12h}"
PROSPECTS_PER_QUERY="${PROSPECTS_PER_QUERY:-2}"
[[ "${EUID}" -eq 0 ]] || { echo "Bitte als root ausführen." >&2; exit 1; }
cat > "/etc/systemd/system/${SERVICE_NAME}-prospect-discovery.service" <<EOF
[Unit]
Description=${SERVICE_NAME} automatische Firmenrecherche
After=network-online.target ${SERVICE_NAME}-worker.service
Wants=network-online.target

[Service]
Type=oneshot
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${APP_DIR}
EnvironmentFile=/etc/aborodesk/${SERVICE_NAME}.env
Environment=PROSPECTS_PER_QUERY=${PROSPECTS_PER_QUERY}
ExecStart=${APP_DIR}/.venv/bin/python ${APP_DIR}/scripts/discover_prospects.py
EOF
cat > "/etc/systemd/system/${SERVICE_NAME}-prospect-discovery.timer" <<EOF
[Unit]
Description=${SERVICE_NAME} Recherche-Timer

[Timer]
OnBootSec=15min
OnUnitActiveSec=${INTERVAL}
Persistent=true
RandomizedDelaySec=30m

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}-prospect-discovery.timer"
echo "Prospect-Recherche aktiv: systemctl list-timers ${SERVICE_NAME}-prospect-discovery.timer"

#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/aborodesk}"
ETC_DIR="${ETC_DIR:-/etc/aborodesk}"
SERVICE_NAME="${SERVICE_NAME:-aborodesk}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/aborodesk/mongodb}"
MONGODB_URI="${MONGODB_URI:-}"
[[ "${EUID}" -eq 0 ]] || { echo "Bitte als root ausführen." >&2; exit 1; }
[[ -n "${MONGODB_URI}" ]] || { echo "MONGODB_URI fehlt." >&2; exit 1; }
install -d -m 0700 "${BACKUP_DIR}"
install -d -m 0750 "${ETC_DIR}"
install -m 0640 /dev/null "${ETC_DIR}/backup.env"
grep -q '^MONGODB_URI=' "${ETC_DIR}/backup.env" 2>/dev/null || printf 'MONGODB_URI=%s\nBACKUP_DIR=%s\nRETENTION_DAYS=14\n' "${MONGODB_URI}" "${BACKUP_DIR}" > "${ETC_DIR}/backup.env"
cat > "/etc/systemd/system/${SERVICE_NAME}-backup.service" <<EOF
[Unit]
Description=${SERVICE_NAME} tägliches MongoDB-Backup
After=network-online.target

[Service]
Type=oneshot
EnvironmentFile=${ETC_DIR}/backup.env
ExecStart=${APP_DIR}/deploy/backup-mongodb.sh
EOF
cat > "/etc/systemd/system/${SERVICE_NAME}-backup.timer" <<EOF
[Unit]
Description=${SERVICE_NAME} Backup-Timer

[Timer]
OnCalendar=*-*-* 02:30:00
Persistent=true
RandomizedDelaySec=15m

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}-backup.timer"
echo "Backup-Timer aktiv: systemctl list-timers ${SERVICE_NAME}-backup.timer"

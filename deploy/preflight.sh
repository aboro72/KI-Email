#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_DIR="${SOURCE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
MONGODB_URI="${MONGODB_URI:-}"
errors=0
check() { if "$@" >/dev/null 2>&1; then echo "OK   $*"; else echo "FEHLT $*"; errors=$((errors + 1)); fi; }

echo "AboroDesk Installationsprüfung"
echo "Projekt: ${SOURCE_DIR}"
[[ -d "${SOURCE_DIR}/app" ]] && echo "OK   app-Verzeichnis" || { echo "FEHLT app-Verzeichnis"; errors=$((errors + 1)); }
[[ -f "${SOURCE_DIR}/requirements.txt" ]] && echo "OK   requirements.txt" || { echo "FEHLT requirements.txt"; errors=$((errors + 1)); }
check command -v python3
check command -v pip3
check command -v curl
check command -v rsync
check command -v openssl
if command -v python3 >/dev/null 2>&1; then
  python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' && echo "OK   Python >= 3.11" || { echo "FEHLT Python >= 3.11"; errors=$((errors + 1)); }
fi
if [[ -n "${MONGODB_URI}" ]]; then
  MONGODB_URI="${MONGODB_URI}" python3 -c 'from urllib.parse import urlparse; import os; raise SystemExit(0 if urlparse(os.environ["MONGODB_URI"]).scheme in {"mongodb", "mongodb+srv"} else 1)' && echo "OK   MongoDB-URI" || { echo "FEHLT gültige MongoDB-URI"; errors=$((errors + 1)); }
else
  echo "WARN MONGODB_URI nicht gesetzt (bei Produktionsinstallation erforderlich)"
fi
if (( errors > 0 )); then echo "Prüfung fehlgeschlagen: ${errors} Problem(e)."; exit 1; fi
echo "Vorprüfung erfolgreich."

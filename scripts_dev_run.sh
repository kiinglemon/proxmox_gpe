#!/usr/bin/env bash
# Lancement local en mode développement/démo (sans installer de service systemd).
# Utile pour tester l'app sur un poste, ou pendant que l'infra Proxmox n'est pas prête.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR/backend"

VENV=".venv"
[[ -d "$VENV" ]] || python3 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --upgrade pip -q
pip install -q -r requirements.txt

# Config par défaut si absente : mode démo (mock).
if [[ ! -f "$DIR/config/infraone.env" ]]; then
  cp "$DIR/config/infraone.env.example" "$DIR/config/infraone.env"
  sed -i 's/^INFRAONE_MOCK_PROXMOX=.*/INFRAONE_MOCK_PROXMOX=1/' "$DIR/config/infraone.env"
fi
set -a; source "$DIR/config/infraone.env"; set +a

echo "→ InfraOne (démo) : http://localhost:${INFRAONE_PORT:-8000}/"
exec uvicorn app.main:app --reload --host 127.0.0.1 --port "${INFRAONE_PORT:-8000}"

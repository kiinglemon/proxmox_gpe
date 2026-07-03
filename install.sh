#!/usr/bin/env bash
# Point d'entrée racine — délègue à setup/bootstrap.sh.
# Exemple :  sudo ./install.sh          (Proxmox réel)
#            sudo ./install.sh --mock   (démo sans infra)
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$DIR/setup/bootstrap.sh" "$@"

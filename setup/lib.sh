#!/usr/bin/env bash
# Bibliothèque partagée par les scripts d'installation InfraOne.
# shellcheck disable=SC2034
set -euo pipefail

# --- Chemins ---------------------------------------------------------------
SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SETUP_DIR/.." && pwd)"
ENV_FILE="$REPO_ROOT/config/infraone.env"
ENV_EXAMPLE="$REPO_ROOT/config/infraone.env.example"

# --- Couleurs / journalisation --------------------------------------------
if [[ -t 1 ]]; then
  C_RESET='\033[0m'; C_BLUE='\033[1;34m'; C_GREEN='\033[1;32m'
  C_YELLOW='\033[1;33m'; C_RED='\033[1;31m'; C_DIM='\033[2m'
else
  C_RESET=''; C_BLUE=''; C_GREEN=''; C_YELLOW=''; C_RED=''; C_DIM=''
fi
log()   { echo -e "${C_BLUE}[InfraOne]${C_RESET} $*"; }
ok()    { echo -e "${C_GREEN}  ✔${C_RESET} $*"; }
warn()  { echo -e "${C_YELLOW}  ⚠${C_RESET} $*"; }
err()   { echo -e "${C_RED}  ✘${C_RESET} $*" >&2; }
die()   { err "$*"; exit 1; }
step()  { echo; echo -e "${C_BLUE}━━ $* ━━${C_RESET}"; }

# --- Vérifications ----------------------------------------------------------
require_root() {
  [[ "${EUID:-$(id -u)}" -eq 0 ]] || die "Ce script doit être exécuté en root (utilisez sudo)."
}
has_cmd() { command -v "$1" >/dev/null 2>&1; }
is_proxmox() { has_cmd pveversion || has_cmd qm; }

# --- Gestion du fichier d'environnement ------------------------------------
ensure_env_file() {
  if [[ ! -f "$ENV_FILE" ]]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    ok "config/infraone.env créé depuis l'exemple."
  fi
}

# Met à jour (ou ajoute) une clé=valeur dans config/infraone.env
set_env() {
  local key="$1" value="$2"
  ensure_env_file
  if grep -qE "^${key}=" "$ENV_FILE"; then
    # échappe les caractères spéciaux sed dans la valeur
    local esc; esc=$(printf '%s' "$value" | sed -e 's/[\/&|]/\\&/g')
    sed -i "s|^${key}=.*|${key}=${esc}|" "$ENV_FILE"
  else
    echo "${key}=${value}" >> "$ENV_FILE"
  fi
}

get_env() {
  local key="$1"
  [[ -f "$ENV_FILE" ]] || { echo ""; return; }
  grep -E "^${key}=" "$ENV_FILE" | tail -n1 | cut -d= -f2-
}

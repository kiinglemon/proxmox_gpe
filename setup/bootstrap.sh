#!/usr/bin/env bash
# ============================================================================
#  InfraOne — installation automatique de bout en bout sur un hôte Proxmox.
#
#  Usage :
#     sudo ./setup/bootstrap.sh              # installation complète (Proxmox réel)
#     sudo ./setup/bootstrap.sh --mock       # installe l'app en mode démo (sans infra)
#     sudo ./setup/bootstrap.sh --no-template  # saute la création du template
#
#  Le script est idempotent : il peut être relancé sans risque.
# ============================================================================
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

MOCK=0
DO_TEMPLATE=1
DO_APIUSER=1
for arg in "$@"; do
  case "$arg" in
    --mock)        MOCK=1 ;;
    --no-template) DO_TEMPLATE=0 ;;
    --no-apiuser)  DO_APIUSER=0 ;;
    -h|--help)
      grep -E '^#( |$)' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) warn "Argument inconnu ignoré : $arg" ;;
  esac
done

echo -e "${C_BLUE}"
cat <<'BANNER'
   ___        __        ___
  |_ _|_ _  / _|_ _ __ / _ \ _ _  ___
   | || ' \|  _| '_/ _` (_) | ' \/ -_)
  |___|_||_|_| |_| \__,_\___/|_||_\___|   Console d'automatisation Proxmox
BANNER
echo -e "${C_RESET}"

require_root
ensure_env_file

# 00 · préflight
bash "$SETUP_DIR/00-preflight.sh"

# 10 · paquets
bash "$SETUP_DIR/10-host-packages.sh"

if [[ "$MOCK" -eq 1 ]]; then
  step "Mode DÉMO (mock Proxmox)"
  set_env INFRAONE_MOCK_PROXMOX 1
  warn "Installation en mode démo : l'app simulera les VMs (aucune infra requise)."
else
  # 20 · compte + token API
  if [[ "$DO_APIUSER" -eq 1 ]] && is_proxmox; then
    bash "$SETUP_DIR/20-proxmox-apiuser.sh"
  else
    warn "Étape API Proxmox ignorée."
  fi
  # 30 · template cloud-init
  if [[ "$DO_TEMPLATE" -eq 1 ]] && is_proxmox; then
    bash "$SETUP_DIR/30-vm-template.sh"
  else
    warn "Étape template ignorée."
  fi
  # Si on n'est pas sur Proxmox, bascule automatiquement en mock pour rester utilisable.
  if ! is_proxmox; then
    warn "Hôte non-Proxmox : bascule automatique en mode démo (mock)."
    set_env INFRAONE_MOCK_PROXMOX 1
  fi
fi

# 40 · application
bash "$SETUP_DIR/40-deploy-app.sh"

step "Installation terminée 🎉"
ok "Configuration : $ENV_FILE"
ok "Documentation : $REPO_ROOT/README.md"

#!/usr/bin/env bash
# 10 — Installation des paquets système requis par InfraOne.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

step "10 · Installation des paquets système"
require_root

PKGS=(python3 python3-venv python3-pip git curl wget ansible libguestfs-tools)

if has_cmd apt-get; then
  export DEBIAN_FRONTEND=noninteractive
  log "Mise à jour de l'index des paquets (apt)…"
  apt-get update -qq || warn "apt-get update a renvoyé un avertissement (on continue)."
  log "Installation : ${PKGS[*]}"
  # On installe paquet par paquet pour ne pas tout casser si l'un manque au dépôt.
  for p in "${PKGS[@]}"; do
    if apt-get install -y -qq "$p" >/dev/null 2>&1; then
      ok "$p installé."
    else
      warn "Échec d'installation de '$p' (dépôt indisponible ?)."
    fi
  done
else
  warn "Gestionnaire apt introuvable. Installez manuellement : ${PKGS[*]}"
fi

# Vérifications clés
for c in python3 pip3 ansible-playbook; do
  if has_cmd "$c"; then ok "$c : $(command -v "$c")"; else warn "$c introuvable."; fi
done

py_ver=$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo "?")
ok "Python détecté : $py_ver"

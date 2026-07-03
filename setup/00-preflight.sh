#!/usr/bin/env bash
# 00 — Vérifications préalables (hôte Proxmox, RAM, CPU) et calibrage.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

step "00 · Vérifications préalables"
require_root

if is_proxmox; then
  ok "Hôte Proxmox détecté : $(pveversion 2>/dev/null | head -n1 || echo 'qm présent')."
else
  warn "Proxmox (pveversion/qm) non détecté sur cette machine."
  warn "Le mode démo (INFRAONE_MOCK_PROXMOX=1) reste disponible pour tester l'app."
fi

# --- Ressources ------------------------------------------------------------
mem_mb=$(free -m 2>/dev/null | awk '/^Mem:/{print $2}')
cpus=$(nproc 2>/dev/null || echo 0)
ok "Ressources détectées : ${mem_mb:-?} Mo RAM, ${cpus:-?} vCPU."

if [[ -n "${mem_mb:-}" && "$mem_mb" -lt 12000 ]]; then
  warn "RAM < 12 Go : hôte modeste. Valeurs par défaut réduites appliquées."
  # Sur 10 Go, on limite fortement les VMs pour préserver l'hôte + InfraOne.
  ensure_env_file
  set_env DEFAULT_VM_CORES 1
  set_env DEFAULT_VM_MEMORY 1024
  set_env DEFAULT_VM_DISK_GB 8
  set_env MAX_VM_CORES 2
  set_env MAX_VM_MEMORY 2048
  set_env MAX_VM_DISK_GB 20
  ok "Garde-fous VM : max 2 vCPU / 2048 Mo / 20 Go par VM."
fi

# --- Node Proxmox ----------------------------------------------------------
if is_proxmox; then
  node=$(hostname)
  set_env PROXMOX_NODE "$node"
  ok "Node Proxmox : $node (enregistré dans config)."
  # Détecte un storage supportant les images (local-lvm par défaut)
  if has_cmd pvesm; then
    if pvesm status 2>/dev/null | awk '{print $1}' | grep -qx "local-lvm"; then
      set_env INFRAONE_STORAGE local-lvm
    elif pvesm status 2>/dev/null | awk 'NR>1{print $1}' | head -n1 | grep -q .; then
      st=$(pvesm status 2>/dev/null | awk 'NR>1{print $1; exit}')
      set_env INFRAONE_STORAGE "$st"
      warn "Storage 'local-lvm' absent : utilisation de '$st'."
    fi
  fi
fi

ok "Préflight terminé."

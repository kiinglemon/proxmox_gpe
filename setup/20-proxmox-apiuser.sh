#!/usr/bin/env bash
# 20 — Création du rôle, de l'utilisateur et du token API InfraOne dans Proxmox.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

step "20 · Compte & token API Proxmox"
require_root
ensure_env_file

if ! has_cmd pveum; then
  warn "pveum introuvable : cette machine n'est pas un hôte Proxmox."
  warn "Étape ignorée. Activez le mode démo ou renseignez PROXMOX_TOKEN_* à la main."
  exit 0
fi

ROLE="InfraOne"
USER_ID="infraone@pve"
TOKEN_NAME="automation"
TOKEN_ID="${USER_ID}!${TOKEN_NAME}"

# Privilèges minimaux nécessaires au provisioning et à la configuration de VM.
PRIVS="VM.Allocate,VM.Clone,VM.Config.CDROM,VM.Config.CPU,VM.Config.Cloudinit,\
VM.Config.Disk,VM.Config.HWType,VM.Config.Memory,VM.Config.Network,\
VM.Config.Options,VM.Monitor,VM.Audit,VM.PowerMgmt,\
Datastore.AllocateSpace,Datastore.Audit"

# --- Rôle ------------------------------------------------------------------
if pveum role list 2>/dev/null | awk '{print $1}' | grep -qx "$ROLE"; then
  pveum role modify "$ROLE" --privs "$PRIVS" >/dev/null 2>&1 || true
  ok "Rôle '$ROLE' mis à jour."
else
  pveum role add "$ROLE" --privs "$PRIVS"
  ok "Rôle '$ROLE' créé."
fi

# --- Utilisateur -----------------------------------------------------------
if pveum user list 2>/dev/null | awk '{print $1}' | grep -qx "$USER_ID"; then
  ok "Utilisateur '$USER_ID' déjà présent."
else
  pveum user add "$USER_ID" --comment "Compte de service InfraOne"
  ok "Utilisateur '$USER_ID' créé."
fi

# --- ACL (droits sur toute l'arborescence /) -------------------------------
pveum aclmod / --users "$USER_ID" --roles "$ROLE" >/dev/null 2>&1 || \
  pveum acl modify / --users "$USER_ID" --roles "$ROLE" >/dev/null 2>&1 || true
ok "ACL appliquée (rôle '$ROLE' sur /)."

# --- Token -----------------------------------------------------------------
existing_secret="$(get_env PROXMOX_TOKEN_SECRET)"
if pveum user token list "$USER_ID" 2>/dev/null | awk '{print $1}' | grep -qx "$TOKEN_NAME"; then
  if [[ -n "$existing_secret" ]]; then
    ok "Token '$TOKEN_ID' déjà configuré (secret présent)."
  else
    warn "Le token '$TOKEN_NAME' existe déjà mais son secret n'est pas connu."
    warn "Suppression puis recréation pour récupérer un nouveau secret…"
    pveum user token remove "$USER_ID" "$TOKEN_NAME" >/dev/null 2>&1 || true
  fi
fi

if ! pveum user token list "$USER_ID" 2>/dev/null | awk '{print $1}' | grep -qx "$TOKEN_NAME"; then
  # --privsep 0 : le token hérite des droits de l'utilisateur.
  out="$(pveum user token add "$USER_ID" "$TOKEN_NAME" --privsep 0 --output-format json 2>/dev/null)"
  secret="$(printf '%s' "$out" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("value",""))' 2>/dev/null)"
  if [[ -z "$secret" ]]; then
    # Repli : format texte "value: xxxx"
    secret="$(printf '%s' "$out" | grep -oE '[0-9a-f]{8}-[0-9a-f-]{27,}' | head -n1)"
  fi
  [[ -n "$secret" ]] || die "Impossible de récupérer le secret du token. Sortie : $out"
  set_env PROXMOX_TOKEN_SECRET "$secret"
  ok "Token '$TOKEN_ID' créé et secret enregistré dans config/infraone.env."
fi

set_env PROXMOX_TOKEN_ID "$TOKEN_ID"
set_env PROXMOX_HOST "127.0.0.1:8006"
set_env INFRAONE_MOCK_PROXMOX 0
ok "Connexion API Proxmox configurée (PROXMOX_TOKEN_ID=$TOKEN_ID)."

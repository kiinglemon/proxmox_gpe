#!/usr/bin/env bash
# 40 — Déploiement de l'application InfraOne (venv, dépendances, service systemd).
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

step "40 · Déploiement de l'application InfraOne"
require_root
ensure_env_file

VENV="$REPO_ROOT/backend/.venv"
PYBIN="$VENV/bin/python"

# --- Environnement virtuel + dépendances -----------------------------------
if [[ ! -d "$VENV" ]]; then
  log "Création de l'environnement virtuel Python…"
  python3 -m venv "$VENV"
fi
log "Installation des dépendances Python…"
"$PYBIN" -m pip install --upgrade pip -q
if "$PYBIN" -m pip install -q -r "$REPO_ROOT/backend/requirements.txt"; then
  ok "Dépendances installées."
else
  warn "Installation en ligne échouée (pas d'accès PyPI ?). Vérifiez la connexion."
fi

# --- Clé secrète JWT --------------------------------------------------------
if [[ "$(get_env INFRAONE_SECRET_KEY)" =~ change-me ]] || [[ -z "$(get_env INFRAONE_SECRET_KEY)" ]]; then
  secret="$(openssl rand -hex 32 2>/dev/null || "$PYBIN" -c 'import secrets;print(secrets.token_hex(32))')"
  set_env INFRAONE_SECRET_KEY "$secret"
  ok "Clé secrète JWT générée."
fi

# --- Mot de passe admin -----------------------------------------------------
admin_pw="$(get_env INFRAONE_ADMIN_PASSWORD)"
if [[ -z "$admin_pw" || "$admin_pw" == "infraone" ]]; then
  new_pw="$(openssl rand -base64 12 2>/dev/null | tr -d '/+=' | cut -c1-14 || echo "InfraOne$RANDOM")"
  set_env INFRAONE_ADMIN_PASSWORD "$new_pw"
  ADMIN_PW_GENERATED="$new_pw"
  ok "Mot de passe administrateur généré."
fi

# --- Service systemd --------------------------------------------------------
PORT="$(get_env INFRAONE_PORT)"; PORT="${PORT:-8000}"
HOST="$(get_env INFRAONE_HOST)"; HOST="${HOST:-0.0.0.0}"
UNIT="/etc/systemd/system/infraone.service"

if [[ -d /run/systemd/system ]]; then
  log "Installation du service systemd…"
  cat > "$UNIT" <<EOF
[Unit]
Description=InfraOne - Console d'automatisation Proxmox
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$REPO_ROOT/backend
EnvironmentFile=$ENV_FILE
ExecStart=$VENV/bin/uvicorn app.main:app --host $HOST --port $PORT
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable infraone.service >/dev/null 2>&1 || true
  systemctl restart infraone.service
  sleep 2
  if systemctl is-active --quiet infraone.service; then
    ok "Service infraone actif (systemctl status infraone)."
  else
    warn "Le service ne s'est pas lancé. Diagnostic : journalctl -u infraone -n 40"
  fi
else
  warn "systemd absent : lancez l'app manuellement (voir README, section 'Lancement manuel')."
fi

# --- Récapitulatif ----------------------------------------------------------
ip=$(hostname -I 2>/dev/null | awk '{print $1}')
echo
ok "InfraOne est déployé."
echo -e "   ${C_GREEN}URL${C_RESET}        : http://${ip:-<ip-hote>}:${PORT}/"
echo -e "   ${C_GREEN}Login${C_RESET}      : $(get_env INFRAONE_ADMIN_USER)"
if [[ -n "${ADMIN_PW_GENERATED:-}" ]]; then
  echo -e "   ${C_GREEN}Mot de passe${C_RESET} : ${ADMIN_PW_GENERATED}   ${C_DIM}(noté dans config/infraone.env)${C_RESET}"
else
  echo -e "   ${C_GREEN}Mot de passe${C_RESET} : (voir INFRAONE_ADMIN_PASSWORD dans config/infraone.env)"
fi

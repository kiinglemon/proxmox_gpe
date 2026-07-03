#!/usr/bin/env bash
# 30 — Création d'un template cloud-init Debian 12 (léger) pour le provisioning.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

step "30 · Template VM cloud-init (Debian 12)"
require_root
ensure_env_file

if ! has_cmd qm; then
  warn "'qm' introuvable : pas un hôte Proxmox. Étape ignorée."
  exit 0
fi

TEMPLATE_ID="$(get_env INFRAONE_TEMPLATE_ID)"; TEMPLATE_ID="${TEMPLATE_ID:-9000}"
STORAGE="$(get_env INFRAONE_STORAGE)";         STORAGE="${STORAGE:-local-lvm}"
BRIDGE="$(get_env INFRAONE_BRIDGE)";           BRIDGE="${BRIDGE:-vmbr0}"
IMG_NAME="debian-12-genericcloud-amd64.qcow2"
IMG_URL="https://cloud.debian.org/images/cloud/bookworm/latest/${IMG_NAME}"
IMG_DIR="/var/lib/vz/template/cache"
IMG_PATH="${IMG_DIR}/${IMG_NAME}"

# Déjà un template ?
if qm status "$TEMPLATE_ID" >/dev/null 2>&1; then
  ok "La VM/template $TEMPLATE_ID existe déjà. Étape ignorée."
  exit 0
fi

mkdir -p "$IMG_DIR"
if [[ ! -f "$IMG_PATH" ]]; then
  log "Téléchargement de l'image cloud Debian 12 (~350 Mo)…"
  if ! wget -q --show-progress -O "$IMG_PATH" "$IMG_URL"; then
    rm -f "$IMG_PATH"
    die "Échec du téléchargement de l'image ($IMG_URL). Vérifiez la connexion Internet."
  fi
  ok "Image téléchargée : $IMG_PATH"
else
  ok "Image déjà présente : $IMG_PATH"
fi

log "Création de la VM template $TEMPLATE_ID…"
qm create "$TEMPLATE_ID" \
  --name "debian12-cloudinit" \
  --memory 1024 --cores 1 --cpu host \
  --net0 "virtio,bridge=${BRIDGE}" \
  --scsihw virtio-scsi-pci \
  --serial0 socket --vga serial0 \
  --agent enabled=1 \
  --ostype l26

log "Import du disque dans le storage '$STORAGE'…"
qm importdisk "$TEMPLATE_ID" "$IMG_PATH" "$STORAGE" >/dev/null

# Le disque importé s'appelle vm-<id>-disk-0 (LVM) ou apparaît en 'unused0'.
qm set "$TEMPLATE_ID" --scsi0 "${STORAGE}:vm-${TEMPLATE_ID}-disk-0" >/dev/null 2>&1 || \
  qm set "$TEMPLATE_ID" --scsi0 "$(qm config "$TEMPLATE_ID" | awk -F': ' '/^unused0/{print $2}')" >/dev/null

qm set "$TEMPLATE_ID" --ide2 "${STORAGE}:cloudinit" >/dev/null
qm set "$TEMPLATE_ID" --boot c --bootdisk scsi0 >/dev/null
qm set "$TEMPLATE_ID" --ipconfig0 "ip=dhcp" >/dev/null

log "Conversion en template…"
qm template "$TEMPLATE_ID" >/dev/null

set_env INFRAONE_TEMPLATE_ID "$TEMPLATE_ID"
ok "Template cloud-init prêt (id $TEMPLATE_ID, storage $STORAGE, bridge $BRIDGE)."
ok "InfraOne clonera ce template pour chaque nouvelle VM."

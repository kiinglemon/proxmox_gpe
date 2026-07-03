"""Déploiement d'un service de base via Ansible (US-007).

On lance ansible-playbook en ciblant l'IP de la VM. En mode mock, le
déploiement est simulé pour rester démontrable sans infra.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .config import get_settings

SUPPORTED = {"nginx": "deploy-nginx.yml", "apache": "deploy-apache.yml"}


def deploy_service(service: str, host: str, *, ssh_user: str | None = None,
                   ssh_password: str | None = None) -> dict:
    settings = get_settings()
    service = service.lower()
    if service not in SUPPORTED:
        return {"ok": False, "message": f"Service non supporté : {service}. "
                                        f"Choix possibles : {', '.join(SUPPORTED)}."}

    playbook = Path(settings.ansible_playbook_dir) / SUPPORTED[service]
    ssh_user = ssh_user or settings.default_ci_user
    ssh_password = ssh_password or settings.default_ci_password

    if settings.infraone_mock_proxmox:
        return {"ok": True,
                "message": f"[MOCK] Déploiement simulé de '{service}' sur {host} "
                           f"(playbook {playbook.name})."}

    if not playbook.exists():
        return {"ok": False, "message": f"Playbook introuvable : {playbook}"}
    if shutil.which("ansible-playbook") is None:
        return {"ok": False, "message": "'ansible-playbook' introuvable. "
                                        "Installez Ansible (setup/10-host-packages.sh)."}

    inventory = f"{host},"
    cmd = [
        "ansible-playbook", str(playbook),
        "-i", inventory,
        "-u", ssh_user,
        "--extra-vars", f"ansible_password={ssh_password} "
                        f"ansible_ssh_common_args='-o StrictHostKeyChecking=no'",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return {"ok": False, "message": f"Déploiement de '{service}' : délai dépassé (600s)."}
    except OSError as exc:
        return {"ok": False, "message": f"Échec du lancement d'Ansible : {exc}"}

    tail = (proc.stdout or "")[-1500:]
    if proc.returncode == 0:
        return {"ok": True, "message": f"Service '{service}' déployé sur {host}.",
                "output": tail}
    return {"ok": False,
            "message": f"Échec du déploiement de '{service}' (code {proc.returncode}).",
            "output": tail + "\n" + (proc.stderr or "")[-800:]}

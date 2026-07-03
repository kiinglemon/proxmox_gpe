"""Configuration centralisée d'InfraOne.

Toutes les valeurs sont surchargeables par variables d'environnement
(voir config/infraone.env.example). Les valeurs par défaut sont calibrées
pour un petit hôte Proxmox (10 Go RAM / 4 vCPU).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Racine du dépôt : .../backend/app/config.py -> remonte de 3 niveaux
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "backend" / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False, extra="ignore")

    # --- Application ---
    app_name: str = "InfraOne"
    infraone_host: str = "0.0.0.0"
    infraone_port: int = 8000

    # --- Sécurité / JWT (US-001, US-002) ---
    infraone_secret_key: str = "change-me-in-production"
    infraone_token_ttl_minutes: int = 720  # 12 h
    infraone_admin_user: str = "admin"
    infraone_admin_password: str = "infraone"  # remplacé au bootstrap

    # --- Connexion Proxmox (US-003..US-007) ---
    proxmox_host: str = "127.0.0.1:8006"
    proxmox_node: str = "pve"
    proxmox_token_id: str = ""      # ex: infraone@pve!automation
    proxmox_token_secret: str = ""
    proxmox_verify_ssl: bool = False

    # --- Mode mock : démontrer l'app sans infra réelle ---
    infraone_mock_proxmox: bool = False

    # --- Valeurs par défaut de provisioning (petit hôte) ---
    infraone_template_id: int = 9000        # template cloud-init créé par setup/30
    infraone_storage: str = "local-lvm"
    infraone_bridge: str = "vmbr0"
    infraone_vmid_min: int = 100
    infraone_vmid_max: int = 199
    default_vm_cores: int = 1
    default_vm_memory: int = 1024           # Mo
    default_vm_disk_gb: int = 8
    # Garde-fous adaptés à 10 Go RAM / 4 vCPU
    max_vm_cores: int = 4
    max_vm_memory: int = 4096               # Mo
    max_vm_disk_gb: int = 40

    # --- Cloud-init / SSH (US-005) ---
    default_ci_user: str = "infra"
    default_ci_password: str = "infraone"
    ssh_public_key_path: str = ""           # facultatif

    # --- Ansible (US-007) ---
    ansible_playbook_dir: str = str(REPO_ROOT / "ansible" / "playbooks")

    @property
    def token_user(self) -> str:
        """Partie 'user@realm' du token id (ex: infraone@pve)."""
        return self.proxmox_token_id.split("!", 1)[0] if self.proxmox_token_id else ""

    @property
    def token_name(self) -> str:
        """Partie 'nom-du-token' du token id (ex: automation)."""
        return self.proxmox_token_id.split("!", 1)[1] if "!" in self.proxmox_token_id else ""


@lru_cache
def get_settings() -> Settings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()

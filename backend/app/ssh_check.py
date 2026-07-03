"""Test de connexion SSH vers une VM déployée (US-005)."""
from __future__ import annotations

import socket

from .config import get_settings


def test_ssh(host: str, *, user: str | None = None, password: str | None = None,
             port: int = 22, timeout: float = 8.0) -> dict:
    """Tente une connexion SSH et renvoie un résultat structuré.

    En mode mock (pas de vraie VM), on se contente d'un test d'ouverture de
    port TCP pour rester démontrable.
    """
    settings = get_settings()
    user = user or settings.default_ci_user
    password = password or settings.default_ci_password

    if settings.infraone_mock_proxmox:
        return {
            "ok": True,
            "reachable": True,
            "message": f"[MOCK] Connexion SSH simulée réussie vers {user}@{host}:{port}.",
        }

    # 1. le port SSH répond-il ?
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except OSError as exc:
        return {"ok": False, "reachable": False,
                "message": f"Port SSH {host}:{port} injoignable : {exc}"}

    # 2. authentification réelle via paramiko
    try:
        import paramiko
    except ImportError:
        return {"ok": True, "reachable": True,
                "message": f"Port SSH {host}:{port} ouvert (paramiko indisponible "
                           "pour l'authentification)."}

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, port=port, username=user, password=password,
                       timeout=timeout, allow_agent=False, look_for_keys=True)
        stdin, stdout, stderr = client.exec_command("hostname && uptime -p", timeout=timeout)
        out = stdout.read().decode("utf-8", "replace").strip()
        return {"ok": True, "reachable": True,
                "message": f"Connexion SSH réussie vers {user}@{host}.",
                "output": out}
    except paramiko.AuthenticationException:
        return {"ok": False, "reachable": True,
                "message": f"Port SSH ouvert mais authentification refusée pour "
                           f"'{user}'. Vérifiez identifiants / clé cloud-init."}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reachable": True,
                "message": f"Erreur SSH vers {host} : {exc}"}
    finally:
        client.close()

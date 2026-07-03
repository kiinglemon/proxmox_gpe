"""Stockage simple des comptes administrateurs (US-001 / US-002).

MVP : persistance dans un fichier JSON (backend/data/users.json). Suffisant
pour la démonstration ; remplaçable par une vraie base plus tard.
"""
from __future__ import annotations

import json
import threading

from .config import DATA_DIR, get_settings
from .security import hash_password

_USERS_FILE = DATA_DIR / "users.json"
_lock = threading.Lock()


def _load() -> dict:
    if not _USERS_FILE.exists():
        return {}
    try:
        return json.loads(_USERS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _USERS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_admin() -> None:
    """Crée le compte admin de bootstrap s'il n'existe pas encore."""
    settings = get_settings()
    with _lock:
        data = _load()
        if settings.infraone_admin_user not in data:
            data[settings.infraone_admin_user] = {
                "username": settings.infraone_admin_user,
                "password_hash": hash_password(settings.infraone_admin_password),
                "reset_token": None,
            }
            _save(data)


def get_user(username: str) -> dict | None:
    with _lock:
        return _load().get(username)


def set_password(username: str, new_password: str) -> bool:
    with _lock:
        data = _load()
        if username not in data:
            return False
        data[username]["password_hash"] = hash_password(new_password)
        data[username]["reset_token"] = None
        _save(data)
        return True


def set_reset_token(username: str, token: str) -> bool:
    with _lock:
        data = _load()
        if username not in data:
            return False
        data[username]["reset_token"] = token
        _save(data)
        return True


def consume_reset_token(token: str) -> str | None:
    """Retourne le username associé au token puis l'invalide, ou None."""
    with _lock:
        data = _load()
        for username, rec in data.items():
            if rec.get("reset_token") and rec["reset_token"] == token:
                rec["reset_token"] = None
                _save(data)
                return username
        return None

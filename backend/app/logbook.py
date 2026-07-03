"""Journal d'évènements et d'erreurs formalisé par InfraOne (US-006).

Chaque entrée est écrite à la fois en mémoire (consultation rapide via l'API)
et dans un fichier JSON Lines persistant sous backend/data/infraone.log.jsonl.
"""
from __future__ import annotations

import json
import threading
from collections import deque
from typing import Literal

from .config import DATA_DIR

Level = Literal["INFO", "WARNING", "ERROR"]

_LOG_FILE = DATA_DIR / "infraone.log.jsonl"
_lock = threading.Lock()
_recent: deque[dict] = deque(maxlen=500)
_counter = {"n": 0}


def _timestamp() -> str:
    # import local pour éviter tout souci d'horloge figée à l'import
    import datetime as dt

    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def log_event(
    action: str,
    message: str,
    level: Level = "INFO",
    *,
    vmid: int | None = None,
    user: str | None = None,
    details: dict | None = None,
) -> dict:
    """Enregistre un évènement structuré et le renvoie."""
    with _lock:
        _counter["n"] += 1
        entry = {
            "id": _counter["n"],
            "ts": _timestamp(),
            "level": level,
            "action": action,
            "message": message,
            "vmid": vmid,
            "user": user,
            "details": details or {},
        }
        _recent.appendleft(entry)
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with _LOG_FILE.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            # Ne jamais faire échouer une opération métier à cause du journal.
            pass
    return entry


def recent(limit: int = 100, level: Level | None = None) -> list[dict]:
    with _lock:
        items = list(_recent)
    if level:
        items = [e for e in items if e["level"] == level]
    return items[:limit]

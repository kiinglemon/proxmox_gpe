"""Consultation du journal d'erreurs et d'évènements (US-006)."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends

from ..deps import current_user
from ..logbook import recent

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("")
def get_logs(limit: int = 100,
             level: Literal["INFO", "WARNING", "ERROR"] | None = None,
             user: str = Depends(current_user)) -> list[dict]:
    return recent(limit=min(limit, 500), level=level)

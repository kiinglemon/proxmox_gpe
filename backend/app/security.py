"""Sécurité : hachage de mot de passe (bcrypt) et jetons JWT.

On utilise bcrypt directement (et non passlib) pour éviter le problème de
compatibilité passlib/bcrypt rencontré au Sprint 1 (cf. rétrospective).
"""
from __future__ import annotations

import datetime as dt

import bcrypt
import jwt

from .config import get_settings

ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, extra: dict | None = None) -> str:
    settings = get_settings()
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + dt.timedelta(minutes=settings.infraone_token_ttl_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.infraone_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.infraone_secret_key, algorithms=[ALGORITHM])

"""Authentification : login (US-001) et mot de passe oublié (US-002)."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, status

from .. import store
from ..logbook import log_event
from ..schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    TokenResponse,
)
from ..security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = store.get_user(payload.username)
    if not user or not verify_password(payload.password, user["password_hash"]):
        log_event("auth.login", f"Échec de connexion pour '{payload.username}'",
                  level="WARNING", user=payload.username)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "Identifiant ou mot de passe incorrect.")
    token = create_access_token(payload.username)
    log_event("auth.login", f"Connexion réussie de '{payload.username}'",
              user=payload.username)
    return TokenResponse(access_token=token, username=payload.username)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest) -> MessageResponse:
    """Génère un jeton de réinitialisation.

    MVP : l'envoi d'email n'est pas branché (cf. rétrospective sprint 1). Le
    jeton est journalisé et renvoyé côté démo pour permettre le test de bout
    en bout. En production, il serait envoyé par email et NON retourné.
    """
    token = secrets.token_urlsafe(16)
    exists = store.set_reset_token(payload.username, token)
    # Réponse volontairement identique que le compte existe ou non (anti-énumération).
    log_event("auth.forgot_password",
              f"Demande de réinitialisation pour '{payload.username}' "
              f"(compte {'connu' if exists else 'inconnu'})",
              level="INFO", user=payload.username,
              details={"reset_token": token if exists else None})
    return MessageResponse(
        message="Si le compte existe, un lien de réinitialisation a été généré.",
        data={"reset_token": token} if exists else None,
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest) -> MessageResponse:
    username = store.consume_reset_token(payload.token)
    if not username:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Jeton de réinitialisation invalide ou déjà utilisé.")
    store.set_password(username, payload.new_password)
    log_event("auth.reset_password", f"Mot de passe réinitialisé pour '{username}'",
              user=username)
    return MessageResponse(message="Mot de passe réinitialisé. Vous pouvez vous connecter.")

"""Schémas Pydantic (validation des entrées/sorties de l'API)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class ForgotPasswordRequest(BaseModel):
    username: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=4)


class VMCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=40, pattern=r"^[a-zA-Z0-9-]+$")
    cores: int | None = Field(default=None, ge=1)
    memory: int | None = Field(default=None, ge=256)  # Mo
    disk_gb: int | None = Field(default=None, ge=4)
    ci_user: str | None = None
    ci_password: str | None = None
    start: bool = True


class VMUpdateRequest(BaseModel):
    """Modification de configuration d'une VM (US-004)."""
    cores: int | None = Field(default=None, ge=1)
    memory: int | None = Field(default=None, ge=256)
    disk_gb: int | None = Field(default=None, ge=4)  # augmentation uniquement


class DeployServiceRequest(BaseModel):
    service: str = Field(pattern=r"^(nginx|apache)$")
    host: str | None = None       # IP/hostname de la VM ; auto-détecté si absent
    ssh_user: str | None = None
    ssh_password: str | None = None


class MessageResponse(BaseModel):
    ok: bool = True
    message: str
    data: dict | None = None

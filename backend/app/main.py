"""Point d'entrée de l'application InfraOne (FastAPI).

Sert l'API REST (auth, VMs, services, logs) et l'interface web légère.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, store
from .config import get_settings
from .logbook import log_event
from .routers import auth, logs, services, vms

WEB_DIR = Path(__file__).resolve().parent / "web"

app = FastAPI(
    title="InfraOne API",
    version=__version__,
    description="Couche d'automatisation Proxmox — MVP TIC-GPE5 (Projet INFRA One)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(vms.router)
app.include_router(services.router)
app.include_router(logs.router)


@app.on_event("startup")
def _startup() -> None:
    store.ensure_admin()
    settings = get_settings()
    mode = "MOCK (démo, sans infra)" if settings.infraone_mock_proxmox else "Proxmox réel"
    log_event("app.startup", f"InfraOne démarré en mode {mode}")


@app.get("/api/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "version": __version__,
        "mock_proxmox": settings.infraone_mock_proxmox,
        "proxmox_host": settings.proxmox_host,
        "node": settings.proxmox_node,
    }


# --- Interface web légère servie par le backend --------------------------- #
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")
else:  # pragma: no cover
    @app.get("/", include_in_schema=False)
    def index() -> JSONResponse:
        return JSONResponse({"message": "InfraOne API. UI non trouvée.",
                             "docs": "/docs"})

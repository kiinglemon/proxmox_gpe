"""Déploiement de services de base sur une VM (US-007)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..ansible_runner import SUPPORTED, deploy_service
from ..deps import current_user
from ..logbook import log_event
from ..proxmox_client import ProxmoxError, get_proxmox
from ..schemas import DeployServiceRequest, MessageResponse

router = APIRouter(prefix="/api/vms", tags=["services"])


@router.get("/catalog/services")
def catalog(user: str = Depends(current_user)) -> dict:
    return {"services": sorted(SUPPORTED.keys())}


@router.post("/{vmid}/deploy-service", response_model=MessageResponse)
def deploy(vmid: int, payload: DeployServiceRequest,
           user: str = Depends(current_user)) -> MessageResponse:
    px = get_proxmox()
    host = payload.host
    if not host:
        try:
            host = px.get_vm_ip(vmid)
        except ProxmoxError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if not host:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"IP de la VM {vmid} inconnue. Fournissez 'host'.")

    log_event("service.deploy",
              f"Déploiement de '{payload.service}' sur VM {vmid} ({host}) demandé",
              vmid=vmid, user=user)
    result = deploy_service(payload.service, host,
                            ssh_user=payload.ssh_user, ssh_password=payload.ssh_password)
    log_event("service.deploy", result["message"],
              level="INFO" if result["ok"] else "ERROR", vmid=vmid, user=user)
    if not result["ok"]:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, result["message"])
    return MessageResponse(ok=True, message=result["message"], data=result)

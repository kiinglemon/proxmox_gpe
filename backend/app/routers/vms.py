"""Gestion des VMs : création, modification, SSH (US-003, US-004, US-005)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..config import get_settings
from ..deps import current_user
from ..logbook import log_event
from ..proxmox_client import ProxmoxError, get_proxmox
from ..schemas import MessageResponse, VMCreateRequest, VMUpdateRequest
from ..ssh_check import test_ssh

router = APIRouter(prefix="/api/vms", tags=["vms"])


def _handle(exc: ProxmoxError, action: str, vmid: int | None, user: str) -> None:
    log_event(action, str(exc), level="ERROR", vmid=vmid, user=user)
    raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))


@router.get("")
def list_vms(user: str = Depends(current_user)) -> list[dict]:
    try:
        return get_proxmox().list_vms()
    except ProxmoxError as exc:
        _handle(exc, "vm.list", None, user)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_vm(payload: VMCreateRequest, user: str = Depends(current_user)) -> dict:
    s = get_settings()
    cores = payload.cores or s.default_vm_cores
    memory = payload.memory or s.default_vm_memory
    disk_gb = payload.disk_gb or s.default_vm_disk_gb

    # Garde-fous adaptés à un petit hôte (10 Go RAM / 4 vCPU).
    if cores > s.max_vm_cores:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"Trop de vCPU demandés (max {s.max_vm_cores} sur cet hôte).")
    if memory > s.max_vm_memory:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"Trop de RAM demandée (max {s.max_vm_memory} Mo sur cet hôte).")
    if disk_gb > s.max_vm_disk_gb:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"Disque trop grand (max {s.max_vm_disk_gb} Go sur cet hôte).")

    try:
        vm = get_proxmox().create_vm(
            name=payload.name, cores=cores, memory=memory, disk_gb=disk_gb,
            ci_user=payload.ci_user or s.default_ci_user,
            ci_password=payload.ci_password or s.default_ci_password,
            start=payload.start,
        )
    except ProxmoxError as exc:
        _handle(exc, "vm.create", None, user)
    log_event("vm.create", f"VM '{vm['name']}' créée (id {vm['vmid']}, "
              f"{cores} vCPU / {memory} Mo / {disk_gb} Go)", vmid=vm["vmid"], user=user)
    return vm


@router.get("/{vmid}")
def get_vm(vmid: int, user: str = Depends(current_user)) -> dict:
    try:
        return get_proxmox().get_vm(vmid)
    except ProxmoxError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.put("/{vmid}")
def update_vm(vmid: int, payload: VMUpdateRequest, user: str = Depends(current_user)) -> dict:
    s = get_settings()
    if payload.cores and payload.cores > s.max_vm_cores:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"Trop de vCPU (max {s.max_vm_cores}).")
    if payload.memory and payload.memory > s.max_vm_memory:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"Trop de RAM (max {s.max_vm_memory} Mo).")
    if payload.disk_gb and payload.disk_gb > s.max_vm_disk_gb:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"Disque trop grand (max {s.max_vm_disk_gb} Go).")
    try:
        vm = get_proxmox().update_vm(vmid, cores=payload.cores,
                                     memory=payload.memory, disk_gb=payload.disk_gb)
    except ProxmoxError as exc:
        _handle(exc, "vm.update", vmid, user)
    log_event("vm.update", f"VM {vmid} reconfigurée "
              f"(cores={payload.cores}, memory={payload.memory}, disk={payload.disk_gb})",
              vmid=vmid, user=user)
    return vm


@router.post("/{vmid}/start", response_model=MessageResponse)
def start_vm(vmid: int, user: str = Depends(current_user)) -> MessageResponse:
    try:
        get_proxmox().start_vm(vmid)
    except ProxmoxError as exc:
        _handle(exc, "vm.start", vmid, user)
    log_event("vm.start", f"VM {vmid} démarrée", vmid=vmid, user=user)
    return MessageResponse(message=f"VM {vmid} démarrée.")


@router.post("/{vmid}/stop", response_model=MessageResponse)
def stop_vm(vmid: int, user: str = Depends(current_user)) -> MessageResponse:
    try:
        get_proxmox().stop_vm(vmid)
    except ProxmoxError as exc:
        _handle(exc, "vm.stop", vmid, user)
    log_event("vm.stop", f"VM {vmid} arrêtée", vmid=vmid, user=user)
    return MessageResponse(message=f"VM {vmid} arrêtée.")


@router.delete("/{vmid}", response_model=MessageResponse)
def delete_vm(vmid: int, user: str = Depends(current_user)) -> MessageResponse:
    try:
        get_proxmox().delete_vm(vmid)
    except ProxmoxError as exc:
        _handle(exc, "vm.delete", vmid, user)
    log_event("vm.delete", f"VM {vmid} supprimée", level="WARNING", vmid=vmid, user=user)
    return MessageResponse(message=f"VM {vmid} supprimée.")


@router.post("/{vmid}/ssh-test", response_model=MessageResponse)
def ssh_test(vmid: int, host: str | None = None,
             user: str = Depends(current_user)) -> MessageResponse:
    """Teste la connexion SSH à la VM (US-005)."""
    px = get_proxmox()
    target = host or px.get_vm_ip(vmid)
    if not target:
        msg = (f"IP de la VM {vmid} inconnue (agent QEMU absent ?). "
               "Fournissez 'host' explicitement.")
        log_event("vm.ssh_test", msg, level="WARNING", vmid=vmid, user=user)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, msg)
    result = test_ssh(target)
    log_event("vm.ssh_test", result["message"],
              level="INFO" if result["ok"] else "ERROR", vmid=vmid, user=user)
    return MessageResponse(ok=result["ok"], message=result["message"], data=result)

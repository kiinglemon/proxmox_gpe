"""Couche d'abstraction Proxmox (US-003, US-004, US-005).

Deux implémentations partageant la même interface :
  * ProxmoxClient      -> pilote un vrai hôte Proxmox via l'API REST (proxmoxer)
  * MockProxmoxClient  -> simule les VMs (mode démo, sans infra réelle)

La factory get_proxmox() choisit l'implémentation selon INFRAONE_MOCK_PROXMOX.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any

from .config import DATA_DIR, get_settings
from .logbook import log_event


class ProxmoxError(RuntimeError):
    """Erreur métier remontée à l'API (mappée en HTTP 502/400)."""


# --------------------------------------------------------------------------- #
#  Implémentation réelle
# --------------------------------------------------------------------------- #
class ProxmoxClient:
    def __init__(self) -> None:
        self.s = get_settings()
        if not self.s.proxmox_token_id or not self.s.proxmox_token_secret:
            raise ProxmoxError(
                "Token Proxmox manquant. Renseignez PROXMOX_TOKEN_ID / "
                "PROXMOX_TOKEN_SECRET (voir setup/20-proxmox-apiuser.sh) "
                "ou activez INFRAONE_MOCK_PROXMOX=1."
            )
        try:
            from proxmoxer import ProxmoxAPI
        except ImportError as exc:  # pragma: no cover
            raise ProxmoxError("Le paquet 'proxmoxer' n'est pas installé.") from exc

        host, _, port = self.s.proxmox_host.partition(":")
        self._api = ProxmoxAPI(
            host,
            port=int(port) if port else 8006,
            user=self.s.token_user,
            token_name=self.s.token_name,
            token_value=self.s.proxmox_token_secret,
            verify_ssl=self.s.proxmox_verify_ssl,
        )
        self._node = self._api.nodes(self.s.proxmox_node)

    # -- lecture ---------------------------------------------------------- #
    def list_vms(self) -> list[dict]:
        try:
            vms = self._node.qemu.get()
        except Exception as exc:  # noqa: BLE001
            raise ProxmoxError(f"Impossible de lister les VMs : {exc}") from exc
        return [self._normalize(v) for v in vms]

    def get_vm(self, vmid: int) -> dict:
        try:
            current = self._node.qemu(vmid).status.current.get()
            config = self._node.qemu(vmid).config.get()
        except Exception as exc:  # noqa: BLE001
            raise ProxmoxError(f"VM {vmid} introuvable : {exc}") from exc
        merged = {**current, **{f"cfg_{k}": v for k, v in config.items()}}
        merged["vmid"] = vmid
        out = self._normalize(merged)
        out["config"] = {
            "cores": config.get("cores"),
            "memory": config.get("memory"),
            "name": config.get("name"),
        }
        out["ip"] = self._guess_ip(vmid)
        return out

    # -- écriture --------------------------------------------------------- #
    def create_vm(self, *, name: str, cores: int, memory: int, disk_gb: int,
                  ci_user: str, ci_password: str, start: bool) -> dict:
        vmid = self._next_vmid()
        s = self.s
        try:
            # 1. clone du template cloud-init
            self._node.qemu(s.infraone_template_id).clone.post(
                newid=vmid, name=name, full=1)
            self._wait_unlock(vmid)
            # 2. configuration ressources + cloud-init
            cfg: dict[str, Any] = {
                "cores": cores,
                "memory": memory,
                "ciuser": ci_user,
                "cipassword": ci_password,
                "ipconfig0": "ip=dhcp",
                "net0": f"virtio,bridge={s.infraone_bridge}",
            }
            if s.ssh_public_key_path:
                try:
                    from pathlib import Path

                    key = Path(s.ssh_public_key_path).read_text(encoding="utf-8").strip()
                    if key:
                        cfg["sshkeys"] = key
                except OSError:
                    pass
            self._node.qemu(vmid).config.put(**cfg)
            # 3. redimensionnement disque si demandé
            if disk_gb and disk_gb > 0:
                try:
                    self._node.qemu(vmid).resize.put(disk="scsi0", size=f"{disk_gb}G")
                except Exception:  # noqa: BLE001
                    # le template peut déjà être plus grand : non bloquant
                    pass
            if start:
                self._node.qemu(vmid).status.start.post()
        except ProxmoxError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ProxmoxError(f"Échec de création de la VM '{name}' : {exc}") from exc
        return self.get_vm(vmid)

    def update_vm(self, vmid: int, *, cores: int | None, memory: int | None,
                  disk_gb: int | None) -> dict:
        cfg: dict[str, Any] = {}
        if cores is not None:
            cfg["cores"] = cores
        if memory is not None:
            cfg["memory"] = memory
        try:
            if cfg:
                self._node.qemu(vmid).config.put(**cfg)
            if disk_gb is not None:
                # Proxmox n'autorise que l'agrandissement à chaud.
                self._node.qemu(vmid).resize.put(disk="scsi0", size=f"{disk_gb}G")
        except Exception as exc:  # noqa: BLE001
            raise ProxmoxError(f"Échec de mise à jour de la VM {vmid} : {exc}") from exc
        return self.get_vm(vmid)

    def start_vm(self, vmid: int) -> None:
        self._power(vmid, "start")

    def stop_vm(self, vmid: int) -> None:
        self._power(vmid, "stop")

    def delete_vm(self, vmid: int) -> None:
        try:
            try:
                self._node.qemu(vmid).status.stop.post()
            except Exception:  # noqa: BLE001
                pass
            self._wait_unlock(vmid)
            self._node.qemu(vmid).delete()
        except Exception as exc:  # noqa: BLE001
            raise ProxmoxError(f"Échec de suppression de la VM {vmid} : {exc}") from exc

    def get_vm_ip(self, vmid: int) -> str | None:
        return self._guess_ip(vmid)

    # -- utilitaires internes -------------------------------------------- #
    def _power(self, vmid: int, action: str) -> None:
        try:
            getattr(self._node.qemu(vmid).status, action).post()
        except Exception as exc:  # noqa: BLE001
            raise ProxmoxError(f"Action '{action}' impossible sur VM {vmid} : {exc}") from exc

    def _next_vmid(self) -> int:
        used = {int(v["vmid"]) for v in self.list_vms()}
        for candidate in range(self.s.infraone_vmid_min, self.s.infraone_vmid_max + 1):
            if candidate not in used:
                return candidate
        raise ProxmoxError("Plus aucun VMID disponible dans la plage configurée.")

    def _wait_unlock(self, vmid: int, timeout: float = 60.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                cfg = self._node.qemu(vmid).config.get()
            except Exception:  # noqa: BLE001
                return
            if "lock" not in cfg:
                return
            time.sleep(1.5)

    def _guess_ip(self, vmid: int) -> str | None:
        """Récupère l'IP via l'agent QEMU (si installé dans la VM)."""
        try:
            res = self._node.qemu(vmid).agent("network-get-interfaces").get()
        except Exception:  # noqa: BLE001
            return None
        for iface in res.get("result", []):
            if iface.get("name") in ("lo", "lo0"):
                continue
            for addr in iface.get("ip-addresses", []):
                ip = addr.get("ip-address", "")
                if addr.get("ip-address-type") == "ipv4" and not ip.startswith("127."):
                    return ip
        return None

    @staticmethod
    def _normalize(v: dict) -> dict:
        return {
            "vmid": int(v.get("vmid")),
            "name": v.get("name") or v.get("cfg_name") or f"vm-{v.get('vmid')}",
            "status": v.get("status", "unknown"),
            "cores": v.get("cpus") or v.get("cfg_cores"),
            "memory": (v.get("maxmem", 0) // (1024 * 1024)) or v.get("cfg_memory"),
            "uptime": v.get("uptime", 0),
        }


# --------------------------------------------------------------------------- #
#  Implémentation simulée (mode démo)
# --------------------------------------------------------------------------- #
class MockProxmoxClient:
    """Simule Proxmox : utile pour démontrer l'app sans infra (cf. sprints 1-2)."""

    _STATE = DATA_DIR / "mock_vms.json"
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.s = get_settings()

    def _read(self) -> dict:
        if not self._STATE.exists():
            return {}
        try:
            return json.loads(self._STATE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _write(self, data: dict) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._STATE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def list_vms(self) -> list[dict]:
        return [self._public(v) for v in self._read().values()]

    def get_vm(self, vmid: int) -> dict:
        vm = self._read().get(str(vmid))
        if not vm:
            raise ProxmoxError(f"VM {vmid} introuvable (mock).")
        out = self._public(vm)
        out["config"] = {"cores": vm["cores"], "memory": vm["memory"], "name": vm["name"]}
        out["ip"] = vm.get("ip")
        return out

    def create_vm(self, *, name, cores, memory, disk_gb, ci_user, ci_password, start) -> dict:
        with self._lock:
            data = self._read()
            used = {int(k) for k in data}
            vmid = next(
                (c for c in range(self.s.infraone_vmid_min, self.s.infraone_vmid_max + 1)
                 if c not in used),
                None,
            )
            if vmid is None:
                raise ProxmoxError("Plus aucun VMID disponible (mock).")
            octet = 100 + (vmid % 150)
            data[str(vmid)] = {
                "vmid": vmid, "name": name, "cores": cores, "memory": memory,
                "disk_gb": disk_gb, "status": "running" if start else "stopped",
                "ci_user": ci_user, "ip": f"192.168.56.{octet}",
            }
            self._write(data)
            return self.get_vm(vmid)

    def update_vm(self, vmid, *, cores, memory, disk_gb) -> dict:
        with self._lock:
            data = self._read()
            vm = data.get(str(vmid))
            if not vm:
                raise ProxmoxError(f"VM {vmid} introuvable (mock).")
            if cores is not None:
                vm["cores"] = cores
            if memory is not None:
                vm["memory"] = memory
            if disk_gb is not None:
                vm["disk_gb"] = max(vm.get("disk_gb", 0), disk_gb)
            self._write(data)
            return self.get_vm(vmid)

    def start_vm(self, vmid) -> None:
        self._set_status(vmid, "running")

    def stop_vm(self, vmid) -> None:
        self._set_status(vmid, "stopped")

    def delete_vm(self, vmid) -> None:
        with self._lock:
            data = self._read()
            if str(vmid) in data:
                del data[str(vmid)]
                self._write(data)

    def get_vm_ip(self, vmid) -> str | None:
        vm = self._read().get(str(vmid))
        return vm.get("ip") if vm else None

    def _set_status(self, vmid, status) -> None:
        with self._lock:
            data = self._read()
            if str(vmid) not in data:
                raise ProxmoxError(f"VM {vmid} introuvable (mock).")
            data[str(vmid)]["status"] = status
            self._write(data)

    @staticmethod
    def _public(vm: dict) -> dict:
        return {
            "vmid": vm["vmid"], "name": vm["name"], "status": vm["status"],
            "cores": vm["cores"], "memory": vm["memory"], "uptime": 0,
        }


# --------------------------------------------------------------------------- #
def get_proxmox() -> ProxmoxClient | MockProxmoxClient:
    settings = get_settings()
    if settings.infraone_mock_proxmox:
        return MockProxmoxClient()
    return ProxmoxClient()

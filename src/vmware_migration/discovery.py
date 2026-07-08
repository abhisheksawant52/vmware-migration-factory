"""vSphere discovery client.

Wraps :mod:`pyVmomi` to enumerate virtual machines from a vCenter server into
:class:`~vmware_migration.models.VirtualMachine` instances. The connection layer
and the parsing/mapping layer are deliberately separated so the mapping logic can
be unit-tested offline against raw dictionaries (or mocked pyVmomi objects)
without a live vCenter.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .config import Settings
from .logging_config import get_logger
from .models import PowerState, VirtualMachine

logger = get_logger(__name__)


def vm_from_raw(raw: dict[str, Any]) -> VirtualMachine:
    """Map a raw property dictionary into a :class:`VirtualMachine`.

    The dictionary keys mirror the vSphere ``config``/``summary`` properties an
    integration would collect from a ``PropertyCollector``. This function is pure
    and therefore fully testable offline.

    Args:
        raw: Dictionary of collected VM properties.

    Returns:
        A validated :class:`VirtualMachine`.
    """
    power = raw.get("power_state", PowerState.POWERED_ON.value)
    if isinstance(power, PowerState):
        power = power.value
    return VirtualMachine(
        name=raw["name"],
        vcpu=int(raw["vcpu"]),
        memory_mb=int(raw["memory_mb"]),
        provisioned_disk_gb=float(raw.get("provisioned_disk_gb", 0.0)),
        guest_os=raw.get("guest_os", "otherGuest"),
        power_state=PowerState(power),
        cluster=raw.get("cluster"),
        datastore=raw.get("datastore"),
    )


def _summarize_vim_vm(managed_vm: Any) -> dict[str, Any]:
    """Extract the properties of interest from a pyVmomi ``vim.VirtualMachine``.

    Args:
        managed_vm: A ``pyVmomi`` managed object representing a VM.

    Returns:
        A raw property dictionary suitable for :func:`vm_from_raw`.
    """
    summary = managed_vm.summary
    config = summary.config
    runtime = summary.runtime
    disk_bytes = sum(
        device.capacityInBytes
        for device in getattr(managed_vm.config.hardware, "device", [])
        if hasattr(device, "capacityInBytes")
    )
    return {
        "name": config.name,
        "vcpu": config.numCpu,
        "memory_mb": config.memorySizeMB,
        "provisioned_disk_gb": round(disk_bytes / (1024**3), 2),
        "guest_os": config.guestFullName,
        "power_state": str(runtime.powerState),
    }


class VSphereDiscovery:
    """Client that connects to vCenter and enumerates virtual machines."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the discovery client.

        Args:
            settings: Resolved application settings holding vCenter credentials.
        """
        self._settings = settings
        self._service_instance: Any | None = None

    def connect(self) -> None:
        """Establish a session with vCenter using ``SmartConnect``.

        The import is performed lazily so that the parsing logic remains usable in
        environments where ``pyVmomi`` is not installed.
        """
        import ssl

        from pyVim.connect import SmartConnect  # type: ignore[import-untyped]

        context: ssl.SSLContext | None = None
        if self._settings.vcenter_insecure:
            context = ssl._create_unverified_context()

        logger.info("Connecting to vCenter %s", self._settings.vcenter_host)
        self._service_instance = SmartConnect(
            host=self._settings.vcenter_host,
            user=self._settings.vcenter_user,
            pwd=self._settings.vcenter_password,
            port=self._settings.vcenter_port,
            sslContext=context,
        )

    def disconnect(self) -> None:
        """Tear down the active vCenter session, if any."""
        if self._service_instance is None:
            return
        from pyVim.connect import Disconnect  # type: ignore[import-untyped]

        Disconnect(self._service_instance)
        self._service_instance = None

    def _iter_managed_vms(self) -> Iterable[Any]:
        """Yield ``vim.VirtualMachine`` managed objects from the inventory."""
        from pyVmomi import vim  # type: ignore[import-untyped]

        if self._service_instance is None:
            raise RuntimeError("Not connected: call connect() first.")

        content = self._service_instance.RetrieveContent()
        view = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.VirtualMachine], True
        )
        try:
            yield from view.view
        finally:
            view.Destroy()

    def discover(self) -> list[VirtualMachine]:
        """Enumerate all virtual machines from the connected vCenter.

        Returns:
            A list of :class:`VirtualMachine` models.
        """
        vms = [vm_from_raw(_summarize_vim_vm(mo)) for mo in self._iter_managed_vms()]
        logger.info("Discovered %d virtual machines", len(vms))
        return vms

    @staticmethod
    def from_records(records: Iterable[dict[str, Any]]) -> list[VirtualMachine]:
        """Build VMs from raw dictionaries, bypassing any vCenter connection.

        Useful for offline testing, fixtures, and importing inventory exports.

        Args:
            records: An iterable of raw VM property dictionaries.

        Returns:
            A list of :class:`VirtualMachine` models.
        """
        return [vm_from_raw(record) for record in records]

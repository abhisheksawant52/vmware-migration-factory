"""Right-sizing assessment and cost estimation.

The :class:`Assessor` maps a discovered :class:`VirtualMachine` to a target cloud
instance family, computes a simple on-demand monthly cost estimate, and assigns a
6 Rs disposition. Instance catalogs are intentionally small and static so that the
mapping logic is deterministic and unit-testable offline.
"""

from __future__ import annotations

from dataclasses import dataclass

from .logging_config import get_logger
from .models import (
    Disposition,
    PowerState,
    Recommendation,
    TargetCloud,
    VirtualMachine,
)

logger = get_logger(__name__)

HOURS_PER_MONTH = 730


@dataclass(frozen=True)
class InstanceType:
    """A candidate target cloud instance type."""

    name: str
    vcpu: int
    memory_gb: float
    hourly_usd: float


# Small, representative on-demand catalogs (Linux, us-east equivalents).
_CATALOGS: dict[TargetCloud, list[InstanceType]] = {
    TargetCloud.AWS: [
        InstanceType("t3.small", 2, 2.0, 0.0208),
        InstanceType("t3.medium", 2, 4.0, 0.0416),
        InstanceType("m5.large", 2, 8.0, 0.096),
        InstanceType("m5.xlarge", 4, 16.0, 0.192),
        InstanceType("m5.2xlarge", 8, 32.0, 0.384),
        InstanceType("m5.4xlarge", 16, 64.0, 0.768),
    ],
    TargetCloud.AZURE: [
        InstanceType("Standard_B2s", 2, 4.0, 0.0416),
        InstanceType("Standard_D2s_v5", 2, 8.0, 0.096),
        InstanceType("Standard_D4s_v5", 4, 16.0, 0.192),
        InstanceType("Standard_D8s_v5", 8, 32.0, 0.384),
        InstanceType("Standard_D16s_v5", 16, 64.0, 0.768),
    ],
    TargetCloud.GCP: [
        InstanceType("e2-small", 2, 2.0, 0.0168),
        InstanceType("e2-medium", 2, 4.0, 0.0335),
        InstanceType("n2-standard-2", 2, 8.0, 0.0971),
        InstanceType("n2-standard-4", 4, 16.0, 0.1942),
        InstanceType("n2-standard-8", 8, 32.0, 0.3885),
        InstanceType("n2-standard-16", 16, 64.0, 0.7770),
    ],
}

# Per-GB-month block storage price by cloud (approximate gp3 / managed / pd-balanced).
_STORAGE_USD_PER_GB_MONTH: dict[TargetCloud, float] = {
    TargetCloud.AWS: 0.08,
    TargetCloud.AZURE: 0.088,
    TargetCloud.GCP: 0.10,
}


class Assessor:
    """Right-sizes virtual machines onto a target cloud."""

    def __init__(
        self, target_cloud: TargetCloud = TargetCloud.AWS, headroom: float = 0.2
    ) -> None:
        """Initialize the assessor.

        Args:
            target_cloud: Cloud whose instance catalog to size against.
            headroom: Fractional capacity buffer applied to source specs
                (e.g. ``0.2`` sizes for 120% of the observed requirement).
        """
        if target_cloud not in _CATALOGS:
            raise ValueError(f"Unsupported target cloud: {target_cloud}")
        self.target_cloud = target_cloud
        self.headroom = headroom

    def _select_instance(self, vm: VirtualMachine) -> InstanceType:
        """Pick the cheapest instance type that satisfies the VM with headroom."""
        required_vcpu = vm.vcpu * (1 + self.headroom)
        required_mem = vm.memory_gb * (1 + self.headroom)
        catalog = sorted(_CATALOGS[self.target_cloud], key=lambda i: i.hourly_usd)
        for instance in catalog:
            if instance.vcpu >= required_vcpu and instance.memory_gb >= required_mem:
                return instance
        # Nothing fits within the catalog; fall back to the largest option.
        return max(catalog, key=lambda i: (i.vcpu, i.memory_gb))

    def _disposition(self, vm: VirtualMachine) -> Disposition:
        """Determine a 6 Rs disposition using simple heuristics."""
        if vm.power_state == PowerState.POWERED_OFF:
            return Disposition.RETIRE
        guest = vm.guest_os.lower()
        if "windows" in guest and ("2003" in guest or "2008" in guest):
            return Disposition.REPLATFORM
        return Disposition.REHOST

    def estimate_monthly_cost(self, instance: InstanceType, vm: VirtualMachine) -> float:
        """Estimate the monthly on-demand cost for compute plus storage.

        Args:
            instance: The selected target instance type.
            vm: The source virtual machine (for storage sizing).

        Returns:
            Estimated monthly cost in USD, rounded to cents.
        """
        compute = instance.hourly_usd * HOURS_PER_MONTH
        storage = vm.provisioned_disk_gb * _STORAGE_USD_PER_GB_MONTH[self.target_cloud]
        return round(compute + storage, 2)

    def assess(self, vm: VirtualMachine) -> Recommendation:
        """Produce a right-sizing recommendation for a single VM.

        Args:
            vm: The source virtual machine to assess.

        Returns:
            A :class:`Recommendation`.
        """
        instance = self._select_instance(vm)
        disposition = self._disposition(vm)
        cost = self.estimate_monthly_cost(instance, vm)
        notes = (
            f"Sized {vm.vcpu} vCPU / {vm.memory_gb} GB (+{int(self.headroom * 100)}% "
            f"headroom) onto {instance.name} ({instance.vcpu} vCPU / "
            f"{instance.memory_gb} GB)."
        )
        logger.debug("Assessed %s -> %s (%s)", vm.name, instance.name, disposition.value)
        return Recommendation(
            source_vm=vm.name,
            target_instance_type=instance.name,
            target_cloud=self.target_cloud,
            disposition=disposition,
            monthly_cost_estimate=cost,
            notes=notes,
        )

    def assess_many(self, vms: list[VirtualMachine]) -> list[Recommendation]:
        """Assess a batch of virtual machines.

        Args:
            vms: Source virtual machines.

        Returns:
            A list of recommendations in input order.
        """
        return [self.assess(vm) for vm in vms]

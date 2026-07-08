"""Domain models for the VMware Migration Factory.

The models are plain :mod:`pydantic` v2 models so they can be validated,
serialized to JSON for reporting, and constructed directly from raw dictionaries
during offline testing (without a live vCenter connection).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class PowerState(str, Enum):
    """Power state of a virtual machine as reported by vSphere."""

    POWERED_ON = "poweredOn"
    POWERED_OFF = "poweredOff"
    SUSPENDED = "suspended"


class TargetCloud(str, Enum):
    """Supported migration target clouds."""

    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class Disposition(str, Enum):
    """The 6 Rs migration disposition for a workload."""

    REHOST = "rehost"
    REPLATFORM = "replatform"
    REPURCHASE = "repurchase"
    REFACTOR = "refactor"
    RETAIN = "retain"
    RETIRE = "retire"


class MigrationStatus(str, Enum):
    """Lifecycle states a migration job moves through."""

    DISCOVERED = "discovered"
    ASSESSED = "assessed"
    REPLICATING = "replicating"
    CUTOVER = "cutover"
    VALIDATED = "validated"
    COMPLETE = "complete"
    FAILED = "failed"


class VirtualMachine(BaseModel):
    """A source virtual machine discovered from vSphere/vCenter."""

    name: str = Field(..., description="Inventory name of the virtual machine.")
    vcpu: int = Field(..., ge=1, description="Number of virtual CPUs.")
    memory_mb: int = Field(..., ge=1, description="Configured memory in megabytes.")
    provisioned_disk_gb: float = Field(
        ..., ge=0, description="Total provisioned disk capacity in gigabytes."
    )
    guest_os: str = Field(..., description="Guest operating system identifier.")
    power_state: PowerState = Field(
        default=PowerState.POWERED_ON, description="Current power state."
    )
    cluster: str | None = Field(default=None, description="Source vSphere cluster.")
    datastore: str | None = Field(default=None, description="Backing datastore name.")

    @property
    def memory_gb(self) -> float:
        """Return configured memory expressed in gigabytes."""
        return round(self.memory_mb / 1024, 2)


class Recommendation(BaseModel):
    """A right-sizing recommendation produced by the assessor."""

    source_vm: str = Field(..., description="Name of the source virtual machine.")
    target_instance_type: str = Field(..., description="Recommended cloud instance type.")
    target_cloud: TargetCloud = Field(..., description="Target cloud provider.")
    disposition: Disposition = Field(..., description="6 Rs migration disposition.")
    monthly_cost_estimate: float = Field(
        ..., ge=0, description="Estimated on-demand monthly cost in USD."
    )
    notes: str | None = Field(default=None, description="Human-readable rationale.")


class MigrationJob(BaseModel):
    """Tracks a single virtual machine through the migration lifecycle."""

    vm: VirtualMachine = Field(..., description="The virtual machine being migrated.")
    status: MigrationStatus = Field(
        default=MigrationStatus.DISCOVERED, description="Current lifecycle state."
    )
    recommendation: Recommendation | None = Field(
        default=None, description="Assessment result, once available."
    )
    history: list[MigrationStatus] = Field(
        default_factory=list, description="Ordered list of visited states."
    )

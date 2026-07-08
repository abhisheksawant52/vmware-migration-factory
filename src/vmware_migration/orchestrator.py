"""Migration job orchestration.

The :class:`MigrationOrchestrator` registers virtual machines as migration jobs
and advances them through a fixed lifecycle, enforcing that only valid state
transitions occur.
"""

from __future__ import annotations

from .logging_config import get_logger
from .models import (
    MigrationJob,
    MigrationStatus,
    Recommendation,
    VirtualMachine,
)

logger = get_logger(__name__)

# Allowed forward transitions in the migration lifecycle.
_TRANSITIONS: dict[MigrationStatus, set[MigrationStatus]] = {
    MigrationStatus.DISCOVERED: {MigrationStatus.ASSESSED, MigrationStatus.FAILED},
    MigrationStatus.ASSESSED: {MigrationStatus.REPLICATING, MigrationStatus.FAILED},
    MigrationStatus.REPLICATING: {MigrationStatus.CUTOVER, MigrationStatus.FAILED},
    MigrationStatus.CUTOVER: {MigrationStatus.VALIDATED, MigrationStatus.FAILED},
    MigrationStatus.VALIDATED: {MigrationStatus.COMPLETE, MigrationStatus.FAILED},
    MigrationStatus.COMPLETE: set(),
    MigrationStatus.FAILED: set(),
}


class TransitionError(RuntimeError):
    """Raised when an invalid lifecycle transition is attempted."""


class MigrationOrchestrator:
    """Tracks migration jobs and enforces valid state transitions."""

    def __init__(self) -> None:
        """Initialize an orchestrator with an empty job registry."""
        self._jobs: dict[str, MigrationJob] = {}

    @property
    def jobs(self) -> list[MigrationJob]:
        """Return all registered jobs."""
        return list(self._jobs.values())

    def register(self, vm: VirtualMachine) -> MigrationJob:
        """Register a VM as a new migration job in the ``discovered`` state.

        Args:
            vm: The virtual machine to track.

        Returns:
            The created :class:`MigrationJob`.

        Raises:
            ValueError: If a job for ``vm.name`` already exists.
        """
        if vm.name in self._jobs:
            raise ValueError(f"Job already registered for VM {vm.name!r}")
        job = MigrationJob(vm=vm, history=[MigrationStatus.DISCOVERED])
        self._jobs[vm.name] = job
        logger.info("Registered migration job for %s", vm.name)
        return job

    def get(self, vm_name: str) -> MigrationJob:
        """Return the job for ``vm_name``.

        Args:
            vm_name: Name of the virtual machine.

        Raises:
            KeyError: If no job exists for the name.
        """
        return self._jobs[vm_name]

    def attach_recommendation(
        self, vm_name: str, recommendation: Recommendation
    ) -> MigrationJob:
        """Attach an assessment result and advance the job to ``assessed``.

        Args:
            vm_name: Name of the virtual machine.
            recommendation: The assessment result to attach.

        Returns:
            The updated job.
        """
        job = self._jobs[vm_name]
        job.recommendation = recommendation
        return self.transition(vm_name, MigrationStatus.ASSESSED)

    def transition(self, vm_name: str, target: MigrationStatus) -> MigrationJob:
        """Move a job to ``target`` if the transition is permitted.

        Args:
            vm_name: Name of the virtual machine.
            target: Desired next status.

        Returns:
            The updated job.

        Raises:
            TransitionError: If the transition is not allowed.
        """
        job = self._jobs[vm_name]
        allowed = _TRANSITIONS[job.status]
        if target not in allowed:
            raise TransitionError(
                f"Cannot move {vm_name!r} from {job.status.value} to {target.value}"
            )
        logger.info("%s: %s -> %s", vm_name, job.status.value, target.value)
        job.status = target
        job.history.append(target)
        return job

    def summary(self) -> dict[str, int]:
        """Return a count of jobs grouped by status.

        Returns:
            A mapping of status value to the number of jobs in that state.
        """
        counts: dict[str, int] = {status.value: 0 for status in MigrationStatus}
        for job in self._jobs.values():
            counts[job.status.value] += 1
        return counts

"""Unit tests for migration job state transitions."""

from __future__ import annotations

import pytest

from vmware_migration.assessment import Assessor
from vmware_migration.discovery import vm_from_raw
from vmware_migration.models import MigrationStatus, TargetCloud
from vmware_migration.orchestrator import MigrationOrchestrator, TransitionError

SAMPLE_VM = {
    "name": "web-01",
    "vcpu": 2,
    "memory_mb": 4096,
    "provisioned_disk_gb": 50,
    "guest_os": "Ubuntu Linux (64-bit)",
}


def _register() -> tuple[MigrationOrchestrator, str]:
    orch = MigrationOrchestrator()
    vm = vm_from_raw(SAMPLE_VM)
    orch.register(vm)
    return orch, vm.name


def test_register_starts_in_discovered() -> None:
    orch, name = _register()
    job = orch.get(name)
    assert job.status == MigrationStatus.DISCOVERED
    assert job.history == [MigrationStatus.DISCOVERED]


def test_duplicate_registration_rejected() -> None:
    orch, name = _register()
    with pytest.raises(ValueError):
        orch.register(vm_from_raw(SAMPLE_VM))


def test_full_lifecycle_transitions() -> None:
    orch, name = _register()
    rec = Assessor(TargetCloud.AWS).assess(orch.get(name).vm)
    orch.attach_recommendation(name, rec)
    for state in (
        MigrationStatus.REPLICATING,
        MigrationStatus.CUTOVER,
        MigrationStatus.VALIDATED,
        MigrationStatus.COMPLETE,
    ):
        orch.transition(name, state)
    job = orch.get(name)
    assert job.status == MigrationStatus.COMPLETE
    assert job.recommendation is not None
    assert job.history[-1] == MigrationStatus.COMPLETE
    assert job.history[0] == MigrationStatus.DISCOVERED


def test_invalid_transition_raises() -> None:
    orch, name = _register()
    with pytest.raises(TransitionError):
        orch.transition(name, MigrationStatus.COMPLETE)


def test_summary_counts_states() -> None:
    orch, name = _register()
    summary = orch.summary()
    assert summary[MigrationStatus.DISCOVERED.value] == 1
    assert summary[MigrationStatus.COMPLETE.value] == 0

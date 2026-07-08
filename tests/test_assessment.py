"""Unit tests for the right-sizing assessor on sample VM dictionaries."""

from __future__ import annotations

import pytest

from vmware_migration.assessment import HOURS_PER_MONTH, Assessor
from vmware_migration.discovery import vm_from_raw
from vmware_migration.models import Disposition, TargetCloud

SMALL_VM = {
    "name": "web-01",
    "vcpu": 2,
    "memory_mb": 4096,
    "provisioned_disk_gb": 50,
    "guest_os": "Ubuntu Linux (64-bit)",
    "power_state": "poweredOn",
}

LARGE_VM = {
    "name": "db-01",
    "vcpu": 8,
    "memory_mb": 32768,
    "provisioned_disk_gb": 500,
    "guest_os": "Red Hat Enterprise Linux 9 (64-bit)",
    "power_state": "poweredOn",
}

LEGACY_VM = {
    "name": "app-legacy",
    "vcpu": 2,
    "memory_mb": 4096,
    "provisioned_disk_gb": 80,
    "guest_os": "Microsoft Windows Server 2008 R2 (64-bit)",
    "power_state": "poweredOn",
}

OFF_VM = {
    "name": "old-01",
    "vcpu": 1,
    "memory_mb": 2048,
    "provisioned_disk_gb": 20,
    "guest_os": "CentOS 6 (64-bit)",
    "power_state": "poweredOff",
}


def test_small_vm_maps_to_headroomed_instance() -> None:
    rec = Assessor(TargetCloud.AWS).assess(vm_from_raw(SMALL_VM))
    # 2 vCPU / 4 GB with 20% headroom needs >4 GB -> m5.large (2 vCPU / 8 GB).
    assert rec.target_instance_type == "m5.large"
    assert rec.disposition == Disposition.REHOST
    assert rec.target_cloud == TargetCloud.AWS


def test_large_vm_selects_larger_family() -> None:
    rec = Assessor(TargetCloud.AWS).assess(vm_from_raw(LARGE_VM))
    assert rec.target_instance_type == "m5.4xlarge"


def test_powered_off_vm_is_retired() -> None:
    rec = Assessor(TargetCloud.AWS).assess(vm_from_raw(OFF_VM))
    assert rec.disposition == Disposition.RETIRE


def test_legacy_windows_is_replatformed() -> None:
    rec = Assessor(TargetCloud.AZURE).assess(vm_from_raw(LEGACY_VM))
    assert rec.disposition == Disposition.REPLATFORM
    assert rec.target_instance_type.startswith("Standard_")


def test_cost_estimate_combines_compute_and_storage() -> None:
    assessor = Assessor(TargetCloud.AWS)
    vm = vm_from_raw(SMALL_VM)
    rec = assessor.assess(vm)
    # m5.large @ 0.096/hr compute + 50 GB * 0.08 storage.
    expected = round(0.096 * HOURS_PER_MONTH + 50 * 0.08, 2)
    assert rec.monthly_cost_estimate == expected


def test_unsupported_cloud_rejected() -> None:
    with pytest.raises(ValueError):
        Assessor(target_cloud="oracle")  # type: ignore[arg-type]


def test_assess_many_preserves_order() -> None:
    vms = [vm_from_raw(SMALL_VM), vm_from_raw(LARGE_VM)]
    recs = Assessor(TargetCloud.GCP).assess_many(vms)
    assert [r.source_vm for r in recs] == ["web-01", "db-01"]

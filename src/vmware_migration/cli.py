"""Command-line interface for the VMware Migration Factory.

Exposes the ``vmf`` entry point with subcommands to discover inventory, run
right-sizing assessments, drive migration jobs, and produce reports.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from . import __version__
from .assessment import Assessor
from .config import get_settings
from .discovery import VSphereDiscovery
from .logging_config import configure_logging
from .models import MigrationStatus, TargetCloud, VirtualMachine
from .orchestrator import MigrationOrchestrator


def _load_inventory(path: Path) -> list[VirtualMachine]:
    """Load virtual machines from a JSON inventory file.

    Args:
        path: Path to a JSON file containing a list of raw VM records.

    Returns:
        A list of :class:`VirtualMachine` models.
    """
    records: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    return VSphereDiscovery.from_records(records)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="vmf")
@click.option("--log-level", default=None, help="Override the configured log level.")
def main(log_level: str | None) -> None:
    """VMware Migration Factory command-line interface."""
    settings = get_settings()
    configure_logging(log_level or settings.log_level)


@main.command()
@click.option(
    "--inventory",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Read VMs from a JSON inventory file instead of connecting to vCenter.",
)
def discover(inventory: Path | None) -> None:
    """Discover virtual machines from vCenter (or a local inventory file)."""
    if inventory is not None:
        vms = _load_inventory(inventory)
    else:
        client = VSphereDiscovery(get_settings())
        client.connect()
        try:
            vms = client.discover()
        finally:
            client.disconnect()
    click.echo(f"Discovered {len(vms)} virtual machine(s):")
    for vm in vms:
        click.echo(f"  - {vm.name}: {vm.vcpu} vCPU / {vm.memory_gb} GB / {vm.guest_os}")


@main.command()
@click.option(
    "--inventory",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="JSON inventory file to assess.",
)
@click.option(
    "--target-cloud",
    type=click.Choice([c.value for c in TargetCloud]),
    default=None,
    help="Target cloud to size against (defaults to configured value).",
)
def assess(inventory: Path, target_cloud: str | None) -> None:
    """Right-size discovered VMs and estimate monthly cost."""
    settings = get_settings()
    cloud = TargetCloud(target_cloud) if target_cloud else settings.target_cloud
    assessor = Assessor(target_cloud=cloud)
    recommendations = assessor.assess_many(_load_inventory(inventory))
    total = 0.0
    for rec in recommendations:
        total += rec.monthly_cost_estimate
        click.echo(
            f"  {rec.source_vm}: {rec.target_instance_type} "
            f"[{rec.disposition.value}] ~${rec.monthly_cost_estimate}/mo"
        )
    click.echo(f"Estimated total: ~${round(total, 2)}/mo on {cloud.value}")


@main.command()
@click.option(
    "--inventory",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="JSON inventory file to migrate.",
)
def migrate(inventory: Path) -> None:
    """Register and advance migration jobs to completion."""
    settings = get_settings()
    assessor = Assessor(target_cloud=settings.target_cloud)
    orchestrator = MigrationOrchestrator()
    lifecycle = [
        MigrationStatus.REPLICATING,
        MigrationStatus.CUTOVER,
        MigrationStatus.VALIDATED,
        MigrationStatus.COMPLETE,
    ]
    for vm in _load_inventory(inventory):
        orchestrator.register(vm)
        orchestrator.attach_recommendation(vm.name, assessor.assess(vm))
        for state in lifecycle:
            orchestrator.transition(vm.name, state)
        click.echo(f"  {vm.name}: {orchestrator.get(vm.name).status.value}")
    click.echo("Migration run complete.")


@main.command()
@click.option(
    "--inventory",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="JSON inventory file to report on.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write the JSON report to this path instead of stdout.",
)
def report(inventory: Path, output: Path | None) -> None:
    """Produce a JSON assessment report for the inventory."""
    settings = get_settings()
    assessor = Assessor(target_cloud=settings.target_cloud)
    vms = _load_inventory(inventory)
    recommendations = assessor.assess_many(vms)
    payload = {
        "target_cloud": settings.target_cloud.value,
        "vm_count": len(vms),
        "monthly_cost_estimate": round(
            sum(r.monthly_cost_estimate for r in recommendations), 2
        ),
        "recommendations": [r.model_dump(mode="json") for r in recommendations],
    }
    text = json.dumps(payload, indent=2)
    if output is not None:
        output.write_text(text, encoding="utf-8")
        click.echo(f"Report written to {output}")
    else:
        click.echo(text)


if __name__ == "__main__":  # pragma: no cover
    main()

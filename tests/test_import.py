"""Smoke tests that the package imports and exposes its version."""

from __future__ import annotations

import vmware_migration


def test_version_exposed() -> None:
    assert vmware_migration.__version__ == "0.1.0"


def test_public_modules_import() -> None:
    from vmware_migration import (  # noqa: F401
        assessment,
        cli,
        config,
        discovery,
        models,
        orchestrator,
    )

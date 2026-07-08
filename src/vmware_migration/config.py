"""Runtime configuration loaded from the environment.

Settings are read from environment variables (optionally a local ``.env`` file)
using :mod:`pydantic-settings`. All variables are prefixed with ``VMF_``.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .models import TargetCloud


class Settings(BaseSettings):
    """Configuration for the migration factory."""

    model_config = SettingsConfigDict(
        env_prefix="VMF_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    vcenter_host: str = Field(
        default="vcenter.example.local", description="vCenter server hostname or IP."
    )
    vcenter_user: str = Field(
        default="administrator@vsphere.local", description="vCenter login user."
    )
    vcenter_password: str = Field(default="", description="vCenter login password.")
    vcenter_port: int = Field(default=443, ge=1, le=65535, description="vCenter API port.")
    vcenter_insecure: bool = Field(
        default=False, description="Skip TLS verification when connecting to vCenter."
    )

    datacenter: str = Field(default="Datacenter", description="Source datacenter name.")
    target_cloud: TargetCloud = Field(
        default=TargetCloud.AWS, description="Default target cloud for assessments."
    )

    log_level: str = Field(default="INFO", description="Root logging level.")


def get_settings() -> Settings:
    """Return a freshly loaded :class:`Settings` instance."""
    return Settings()

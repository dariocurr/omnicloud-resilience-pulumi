"""
Stack configuration loaded from pulumi.Config().

Provides a typed, immutable view of stack settings. All settings are read from
Pulumi config (e.g. Pulumi.<stack>.yaml or pulumi config set). Every key is
required. Used by __main__.main() to name resources, toggle Azure soft-delete,
AWS public access block, and pass TTLs/retention.
"""

from dataclasses import dataclass
from typing import Any, Callable

import pulumi


def _require_bool(config: pulumi.Config, key: str) -> bool:
    raw = config.require(key)
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ("1", "true", "yes")


def _require_int(config: pulumi.Config, key: str) -> int:
    return int(config.require(key))


def _require_str(config: pulumi.Config, key: str) -> str:
    return config.require(key)


# (key, parser); parser receives (config, key) and returns value.
_CONFIG_SPEC: list[tuple[str, Callable[[pulumi.Config, str], Any]]] = [
    ("domain_name", _require_str),
    ("environment", _require_str),
    ("aws_bucket_name", _require_str),
    ("enable_azure_backup", _require_bool),
    ("project_name", _require_str),
    ("enable_public_access_block", _require_bool),
    ("backup_retention_days", _require_int),
    ("gcp_primary_ttl", _require_int),
    ("gcp_backup_ttl", _require_int),
]


@dataclass(frozen=True)
class StackConfig:
    """
    Stack configuration from Pulumi config.

    Attributes:
        domain_name: Domain for GCP DNS managed zone and records (required).
        environment: Environment label used in resource naming (required).
        aws_bucket_name: AWS S3 bucket name (required; must be globally unique).
        enable_azure_backup: Whether to enable Azure blob/container soft-delete (required).
        project_name: Project name used in resource naming (required).
        enable_public_access_block: Whether to enable S3 Block Public Access (required).
        backup_retention_days: Azure blob/container soft-delete retention in days (required).
        gcp_primary_ttl: TTL in seconds for primary (www) CNAME record (required).
        gcp_backup_ttl: TTL in seconds for backup CNAME record (required).
    """

    domain_name: str
    environment: str
    aws_bucket_name: str
    enable_azure_backup: bool
    project_name: str
    enable_public_access_block: bool
    backup_retention_days: int
    gcp_primary_ttl: int
    gcp_backup_ttl: int

    @classmethod
    def from_pulumi_config(cls, config: pulumi.Config) -> "StackConfig":
        """
        Build StackConfig from pulumi.Config(). All keys in _CONFIG_SPEC are required.
        """
        kwargs = {key: parser(config, key) for key, parser in _CONFIG_SPEC}
        return cls(**kwargs)

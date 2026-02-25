"""
Stack configuration loaded from pulumi.Config().

Provides a typed, immutable view of stack settings. ``domain_name`` is required
(config.require); ``environment`` and ``enable_azure_backup`` default to
"dev" and False. Used by __main__.main() to name resources and toggle
Azure soft-delete and to pass the domain into GCP DNS.
"""

from dataclasses import dataclass

import pulumi


@dataclass(frozen=True)
class StackConfig:
    """
    Stack configuration from Pulumi config.

    Attributes:
        domain_name: Domain for GCP DNS managed zone and records (required).
        environment: Environment label used in resource naming (e.g. "dev").
        enable_azure_backup: Whether to enable Azure blob/container soft-delete.
    """

    domain_name: str
    environment: str
    enable_azure_backup: bool

    @classmethod
    def from_pulumi_config(
        cls,
        config: pulumi.Config,
    ) -> "StackConfig":
        """
        Build StackConfig from pulumi.Config().

        Args:
            config: Pulumi config for the current stack (e.g. pulumi.Config()).

        Config keys:
            domain_name (required): Used for GCP DNS zone and CNAME records.
            environment: Optional; defaults to "dev".
            enable_azure_backup: Optional bool; defaults to False.

        Returns:
            StackConfig: Frozen dataclass instance.
        """
        environment = config.get("environment") or "dev"
        enable_azure_backup = config.get_bool("enable_azure_backup") or False
        domain_name = config.require("domain_name")
        return cls(
            domain_name=domain_name,
            enable_azure_backup=enable_azure_backup,
            environment=environment,
        )

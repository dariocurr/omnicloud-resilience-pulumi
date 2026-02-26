"""
Azure static website: Storage Account + static website + optional soft-delete.

This component creates a resource group, a general-purpose v2 storage account
with static website hosting (index.html, 404.html), and optionally enables
blob and container soft-delete for a fixed retention period. The bucket is
not publicly exposed; access is via the primary endpoint URL. The
``primary_endpoint`` output is an ``Output[str]`` so other components (e.g.
GCP DNS) can use it as a CNAME target for backup/failover.

Storage account names are derived from ``name`` and sanitized to meet Azure
rules: alphanumeric only, 3-24 characters, globally unique.
"""

import pulumi
import pulumi_azure_native as azure_native

from components._helpers import sanitize_storage_account_name

ID: str = "omnicloud:azure:AzureInfra"


class AzureInfra(pulumi.ComponentResource):
    """
    Storage Account with static website hosting and optional soft-delete.

    Resources: ResourceGroup, StorageAccount, StorageAccountStaticWebsite,
    and optionally BlobServiceProperties (delete retention).
    """

    def __init__(
        self,
        name: str,
        enable_backup: bool = False,
        backup_retention_days: int = 30,
    ):
        """
        Create the resource group, storage account, and static website.

        Args:
            name: Pulumi resource name; used for resource group, account, and
                child resources. Storage account name is sanitized (alphanumeric,
                max 24 chars) via sanitize_storage_account_name.
            enable_backup: If True, enable blob and container soft-delete for
                backup_retention_days so deleted data can be recovered.
            backup_retention_days: Retention in days when enable_backup is True.

        Outputs (set on self, registered for the component):
            primary_endpoint: HTTPS URL base for the static website (e.g. for
                GCP backup CNAME or stack exports).
        """
        super().__init__(ID, name)

        # Child resources get parent=self so Pulumi builds a proper hierarchy:
        # lifecycle order (e.g. destroy StorageAccount before BlobServiceProperties)
        # and UI grouping.
        child_opts = pulumi.ResourceOptions(parent=self)

        # Create the resource group.
        # This is needed to group the resources together.
        rg = azure_native.resources.ResourceGroup(
            resource_name=f"{name}-rg",
            resource_group_name=f"{name}-rg",
            opts=child_opts,
        )

        # Storage account names must be globally unique, 3-24 chars, alphanumeric only.
        account_name = pulumi.Output.from_input(name).apply(
            sanitize_storage_account_name
        )
        # Create the storage account SKU.
        # This is needed to store the static website.
        sku = azure_native.storage.SkuArgs(
            name=azure_native.storage.SkuName.STANDARD_LRS
        )

        self.storage_account = azure_native.storage.StorageAccount(
            resource_name=f"{name}sa",
            resource_group_name=rg.name,
            account_name=account_name,
            sku=sku,
            kind=azure_native.storage.Kind.STORAGE_V2,
            enable_https_traffic_only=True,
            minimum_tls_version=azure_native.storage.MinimumTlsVersion.TLS1_2,
            allow_blob_public_access=False,
            opts=child_opts,
        )

        # Create the storage account static website.
        # This is needed to serve the static website from the storage account.
        azure_native.storage.StorageAccountStaticWebsite(
            resource_name=f"{name}-static",
            account_name=self.storage_account.name,
            resource_group_name=rg.name,
            index_document="index.html",
            error404_document="404.html",
            opts=child_opts,
        )

        # Soft-delete keeps blobs/containers recoverable for backup_retention_days.
        if enable_backup:
            retention = azure_native.storage.DeleteRetentionPolicyArgs(
                enabled=True,
                days=backup_retention_days,
            )
            azure_native.storage.BlobServiceProperties(
                resource_name=f"{name}-backup",
                resource_group_name=rg.name,
                account_name=self.storage_account.name,
                blob_services_name="default",
                delete_retention_policy=retention,
                container_delete_retention_policy=retention,
                opts=child_opts,
            )

        # Output so callers can chain (e.g. GCP backup CNAME points at this host).
        self.primary_endpoint: pulumi.Output[str] = pulumi.Output.concat(
            "https://",
            self.storage_account.name,
            ".blob.core.windows.net/",
        )
        self.register_outputs({"primary_endpoint": self.primary_endpoint})

"""
Omnicloud Resilience - multi-cloud IaC entrypoint.

Wires three ComponentResources using Pulumi config and output chaining:

- **AWS**: S3 + CloudFront as the primary origin. CloudFront domain is passed
  to GCP DNS as the primary CNAME target.
- **Azure**: Storage Account static website. Optional soft-delete from config.
  The static-website host is derived and passed to GCP DNS as the backup
  CNAME target (failover).
- **GCP**: Cloud DNS managed zone and www/backup CNAME records. Domain comes
  from config; caller must delegate the domain to the zone name servers.

Stack exports: aws_cloudfront_url, aws_cloudfront_domain, azure_primary_endpoint,
gcp_name_servers.
"""

import pulumi

from components import AwsInfra, AzureInfra, GcpInfra
from config import StackConfig


def _component_name(project_name: str, environment: str, prefix: str) -> str:
    return f"{prefix}-{project_name}-{environment}"


def main():
    """
    Build AWS, Azure, and GCP components and export stack outputs.

    Reads config (environment, domain_name, enable_azure_backup), instantiates
    each cloud component, chains AWS and Azure outputs into GCP as primary and
    backup CNAME targets, and exports the main URLs and GCP name servers.
    """
    config = StackConfig.from_pulumi_config(pulumi.Config())

    def name(prefix: str) -> str:
        return _component_name(config.project_name, config.environment, prefix)

    aws = AwsInfra(
        name=name("aws"),
        bucket_name=config.aws_bucket_name,
        enable_public_access_block=config.enable_public_access_block,
    )

    azure = AzureInfra(
        name=name("azure"),
        enable_backup=config.enable_azure_backup,
        backup_retention_days=config.backup_retention_days,
    )

    backup_host = azure.primary_endpoint.apply(
        lambda url: url.replace("https://", "").split("/")[0]
    )
    gcp = GcpInfra(
        name=name("gcp"),
        domain_name=config.domain_name,
        primary_target=aws.cloudfront_domain_name,
        backup_target=backup_host,
        primary_ttl=config.gcp_primary_ttl,
        backup_ttl=config.gcp_backup_ttl,
    )

    for output_name, value in [
        ("aws_cloudfront_url", aws.cloudfront_url),
        ("aws_cloudfront_domain", aws.cloudfront_domain_name),
        ("azure_primary_endpoint", azure.primary_endpoint),
        ("gcp_name_servers", gcp.name_servers),
    ]:
        pulumi.export(output_name, value)


if __name__ == "__main__":
    main()

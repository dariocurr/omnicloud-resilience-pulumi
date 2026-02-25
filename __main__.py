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


def main():
    """
    Build AWS, Azure, and GCP components and export stack outputs.

    Reads config (environment, domain_name, enable_azure_backup), instantiates
    each cloud component, chains AWS and Azure outputs into GCP as primary and
    backup CNAME targets, and exports the main URLs and GCP name servers.
    """
    project_name = "omnicloud-resilience"
    config = StackConfig.from_pulumi_config(pulumi.Config())

    # AWS is primary origin; CloudFront domain is used as GCP DNS CNAME target.
    aws_name = f"aws-{project_name}-{config.environment}"
    aws = AwsInfra(
        name=aws_name,
        enable_public_access_block=True,
    )

    azure_name = f"azure-{project_name}-{config.environment}"
    azure = AzureInfra(
        name=azure_name,
        enable_backup=config.enable_azure_backup,
    )

    # Extract host from Azure static-website URL for GCP backup CNAME (e.g. failover).
    backup_host = azure.primary_endpoint.apply(
        lambda url: url.replace("https://", "").split("/")[0]
    )
    gcp_name = f"gcp-{project_name}-{config.environment}"
    gcp = GcpInfra(
        name=gcp_name,
        domain_name=config.domain_name,
        primary_target=aws.cloudfront_domain_name,
        backup_target=backup_host,
    )

    pulumi.export(
        "aws_cloudfront_url",
        aws.cloudfront_url,
    )
    pulumi.export(
        "aws_cloudfront_domain",
        aws.cloudfront_domain_name,
    )
    pulumi.export(
        "azure_primary_endpoint",
        azure.primary_endpoint,
    )
    pulumi.export(
        "gcp_name_servers",
        gcp.name_servers,
    )


if __name__ == "__main__":
    main()

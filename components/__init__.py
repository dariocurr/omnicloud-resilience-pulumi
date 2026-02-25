"""
Multi-cloud infrastructure components.

Each cloud is encapsulated in its own ComponentResource for clear ownership,
testability, and reuse. Use from the Pulumi entrypoint (e.g. __main__.py) with
config and output chaining:

- **AwsInfra**: S3 + CloudFront; exposes cloudfront_domain_name for DNS.
- **AzureInfra**: Storage Account static website; exposes primary_endpoint for
  backup/failover DNS.
- **GcpInfra**: Cloud DNS zone + www/backup CNAMEs; accepts primary_target and
  backup_target (str or Output[str]) and exposes name_servers.
"""

from components.aws import AwsInfra
from components.azure import AzureInfra
from components.gcp import GcpInfra

__all__ = ["AwsInfra", "AzureInfra", "GcpInfra"]

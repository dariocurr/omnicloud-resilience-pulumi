"""
GCP Cloud DNS: managed zone and CNAME records for primary/backup failover.

This component creates a Cloud DNS managed zone for a given domain and two CNAME
records: one for the primary origin (e.g. AWS CloudFront) and an optional one
for a backup origin (e.g. Azure static website). It is designed to be wired
with outputs from other components: pass ``primary_target`` as an
``Output[str]`` (e.g. CloudFront domain name) and ``backup_target`` as another
(e.g. Azure blob host) so DNS can point to either without code changes.

After deployment, the domain must be delegated at the registrar to the zone's
name servers (exposed as ``name_servers``). Primary record uses TTL 300s;
backup uses 60s so failover propagates quickly when switching.
"""

import pulumi
import pulumi_gcp as gcp

from components._helpers import cname_rrdata, ensure_trailing_dot, fqdn

ID = "omnicloud:gcp:GcpInfra"

# CNAME target may be known now (str) or only after another resource is created
# (pulumi.Output[str]). Use a plain string for a fixed target (e.g. "lb.example.com");
# use an Output when wiring this component to another (e.g. pass an AWS ALB's
# dns_name so GCP DNS points at it). The code normalizes both with
# pulumi.Output.from_input() before building the record set.
DnsTarget = str | pulumi.Output[str]


class GcpInfra(pulumi.ComponentResource):
    """
    Cloud DNS managed zone with www (primary) and optional backup CNAME records.

    Primary record: ``www.<domain_name>`` → primary_target (TTL 300).
    Backup record (if given): ``backup.<domain_name>`` → backup_target (TTL 60).
    """

    def __init__(
        self,
        name: str,
        domain_name: str,
        primary_target: DnsTarget,
        backup_target: DnsTarget | None = None,
        primary_ttl: int = 300,
        backup_ttl: int = 60,
    ):
        """
        Create the managed zone and CNAME record set(s).

        Args:
            name: Pulumi resource name (used for zone and record naming).
            domain_name: Domain for the zone (e.g. "example.com"). Used as-is;
                trailing dot is added for the zone FQDN.
            primary_target: CNAME target for www.<domain_name>. A string or
                Output[str], e.g. from AWS CloudFront's domain_name.
            backup_target: Optional CNAME target for backup.<domain_name>, e.g.
                Azure static-website host for failover.
            primary_ttl: TTL in seconds for the primary (www) CNAME record.
            backup_ttl: TTL in seconds for the backup CNAME record.

        Outputs (set on self, registered for the component):
            name_servers: Zone name servers; delegate the domain to these at
                the registrar.
            primary_record: The primary CNAME RecordSetArgs (for reference).
        """
        super().__init__(ID, name)

        child_opts = pulumi.ResourceOptions(parent=self)

        # Trailing dot required by Cloud DNS for zone FQDN.
        zone_dns = ensure_trailing_dot(domain_name)
        zone = gcp.dns.ManagedZone(
            resource_name=f"{name}-zone",
            name=f"{name}-zone",
            dns_name=zone_dns,
            description=f"Managed zone for {name} (failover)",
            opts=child_opts,
        )

        # Primary CNAME record: www.<domain> → primary_target (e.g. CloudFront domain).
        primary_name = fqdn(domain_name, "www")
        rrdatas = pulumi.Output.from_input(primary_target).apply(cname_rrdata)
        self.primary_record = gcp.dns.RecordSetArgs(
            name=primary_name,
            managed_zone=zone.name,
            type="CNAME",
            ttl=primary_ttl,
            rrdatas=rrdatas,
        )

        # Shorter TTL on backup so failover propagation is faster when switching.
        if backup_target:
            rrdatas = pulumi.Output.from_input(backup_target).apply(cname_rrdata)
            backup_name = fqdn(domain_name, "backup")
            gcp.dns.RecordSet(
                resource_name=f"{name}-backup",
                name=backup_name,
                managed_zone=zone.name,
                type="CNAME",
                ttl=backup_ttl,
                rrdatas=rrdatas,
                opts=child_opts,
            )

        # Caller must delegate the domain at the registrar to these name servers.
        self.name_servers: pulumi.Output[list[str]] = zone.name_servers
        self.register_outputs({"name_servers": self.name_servers})

"""
AWS static hosting: S3 bucket + CloudFront distribution.

This component creates an S3 bucket as the origin for a CloudFront
distribution. The bucket is not publicly readable: Block Public Access can be
enabled (default), and CloudFront accesses S3 via Origin Access Control (OAC)
with signed requests. The distribution uses HTTPS redirect and the default
CloudFront certificate. Outputs (``cloudfront_domain_name``, ``cloudfront_url``,
``cloudfront_hosted_zone_id``) are ``Output[str]`` so other components (e.g.
GCP DNS) can use them as CNAME targets for the primary origin.
"""

import pulumi
import pulumi_aws as aws

ID: str = "omnicloud:aws:AwsInfra"

# Applied when enable_public_access_block is True. Used by tests and callers
# to assert on secure defaults.
S3_BLOCK_PUBLIC_ACCESS: dict[str, bool] = {
    "block_public_acls": True,
    "block_public_policy": True,
    "ignore_public_acls": True,
    "restrict_public_buckets": True,
}


class AwsInfra(pulumi.ComponentResource):
    """
    S3 bucket with optional Block Public Access + CloudFront (OAC, HTTPS).

    Resources: Bucket, optional BucketPublicAccessBlock, OriginAccessControl,
    Distribution. Content is served only via CloudFront.
    """

    def __init__(
        self,
        name: str,
        enable_public_access_block: bool = True,
    ):
        """
        Create the S3 bucket and CloudFront distribution.

        Args:
            name: Pulumi resource name for the bucket and related resources
                (e.g. bucket id, OAC, distribution).
            enable_public_access_block: If True (default), apply
                S3_BLOCK_PUBLIC_ACCESS so the bucket cannot be made public.

        Outputs (set on self, registered for the component):
            cloudfront_domain_name: Distribution FQDN (e.g. for GCP DNS
                primary CNAME).
            cloudfront_hosted_zone_id: Route53 hosted zone ID for the
                distribution (for alias records if needed).
            cloudfront_url: HTTPS URL of the distribution.
        """
        super().__init__(
            ID,
            name,
        )

        # Child resources get parent=self so Pulumi builds a proper hierarchy:
        # lifecycle order (e.g. destroy CloudFront before bucket) and UI grouping.
        child_opts = pulumi.ResourceOptions(parent=self)

        # Create the S3 bucket
        self.bucket = aws.s3.Bucket(
            resource_name=name,
            opts=child_opts,
        )

        # Create the S3 bucket public access block.
        # This is needed to ensure that the bucket is not publicly accessible.
        if enable_public_access_block:
            aws.s3.BucketPublicAccessBlock(
                resource_name=f"{name}-block-public",
                bucket=self.bucket.id,
                opts=child_opts,
                **S3_BLOCK_PUBLIC_ACCESS,
            )

        # OAC (recommended over legacy OAI): CloudFront signs requests; S3 allows only
        # that identity, so the bucket stays non-public.
        # retain_on_delete=True avoids AWS 409 OriginAccessControlInUse on destroy:
        # the distribution is deleted first (via depends_on), but AWS may still
        # reference the OAC briefly; retaining skips the delete API and removes
        # from state only. Orphan OAC can be deleted manually in AWS if desired.
        pac_opts = pulumi.ResourceOptions(
            parent=self,
            retain_on_delete=True,
        )
        oac = aws.cloudfront.OriginAccessControl(
            resource_name=f"{name}-oac",
            origin_access_control_origin_type="s3",
            signing_behavior="always",
            signing_protocol="sigv4",
            opts=pac_opts,
        )

        # Create the CloudFront distribution.
        # This is needed to serve the static website from the S3 bucket.
        origins = [
            aws.cloudfront.DistributionOriginArgs(
                domain_name=self.bucket.bucket_regional_domain_name,
                origin_id="s3-origin",
                origin_access_control_id=oac.id,
            )
        ]

        # Create the CloudFront default cache behavior.
        # This is needed to serve the static website from the S3 bucket.
        # ForwardedValues is required by the API when not using a cache policy.
        forwarded_values = aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesArgs(
            query_string=False,
            cookies=aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesCookiesArgs(
                forward="none",
            ),
        )
        default_cache_behavior = aws.cloudfront.DistributionDefaultCacheBehaviorArgs(
            target_origin_id="s3-origin",
            viewer_protocol_policy="redirect-to-https",
            allowed_methods=["GET", "HEAD", "OPTIONS"],
            cached_methods=["GET", "HEAD"],
            compress=True,
            forwarded_values=forwarded_values,
        )

        # Create the CloudFront restrictions.
        # This is needed to ensure that the CloudFront distribution can only be accessed
        # from the specified countries.
        geo_restriction = aws.cloudfront.DistributionRestrictionsGeoRestrictionArgs(
            restriction_type="none",
        )
        restrictions = aws.cloudfront.DistributionRestrictionsArgs(
            geo_restriction=geo_restriction,
        )

        # Create the CloudFront viewer certificate.
        # This is needed to ensure that the CloudFront distribution can only be accessed
        # over HTTPS.
        viewer_certificate = aws.cloudfront.DistributionViewerCertificateArgs(
            cloudfront_default_certificate=True,
        )

        # Create the CloudFront distribution.
        # This is needed to serve the static website from the S3 bucket.
        # Explicit depends_on so destroy order is correct: distribution is deleted
        # before the OAC (AWS returns 409 OriginAccessControlInUse otherwise).
        distribution_opts = pulumi.ResourceOptions(
            parent=self,
            depends_on=[oac],
        )
        self.distribution = aws.cloudfront.Distribution(
            resource_name=f"{name}-cdn",
            enabled=True,
            origins=origins,
            default_cache_behavior=default_cache_behavior,
            restrictions=restrictions,
            viewer_certificate=viewer_certificate,
            opts=distribution_opts,
        )

        # Exposed as Output[str] so GCP DNS (or other stacks) can use as CNAME target.
        self.cloudfront_domain_name: pulumi.Output[str] = self.distribution.domain_name
        self.cloudfront_hosted_zone_id: pulumi.Output[str] = (
            self.distribution.hosted_zone_id
        )
        self.cloudfront_url: pulumi.Output[str] = pulumi.Output.concat(
            "https://", self.distribution.domain_name
        )
        self.register_outputs(
            {
                "cloudfront_domain_name": self.cloudfront_domain_name,
                "cloudfront_hosted_zone_id": self.cloudfront_hosted_zone_id,
                "cloudfront_url": self.cloudfront_url,
            }
        )

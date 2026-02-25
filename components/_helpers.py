"""
Pure helpers for DNS and naming. Testable without Pulumi runtime.

Used by the GCP component (ensure_trailing_dot, fqdn, cname_rrdata) and the
Azure component (sanitize_storage_account_name). No Pulumi types; all
functions accept and return plain Python types so they can be unit-tested
without a Pulumi stack.
"""


def ensure_trailing_dot(
    domain: str,
) -> str:
    """
    Return domain with a single trailing dot for DNS FQDN.

    Cloud DNS (and many DNS APIs) expect zone and record names with a trailing
    dot when they are fully qualified. Idempotent if already present.
    """
    return domain if domain.endswith(".") else f"{domain}."


def fqdn(
    domain: str,
    subdomain: str,
) -> str:
    """
    Build FQDN like 'www.example.com.' from domain and subdomain.

    Args:
        domain: Base domain (e.g. "example.com"); trailing dot is ensured.
        subdomain: Leading label (e.g. "www", "backup").

    Returns:
        FQDN with trailing dot (e.g. "www.example.com.").
    """
    base = ensure_trailing_dot(domain)
    return f"{subdomain}.{base}" if not base.startswith(f"{subdomain}.") else base


def cname_rrdata(
    target: str,
) -> list[str]:
    """
    Return CNAME rrdatas list (single target with trailing dot).

    GCP Cloud DNS RecordSet.rrdatas expects a list of strings; CNAME has
    one target. Target is normalized with a trailing dot.
    """
    return [target if target.endswith(".") else f"{target}."]


def sanitize_storage_account_name(
    prefix: str,
    max_len: int = 24,
) -> str:
    """
    Produce an Azure-compliant storage account name from a prefix.

    Azure storage account names must be globally unique, 3-24 characters,
    alphanumeric only. This function strips hyphens and underscores, truncates
    to reserve space for a "sa" suffix, and appends "sa".

    Args:
        prefix: Base name (e.g. from Pulumi resource name).
        max_len: Maximum length (default 24 per Azure).

    Returns:
        Sanitized name ending with "sa" (e.g. "omnicloudresiliencedevsa").
    """
    # Reserve 2 chars for "sa" suffix; strip chars Azure disallows.
    cleaned = prefix.replace("-", "").replace("_", "")[: max_len - 2]
    return f"{cleaned}sa"

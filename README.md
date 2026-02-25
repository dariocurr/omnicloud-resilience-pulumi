# Omnicloud Resilience (Pulumi)

resilient static hosting with a primary (AWS S3 + CloudFront) and backup (Azure Storage) origin,
and GCP Cloud DNS for failover routing—implemented
with Pulumi as software engineering (ComponentResources, typing, config, output chaining, tests).

## Architecture

| Cloud | Resources |
| ----- | --------- |
| **AWS** | S3 (origin) + CloudFront; S3 Block Public Access enabled |
| **Azure** | Storage Account (static website); optional backup (soft delete) via config |
| **GCP** | Cloud DNS Managed Zone + primary/backup CNAME records (failover structure) |

## Patterns used

- **ComponentResources** - Each cloud is encapsulated in its own class (`AwsInfra`, `AzureInfra`, `GcpInfra`) under `components/`.
- **Strong typing** - Python type hints throughout (e.g. `Output[str]`, `Optional[pulumi.ResourceOptions]`).
- **Output chaining** - AWS CloudFront domain (`Output[str]`) is passed into the GCP component as the primary DNS target.
- **Config** - `pulumi.Config()` for `domain_name`, `environment`, and `enable_azure_backup` (toggle Azure backup on/off).
- **Logic** - `enable_azure_backup` drives a conditional that creates `BlobServiceProperties` (soft delete) only when true.
- **Testing** - Pure unit tests for helpers only (no mocks).

## Project layout

```tree
├── Pulumi.yaml              # Pulumi metadata
├── Pulumi.dev.yaml          # Stack config (domain_name, enable_azure_backup, etc.)
├── pyproject.toml           # Project & dependencies (uv)
├── uv.lock                  # Lockfile (uv)
├── config.py                # StackConfig dataclass and from_pulumi_config()
├── __main__.py              # Entrypoint: load config, wire components, export outputs
├── components/
│   ├── __init__.py
│   ├── _helpers.py          # Pure DNS/naming helpers (testable without Pulumi)
│   ├── aws.py               # AwsInfra (S3 + CloudFront, S3_BLOCK_PUBLIC_ACCESS)
│   ├── azure.py             # AzureInfra (Storage + optional soft-delete)
│   └── gcp.py               # GcpInfra (DNS zone + primary/backup CNAMEs)
└── tests/
    └── test_helpers.py      # ensure_trailing_dot, fqdn, cname_rrdata, sanitize_storage_account_name
```

## Setup

Uses [uv](https://docs.astral.sh/uv/) as the package manager.

```bash
uv sync                   # install deps (creates .venv; run uv lock after clone and commit uv.lock)
pulumi stack select dev   # or: pulumi stack init dev
# Set config if not using Pulumi.dev.yaml: pulumi config set domain_name example.com
```

## Deploy

```bash
uv run pulumi up
```

## Destroy

To tear down all resources managed by the stack (AWS, Azure, GCP):

```bash
uv run pulumi destroy
```

Confirm when prompted.
This removes the stack’s resources in dependency order
(e.g. CloudFront, then S3; DNS records, then zone; Storage Account, Resource Group).

## Run tests

```bash
uv run pytest tests -v
```

## Config (Pulumi.dev.yaml / CLI)

| Key | Description |
| --- | ----------- |
| `domain_name` | Domain for GCP DNS (e.g. `example.com`) |
| `environment` | Environment label (e.g. `dev`) |
| `enable_azure_backup` | `true` / `false` - toggles Azure blob/container soft-delete (30 days) |

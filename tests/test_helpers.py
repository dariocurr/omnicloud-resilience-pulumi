"""Tests for pure helpers"""

from components import _helpers


class TestEnsureTrailingDot:
    def test_adds_dot_when_missing(self):
        assert _helpers.ensure_trailing_dot("example.com") == "example.com."

    def test_leaves_dot_when_present(self):
        assert _helpers.ensure_trailing_dot("example.com.") == "example.com."


class TestFqdn:
    def test_builds_www_subdomain(self):
        assert _helpers.fqdn("example.com", "www") == "www.example.com."

    def test_domain_with_trailing_dot(self):
        assert _helpers.fqdn("example.com.", "www") == "www.example.com."

    def test_backup_subdomain(self):
        assert _helpers.fqdn("example.com", "backup") == "backup.example.com."


class TestCnameRrdata:
    def test_adds_trailing_dot(self):
        assert _helpers.cname_rrdata("cdn.example.com") == ["cdn.example.com."]

    def test_leaves_dot_unchanged(self):
        assert _helpers.cname_rrdata("cdn.example.com.") == ["cdn.example.com."]


class TestSanitizeStorageAccountName:
    def test_strips_hyphens_and_appends_sa(self):
        assert _helpers.sanitize_storage_account_name("azure-dev") == "azuredevsa"

    def test_respects_max_len(self):
        long_prefix = "a" * 30
        result = _helpers.sanitize_storage_account_name(long_prefix, max_len=24)
        assert len(result) == 24
        assert result.endswith("sa")

    def test_short_prefix(self):
        assert _helpers.sanitize_storage_account_name("az") == "azsa"

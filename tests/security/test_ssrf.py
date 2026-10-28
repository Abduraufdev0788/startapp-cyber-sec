"""
Security tests for SSRF (Server-Side Request Forgery) and DNS Rebinding protections.
"""

import pytest

from app.core.exceptions import AppException, SSRFBlockedException
from app.modules.url_scanning.ssrf import is_ip_allowed, validate_url_for_ssrf


@pytest.mark.parametrize(
    "prohibited_ip",
    [
        "127.0.0.1",
        "127.0.0.2",
        "127.255.255.255",
        "169.254.169.254",  # AWS/GCP Metadata IP
        "169.254.1.1",
        "10.0.0.1",
        "10.255.255.255",
        "172.16.0.1",
        "172.31.255.255",
        "192.168.1.1",
        "192.168.0.254",
        "0.0.0.0",
        "100.64.0.1",      # CGNAT
        "224.0.0.1",      # Multicast
        "::1",            # IPv6 Loopback
        "fe80::1",        # IPv6 Link-local
        "fc00::1",        # IPv6 Unique local
    ],
)
def test_prohibited_ips_blocked(prohibited_ip: str):
    """Verifies that all reserved, private, loopback, and cloud metadata IPs are rejected."""
    assert is_ip_allowed(prohibited_ip) is False


@pytest.mark.parametrize(
    "public_ip",
    [
        "8.8.8.8",
        "1.1.1.1",
        "142.250.190.46",  # Google
        "104.244.42.1",    # Twitter
    ],
)
def test_public_ips_allowed(public_ip: str):
    """Verifies that legitimate public IPs are permitted."""
    assert is_ip_allowed(public_ip) is True


def test_ssrf_blocks_direct_private_ip_url():
    """Verifies that direct private IP URLs are blocked immediately."""
    with pytest.raises(SSRFBlockedException):
        validate_url_for_ssrf("http://169.254.169.254/latest/meta-data/")

    with pytest.raises(SSRFBlockedException):
        validate_url_for_ssrf("http://127.0.0.1:5432/")

    with pytest.raises(SSRFBlockedException):
        validate_url_for_ssrf("http://10.0.0.1/admin")


def test_ssrf_rejects_invalid_schemes():
    """Verifies that non-http/https schemes are rejected."""
    with pytest.raises(AppException, match="Unsupported URL scheme"):
        validate_url_for_ssrf("file:///etc/passwd")

    with pytest.raises(AppException, match="Unsupported URL scheme"):
        validate_url_for_ssrf("gopher://127.0.0.1:6379/")

    with pytest.raises(AppException, match="Unsupported URL scheme"):
        validate_url_for_ssrf("ftp://example.com/test.zip")

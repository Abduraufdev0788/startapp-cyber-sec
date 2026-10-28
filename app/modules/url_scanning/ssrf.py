"""
SSRF (Server-Side Request Forgery) and DNS Rebinding protection module.
Validates target URLs against blacklisted private, reserved, loopback, and cloud metadata networks.
"""

import ipaddress
import socket
from urllib.parse import urlparse

from app.core.exceptions import AppException, SSRFBlockedException

# Prohibited IPv4 Networks (RFC 1918, RFC 3927, RFC 5735, Cloud Metadata, etc.)
PROHIBITED_IPV4_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network
    ipaddress.ip_network("10.0.0.0/8"),         # Private-use (RFC 1918)
    ipaddress.ip_network("100.64.0.0/10"),      # Shared Address Space (CGNAT)
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local & Cloud Metadata (AWS, GCP, etc.)
    ipaddress.ip_network("172.16.0.0/12"),      # Private-use (RFC 1918)
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # TEST-NET-1
    ipaddress.ip_network("192.88.99.0/24"),     # 6to4 Relay Anycast
    ipaddress.ip_network("192.168.0.0/16"),     # Private-use (RFC 1918)
    ipaddress.ip_network("198.18.0.0/15"),      # Network benchmark tests
    ipaddress.ip_network("198.51.100.0/24"),    # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),     # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved for future use
    ipaddress.ip_network("255.255.255.255/32"), # Limited Broadcast
]

# Prohibited IPv6 Networks
PROHIBITED_IPV6_NETWORKS = [
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("::1/128"),           # Loopback
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-local
    ipaddress.ip_network("ff00::/8"),           # Multicast
]


def is_ip_allowed(ip_str: str) -> bool:
    """
    Checks if an IP address string is a safe, publicly routable IP.
    Returns False if the IP belongs to any private, loopback, or reserved range.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_reserved:
        return False

    if isinstance(ip, ipaddress.IPv4Address):
        for prohibited in PROHIBITED_IPV4_NETWORKS:
            if ip in prohibited:
                return False
    elif isinstance(ip, ipaddress.IPv6Address):
        for prohibited in PROHIBITED_IPV6_NETWORKS:
            if ip in prohibited:
                return False

    return True


def resolve_hostname_ips(hostname: str) -> list[str]:
    """
    Resolves a hostname to all associated IPv4 and IPv6 addresses.
    """
    clean_host = hostname.strip().rstrip(".")
    resolved_ips: set[str] = set()

    try:
        # Resolve both IPv4 (AF_INET) and IPv6 (AF_INET6)
        addr_info = socket.getaddrinfo(clean_host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for entry in addr_info:
            ip = entry[4][0]
            resolved_ips.add(ip)
    except socket.gaierror as e:
        raise AppException(
            f"DNS resolution failed for hostname '{hostname}': {e}",
            code="DNS_RESOLUTION_ERROR",
            status_code=400,
        ) from e

    return list(resolved_ips)


def validate_url_for_ssrf(url: str) -> tuple[str, list[str]]:
    """
    Validates a URL against SSRF attacks:
    1. Ensures scheme is strictly 'http' or 'https'.
    2. Parses host and resolves all underlying IP addresses.
    3. Verifies that every resolved IP is public and safe.
    Returns (hostname, list_of_safe_ips).
    Raises SSRFBlockedException if any IP is prohibited.
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme not in ("http", "https"):
        raise AppException(
            f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are allowed.",
            code="INVALID_URL_SCHEME",
            status_code=400,
        )

    hostname = parsed.hostname
    if not hostname:
        raise AppException(
            "URL does not contain a valid hostname.",
            code="INVALID_HOSTNAME",
            status_code=400,
        )

    # Check if the hostname itself is directly an IP literal (e.g. http://127.0.0.1/)
    try:
        direct_ip = ipaddress.ip_address(hostname)
        if not is_ip_allowed(str(direct_ip)):
            raise SSRFBlockedException(target_ip=str(direct_ip))
        return hostname, [str(direct_ip)]
    except ValueError:
        pass  # Hostname is a domain name, proceed to DNS resolution

    resolved_ips = resolve_hostname_ips(hostname)
    if not resolved_ips:
        raise AppException(
            f"No IP addresses found for hostname '{hostname}'.",
            code="HOST_UNRESOLVABLE",
            status_code=400,
        )

    for ip_str in resolved_ips:
        if not is_ip_allowed(ip_str):
            raise SSRFBlockedException(
                message=f"SSRF target blocked: '{hostname}' resolved to prohibited IP '{ip_str}'.",
                target_ip=ip_str,
            )

    return hostname, resolved_ips

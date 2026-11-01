"""
URL Extraction, Normalization, Canonicalization, and Hashing Pipeline.
Protects against obfuscation, homograph attacks (Punycode/IDN), and tracking parameter noise.
"""

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import idna

# Common tracking and session parameters to strip for canonicalization
STRIPPED_QUERY_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "ref",
    "ref_src",
    "_ga",
    "_gl",
}

# Robust regex for detecting URLs and domains in raw text when entities are absent
URL_REGEX = re.compile(
    r"(?i)\b(?:https?://[^\s()<>]+|(?:www\d{0,3}[.]|[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:[a-z]{2,10}))(?:/[^\s()<>]*)?)(?<![.,?!;:«»\"\'\(\)\[\]{}])",
    re.IGNORECASE,
)


def extract_urls_from_text(text: str) -> list[str]:
    """Extracts raw URL strings from text using regex."""
    if not text:
        return []
    matches = URL_REGEX.findall(text)
    urls: list[str] = []
    for match in matches:
        raw_match = match[0] if isinstance(match, tuple) else match
        raw_match = raw_match.strip(".,?!;:«»\"'()[]{}")
        if not raw_match:
            continue
        if not raw_match.startswith(("http://", "https://")):
            raw_match = f"https://{raw_match}"
        urls.append(raw_match)
    return urls


def canonicalize_url(url: str) -> str:
    """
    Transforms a raw URL into a normalized, canonical form:
    1. Trims whitespace.
    2. Lowercases scheme and netloc.
    3. Converts internationalized domain names (IDN) to ASCII Punycode.
    4. Strips default ports (:80 for http, :443 for https).
    5. Strips tracking query parameters and sorts remaining query parameters.
    6. Strips fragment identifiers (#...).
    """
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = f"https://{clean_url}"

    parsed = urlparse(clean_url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Split host and port
    if ":" in netloc:
        host, port_str = netloc.rsplit(":", 1)
        if (scheme == "http" and port_str == "80") or (scheme == "https" and port_str == "443"):
            netloc = host
    else:
        host = netloc

    # IDN / Punycode conversion for homograph attack resilience
    try:
        punycode_host = idna.encode(host).decode("ascii")
        if ":" in netloc:
            _, port_str = netloc.rsplit(":", 1)
            netloc = f"{punycode_host}:{port_str}"
        else:
            netloc = punycode_host
    except (idna.IDNAError, UnicodeError):
        # Fallback to existing host if IDN conversion fails
        pass

    # Normalize path
    path = parsed.path or "/"

    # Strip tracking parameters and sort remaining query parameters
    query_params = parse_qsl(parsed.query, keep_blank_values=True)
    filtered_params = [
        (k, v) for k, v in query_params if k.lower() not in STRIPPED_QUERY_PARAMS
    ]
    filtered_params.sort(key=lambda item: item[0])
    canonical_query = urlencode(filtered_params)

    # Reconstruct canonical URL (fragments are dropped)
    return urlunparse((scheme, netloc, path, "", canonical_query, ""))


def compute_url_hash(canonical_url: str) -> str:
    """Computes a SHA-256 hexadecimal digest of the canonical URL."""
    return hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()

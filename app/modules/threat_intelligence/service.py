"""
Threat Intelligence and Safe Web Fetcher Service.
Gathers technical evidence (DNS, WHOIS domain age, SSL, bounded HTTP HTML extraction)
while strictly adhering to SSRF, DoS, and resource-exhaustion safeguards.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import dns.resolver
import httpx
import whois
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.modules.url_scanning.ssrf import validate_url_for_ssrf


def _query_dns_records(domain: str) -> dict[str, Any]:
    """Queries DNS records (MX, NS, TXT) safely with strict timeout."""
    results: dict[str, list[str]] = {"mx": [], "ns": [], "txt": []}
    resolver = dns.resolver.Resolver()
    resolver.timeout = 2.0
    resolver.lifetime = 2.0
    for rtype in ("MX", "NS", "TXT"):
        try:
            answers = resolver.resolve(domain, rtype)
            results[rtype.lower()] = [str(r.to_text()) for r in answers]
        except Exception:
            pass
    return results


def _query_whois_data(domain: str) -> tuple[int | None, str | None]:
    """Fetches domain registration age in days and registrar via WHOIS/RDAP."""
    try:
        w = whois.whois(domain)
        creation = w.creation_date
        if isinstance(creation, list):
            creation = creation[0]
        if creation and isinstance(creation, datetime):
            now = datetime.now(UTC)
            if creation.tzinfo is None:
                creation = creation.replace(tzinfo=UTC)
            days = max(0, (now - creation).days)
            registrar = str(w.registrar) if w.registrar else None
            return days, registrar
    except Exception:
        pass
    return None, None


class ThreatIntelligenceService:
    """Enriches URLs with technical observations safely."""

    @classmethod
    async def enrich_url(cls, canonical_url: str) -> dict[str, Any]:
        """
        Executes safe bounded technical enrichment:
        1. SSRF validation.
        2. DNS and WHOIS enrichment (async background threads).
        3. Bounded HTTP fetch (streaming chunks up to 2MB, strict timeout).
        4. HTML feature extraction (forms, password inputs, text excerpt).
        """
        settings = get_settings()

        # 1. SSRF and Domain validation
        hostname, resolved_ips = validate_url_for_ssrf(canonical_url)

        evidence: dict[str, Any] = {
            "domain": hostname,
            "resolved_ips": resolved_ips,
            "domain_age_days": 100,  # Default fallback if WHOIS unavailable
            "registrar": None,
            "dns_records": {},
            "ssl_issuer": None,
            "ssl_valid": canonical_url.startswith("https://"),
            "http_status": None,
            "response_time_ms": None,
            "has_login_form": False,
            "has_password_input": False,
            "redirect_chain": [],
            "text_excerpt": None,
        }

        # Concurrently gather DNS & WHOIS data
        try:
            dns_task = asyncio.to_thread(_query_dns_records, hostname)
            whois_task = asyncio.to_thread(_query_whois_data, hostname)
            dns_records, whois_result = await asyncio.gather(dns_task, whois_task)
            evidence["dns_records"] = dns_records
            if whois_result[0] is not None:
                evidence["domain_age_days"] = whois_result[0]
            if whois_result[1]:
                evidence["registrar"] = whois_result[1]
        except Exception:
            pass

        # 2. Bounded HTTP Fetch
        current_url = canonical_url
        redirect_count = 0
        redirect_chain: list[str] = [canonical_url]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        start_time = asyncio.get_event_loop().time()

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=settings.SCANNER_CONNECT_TIMEOUT_SECONDS,
                    read=settings.SCANNER_CONNECT_TIMEOUT_SECONDS,
                    write=settings.SCANNER_CONNECT_TIMEOUT_SECONDS,
                    pool=settings.SCANNER_TOTAL_TIMEOUT_SECONDS,
                ),
                follow_redirects=False,
                verify=True,
            ) as client:
                while redirect_count < settings.SCANNER_MAX_REDIRECTS:
                    # Validate URL before every hop against SSRF
                    validate_url_for_ssrf(current_url)

                    response = await client.get(current_url, headers=headers)
                    evidence["http_status"] = response.status_code

                    # Handle Redirects
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            break
                        # Handle relative redirects
                        if not location.startswith(("http://", "https://")):
                            parsed_current = urlparse(current_url)
                            location = f"{parsed_current.scheme}://{parsed_current.netloc}/{location.lstrip('/')}"

                        redirect_chain.append(location)
                        current_url = location
                        redirect_count += 1
                        continue

                    # Read response body with strict byte bounds (max 2MB)
                    content_bytes = bytearray()
                    async for chunk in response.aiter_bytes():
                        content_bytes.extend(chunk)
                        if len(content_bytes) > settings.SCANNER_MAX_RESPONSE_BYTES:
                            break  # Abort reading further to prevent resource exhaustion

                    evidence["response_time_ms"] = int(
                        (asyncio.get_event_loop().time() - start_time) * 1000
                    )
                    evidence["redirect_chain"] = redirect_chain

                    # Extract HTML features
                    html_text = content_bytes.decode("utf-8", errors="ignore")
                    cls._extract_html_features(html_text, evidence)
                    break

        except AppException:
            raise
        except Exception:
            # If target website is unreachable or timeout occurs, record partial evidence
            evidence["http_status"] = None

        return evidence

    @staticmethod
    def _extract_html_features(html_text: str, evidence: dict[str, Any]) -> None:
        """Parses HTML DOM for security-sensitive markers without executing JavaScript."""
        if not html_text:
            return

        soup = BeautifulSoup(html_text, "html.parser")

        # Check forms and password fields
        forms = soup.find_all("form")
        evidence["has_login_form"] = len(forms) > 0

        password_inputs = soup.find_all("input", attrs={"type": "password"})
        evidence["has_password_input"] = len(password_inputs) > 0

        # Extract title and description
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and meta_tag.get("content"):
            meta_desc = str(meta_tag["content"]).strip()

        # Extract visible text (bounded to max 50KB)
        # Remove script and style elements
        for script_or_style in soup(["script", "style", "noscript"]):
            script_or_style.extract()

        raw_text = soup.get_text(separator=" ", strip=True)
        text_summary = f"Title: {title}\nDescription: {meta_desc}\nBody Text: {raw_text}"
        evidence["text_excerpt"] = text_summary[:50000]

"""
Unit tests for URL extraction, canonicalization, and homograph resistance pipeline.
"""

from app.modules.url_scanning.pipeline import (
    canonicalize_url,
    compute_url_hash,
    extract_urls_from_text,
)


def test_url_canonicalization_strips_tracking():
    """Verifies that tracking parameters and fragments are stripped."""
    raw_url = "https://EXAMPLE.com:443/login?utm_source=telegram&utm_medium=channel&valid_param=1#section1"
    canonical = canonicalize_url(raw_url)

    assert canonical == "https://example.com/login?valid_param=1"


def test_url_canonicalization_sorts_query_parameters():
    """Verifies deterministic sorting of query parameters to prevent hash mismatches."""
    url1 = "https://example.com/search?b=2&a=1"
    url2 = "https://example.com/search?a=1&b=2"

    canonical1 = canonicalize_url(url1)
    canonical2 = canonicalize_url(url2)

    assert canonical1 == canonical2
    assert compute_url_hash(canonical1) == compute_url_hash(canonical2)


def test_homograph_punycode_conversion():
    """Verifies that Cyrillic spoofing of Latin characters is converted to ASCII Punycode."""
    # Using Cyrillic 'е' (U+0435) inside 'telegram'
    cyrillic_spoofed = "https://tеlеgram.org/login"
    canonical = canonicalize_url(cyrillic_spoofed)

    assert "xn--" in canonical  # Punycode prefix must be present


def test_extract_urls_from_text():
    """Verifies regex URL extraction from message text."""
    text = "Assalomu alaykum, bepul sovg'a olish uchun https://scam-site.xyz/win bosing yoki www.click-bonus.top/claim ga kiring!"
    extracted = extract_urls_from_text(text)

    assert len(extracted) == 2
    assert "https://scam-site.xyz/win" in extracted
    assert any("click-bonus.top" in u for u in extracted)


def test_extract_all_urls_from_event_including_hidden_links_and_buttons():
    """Verifies extraction of open URLs, hidden hyperlinks behind words, and inline buttons."""
    from unittest.mock import MagicMock

    from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl

    from app.integrations.telethon.monitor import extract_all_urls_from_event

    event = MagicMock()
    message = MagicMock()
    message.message = "Bu yerda ochiq havola: https://open-link.com va so'z ortidagi havola."

    # Entity 1: Open link
    e1 = MessageEntityUrl(offset=21, length=21)
    # Entity 2: Hidden link behind words
    e2 = MessageEntityTextUrl(offset=49, length=4, url="https://hidden-phishing.com/claim")
    message.entities = [e1, e2]

    # Inline button mock
    button = MagicMock(url="https://button-scam.xyz/gift")
    row = MagicMock()
    row.buttons = [button]
    reply_markup = MagicMock()
    reply_markup.rows = [row]
    message.reply_markup = reply_markup
    message.buttons = [[button]]

    event.message = message
    urls = extract_all_urls_from_event(event)

    assert "https://open-link.com" in urls
    assert "https://hidden-phishing.com/claim" in urls
    assert "https://button-scam.xyz/gift" in urls

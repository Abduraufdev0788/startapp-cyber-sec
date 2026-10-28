"""
Unit tests for notification active state, URL defanging, and alert dismissal lifecycle.
"""

from app.api.v1.endpoints.notifications import defang_url


def test_defang_url_replaces_protocols_and_dots():
    """Verifies that URLs are properly defanged to prevent accidental clicks."""
    raw_url = "https://phishing-bank-login.com/auth"
    defanged = defang_url(raw_url)

    assert defanged == "hxxps://phishing-bank-login[.]com/auth"
    assert "https://" not in defanged
    assert "[.]" in defanged.split("/")[2]
    assert "login.com" not in defanged


def test_defang_http_url():
    """Verifies http defanging."""
    raw_url = "http://scam-giveaway.xyz"
    defanged = defang_url(raw_url)

    assert defanged == "hxxp://scam-giveaway[.]xyz"

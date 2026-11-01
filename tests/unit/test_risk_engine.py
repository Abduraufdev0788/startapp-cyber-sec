"""
Unit tests for multi-factor risk engine and heuristic brand impersonation evaluation.
"""

from app.modules.risk_engine.engine import RiskEngine


def test_benign_site_low_risk_score():
    """Verifies that an established domain without password inputs produces a BENIGN verdict."""
    evidence = {
        "domain_age_days": 1500,
        "ssl_valid": True,
        "has_password_input": False,
        "text_excerpt": "Welcome to our open source project documentation and guides.",
    }
    result = RiskEngine.evaluate("docs.example.org", technical_evidence=evidence)

    assert result["verdict"] == "BENIGN"
    assert result["risk_score"] < 25
    assert result["impersonated_brand"] is None


def test_new_domain_with_password_triggers_suspicious():
    """Verifies that a brand-new domain with a password field elevates risk."""
    evidence = {
        "domain_age_days": 4,  # <7 days (+30)
        "ssl_valid": False,    # Invalid SSL (+30)
        "has_password_input": True,  # (+25)
        "text_excerpt": "Sign in to view private dashboard content.",
    }
    result = RiskEngine.evaluate("newportal-login.xyz", technical_evidence=evidence)

    assert result["verdict"] in ("SCAM", "PHISHING")
    assert result["risk_score"] >= 70


def test_brand_impersonation_critical_override():
    """Verifies that mimicking a protected brand (e.g. Telegram) on an unofficial domain triggers CRITICAL PHISHING."""
    evidence = {
        "domain_age_days": 2,
        "ssl_valid": True,
        "has_password_input": True,
        "text_excerpt": "Official Telegram Web Login. Enter your phone number and SMS code to claim free Premium.",
    }
    result = RiskEngine.evaluate("telegram-bonus-claim.top", technical_evidence=evidence)

    assert result["verdict"] == "PHISHING"
    assert result["risk_score"] >= 80
    assert result["impersonated_brand"] == "Telegram"
    assert any("Brand Impersonation" in r for r in result["reasons"])


def test_gambling_casino_detection():
    """Verifies that predatory gambling, casinos, and slots sites are classified as SCAM with high risk."""
    evidence = {
        "domain_age_days": 3000,
        "ssl_valid": True,
        "has_password_input": True,
        "raw_url": "https://uz.1xbet.com/ru/slots",
        "text_excerpt": "1xBet - stavki na sport, kazino, onlayn slotlar.",
    }
    result = RiskEngine.evaluate("uz.1xbet.com", technical_evidence=evidence)

    assert result["verdict"] == "SCAM"
    assert result["risk_score"] >= 75
    assert "1xBet" in (result["impersonated_brand"] or "")
    assert any("qimor" in r.lower() or "kazino" in r.lower() for r in result["reasons"])

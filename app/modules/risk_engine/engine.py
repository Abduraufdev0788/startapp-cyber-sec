"""
Risk Scoring Engine.
Synthesizes deterministic technical evidence, brand impersonation rules, and AI evaluations
into an explainable 0-100 risk score and definitive verdict.
"""

from typing import Any

from app.integrations.gemini.schemas import GeminiPhishingAssessment, VerdictEnum

# Known high-value brands frequently targeted by phishing campaigns
PROTECTED_BRANDS: dict[str, list[str]] = {
    "Telegram": ["telegram.org", "t.me", "telegram.me"],
    "Click": ["click.uz"],
    "Payme": ["payme.uz"],
    "Uzum": ["uzum.uz", "uzum.com", "uzumbank.uz"],
    "Binance": ["binance.com"],
}


class RiskEngine:
    """Calculates multi-factor phishing and scam scores with explainable reasons."""

    @classmethod
    def evaluate(
        cls,
        domain: str,
        technical_evidence: dict[str, Any],
        ai_assessment: GeminiPhishingAssessment | None = None,
    ) -> dict[str, Any]:
        """
        Synthesizes technical evidence and AI assessment into a final score (0-100) and verdict.
        """
        base_score = 0
        reasons: list[str] = []
        impersonated_brand: str | None = None

        # ----------------------------------------------------------------------
        # 1. Technical Indicators
        # ----------------------------------------------------------------------
        domain_age = technical_evidence.get("domain_age_days")
        if domain_age is not None:
            if domain_age < 7:
                base_score += 30
                reasons.append(f"Domain is extremely new (Registered {domain_age} days ago).")
            elif domain_age < 14:
                base_score += 20
                reasons.append(f"Newly registered domain (Registered {domain_age} days ago).")
            elif domain_age < 30:
                base_score += 10
                reasons.append(f"Recent domain registration (Age: {domain_age} days).")

        if technical_evidence.get("has_password_input"):
            base_score += 25
            reasons.append("Web page contains a password input field.")

        if not technical_evidence.get("ssl_valid", False):
            base_score += 30
            reasons.append("Missing, invalid, or untrusted SSL/TLS certificate.")

        # Homograph / Punycode check
        if domain.startswith("xn--"):
            base_score += 40
            reasons.append(f"Punycode/Homograph domain detected ('{domain}'), likely spoofing another script.")

        # ----------------------------------------------------------------------
        # 2. Brand Impersonation Override (Deterministic Heuristics)
        # ----------------------------------------------------------------------
        clean_domain = domain.lower().strip()
        page_text = (technical_evidence.get("text_excerpt") or "").lower()

        for brand, official_domains in PROTECTED_BRANDS.items():
            brand_lower = brand.lower()
            if brand_lower in page_text or brand_lower in clean_domain:
                # Check if the domain is actually one of the official domains
                is_official = any(clean_domain == off or clean_domain.endswith(f".{off}") for off in official_domains)
                if not is_official:
                    impersonated_brand = brand
                    base_score += 60
                    reasons.append(
                        f"Brand Impersonation: Page mentions or targets '{brand}', but domain '{clean_domain}' is NOT official."
                    )
                    break

        # ----------------------------------------------------------------------
        # 3. AI Assessment Integration
        # ----------------------------------------------------------------------
        if ai_assessment:
            # Weighted average between deterministic signals and AI score
            combined_score = int((base_score * 0.5) + (ai_assessment.risk_score * 0.5))
            if ai_assessment.impersonated_brand and not impersonated_brand:
                impersonated_brand = ai_assessment.impersonated_brand
            # Merge reasons without duplicates
            for r in ai_assessment.reasons:
                if r not in reasons:
                    reasons.append(r)
            confidence = ai_assessment.confidence
        else:
            combined_score = base_score
            confidence = 0.6 if base_score > 30 else 0.4

        # Clamp score between 0 and 100
        final_score = max(0, min(100, combined_score))

        # ----------------------------------------------------------------------
        # 4. Final Verdict Categorization
        # ----------------------------------------------------------------------
        if impersonated_brand and final_score >= 70:
            verdict = VerdictEnum.PHISHING.value
        elif final_score >= 80:
            verdict = VerdictEnum.PHISHING.value
        elif final_score >= 60:
            verdict = VerdictEnum.SCAM.value
        elif final_score >= 26:
            verdict = VerdictEnum.SUSPICIOUS.value
        else:
            verdict = VerdictEnum.BENIGN.value

        return {
            "verdict": verdict,
            "risk_score": final_score,
            "confidence": confidence,
            "impersonated_brand": impersonated_brand,
            "reasons": reasons,
        }

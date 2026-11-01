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

# Known gambling, illegal online casino, and predatory betting platforms
GAMBLING_DOMAINS_AND_BRANDS: dict[str, list[str]] = {
    "1xBet": ["1xbet", "1x-bet", "1xstavka", "1xstavk"],
    "1Win": ["1win", "1-win"],
    "Mostbet": ["mostbet"],
    "Melbet": ["melbet"],
    "Pin-Up": ["pin-up", "pinup"],
    "Linebet": ["linebet"],
    "Vavada": ["vavada"],
    "Joycasino": ["joycasino"],
    "Pokerdom": ["pokerdom"],
    "Parimatch": ["parimatch"],
    "Betwinner": ["betwinner"],
    "Megapari": ["megapari"],
    "Spinbetter": ["spinbetter"],
}

GAMBLING_KEYWORDS: list[str] = [
    "slots",
    "slotlar",
    "kazino",
    "casino",
    "bukmeker",
    "stavki",
    "qimor",
    "garov",
    "ruletka",
    "aviator",
    "lucky-jet",
]

# Known pirated sports streaming domains that serve malicious redirects and predatory casino popups
PIRATED_STREAMING_DOMAINS: dict[str, list[str]] = {
    "LiveBall": ["liveball"],
    "YallaShoot": ["yalla-shoot", "yallashoot"],
    "KooraLive": ["kooralive", "koora-live"],
    "BuffStreams": ["buffstreams", "buffstream"],
    "HesGoal": ["hesgoal"],
    "TotalSportek": ["totalsportek"],
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
        # 0. Critical Security Flags (SSRF / DNS Unresolvable)
        # ----------------------------------------------------------------------
        if technical_evidence.get("is_ssrf_blocked"):
            return {
                "risk_score": 95,
                "verdict": "MALICIOUS",
                "confidence": 0.99,
                "impersonated_brand": None,
                "reasons": ["Havola xavfli, man etilgan yoki ichki tarmoq manziliga (SSRF) yo'naltirilgan."],
            }

        if technical_evidence.get("dns_failed"):
            return {
                "risk_score": 45,
                "verdict": "SUSPICIOUS",
                "confidence": 0.85,
                "impersonated_brand": None,
                "reasons": ["Domen nomi DNS tizimida topilmadi (mavjud emas yoki muddati o'tgan)."],
            }

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
        # 1.5. Illegal Gambling, Casino, and Predatory Betting Detection
        # ----------------------------------------------------------------------
        clean_domain = domain.lower().strip()
        page_text = (technical_evidence.get("text_excerpt") or "").lower()
        has_login = technical_evidence.get("has_login_form", False) or technical_evidence.get("has_password_input", False)

        detected_gambling_brand = None
        for g_brand, patterns in GAMBLING_DOMAINS_AND_BRANDS.items():
            if any(p in clean_domain for p in patterns):
                detected_gambling_brand = g_brand
                break

        page_has_gambling = any(kw in page_text for kw in GAMBLING_KEYWORDS)
        domain_has_gambling = any(kw in clean_domain for kw in GAMBLING_KEYWORDS)
        raw_url = (technical_evidence.get("raw_url") or "").lower()
        url_has_gambling = any(f"/{kw}" in raw_url or f"{kw}/" in raw_url for kw in GAMBLING_KEYWORDS)

        if detected_gambling_brand or (page_has_gambling and (domain_has_gambling or url_has_gambling)):
            target_name = detected_gambling_brand or "Onlayn Kazino / Qimor"
            base_score = max(base_score, 75)
            impersonated_brand = f"{target_name} (Xavfli Qimor / Kazino)"
            reasons.append(
                f"Noqonuniy qimor va bukmekerlik xizmati ({target_name}): Onlayn kazino, slot va tavakkalchilikka asoslangan o'yinlar — Yuqori moliyaviy firibgarlik va mablag' yo'qotish xavfi!"
            )

        # ----------------------------------------------------------------------
        # 1.6. Pirated Sports Streaming & Malicious Ad-Redirect Detection
        # ----------------------------------------------------------------------
        detected_streaming_brand = None
        for s_brand, patterns in PIRATED_STREAMING_DOMAINS.items():
            if any(p in clean_domain for p in patterns):
                detected_streaming_brand = s_brand
                break

        if detected_streaming_brand:
            base_score = max(base_score, 68)
            impersonated_brand = f"{detected_streaming_brand} (Pirat Sport Striming)"
            reasons.append(
                f"Noqonuniy sport translatsiyasi ({detected_streaming_brand}): Pirat striming portali — Agressiv bukmekerlik/qimor reklamalari, soxta 'Play' tugmalari va zararli qayta yo'naltirish (redirect) xavfi yuqori!"
            )

        if technical_evidence.get("http_status") == 404:
            base_score = max(base_score, 50)
            reasons.append("Sahifa serverda topilmadi (HTTP 404 Not Found) — Sayt bloklangan, yopilgan yoki ko'chirilgan bo'lishi mumkin.")

        # ----------------------------------------------------------------------
        # 2. Brand Impersonation Override (Deterministic Heuristics)
        # ----------------------------------------------------------------------
        for brand, official_domains in PROTECTED_BRANDS.items():
            brand_lower = brand.lower()
            is_official = any(clean_domain == off or clean_domain.endswith(f".{off}") for off in official_domains)
            if is_official:
                continue

            # Case A: Domain explicitly spoofs the brand name (e.g., payme-gift.xyz, telegram-login.com)
            if brand_lower in clean_domain:
                impersonated_brand = brand
                base_score += 60
                reasons.append(
                    f"Brand Impersonation: Domain '{clean_domain}' contains brand name '{brand}' but is NOT official."
                )
                break

            # Case B: Page mentions brand AND has credential/login harvesting form OR AI confirmed impersonation
            ai_flagged_brand = bool(ai_assessment and ai_assessment.impersonated_brand and ai_assessment.impersonated_brand.lower() == brand_lower)
            if brand_lower in page_text and (has_login or ai_flagged_brand):
                impersonated_brand = brand
                base_score += 45
                reasons.append(
                    f"Brand Impersonation: Page targets '{brand}' credentials/login on non-official domain '{clean_domain}'."
                )
                break

        # ----------------------------------------------------------------------
        # 3. AI Assessment Integration
        # ----------------------------------------------------------------------
        if ai_assessment:
            # Weighted synthesis: deterministic high-confidence signals are never diluted down
            if impersonated_brand or base_score >= 60:
                combined_score = max(base_score, ai_assessment.risk_score)
            else:
                combined_score = int((base_score * 0.4) + (ai_assessment.risk_score * 0.6))

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

        # Clean contradictory fallback text if high risk is detected
        if impersonated_brand or combined_score >= 50:
            reasons = [r for r in reasons if "No active malicious indicators detected" not in r]

        # Clamp score between 0 and 100
        final_score = max(0, min(100, combined_score))

        # ----------------------------------------------------------------------
        # 4. Final Verdict Categorization
        # ----------------------------------------------------------------------
        if impersonated_brand and ("Qimor" in impersonated_brand or "Striming" in impersonated_brand):
            verdict = VerdictEnum.SCAM.value
        elif impersonated_brand and final_score >= 70:
            verdict = VerdictEnum.PHISHING.value
        elif final_score >= 80:
            verdict = VerdictEnum.PHISHING.value
        elif final_score >= 60:
            verdict = VerdictEnum.SCAM.value
        elif final_score >= 40:
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

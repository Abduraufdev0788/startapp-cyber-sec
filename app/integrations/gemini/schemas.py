"""
Google Gemini Structured Output Schemas.
Enforces strict schema validation for AI phishing and scam assessments.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class VerdictEnum(StrEnum):
    """Phishing assessment verdict categories."""

    PHISHING = "PHISHING"        # Credential, OTP, or payment card harvesting
    SCAM = "SCAM"                # Financial fraud, pyramid schemes, fake giveaways
    SUSPICIOUS = "SUSPICIOUS"    # Strong deceptive signals present, but inconclusive
    BENIGN = "BENIGN"            # Legitimate, non-malicious website
    UNKNOWN = "UNKNOWN"          # Unreachable, empty, or unanalyzable


class GeminiPhishingAssessment(BaseModel):
    """Structured response contract expected from Google Gemini model."""

    verdict: VerdictEnum = Field(
        ...,
        description="The categorical classification of the target website.",
    )
    risk_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence-adjusted risk score from 0 (completely safe) to 100 (actively malicious).",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence level in the assessment from 0.0 to 1.0.",
    )
    impersonated_brand: str | None = Field(
        None,
        description="Name of the brand or organization being mimicked or impersonated (e.g. 'Telegram', 'Click', 'Payme', 'Binance').",
    )
    reasons: list[str] = Field(
        ...,
        description="Clear, traceable, bullet-point evidence and reasoning behind the verdict.",
    )
    evidence_matches: list[str] = Field(
        default_factory=list,
        description="Standardized threat indicators detected, e.g. ['fake_login_form', 'urgency_tactic', 'unrealistic_rewards', 'brand_domain_mismatch'].",
    )

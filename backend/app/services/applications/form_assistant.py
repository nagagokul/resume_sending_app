"""Playwright-based application form assistance.

Compliance rules (hard):
- Never bypass CAPTCHA, MFA, OTP, anti-bot, auth, or rate limits
- Stop and ask the user when security controls appear
- Only autofill GREEN-confidence fields from verified profile data
- User must review and submit
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FieldConfidence(str, Enum):
    GREEN = "GREEN"  # safe automatic fill
    YELLOW = "YELLOW"  # requires confirmation
    RED = "RED"  # never auto-fill


SENSITIVE_FIELD_PATTERNS = (
    "ssn",
    "social security",
    "disability",
    "veteran",
    "race",
    "ethnicity",
    "gender",
    "sexual orientation",
    "criminal",
    "conviction",
    "immigration",
    "visa",
    "work authorization",
    "citizenship",
    "salary",
    "compensation",
    "password",
    "otp",
    "mfa",
    "captcha",
)


@dataclass
class MappedField:
    name: str
    label: str
    value: str | None
    confidence: FieldConfidence
    reason: str = ""


@dataclass
class FormInspectionResult:
    url: str
    fields: list[MappedField] = field(default_factory=list)
    blocked_reason: str | None = None
    requires_manual: bool = False


def classify_field(label: str, name: str = "") -> FieldConfidence:
    text = f"{label} {name}".lower()
    if any(p in text for p in SENSITIVE_FIELD_PATTERNS):
        return FieldConfidence.RED
    if any(k in text for k in ("email", "phone", "first name", "last name", "full name", "city", "linkedin")):
        return FieldConfidence.GREEN
    if any(k in text for k in ("cover letter", "why", "experience", "tell us", "describe")):
        return FieldConfidence.YELLOW
    return FieldConfidence.YELLOW


def map_profile_to_fields(profile: dict[str, Any], field_labels: list[str]) -> list[MappedField]:
    mapped: list[MappedField] = []
    for label in field_labels:
        conf = classify_field(label)
        value = None
        reason = ""
        lower = label.lower()
        if "email" in lower:
            value = profile.get("email")
            reason = "Verified profile email"
        elif "phone" in lower:
            value = profile.get("phone")
            reason = "Verified profile phone"
        elif "name" in lower:
            value = profile.get("full_name")
            reason = "Verified profile name"
        elif "location" in lower or "city" in lower:
            value = profile.get("location")
            reason = "Verified profile location"
        if conf == FieldConfidence.RED:
            value = None
            reason = "Sensitive field — manual review required"
        mapped.append(MappedField(name=label, label=label, value=value, confidence=conf, reason=reason))
    return mapped


async def inspect_application_page(url: str) -> FormInspectionResult:
    """Open page with Playwright when available; never bypass security controls."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return FormInspectionResult(
            url=url,
            requires_manual=True,
            blocked_reason="Playwright not installed — open the official URL manually",
        )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        content = (await page.content()).lower()
        if "captcha" in content or "recaptcha" in content or "hcaptcha" in content:
            await browser.close()
            return FormInspectionResult(
                url=url,
                requires_manual=True,
                blocked_reason="CAPTCHA detected — complete it manually, then continue",
            )
        if any(x in content for x in ("two-factor", "mfa", "one-time", "otp", "verify your identity")):
            await browser.close()
            return FormInspectionResult(
                url=url,
                requires_manual=True,
                blocked_reason="MFA/OTP detected — complete it manually",
            )
        # Collect basic input labels without submitting
        labels = await page.eval_on_selector_all(
            "label",
            "els => els.map(e => (e.innerText || '').trim()).filter(Boolean).slice(0, 40)",
        )
        await browser.close()
        return FormInspectionResult(url=url, fields=[MappedField(name=l, label=l, value=None, confidence=classify_field(l)) for l in labels])

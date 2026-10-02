from fontguard.core.config import Policy
from fontguard.core.models import DetectedFont, RiskLevel, RiskResult
from fontguard.identity import normalize_font_name


def evaluate_policy(font: DetectedFont, policy: Policy) -> RiskResult | None:
    def policy_name(value: str) -> str:
        return normalize_font_name(value, preserve_locale=True)

    names = {policy_name(font.canonical_name), policy_name(font.font_family)}
    if font.identity:
        names.update(policy_name(a) for a in font.identity.aliases)
    if names & {policy_name(n) for n in policy.denied_fonts}:
        return RiskResult(
            risk_level=RiskLevel.HIGH,
            reason="Font denied by organization policy.",
            rule="denied-font",
        )
    if policy.allowed_fonts and not names & {policy_name(n) for n in policy.allowed_fonts}:
        return RiskResult(
            risk_level=RiskLevel.HIGH,
            reason="Font is outside the organization font allowlist.",
            rule="font-not-allowed",
        )
    if (
        policy.allowed_licenses
        and font.license.type != "Unknown"
        and (font.license.type not in policy.allowed_licenses)
    ):
        return RiskResult(
            risk_level=RiskLevel.HIGH,
            reason="License is outside the organization license allowlist.",
            rule="license-not-allowed",
        )
    if font.risk_level == RiskLevel.UNKNOWN and policy.unknown_font.action != "unknown":
        return RiskResult(
            risk_level=RiskLevel(policy.unknown_font.action.upper()),
            reason="Unknown font escalated by organization policy.",
            rule="unknown-font-policy",
        )
    return None

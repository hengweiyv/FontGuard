from fontguard.core.models import LicenseEvaluation, RiskLevel, UsageContext
from fontguard.database.loader import FontRecord


def evaluate_license(font: FontRecord | None, usage_context: UsageContext) -> LicenseEvaluation:
    if font is None:
        return LicenseEvaluation(
            status="unknown",
            risk=RiskLevel.UNKNOWN,
            reason="Font identity or license cannot be confirmed.",
        )
    if usage_context == UsageContext.UNKNOWN:
        return LicenseEvaluation(
            status="usage_unknown",
            risk=RiskLevel.REVIEW,
            reason="Font identified; specify --usage to evaluate license permissions.",
            sources=font.sources,
        )
    permission = font.usage.get(usage_context, "unknown")
    mapping = {
        "allowed": (RiskLevel.SAFE, "Recorded license permits this usage."),
        "conditional": (RiskLevel.LOW, "Usage permitted subject to license conditions."),
        "requires_license": (
            RiskLevel.REVIEW,
            "Commercial font detected. License ownership "
            "cannot be determined automatically; verify your license.",
        ),
        "denied": (RiskLevel.HIGH, "Recorded license permissions conflict with this usage."),
        "unknown": (RiskLevel.UNKNOWN, "License permissions for this usage are unconfirmed."),
    }
    risk, reason = mapping[permission]
    return LicenseEvaluation(
        status=permission,
        risk=risk,
        reason=reason,
        evidence=font.license.conditions,
        sources=font.sources,
    )

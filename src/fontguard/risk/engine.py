from fontguard.core.config import Policy
from fontguard.core.models import DetectedFont, RiskLevel
from fontguard.database.loader import FontDatabase
from fontguard.identity import FontIdentityEngine, normalize_font_name
from fontguard.licenses.engine import evaluate_license
from fontguard.policy.engine import evaluate_policy


def evaluate_font(font: DetectedFont, database: FontDatabase, policy: Policy) -> DetectedFont:
    font.normalized_name = normalize_font_name(font.font_family)
    identity, record = FontIdentityEngine(database).identify(font)
    font.identity = identity
    font.canonical_name = identity.canonical_name
    font.confidence = identity.confidence
    font.vendor = identity.vendor or font.vendor
    if record:
        font.license = record.license.model_copy(deep=True)
        font.sources = record.sources
        font.verified_at = str(record.verified_at)
    evaluation = evaluate_license(record, font.usage_context)
    font.risk_level, font.risk_reason = evaluation.risk, evaluation.reason
    font.rule = "license-" + evaluation.status
    if font.detection_method == "font_path_reference":
        font.risk_level = RiskLevel.UNKNOWN
        font.risk_reason = "Filename reference only; font identity has not been verified."
        font.rule = "unverified-reference"
    # Name tables are self-reported, not cryptographic proof of provenance.
    if record and identity.match_method != "sha256":
        font.risk_reason += " Identity matched by name; verify provenance of the actual font."
    override = evaluate_policy(font, policy)
    if override:
        font.risk_level, font.risk_reason, font.rule = (
            override.risk_level,
            override.reason,
            override.rule,
        )
    return font

from pathlib import Path
from shutil import copy2, copytree

import pytest
import yaml

from fontguard.core.config import Config, Policy, UnknownRule, failure_levels
from fontguard.core.models import DetectedFont, RiskLevel, UsageContext
from fontguard.database.loader import FontDatabase, default_data_path
from fontguard.identity import FontIdentityEngine, normalize_font_name
from fontguard.licenses.engine import evaluate_license
from fontguard.risk.engine import evaluate_font


@pytest.mark.parametrize(
    "name",
    [
        "Source Han Sans CN",
        "SourceHanSansSC-Regular",
        "ABCDEF+SourceHanSansCN-Bold",
        "Source_Han_Sans_TC.woff2",
        "SOURCE-HAN-SANS Light",
    ],
)
def test_normalization(name: str) -> None:
    assert normalize_font_name(name) == "sourcehansans"


def test_chinese_alias_and_hash_precedence() -> None:
    db = FontDatabase()
    db.hashes["a" * 64] = db.records[0]
    raw = DetectedFont(
        source_file="a.ttf",
        font_family="Renamed",
        sha256="a" * 64,
        detection_method="font_metadata",
    )
    identity, record = FontIdentityEngine(db).identify(raw)
    assert record and identity.match_method == "sha256"
    raw.sha256 = None
    raw.font_family = "思源黑體"
    assert FontIdentityEngine(db).identify(raw)[0].canonical_name == "Source Han Sans"


def test_camel_case_weight_suffixes() -> None:
    assert normalize_font_name("NotoSans-SemiBold") == "notosans"
    assert normalize_font_name("SourceHanSansSC-ExtraLight") == "sourcehansans"


def test_license_usage_permissions() -> None:
    db = FontDatabase()
    font = next(f for f in db.records if f.id == "source-han-sans")
    assert evaluate_license(font, UsageContext.COMMERCIAL_DESIGN).risk == RiskLevel.SAFE
    assert evaluate_license(font, UsageContext.WEBFONT).risk == RiskLevel.LOW
    assert evaluate_license(font, UsageContext.UNKNOWN).risk == RiskLevel.REVIEW
    commercial = font.model_copy(deep=True)
    commercial.usage[UsageContext.LOGO] = "requires_license"
    result = evaluate_license(commercial, UsageContext.LOGO)
    assert result.risk == RiskLevel.REVIEW
    assert "ownership" in result.reason
    commercial.usage[UsageContext.LOGO] = "denied"
    assert evaluate_license(commercial, UsageContext.LOGO).risk == RiskLevel.HIGH


def test_policy_denial_overrides_allowed_name() -> None:
    raw = DetectedFont(
        source_file="a.css",
        font_family="Noto Sans",
        detection_method="web_declaration",
        usage_context=UsageContext.PERSONAL,
    )
    font = evaluate_font(
        raw, FontDatabase(), Policy(allowed_fonts=["Noto Sans"], denied_fonts=["NotoSans"])
    )
    assert font.risk_level == RiskLevel.HIGH
    assert font.rule == "denied-font"


def test_unknown_action_and_license_policy() -> None:
    unknown = DetectedFont(
        source_file="a.css", font_family="Random", detection_method="web_declaration"
    )
    assert (
        evaluate_font(
            unknown, FontDatabase(), Policy(unknown_font=UnknownRule(action="review"))
        ).risk_level
        == RiskLevel.REVIEW
    )
    known = unknown.model_copy(update={"font_family": "Noto Sans"})
    assert (
        evaluate_font(known, FontDatabase(), Policy(allowed_licenses=["Apache-2.0"])).risk_level
        == RiskLevel.HIGH
    )


def test_thresholds_unknown_is_independent() -> None:
    assert failure_levels([RiskLevel.HIGH]) == {RiskLevel.HIGH}
    assert failure_levels([RiskLevel.REVIEW]) == {RiskLevel.REVIEW, RiskLevel.HIGH}
    assert failure_levels([RiskLevel.UNKNOWN]) == {RiskLevel.UNKNOWN}
    assert failure_levels([RiskLevel.HIGH, RiskLevel.UNKNOWN]) == {
        RiskLevel.HIGH,
        RiskLevel.UNKNOWN,
    }


@pytest.mark.parametrize(
    "mutation,match",
    [
        ({"id": "noto-sans"}, "Duplicate font ID"),
        ({"aliases": ["NotoSans"]}, "Duplicate alias"),
        ({"license": {"type": "Fake"}}, "Invalid license"),
        ({"hashes": ["broken"]}, "Malformed SHA256"),
        ({"sources": []}, "at least 1"),
        ({"unexpected": True}, "Extra inputs"),
    ],
)
def test_database_validation_rejects_bad_records(tmp_path: Path, mutation, match) -> None:
    directory = tmp_path / "data"
    source = default_data_path()
    copytree(source / "licenses", directory / "licenses")
    copytree(source / "vendors", directory / "vendors")
    (directory / "fonts").mkdir()
    for filename in ("source-han-sans.yaml", "noto-sans.yaml"):
        copy2(source / "fonts" / filename, directory / "fonts" / filename)
    path = directory / "fonts" / "source-han-sans.yaml"
    record = yaml.safe_load(path.read_text(encoding="utf-8"))
    record.update(mutation)
    path.write_text(yaml.safe_dump(record, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        FontDatabase(directory)


def test_config_schema_rejects_typos() -> None:
    with pytest.raises(ValueError):
        Config.model_validate({"version": 2})
    with pytest.raises(ValueError):
        Config.model_validate({"policy": {"allow_licenses": ["OFL-1.1"]}})

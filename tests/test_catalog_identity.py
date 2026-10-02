from pathlib import Path

from fontguard.core.config import Config, Policy
from fontguard.core.models import DetectedFont, RiskLevel, UsageContext
from fontguard.core.records import create_baseline
from fontguard.core.scanner import Scanner
from fontguard.database.loader import FontDatabase
from fontguard.identity import FontIdentityEngine


def test_locale_specific_families_remain_distinct() -> None:
    db = FontDatabase()
    engine = FontIdentityEngine(db)
    for value, expected in [
        ("NotoSans-Regular", "Noto Sans"),
        ("NotoSansSC-Regular", "Noto Sans SC"),
        ("NotoSansTC-Bold", "Noto Sans TC"),
    ]:
        raw = DetectedFont(
            source_file="poster.pdf", font_family=value, detection_method="pdf_metadata"
        )
        assert engine.identify(raw)[0].canonical_name == expected


def test_catalog_has_licenses_sources_and_no_invented_hashes() -> None:
    db = FontDatabase()
    assert len(db.records) >= 2000
    assert {"OFL-1.1", "Apache-2.0", "Ubuntu-font-1.0"} <= {f.license.type for f in db.records}
    assert all(f.sources and f.verified_at for f in db.records)


def test_locale_change_is_new_baseline_finding(tmp_path: Path) -> None:
    css = tmp_path / "site.css"
    css.write_text('body {font-family: "Noto Sans SC"}', encoding="utf-8")
    scanner = Scanner(cache=False)
    baseline = tmp_path / "baseline.json"
    create_baseline(scanner.scan(css), baseline)
    css.write_text('body {font-family: "Noto Sans TC"}', encoding="utf-8")
    result = scanner.scan(css, baseline=baseline, fail_on=[RiskLevel.REVIEW])
    assert result.exit_code == 1 and not result.fonts[0].baselined


def test_policy_and_dedup_do_not_confuse_regional_families(tmp_path: Path) -> None:
    css = tmp_path / "site.css"
    css.write_text('body {font-family: "Noto Sans", "Noto Sans SC"}', encoding="utf-8")
    scanner = Scanner(cache=False, config=Config(policy=Policy(denied_fonts=["Noto Sans"])))
    result = scanner.scan(css, usage=UsageContext.COMMERCIAL_DESIGN)
    risks = {f.canonical_name: f.risk_level for f in result.fonts}
    assert risks == {"Noto Sans": RiskLevel.HIGH, "Noto Sans SC": RiskLevel.SAFE}

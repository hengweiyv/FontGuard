import json
from pathlib import Path

import jsonschema

from fontguard.core.models import UsageContext
from fontguard.core.records import create_baseline
from fontguard.core.scanner import Scanner
from fontguard.reporters.sarif import render_sarif


def test_full_sarif_schema_and_baseline(tmp_path: Path) -> None:
    (tmp_path / "site.css").write_text('body {font-family: "Unknown Brand"}', encoding="utf-8")
    scanner = Scanner(cache=False)
    result = scanner.scan(tmp_path, usage=UsageContext.WEBFONT)
    baseline = tmp_path / "baseline.json"
    create_baseline(result, baseline)
    result = scanner.scan(tmp_path, usage=UsageContext.WEBFONT, baseline=baseline)
    schema = json.loads(
        (Path(__file__).parent / "schemas" / "sarif-2.1.0.json").read_text(encoding="utf-8")
    )
    jsonschema.Draft7Validator(schema).validate(json.loads(render_sarif(result)))

import json
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import quote

from fontguard.core.models import RiskLevel, ScanResult


def render_sarif(result: ScanResult) -> str:
    rules: dict[str, dict[str, Any]] = {}
    results = []
    for font in result.fonts:
        if font.risk_level == RiskLevel.SAFE:
            continue
        rule_id = "fontguard/" + font.rule
        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "shortDescription": {"text": font.rule},
                "fullDescription": {"text": "Potential font licensing or policy risk."},
            }
        locations = []
        for evidence in font.evidence:
            physical: dict[str, Any] = {
                "artifactLocation": {
                    "uri": quote(PurePosixPath(font.source_file).as_posix(), safe="/"),
                    "uriBaseId": "%SRCROOT%",
                }
            }
            if evidence.line is not None:
                physical["region"] = {"startLine": evidence.line}
            location = {"physicalLocation": physical}
            if location not in locations:
                locations.append(location)
        if not locations:
            locations = [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": quote(font.source_file, safe="/"),
                            "uriBaseId": "%SRCROOT%",
                        }
                    }
                }
            ]
        entry: dict[str, Any] = {
            "ruleId": rule_id,
            "level": "error"
            if font.risk_level == RiskLevel.HIGH
            else ("note" if font.risk_level == RiskLevel.LOW else "warning"),
            "message": {"text": f"{font.canonical_name}: {font.risk_reason}"},
            "locations": locations,
            "partialFingerprints": {"fontguard/v1": font.fingerprint},
            "properties": {
                "risk": font.risk_level.value,
                "license": font.license.type,
                "usage": font.usage_context.value,
                "embedded": font.embedded,
                "confidence": font.confidence,
                "evidence": [e.model_dump() for e in font.evidence],
                "sources": [s.model_dump() for s in font.sources],
            },
        }
        if font.baselined:
            entry["baselineState"] = "unchanged"
            entry["suppressions"] = [
                {
                    "kind": "external",
                    "status": "accepted",
                    "justification": "Recorded in organization baseline.",
                }
            ]
        results.append(entry)
    notifications = [
        {
            "level": "error" if d.severity == "error" else "warning",
            "message": {"text": f"{d.file}: {d.message}"},
        }
        for d in result.diagnostics
    ]
    payload = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "FontGuard",
                        "version": result.tool_version,
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
                "invocations": [
                    {
                        "executionSuccessful": result.status != "error",
                        "exitCode": result.exit_code,
                        "toolExecutionNotifications": notifications,
                    }
                ],
            }
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

"""Versioned local baseline and organization approval records."""

import hashlib
import json
import re
from pathlib import Path

import yaml
from pydantic import Field

from fontguard.core.models import DetectedFont, Model, ScanResult, UsageContext
from fontguard.identity.engine import exact_font_name


class Baseline(Model):
    version: int = Field(default=1, ge=1, le=1)
    fingerprints: list[str]


class Approval(Model):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reason: str = Field(min_length=1)
    approved_by: str = Field(min_length=1)
    usages: list[UsageContext] = Field(min_length=1)


class ApprovalFile(Model):
    version: int = Field(default=1, ge=1, le=1)
    approved_fonts: list[Approval] = Field(default_factory=list)


def fingerprint(font: DetectedFont) -> str:
    data = [
        font.source_file,
        font.sha256
        or (font.identity.database_id if font.identity else None)
        or exact_font_name(font.font_family),
        font.rule,
        font.risk_level,
        font.usage_context,
        font.license.type,
    ]
    return hashlib.sha256(json.dumps(data, ensure_ascii=False).encode()).hexdigest()


def read_baseline(path: Path | None) -> set[str]:
    if path is None:
        return set()
    baseline = Baseline.model_validate_json(path.read_text(encoding="utf-8"))
    if any(not re.fullmatch(r"[0-9a-f]{64}", v) for v in baseline.fingerprints):
        raise ValueError("Malformed baseline fingerprint.")
    return set(baseline.fingerprints)


def create_baseline(result: ScanResult, path: Path) -> None:
    if result.diagnostics and any(d.severity == "error" for d in result.diagnostics):
        raise ValueError("Cannot baseline an incomplete scan.")
    baseline = Baseline(
        fingerprints=sorted({f.fingerprint for f in result.fonts if f.risk_level != "SAFE"})
    )
    path.write_text(baseline.model_dump_json(indent=2) + "\n", encoding="utf-8")


def read_approvals(path: Path) -> ApprovalFile:
    if not path.exists():
        return ApprovalFile()
    return ApprovalFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))

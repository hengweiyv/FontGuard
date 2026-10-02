"""Versioned data contracts shared by analyzers, policy and reporters."""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from fontguard import __version__


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RiskLevel(StrEnum):
    SAFE = "SAFE"
    LOW = "LOW"
    REVIEW = "REVIEW"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class UsageContext(StrEnum):
    UNKNOWN = "unknown"
    PERSONAL = "personal"
    COMMERCIAL_DESIGN = "commercial_design"
    PRINT = "print"
    ADVERTISING = "advertising"
    WEBSITE = "website"
    WEBFONT = "webfont"
    VIDEO = "video"
    LOGO = "logo"
    EBOOK = "ebook"
    DOCUMENT_EMBEDDING = "document_embedding"
    APP_EMBEDDING = "app_embedding"
    SOFTWARE_DISTRIBUTION = "software_distribution"
    FONT_REDISTRIBUTION = "font_redistribution"


class Source(Model):
    type: Literal[
        "official_license",
        "official_repository",
        "official_vendor",
        "official_documentation",
        "third_party",
    ]
    url: str = Field(pattern=r"^https?://")


class FontMetadata(Model):
    family: str = ""
    full_name: str = ""
    postscript_name: str = ""
    manufacturer: str = ""
    version: str = ""
    raw_names: dict[str, list[str]] = Field(default_factory=dict)
    fs_type: int | None = None


class FontIdentity(Model):
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    vendor: str = ""
    confidence: float = Field(default=0, ge=0, le=1)
    match_method: str = "unmatched"
    database_id: str | None = None


class LicenseInfo(Model):
    type: str = "Unknown"
    conditions: list[str] = Field(default_factory=list)


class Evidence(Model):
    type: str
    file: str
    raw_font_name: str = ""
    page: int | None = None
    line: int | None = None
    member: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class LicenseEvaluation(Model):
    status: str
    risk: RiskLevel
    reason: str
    evidence: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)


class RiskResult(Model):
    risk_level: RiskLevel
    reason: str
    rule: str


class DetectedFont(Model):
    source_file: str
    font_family: str
    normalized_name: str = ""
    canonical_name: str = ""
    postscript_name: str = ""
    vendor: str = ""
    version: str = ""
    sha256: str | None = None
    detection_method: str
    confidence: float = Field(default=0, ge=0, le=1)
    embedded: bool | None = None
    subset: bool | None = None
    usage_context: UsageContext = UsageContext.UNKNOWN
    metadata: FontMetadata | None = None
    identity: FontIdentity | None = None
    license: LicenseInfo = Field(default_factory=LicenseInfo)
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    risk_reason: str = "Font identity or license is unknown."
    rule: str = "unknown-license"
    evidence: list[Evidence] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    verified_at: str | None = None
    fingerprint: str = ""
    baselined: bool = False
    approval: dict[str, str] | None = None


class Diagnostic(Model):
    file: str
    message: str
    severity: Literal["error", "warning"] = "error"


class AnalysisResult(Model):
    fonts: list[DetectedFont] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class ScanResult(Model):
    schema_version: str = "1.0"
    tool_version: str = __version__
    root: str
    status: Literal["passed", "failed", "error"] = "passed"
    files_scanned: int = 0
    cache_hits: int = 0
    summary: dict[str, int] = Field(default_factory=dict)
    fonts: list[DetectedFont] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)

    @property
    def exit_code(self) -> int:
        return {"passed": 0, "failed": 1, "error": 2}[self.status]

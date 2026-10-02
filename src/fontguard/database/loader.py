import re
from datetime import date
from importlib.resources import files
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field

from fontguard.core.models import LicenseInfo, Model, Source, UsageContext

SAFE_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def read_yaml(path: Path) -> object:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=SAFE_LOADER)


class FontRecord(Model):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    vendor: str = Field(min_length=1)
    license: LicenseInfo
    usage: dict[
        UsageContext, Literal["allowed", "conditional", "requires_license", "denied", "unknown"]
    ]
    sources: list[Source] = Field(min_length=1)
    verified_at: date
    hashes: list[str] = Field(default_factory=list)


class LicenseRecord(Model):
    id: str
    name: str
    sources: list[Source] = Field(min_length=1)


class VendorRecord(Model):
    id: str
    name: str
    url: str = Field(pattern=r"^https?://")


def default_data_path() -> Path:
    packaged = Path(str(files("fontguard").joinpath("data")))
    if packaged.is_dir():
        return packaged
    return Path(__file__).resolve().parents[3] / "data"


class FontDatabase:
    def __init__(self, path: Path | None = None) -> None:
        from fontguard.identity.engine import exact_font_name, normalize_font_name

        self.path = path or default_data_path()
        self.records: list[FontRecord] = []
        self.names: dict[str, FontRecord] = {}
        self.exact_names: dict[str, FontRecord] = {}
        self.styled_names: dict[str, FontRecord] = {}
        self.ambiguous_names: set[str] = set()
        ambiguous_styles: set[str] = set()
        self.hashes: dict[str, FontRecord] = {}
        if not (self.path / "fonts").is_dir():
            raise ValueError(f"Database fonts directory missing: {self.path}")
        licenses: dict[str, LicenseRecord] = {}
        for file in sorted((self.path / "licenses").rglob("*.yaml")):
            record = LicenseRecord.model_validate(read_yaml(file))
            if record.id in licenses:
                raise ValueError(f"Duplicate license ID: {record.id}")
            licenses[record.id] = record
        vendors: set[str] = set()
        for file in sorted((self.path / "vendors").rglob("*.yaml")):
            vendor = VendorRecord.model_validate(read_yaml(file))
            if vendor.name in vendors:
                raise ValueError(f"Duplicate vendor: {vendor.name}")
            vendors.add(vendor.name)
        ids: set[str] = set()
        for file in sorted((self.path / "fonts").rglob("*.yaml")):
            font = FontRecord.model_validate(read_yaml(file))
            if font.id in ids:
                raise ValueError(f"Duplicate font ID: {font.id}")
            if font.license.type not in licenses:
                raise ValueError(f"Invalid license: {font.license.type}")
            if font.vendor not in vendors:
                raise ValueError(f"Missing vendor: {font.vendor}")
            if font.verified_at > date.today():
                raise ValueError(f"Future verification date: {font.id}")
            ids.add(font.id)
            for alias in [font.name, *font.aliases]:
                literal = exact_font_name(alias)
                if literal in self.exact_names and self.exact_names[literal].id != font.id:
                    raise ValueError(f"Duplicate alias: {alias}")
                self.exact_names[literal] = font
                styled = normalize_font_name(alias, preserve_locale=True)
                if styled in self.styled_names and self.styled_names[styled].id != font.id:
                    ambiguous_styles.add(styled)
                    del self.styled_names[styled]
                elif styled not in ambiguous_styles:
                    self.styled_names[styled] = font
                key = normalize_font_name(alias)
                if not key:
                    raise ValueError(f"Empty normalized alias: {alias}")
                if key in self.names and self.names[key].id != font.id:
                    self.ambiguous_names.add(key)
                    del self.names[key]
                elif key not in self.ambiguous_names:
                    self.names[key] = font
            for digest in font.hashes:
                if not re.fullmatch(r"[0-9a-f]{64}", digest):
                    raise ValueError(f"Malformed SHA256: {font.id}")
                if digest in self.hashes:
                    raise ValueError(f"Duplicate hash: {digest}")
                self.hashes[digest] = font
            self.records.append(font)
        if not self.records:
            raise ValueError("Database must contain at least one font record.")

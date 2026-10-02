from io import BytesIO
from pathlib import Path
from typing import Any

from fontTools.ttLib import TTFont

from fontguard.analyzers.base import Analyzer
from fontguard.core.models import AnalysisResult, DetectedFont, Evidence, FontMetadata
from fontguard.utils.hashing import file_sha256

NAME_IDS = (0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 13, 14, 16, 17)


def extract_metadata(font: Any) -> FontMetadata:
    raw: dict[str, list[str]] = {}
    for record in font["name"].names:
        if record.nameID in NAME_IDS:
            value = record.toUnicode(errors="replace").strip()
            values = raw.setdefault(str(record.nameID), [])
            if value and value not in values:
                values.append(value)

    def name(key: int) -> str:
        # Prefer an English record for stable matching; preserve all locales above.
        for record in font["name"].names:
            if record.nameID == key and record.langID in (0x409, 0):
                return str(record.toUnicode(errors="replace")).strip()
        return next(iter(raw.get(str(key), [])), "")

    return FontMetadata(
        family=name(16) or name(1),
        full_name=name(4),
        postscript_name=name(6),
        manufacturer=name(8),
        version=name(5),
        raw_names=raw,
        fs_type=int(font["OS/2"].fsType) if "OS/2" in font else None,
    )


class FontFileAnalyzer(Analyzer):
    extensions = frozenset({".ttf", ".otf", ".woff", ".woff2"})

    def analyze(self, path: Path) -> AnalysisResult:
        with TTFont(str(path), lazy=True) as font:
            metadata = extract_metadata(font)
        return AnalysisResult(
            fonts=[
                DetectedFont(
                    source_file=str(path),
                    font_family=metadata.family or metadata.full_name or path.stem,
                    postscript_name=metadata.postscript_name,
                    vendor=metadata.manufacturer,
                    version=metadata.version,
                    sha256=file_sha256(path),
                    metadata=metadata,
                    detection_method="font_metadata",
                    evidence=[
                        Evidence(
                            type="opentype_name_table",
                            file=str(path),
                            raw_font_name=metadata.family,
                            details={"raw_names": metadata.raw_names, "fs_type": metadata.fs_type},
                        )
                    ],
                )
            ]
        )

    @staticmethod
    def metadata_from_bytes(data: bytes) -> FontMetadata:
        with TTFont(BytesIO(data), lazy=True) as font:
            return extract_metadata(font)

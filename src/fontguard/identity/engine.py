import re
import unicodedata

from fontguard.core.models import DetectedFont, FontIdentity
from fontguard.database.loader import FontDatabase, FontRecord


def normalize_font_name(name: str, *, preserve_locale: bool = False) -> str:
    value = unicodedata.normalize("NFKC", name).strip().strip("\"'")
    value = re.sub(r"^[A-Z]{6}\+", "", value)
    value = re.sub(r"\.(ttf|otf|woff2?)$", "", value, flags=re.I)
    # Split PostScript camel-case before removing style and locale tokens.
    value = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    value = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", value)
    value = value.casefold().replace("體", "体")
    value = re.sub(r"[\s_-]+", " ", value)
    value = re.sub(r"\b(?:semi|demi|extra|ultra)\s+(?:bold|light|thin)\b", "", value)
    tokens = (
        r"regular|bold|light|medium|italic|oblique|thin|black|heavy|"
        r"semibold|demibold|extralight|extrabold"
    )
    if not preserve_locale:
        tokens += r"|cn|sc|tc|hk|jp|kr"
    value = re.sub(
        rf"\b({tokens})\b",
        "",
        value,
    )
    return re.sub(r"[\s_-]+", "", value)


def exact_font_name(name: str) -> str:
    """Compare literal names without discarding meaningful family/locale tokens."""
    value = unicodedata.normalize("NFKC", name).strip().strip("\"'").casefold()
    value = re.sub(r"^[a-z]{6}\+", "", value)
    value = re.sub(r"\.(ttf|otf|woff2?)$", "", value)
    return re.sub(r"[\s_-]+", "", value).replace("體", "体")


class FontIdentityEngine:
    def __init__(self, database: FontDatabase) -> None:
        self.database = database

    def identify(self, font: DetectedFont) -> tuple[FontIdentity, FontRecord | None]:
        if font.sha256 and font.sha256 in self.database.hashes:
            record = self.database.hashes[font.sha256]
            return self._identity(record, "sha256", 1.0), record
        metadata = font.metadata
        candidates = [
            (metadata.postscript_name if metadata else font.postscript_name, "postscript", 0.98),
            (metadata.full_name if metadata else "", "full_name", 0.95),
            (metadata.family if metadata else font.font_family, "family", 0.90),
            (font.font_family, "alias", 0.85),
        ]
        for value, method, confidence in candidates:
            if not value:
                continue
            candidate = self.database.exact_names.get(exact_font_name(value))
            if candidate is None:
                candidate = self.database.styled_names.get(
                    normalize_font_name(value, preserve_locale=True)
                )
            if candidate is None:
                candidate = self.database.names.get(normalize_font_name(value))
            if candidate:
                return self._identity(candidate, method, confidence), candidate
        return FontIdentity(canonical_name=font.font_family, vendor=font.vendor), None

    @staticmethod
    def _identity(record: FontRecord, method: str, confidence: float) -> FontIdentity:
        return FontIdentity(
            canonical_name=record.name,
            aliases=record.aliases,
            vendor=record.vendor,
            confidence=confidence,
            match_method=method,
            database_id=record.id,
        )

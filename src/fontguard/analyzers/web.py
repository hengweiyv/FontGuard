import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from fontguard.analyzers.base import Analyzer
from fontguard.analyzers.font_file import FontFileAnalyzer
from fontguard.core.models import AnalysisResult, DetectedFont, Diagnostic, Evidence

GENERICS = {
    "serif",
    "sans-serif",
    "monospace",
    "cursive",
    "fantasy",
    "system-ui",
    "inherit",
    "initial",
    "unset",
    "revert",
    "revert-layer",
    "ui-serif",
    "ui-sans-serif",
    "ui-monospace",
    "ui-rounded",
    "emoji",
    "math",
    "fangsong",
}
FAMILY = re.compile(r"font-family\s*:\s*([^;}\n]+)|\bfontFamily\s*:\s*([\"'][^\n]+?[\"'])", re.I)
FACE = re.compile(r"@font-face\s*\{([^}]+)\}", re.I | re.S)
URL = re.compile(r"url\(\s*([\"']?)(.*?)\1\s*\)", re.I | re.S)
INLINE_STYLE = re.compile(r"\bstyle\s*=\s*([\"'])(.*?)\1", re.I | re.S)


def families(value: str) -> list[str]:
    # Quoted family names may contain commas.
    tokens = re.findall(r'"([^"]+)"|\'([^\']+)\'|([^,]+)', value.strip())
    names = [next(part for part in token if part).strip().strip("\"'") for token in tokens]
    return [
        name
        for name in names
        if name and name.casefold() not in GENERICS and not re.search(r"\b(var|env)\s*\(", name)
    ]


def analyze_text(
    path: Path, text: str, *, resolve_sources: bool = True, root: Path | None = None
) -> AnalysisResult:
    result = AnalysisResult()
    # Retain offsets for source lines while discarding CSS/HTML comments.
    text = re.sub(
        r"/\*.*?\*/|<!--.*?-->", lambda m: re.sub(r"[^\n]", " ", m.group()), text, flags=re.S
    )
    # HTML attributes can end without a CSS semicolon. Preserve source offsets
    # while terminating their CSS before the closing quote and following markup.
    text = INLINE_STYLE.sub(lambda match: match.group()[:-1] + ";", text)
    mapped_spans: list[tuple[int, int]] = []
    aliases: dict[str, list[DetectedFont]] = {}
    for face in FACE.finditer(text):
        family_match = FAMILY.search(face.group(1))
        alias = families(next(g for g in family_match.groups() if g)) if family_match else []
        resolved: list[DetectedFont] = []
        for url in URL.finditer(face.group(1)):
            raw = url.group(2).strip()
            parts = urlsplit(raw)
            if parts.scheme or parts.netloc or raw.startswith(("/", "#")):
                result.diagnostics.append(
                    Diagnostic(
                        file=str(path),
                        severity="warning",
                        message=f"Font URL not read locally: {raw}",
                    )
                )
                continue
            target = (path.parent / unquote(parts.path)).resolve()
            if target.suffix.lower() not in FontFileAnalyzer.extensions:
                continue
            if not resolve_sources:
                continue
            allowed_root = (root or path.parent).resolve()
            if not target.is_relative_to(allowed_root):
                result.diagnostics.append(
                    Diagnostic(
                        file=str(path),
                        severity="warning",
                        message=f"Font source outside scan root was not read: {raw}",
                    )
                )
                continue
            if not target.is_file() or target.is_symlink():
                result.diagnostics.append(
                    Diagnostic(file=str(path), message=f"Font source missing: {raw}")
                )
                continue
            if target.stat().st_size > 256 * 1024 * 1024:
                result.diagnostics.append(
                    Diagnostic(
                        file=str(path), message=f"Font source exceeds 256 MiB size limit: {raw}"
                    )
                )
                continue
            try:
                observations = FontFileAnalyzer().analyze(target)
            except Exception as exc:
                result.diagnostics.append(Diagnostic(file=str(path), message=f"{raw}: {exc}"))
                continue
            for font in observations.fonts:
                font.source_file = str(path)
                font.detection_method = "css_font_source"
                font.evidence.append(
                    Evidence(
                        type="css_font_face",
                        file=str(path),
                        raw_font_name=", ".join(alias),
                        line=text[: face.start()].count("\n") + 1,
                        details={"url": raw, "resolved_file": str(target)},
                    )
                )
                resolved.append(font)
        if resolved:
            mapped_spans.append(face.span())
            result.fonts.extend(resolved)
            for name in alias:
                aliases[name.casefold()] = resolved
    for match in FAMILY.finditer(text):
        if any(start <= match.start() < end for start, end in mapped_spans):
            continue
        value = next(g for g in match.groups() if g)
        for name in families(value):
            if name.casefold() in aliases:
                for resolved_font in aliases[name.casefold()]:
                    resolved_font.evidence.append(
                        Evidence(
                            type="css_alias_usage",
                            file=str(path),
                            raw_font_name=name,
                            line=text[: match.start()].count("\n") + 1,
                        )
                    )
                continue
            result.fonts.append(
                DetectedFont(
                    source_file=str(path),
                    font_family=name,
                    detection_method="web_declaration",
                    evidence=[
                        Evidence(
                            type="font_family_declaration",
                            file=str(path),
                            raw_font_name=name,
                            line=text[: match.start()].count("\n") + 1,
                            details={"declaration_only": True},
                        )
                    ],
                )
            )
    # Keep direct imports/references visible even without an @font-face rule.
    for match in re.finditer(
        r'["\']([^"\'\n]+\.(?:ttf|otf|woff2?)(?:\?[^"\']*)?)["\']', text, re.I
    ):
        if any(start <= match.start() < end for start, end in mapped_spans):
            continue
        name = Path(urlsplit(match.group(1)).path).stem
        result.fonts.append(
            DetectedFont(
                source_file=str(path),
                font_family=name,
                detection_method="font_path_reference",
                evidence=[
                    Evidence(
                        type="font_path_reference",
                        file=str(path),
                        raw_font_name=name,
                        line=text[: match.start()].count("\n") + 1,
                        details={"reference": match.group(1), "identity_unverified": True},
                    )
                ],
            )
        )
    return result


class CSSAnalyzer(Analyzer):
    extensions = frozenset({".css", ".scss", ".less"})

    def analyze(self, path: Path) -> AnalysisResult:
        return analyze_text(
            path, path.read_text(encoding="utf-8-sig", errors="strict"), resolve_sources=False
        )


class WebProjectAnalyzer(CSSAnalyzer):
    extensions = frozenset({".html", ".htm", ".vue", ".jsx", ".tsx", ".js", ".ts", ".svelte"})

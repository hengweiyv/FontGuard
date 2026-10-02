from pathlib import Path

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont


def make_font(path: Path, family: str = "Source Han Sans CN") -> Path:
    """Generate a tiny original font; no third-party font binaries in tests."""
    is_ttf = path.suffix != ".otf"
    builder = FontBuilder(1000, isTTF=is_ttf)
    glyphs = [".notdef", "space", "A"]
    builder.setupGlyphOrder(glyphs)
    builder.setupCharacterMap({32: "space", 65: "A"})
    builder.setupHorizontalMetrics({g: (600, 0) for g in glyphs})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable(
        {
            "familyName": family,
            "styleName": "Regular",
            "uniqueFontIdentifier": "FontGuard-Synthetic-1",
            "fullName": family + " Regular",
            "psName": family.replace(" ", "") + "-Regular",
            "version": "Version 1.0",
            "manufacturer": "FontGuard Synthetic Tests",
            "licenseDescription": "Synthetic fixture",
            "licenseInfoURL": "https://example.invalid/synthetic-license",
        }
    )
    builder.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    builder.setupPost()
    if is_ttf:
        outlines = {}
        for glyph in glyphs:
            pen = TTGlyphPen(None)
            if glyph == "A":
                pen.moveTo((100, 0))
                pen.lineTo((300, 700))
                pen.lineTo((500, 0))
                pen.closePath()
            outlines[glyph] = pen.glyph()
        builder.setupGlyf(outlines)
    else:
        outlines = {}
        for glyph in glyphs:
            pen = T2CharStringPen(600, None)
            if glyph == "A":
                pen.moveTo((100, 0))
                pen.lineTo((300, 700))
                pen.lineTo((500, 0))
                pen.closePath()
            outlines[glyph] = pen.getCharString()
        builder.setupCFF(family.replace(" ", ""), {"FullName": family}, outlines, {})
    builder.setupMaxp()
    path.parent.mkdir(parents=True, exist_ok=True)
    builder.save(str(path))
    if path.suffix in {".woff", ".woff2"}:
        with TTFont(path) as font:
            font.flavor = path.suffix[1:]
            font.save(path)
    return path


@pytest.fixture
def font_file(tmp_path: Path) -> Path:
    return make_font(tmp_path / "renamed-company-font.ttf")

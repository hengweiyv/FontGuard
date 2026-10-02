from pathlib import Path
from zipfile import ZipFile

import pymupdf
import pytest
from conftest import make_font

from fontguard.analyzers.docx import DOCXAnalyzer
from fontguard.analyzers.font_file import FontFileAnalyzer
from fontguard.analyzers.pdf import PDFAnalyzer
from fontguard.analyzers.pptx import PPTXAnalyzer
from fontguard.analyzers.svg import SVGAnalyzer
from fontguard.core.config import Config, Policy
from fontguard.core.models import UsageContext
from fontguard.core.scanner import Scanner


@pytest.mark.parametrize("suffix", [".ttf", ".otf", ".woff", ".woff2"])
def test_actual_font_formats(tmp_path: Path, suffix: str) -> None:
    file = make_font(tmp_path / ("arbitrary-name" + suffix))
    font = FontFileAnalyzer().analyze(file).fonts[0]
    assert font.font_family == "Source Han Sans CN"
    assert len(font.sha256) == 64
    assert font.metadata.raw_names["13"] == ["Synthetic fixture"]
    assert font.postscript_name == "SourceHanSansCN-Regular"


def test_real_pdf_metadata_and_embedding(tmp_path: Path, font_file: Path) -> None:
    path = tmp_path / "poster.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_font(fontname="brand", fontfile=str(font_file))
        page.insert_text((30, 30), "AAA", fontname="brand")
        page.insert_text((30, 60), "Standard PDF font")
        doc.save(str(path))
    result = PDFAnalyzer().analyze(path)
    assert any(f.embedded and f.metadata.family == "Source Han Sans CN" for f in result.fonts)
    assert any(f.font_family == "Helvetica" and f.embedded is False for f in result.fonts)
    assert all(f.evidence[0].page == 1 for f in result.fonts)


@pytest.mark.parametrize(
    "suffix,prefix,analyzer",
    [
        (".docx", "word", DOCXAnalyzer()),
        (".pptx", "ppt", PPTXAnalyzer()),
    ],
)
def test_office_theme_styles_and_asian_fonts(tmp_path: Path, suffix, prefix, analyzer) -> None:
    path = tmp_path / ("document" + suffix)
    with ZipFile(path, "w") as archive:
        archive.writestr(
            f"{prefix}/document.xml",
            '<root xmlns:w="urn:w"><w:rFonts w:ascii="Noto Sans" w:eastAsia="思源黑体"/></root>',
        )
        archive.writestr(f"{prefix}/theme/theme1.xml", '<root><font typeface="Brand Font"/></root>')
    result = analyzer.analyze(path)
    assert {f.font_family for f in result.fonts} == {"Noto Sans", "思源黑体", "Brand Font"}
    assert all(f.embedded is None for f in result.fonts)
    assert all(f.evidence[0].member for f in result.fonts)


def test_svg_styles_and_attributes(tmp_path: Path) -> None:
    file = tmp_path / "poster.svg"
    file.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><style>text { '
        'font-family: "Noto Sans", sans-serif; }</style><text font-family="思源黑体">'
        "A</text></svg>",
        encoding="utf-8",
    )
    assert {f.font_family for f in SVGAnalyzer().analyze(file).fonts} == {"Noto Sans", "思源黑体"}


def test_entity_expansion_rejected(tmp_path: Path) -> None:
    file = tmp_path / "bad.svg"
    file.write_text(
        '<!DOCTYPE svg [<!ENTITY e SYSTEM "file:///etc/passwd">]><svg>&e;</svg>', encoding="utf-8"
    )
    result = Scanner(cache=False).scan(file)
    assert result.exit_code == 2


def test_css_alias_resolves_real_font_and_cache_dependency(tmp_path: Path, font_file: Path) -> None:
    css = tmp_path / "site.css"
    css.write_text(
        '@font-face {font-family: "Brand"; src: url("renamed-company-font.ttf");}'
        '\nbody {font-family: "Brand", sans-serif;}',
        encoding="utf-8",
    )
    scanner = Scanner()
    result = scanner.scan(css, usage=UsageContext.WEBFONT)
    assert len(result.fonts) == 1
    assert result.fonts[0].canonical_name == "Source Han Sans"
    assert result.fonts[0].sha256
    assert any(e.type == "css_alias_usage" for e in result.fonts[0].evidence)
    assert scanner.scan(css).cache_hits == 1
    make_font(font_file, "New Unknown Font")
    changed = scanner.scan(css)
    assert changed.cache_hits == 0
    assert changed.fonts[0].canonical_name == "New Unknown Font"


@pytest.mark.parametrize(
    "extension", ["css", "scss", "less", "html", "vue", "js", "ts", "jsx", "tsx"]
)
def test_web_formats(tmp_path: Path, extension: str) -> None:
    file = tmp_path / ("component." + extension)
    file.write_text(
        'body {font-family: "Noto Sans", serif;}\n'
        'const style = {fontFamily: "Source Han Sans CN"};',
        encoding="utf-8",
    )
    result = Scanner(cache=False).scan(file)
    assert {f.canonical_name for f in result.fonts} == {"Noto Sans", "Source Han Sans"}


def test_remote_and_missing_font_sources(tmp_path: Path) -> None:
    file = tmp_path / "site.css"
    file.write_text(
        "@font-face { font-family: Remote; src: url(https://example.org/font.woff2); }"
        "@font-face { font-family: Missing; src: url(missing.ttf); }",
        encoding="utf-8",
    )
    result = Scanner(cache=False).scan(file)
    assert result.exit_code == 2
    assert any(
        d.severity == "warning" and "not read locally" in d.message for d in result.diagnostics
    )


@pytest.mark.parametrize(
    "markup,names",
    [
        ('<span style="font-family: Arial">Test</span>', {"Arial"}),
        ("<span style='font-family: Arial'>Test</span>", {"Arial"}),
        (
            "<span style=\"font-family: 'Noto Sans SC', Arial\">Test</span>",
            {"Noto Sans SC", "Arial"},
        ),
    ],
)
def test_inline_html_style_boundary_enforces_policy(tmp_path: Path, markup, names) -> None:
    file = tmp_path / "index.html"
    file.write_text("\n" + markup, encoding="utf-8")
    result = Scanner(config=Config(policy=Policy(denied_fonts=["Arial"])), cache=False).scan(file)
    assert {font.canonical_name for font in result.fonts} == names
    assert result.exit_code == 1
    assert all(font.evidence[0].line == 2 for font in result.fonts)


def test_font_reference_outside_root_not_opened(tmp_path: Path) -> None:
    css = tmp_path / "project" / "site.css"
    css.parent.mkdir()
    css.write_text("@font-face {font-family: External; src: url(../secret.ttf)}", encoding="utf-8")
    result = Scanner(cache=False).scan(css)
    assert any("outside scan root" in d.message for d in result.diagnostics)


def test_encrypted_pdf_is_scan_error(tmp_path: Path) -> None:
    file = tmp_path / "encrypted.pdf"
    with pymupdf.open() as doc:
        doc.new_page()
        doc.save(
            str(file), encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="owner"
        )
    assert Scanner(cache=False).scan(file).exit_code == 2

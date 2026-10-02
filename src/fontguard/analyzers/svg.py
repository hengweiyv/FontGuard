from pathlib import Path

from defusedxml import ElementTree

from fontguard.analyzers.base import Analyzer
from fontguard.analyzers.web import analyze_text, families
from fontguard.core.models import AnalysisResult, DetectedFont, Evidence


class SVGAnalyzer(Analyzer):
    extensions = frozenset({".svg"})

    def analyze(self, path: Path) -> AnalysisResult:
        text = path.read_text(encoding="utf-8-sig")
        root = ElementTree.fromstring(text)
        result: AnalysisResult = analyze_text(path, text, resolve_sources=False)
        for element in root.iter():
            for name in families(element.attrib.get("font-family", "")):
                result.fonts.append(
                    DetectedFont(
                        source_file=str(path),
                        font_family=name,
                        detection_method="svg_attribute",
                        evidence=[
                            Evidence(type="svg_attribute", file=str(path), raw_font_name=name)
                        ],
                    )
                )
        return result

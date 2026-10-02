from pathlib import Path

from fontguard.analyzers.base import Analyzer
from fontguard.core.models import AnalysisResult, DetectedFont
from fontguard.core.registry import AnalyzerRegistry
from fontguard.core.scanner import Scanner


class SubtitleAnalyzer(Analyzer):
    extensions = frozenset({".ass"})

    def analyze(self, path: Path) -> AnalysisResult:
        return AnalysisResult(
            fonts=[
                DetectedFont(
                    source_file=str(path),
                    font_family="Subtitle Test Font",
                    detection_method="test_subtitle",
                )
            ]
        )


def test_registered_analyzer_participates_in_scan(tmp_path: Path) -> None:
    file = tmp_path / "subtitle.ass"
    file.write_text("synthetic subtitle", encoding="utf-8")
    registry = AnalyzerRegistry.default()
    registry.register(SubtitleAnalyzer())
    result = Scanner(registry=registry, cache=False).scan(tmp_path)
    assert result.files_scanned == 1
    assert result.fonts[0].font_family == "Subtitle Test Font"
    assert result.fonts[0].risk_level == "UNKNOWN"


def test_registry_matching_is_case_insensitive_and_deterministic() -> None:
    registry = AnalyzerRegistry()
    first = SubtitleAnalyzer()
    registry.register(first)
    registry.register(SubtitleAnalyzer())
    assert registry.get(Path("x.ASS")) is first
    assert registry.get(Path("unknown.xyz")) is None

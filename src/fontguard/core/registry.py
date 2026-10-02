from importlib.metadata import entry_points
from pathlib import Path

from fontguard.analyzers.base import Analyzer


class AnalyzerRegistry:
    def __init__(self) -> None:
        self.analyzers: list[Analyzer] = []

    def register(self, analyzer: Analyzer) -> None:
        self.analyzers.append(analyzer)

    def get(self, path: Path) -> Analyzer | None:
        return next((a for a in self.analyzers if a.supports(path)), None)

    @classmethod
    def default(cls, *, plugins: bool = False) -> "AnalyzerRegistry":
        from fontguard.analyzers.docx import DOCXAnalyzer
        from fontguard.analyzers.font_file import FontFileAnalyzer
        from fontguard.analyzers.pdf import PDFAnalyzer
        from fontguard.analyzers.pptx import PPTXAnalyzer
        from fontguard.analyzers.svg import SVGAnalyzer
        from fontguard.analyzers.web import CSSAnalyzer, WebProjectAnalyzer

        registry = cls()
        for analyzer in (
            FontFileAnalyzer(),
            PDFAnalyzer(),
            DOCXAnalyzer(),
            PPTXAnalyzer(),
            SVGAnalyzer(),
            CSSAnalyzer(),
            WebProjectAnalyzer(),
        ):
            registry.register(analyzer)
        if plugins:
            for entry in entry_points(group="fontguard.analyzers"):
                analyzer = entry.load()()
                if not isinstance(analyzer, Analyzer):
                    raise ValueError(f"Invalid analyzer plugin: {entry.name}")
                registry.register(analyzer)
        return registry

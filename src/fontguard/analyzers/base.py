from abc import ABC, abstractmethod
from pathlib import Path

from fontguard.core.models import AnalysisResult


class Analyzer(ABC):
    """An analyzer must be stateless/thread-safe and perform no network requests."""

    extensions: frozenset[str] = frozenset()

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in self.extensions

    @abstractmethod
    def analyze(self, path: Path) -> AnalysisResult:
        """Return raw observations; policy is applied by the scanner."""

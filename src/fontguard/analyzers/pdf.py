import hashlib
import re
from pathlib import Path
from threading import Lock

import pymupdf

from fontguard.analyzers.base import Analyzer
from fontguard.analyzers.font_file import FontFileAnalyzer
from fontguard.core.models import AnalysisResult, DetectedFont, Evidence

PDF_LOCK = Lock()  # PyMuPDF explicitly does not support concurrent threads.


class PDFAnalyzer(Analyzer):
    extensions = frozenset({".pdf"})

    def analyze(self, path: Path) -> AnalysisResult:
        with PDF_LOCK:
            return self._analyze(path)

    def _analyze(self, path: Path) -> AnalysisResult:
        result = AnalysisResult()
        seen: dict[tuple[int, str], DetectedFont] = {}
        with pymupdf.open(str(path)) as document:  # type: ignore[no-untyped-call]
            if document.needs_pass:
                raise ValueError("Encrypted PDF requires a password; scan incomplete.")
            for page in document:
                for item in page.get_fonts(full=True):
                    xref, ext, kind, raw_name = item[:4]
                    name = re.sub(r"^[A-Z]{6}\+", "", raw_name)
                    key = (xref, raw_name)
                    evidence = Evidence(
                        type="pdf_metadata",
                        file=str(path),
                        raw_font_name=raw_name,
                        page=page.number + 1,
                        details={"xref": xref, "font_type": kind},
                    )
                    if key in seen:
                        seen[key].evidence.append(evidence)
                        continue
                    data = document.extract_font(xref)[3] if xref else b""
                    detected = DetectedFont(
                        source_file=str(path),
                        font_family=name,
                        postscript_name=name,
                        detection_method="pdf_metadata",
                        embedded=bool(data),
                        subset=bool(re.match(r"^[A-Z]{6}\+", raw_name)),
                        evidence=[evidence],
                    )
                    if data:
                        detected.sha256 = hashlib.sha256(data).hexdigest()
                        if ext in ("ttf", "otf", "woff", "woff2"):
                            try:
                                detected.metadata = FontFileAnalyzer.metadata_from_bytes(data)
                                detected.version = detected.metadata.version
                                detected.vendor = detected.metadata.manufacturer
                                detected.postscript_name = detected.metadata.postscript_name or name
                            except Exception as exc:
                                evidence.details["metadata_error"] = str(exc)
                    seen[key] = detected
                    result.fonts.append(detected)
        return result

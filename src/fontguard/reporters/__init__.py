from fontguard.core.models import ScanResult
from fontguard.reporters.html import render_html
from fontguard.reporters.json import render_json
from fontguard.reporters.sarif import render_sarif
from fontguard.reporters.terminal import render_terminal


def render(result: ScanResult, format: str) -> str:
    return {
        "terminal": render_terminal,
        "json": render_json,
        "sarif": render_sarif,
        "html": render_html,
    }[format](result)

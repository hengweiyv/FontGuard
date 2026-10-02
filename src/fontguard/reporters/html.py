from html import escape

from fontguard.core.models import ScanResult


def render_html(result: ScanResult) -> str:
    rows = "".join(
        "<tr>"
        + "".join(
            f"<td>{escape(str(value))}</td>"
            for value in (
                font.source_file,
                font.canonical_name,
                font.license.type,
                font.usage_context,
                font.risk_level,
                font.risk_reason,
                "existing" if font.baselined else "new",
            )
        )
        + "</tr>"
        for font in result.fonts
    )
    diagnostics = "".join(
        f"<li>{escape(d.severity)}: {escape(d.file)}: {escape(d.message)}</li>"
        for d in result.diagnostics
    )
    return (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>FontGuard report</title><style>body{font:16px system-ui;margin:2rem}"
        "table{border-collapse:collapse;width:100%}td,th{border:1px solid #aaa;"
        "padding:.6rem;text-align:left}th{background:#eee}</style>"
        f"<h1>FontGuard</h1><p>Status: {escape(result.status)} · "
        f"Files: {result.files_scanned} · Fonts: {len(result.fonts)}</p>"
        "<table><thead><tr><th>File</th><th>Font</th><th>License</th><th>Usage</th>"
        "<th>Risk</th><th>Reason</th><th>Baseline</th></tr></thead>"
        f"<tbody>{rows}</tbody></table><ul>{diagnostics}</ul>"
        "<p>Compliance assistance only; results are not legal advice.</p></html>\n"
    )

from fontguard.core.models import ScanResult


def render_terminal(result: ScanResult) -> str:
    lines = [
        f"FontGuard {result.tool_version}",
        "",
        f"Files scanned: {result.files_scanned}",
        f"Fonts detected: {len(result.fonts)}",
        f"Cache hits: {result.cache_hits}",
        "",
    ]
    lines.extend(f"{risk.upper():<10} {count}" for risk, count in result.summary.items())
    for font in result.fonts:
        lines.extend(
            [
                "",
                "-" * 50,
                font.canonical_name or font.font_family,
                f"File: {font.source_file}",
                f"Detection: {font.detection_method}",
                f"Vendor: {font.vendor or 'Unknown'}",
                f"License: {font.license.type}",
                f"Usage: {font.usage_context}",
                f"Risk: {font.risk_level}",
                f"Reason: {font.risk_reason}",
            ]
        )
        if font.identity:
            lines.append(f"Identity: {font.identity.match_method} ({font.confidence:.2f})")
        if font.baselined:
            lines.append("Baseline: existing finding (not counted for CI failure)")
        for condition in font.license.conditions:
            lines.append(f"Condition: {condition}")
        for source in font.sources:
            lines.append(f"Source: {source.url} (verified {font.verified_at})")
    for diagnostic in result.diagnostics:
        lines.extend(
            ["", f"{diagnostic.severity.upper()}: {diagnostic.file}: {diagnostic.message}"]
        )
    lines.extend(["", f"FontGuard scan {result.status}.", f"Exit code: {result.exit_code}"])
    return "\n".join(lines) + "\n"

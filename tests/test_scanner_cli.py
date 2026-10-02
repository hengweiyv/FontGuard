import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from fontguard.cli.main import main
from fontguard.core.config import Config, Policy
from fontguard.core.models import RiskLevel, UsageContext
from fontguard.core.records import create_baseline
from fontguard.core.scanner import Scanner
from fontguard.reporters.html import render_html
from fontguard.reporters.sarif import render_sarif


def write_css(path: Path, name: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'body {{font-family: "{name}";}}', encoding="utf-8")
    return path


def test_ignore_nested_and_unignore(tmp_path: Path) -> None:
    write_css(tmp_path / "included.css", "Noto Sans")
    write_css(tmp_path / "skip.css", "Unknown")
    write_css(tmp_path / "node_modules" / "hidden.css", "Unknown")
    write_css(tmp_path / "sub" / "a.css", "Unknown")
    write_css(tmp_path / "sub" / "keep.css", "Noto Sans")
    (tmp_path / ".gitignore").write_text("skip.css\nsub/*.css\n", encoding="utf-8")
    (tmp_path / "sub" / ".fontguardignore").write_text("!keep.css\n", encoding="utf-8")
    result = Scanner(cache=False).scan(tmp_path)
    assert result.files_scanned == 2
    assert {f.source_file for f in result.fonts} == {"included.css", "sub/keep.css"}
    assert not (tmp_path / ".fontguard-cache").exists()


def test_cache_reapplies_policy_and_corrupt_cache_recovers(tmp_path: Path) -> None:
    write_css(tmp_path / "a.css", "Noto Sans")
    scanner = Scanner()
    assert scanner.scan(tmp_path).cache_hits == 0
    scanner.config = Config(policy=Policy(denied_fonts=["Noto Sans"]))
    result = scanner.scan(tmp_path)
    assert result.cache_hits == 1
    assert result.exit_code == 1
    for file in (tmp_path / ".fontguard-cache").glob("*.json"):
        file.write_text("broken", encoding="utf-8")
    assert scanner.scan(tmp_path).cache_hits == 0


def test_baseline_only_suppresses_existing_risk(tmp_path: Path) -> None:
    file = write_css(tmp_path / "a.css", "Noto Sans")
    scanner = Scanner(cache=False)
    result = scanner.scan(tmp_path, fail_on=[RiskLevel.REVIEW])
    baseline = tmp_path / ".fontguard-baseline.json"
    create_baseline(result, baseline)
    assert scanner.scan(tmp_path, fail_on=[RiskLevel.REVIEW], baseline=baseline).exit_code == 0
    scanner.config = Config(policy=Policy(denied_fonts=["Noto Sans"]))
    assert scanner.scan(tmp_path, baseline=baseline).exit_code == 1
    write_css(file, "Unknown Brand")
    changed = scanner.scan(tmp_path, fail_on=[RiskLevel.UNKNOWN], baseline=baseline)
    assert changed.exit_code == 1 and not changed.fonts[0].baselined


def test_baseline_creation_refuses_errors(tmp_path: Path) -> None:
    file = tmp_path / "broken.ttf"
    file.write_bytes(b"invalid")
    result = Scanner(cache=False).scan(file)
    with pytest.raises(ValueError, match="incomplete"):
        create_baseline(result, tmp_path / "baseline.json")


def test_hash_approval_scoped_to_usage_and_policy(font_file: Path, tmp_path: Path) -> None:
    lock = tmp_path / "fontguard.lock"
    assert (
        main(
            [
                "allow",
                str(font_file),
                "--reason",
                "Test approval",
                "--approved-by",
                "legal",
                "--usage",
                "webfont",
                "--lock",
                str(lock),
            ]
        )
        == 0
    )
    scanner = Scanner(cache=False)
    approved = scanner.scan(font_file, usage=UsageContext.WEBFONT).fonts[0]
    assert approved.approval["approved_by"] == "legal"
    assert approved.rule == "organization-approval"
    assert scanner.scan(font_file, usage=UsageContext.LOGO).fonts[0].approval is None
    scanner.config = Config(policy=Policy(denied_fonts=["Source Han Sans"]))
    denied = scanner.scan(font_file, usage=UsageContext.WEBFONT).fonts[0]
    assert denied.risk_level == RiskLevel.HIGH and denied.approval is None


@pytest.mark.parametrize("format", ["terminal", "json", "sarif", "html"])
def test_cli_report_and_exit_codes(tmp_path: Path, format: str) -> None:
    file = write_css(tmp_path / "a.css", "Unknown Brand")
    report = tmp_path / ("report." + format)
    assert (
        main(
            [
                "scan",
                str(file),
                "--fail-on",
                "unknown",
                "--format",
                format,
                "--output",
                str(report),
                "--no-cache",
            ]
        )
        == 1
    )
    assert report.is_file()
    if format == "json":
        payload = json.loads(report.read_text(encoding="utf-8"))
        assert payload["status"] == "failed" and payload["summary"]["unknown"] == 1
    if format == "sarif":
        payload = json.loads(report.read_text(encoding="utf-8"))
        assert payload["version"] == "2.1.0"
        assert (
            payload["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["region"][
                "startLine"
            ]
            == 1
        )


def test_cli_errors_are_machine_readable(tmp_path: Path, capsys) -> None:
    assert main(["scan", str(tmp_path / "missing"), "--format", "json"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "error"
    file = write_css(tmp_path / "a.css", "Noto Sans")
    assert main(["scan", str(file), "--workers", "0", "--format", "json"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "error"


def test_policy_auto_discovery_and_override(tmp_path: Path) -> None:
    file = write_css(tmp_path / "a.css", "Noto Sans")
    (tmp_path / ".fontguard.yml").write_text(
        yaml.safe_dump(
            {"version": 1, "policy": {"denied_fonts": ["Noto Sans"], "fail_on": ["HIGH"]}}
        ),
        encoding="utf-8",
    )
    assert main(["scan", str(file), "--no-cache"]) == 1
    assert main(["scan", str(file), "--fail-on", "unknown", "--no-cache"]) == 0


def test_reports_escape_untrusted_font_names(tmp_path: Path) -> None:
    write_css(tmp_path / "font with space.css", "<script>alert(1)</script>")
    result = Scanner(cache=False).scan(tmp_path)
    assert "<script>" not in render_html(result)
    sarif = json.loads(render_sarif(result))
    uri = sarif["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"][
        "uri"
    ]
    assert uri == "font%20with%20space.css"


def test_unverified_reference_not_hidden_by_known_declaration(tmp_path: Path) -> None:
    file = tmp_path / "site.css"
    file.write_text(
        'body {font-family: "Noto Sans"} const font = "NotoSans.ttf";', encoding="utf-8"
    )
    result = Scanner(cache=False).scan(
        file, usage=UsageContext.PERSONAL, fail_on=[RiskLevel.UNKNOWN]
    )
    assert any(f.risk_level == RiskLevel.UNKNOWN for f in result.fonts)
    assert result.exit_code == 1


def test_git_diff_only_modified_and_untracked(tmp_path: Path) -> None:
    def git(*args):
        return subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    git("init")
    git("config", "user.name", "FontGuard Test")
    git("config", "user.email", "test@example.invalid")
    write_css(tmp_path / "old.css", "Noto Sans")
    write_css(tmp_path / "changed.css", "Noto Sans")
    git("add", ".")
    git("commit", "-m", "test fixture")
    write_css(tmp_path / "changed.css", "Unknown")
    write_css(tmp_path / "new.css", "New Brand")
    result = Scanner(cache=False).scan(tmp_path, git_diff="HEAD")
    assert {f.source_file for f in result.fonts} == {"changed.css", "new.css"}


def test_installed_module_cli(tmp_path: Path) -> None:
    file = write_css(tmp_path / "未知.css", "Unknown Brand")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "fontguard",
            "scan",
            str(file),
            "--format",
            "json",
            "--fail-on",
            "unknown",
            "--no-cache",
        ],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert run.returncode == 1
    assert json.loads(run.stdout)["fonts"][0]["source_file"] == "未知.css"


def test_malformed_yaml_is_operational_error(tmp_path: Path, capsys) -> None:
    write_css(tmp_path / "a.css", "Noto Sans")
    (tmp_path / ".fontguard.yml").write_text("policy: [unterminated", encoding="utf-8")
    assert main(["scan", str(tmp_path), "--format", "json", "--no-cache"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "error"


@pytest.mark.parametrize("level,expected", [("high", 0), ("review", 1), ("unknown", 0)])
def test_cli_threshold_semantics(tmp_path: Path, level: str, expected: int) -> None:
    file = write_css(tmp_path / "a.css", "Noto Sans")
    assert main(["scan", str(file), "--fail-on", level, "--no-cache"]) == expected


def test_scan_does_not_use_network(tmp_path: Path, monkeypatch) -> None:
    import socket

    def fail_network(*args, **kwargs):
        raise AssertionError("Network used during offline scan")

    monkeypatch.setattr(socket.socket, "connect", fail_network)
    file = tmp_path / "site.css"
    file.write_text(
        "@font-face {font-family: Remote; src: url(https://example.org/a.woff2)}"
        'body {font-family: "Noto Sans"}',
        encoding="utf-8",
    )
    result = Scanner(cache=False).scan(file, usage=UsageContext.WEBFONT)
    assert result.exit_code == 0
    assert any(d.severity == "warning" for d in result.diagnostics)

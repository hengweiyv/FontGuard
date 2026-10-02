import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import yaml

from fontguard import __version__
from fontguard.core.config import load_config
from fontguard.core.models import Diagnostic, RiskLevel, ScanResult, UsageContext
from fontguard.core.records import Approval, create_baseline, read_approvals
from fontguard.core.registry import AnalyzerRegistry
from fontguard.core.scanner import Scanner
from fontguard.database.loader import FontDatabase
from fontguard.reporters import render
from fontguard.utils.hashing import file_sha256


def scan_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--usage", choices=[u.value for u in UsageContext], default="unknown")
    parser.add_argument("--fail-on", action="append", choices=[r.value.lower() for r in RiskLevel])
    parser.add_argument("--config", type=Path)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--plugins", action="store_true", help="Enable installed analyzer plugins")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="fontguard", description="Offline font compliance scanner")
    root.add_argument("--version", action="version", version=f"FontGuard {__version__}")
    commands = root.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan", help="Scan local files or a project")
    scan_arguments(scan)
    scan.add_argument("--format", choices=["terminal", "json", "sarif", "html"], default="terminal")
    scan.add_argument("--output", type=Path)
    scan.add_argument("--baseline", type=Path)
    scan.add_argument("--git-diff", nargs="?", const="HEAD")
    baseline = commands.add_parser("baseline", help="Manage existing findings")
    baseline_commands = baseline.add_subparsers(dest="baseline_command", required=True)
    create = baseline_commands.add_parser("create")
    scan_arguments(create)
    create.add_argument("--output", type=Path, default=Path(".fontguard-baseline.json"))
    database = commands.add_parser("database", help="Validate the offline database")
    database_commands = database.add_subparsers(dest="database_command", required=True)
    validate = database_commands.add_parser("validate")
    validate.add_argument("--database", type=Path)
    allow = commands.add_parser("allow", help="Record an organization hash approval")
    allow.add_argument("font", type=Path)
    allow.add_argument("--reason", required=True)
    allow.add_argument("--approved-by", required=True)
    allow.add_argument(
        "--usage",
        action="append",
        choices=[u.value for u in UsageContext if u != UsageContext.UNKNOWN],
        required=True,
    )
    allow.add_argument("--lock", type=Path, default=Path("fontguard.lock"))
    return root


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "database":
            database = FontDatabase(args.database)
            print(
                f"Database valid: {len(database.records)} fonts, "
                f"{len(database.exact_names)} aliases, "
                f"{len(database.ambiguous_names)} normalized keys excluded as ambiguous."
            )
            return 0
        if args.command == "allow":
            from fontguard.analyzers.font_file import FontFileAnalyzer

            analyzer = FontFileAnalyzer()
            if not analyzer.supports(args.font):
                raise ValueError("allow requires a TTF, OTF, WOFF or WOFF2 font file.")
            analyzer.analyze(args.font)  # Refuse approvals for damaged/non-font files.
            approvals = read_approvals(args.lock)
            approval = Approval(
                sha256=file_sha256(args.font),
                reason=args.reason,
                approved_by=args.approved_by,
                usages=[UsageContext(u) for u in args.usage],
            )
            approvals.approved_fonts = [
                a for a in approvals.approved_fonts if a.sha256 != approval.sha256
            ] + [approval]
            args.lock.write_text(
                yaml.safe_dump(
                    approvals.model_dump(mode="json"), allow_unicode=True, sort_keys=False
                ),
                encoding="utf-8",
            )
            print(f"Organization approval saved to {args.lock}; license ownership not verified.")
            return 0
        if not 1 <= args.workers <= 64:
            raise ValueError("--workers must be between 1 and 64.")
        target = args.path.resolve()
        root = target if target.is_dir() else target.parent
        config_path = args.config or (root / ".fontguard.yml")
        if args.config and not config_path.is_file():
            raise ValueError(f"Config does not exist: {config_path}")
        config = load_config(config_path if config_path.is_file() else None)
        scanner = Scanner(
            database=FontDatabase(args.database),
            config=config,
            registry=AnalyzerRegistry.default(plugins=args.plugins),
            workers=args.workers,
            cache=not args.no_cache,
        )
        levels = [RiskLevel(r.upper()) for r in args.fail_on] if args.fail_on else None
        result = scanner.scan(
            target,
            usage=UsageContext(args.usage),
            fail_on=levels,
            baseline=getattr(args, "baseline", None),
            git_diff=getattr(args, "git_diff", None),
        )
        if args.command == "baseline":
            create_baseline(result, args.output)
            print(f"Baseline saved to {args.output}: {len(result.fonts)} observations.")
            return 0
        output = render(result, args.format)
        if args.output:
            args.output.write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
        return result.exit_code
    except Exception as exc:
        # CLI boundary: all incomplete scans (including malformed YAML and plugin
        # failures) must retain a machine-readable report and operational exit 2.
        if args.command == "scan":
            result = ScanResult(
                root=str(args.path.resolve()),
                status="error",
                diagnostics=[Diagnostic(file=str(args.path), message=str(exc))],
            )
            output = render(result, args.format)
            if args.output:
                try:
                    args.output.write_text(output, encoding="utf-8")
                except OSError as output_error:
                    print(f"FontGuard error: {output_error}", file=sys.stderr)
            else:
                sys.stdout.write(output)
        else:
            print(f"FontGuard error: {exc}", file=sys.stderr)
        return 2

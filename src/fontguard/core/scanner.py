"""Filesystem orchestration; analyzers never decide license or policy outcomes."""

import hashlib
import os
import subprocess
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pathspec

from fontguard.analyzers.pdf import PDFAnalyzer
from fontguard.analyzers.web import URL, CSSAnalyzer, analyze_text
from fontguard.core.config import Config, failure_levels
from fontguard.core.models import (
    AnalysisResult,
    DetectedFont,
    Diagnostic,
    RiskLevel,
    ScanResult,
    UsageContext,
)
from fontguard.core.records import fingerprint, read_approvals, read_baseline
from fontguard.core.registry import AnalyzerRegistry
from fontguard.database.loader import FontDatabase
from fontguard.identity.engine import exact_font_name
from fontguard.risk.engine import evaluate_font
from fontguard.utils.hashing import file_sha256

EXCLUDED = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    ".fontguard-cache",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}
MAX_FILE_SIZE = 256 * 1024 * 1024
CACHE_VERSION = "fontguard-0.2.0-v2"


def git_changed(root: Path, revision: str) -> set[Path]:
    if revision.startswith("-"):
        raise ValueError("Git revision must not start with '-'.")

    def git(*args: str) -> bytes:
        process = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, check=False, timeout=60
        )
        if process.returncode:
            raise ValueError(process.stderr.decode("utf-8", errors="replace").strip())
        return process.stdout

    top = Path(os.fsdecode(git("rev-parse", "--show-toplevel")).strip()).resolve()
    # Explicit base uses merge-base semantics for PR changes; HEAD includes working tree.
    base = (
        revision if revision == "HEAD" else os.fsdecode(git("merge-base", "HEAD", revision)).strip()
    )
    modified = git("diff", "--name-only", "--diff-filter=ACMRT", "-z", base, "--")
    untracked = git("ls-files", "--others", "--exclude-standard", "-z")
    return {
        (top / os.fsdecode(name)).resolve()
        for name in (modified + untracked).split(b"\0")
        if name and (top / os.fsdecode(name)).resolve().is_relative_to(root)
    }


def is_ignored(
    path: Path, rules: list[tuple[Path, pathspec.GitIgnoreSpec]], is_dir: bool = False
) -> bool:
    decision = False
    for base, spec in rules:
        relative = path.relative_to(base).as_posix() + ("/" if is_dir else "")
        check = spec.check_file(relative)
        if check.include is not None:
            decision = check.include
    return decision


def collect_files(root: Path, target: Path, registry: AnalyzerRegistry) -> list[Path]:
    if target.is_file():
        return [target] if registry.get(target) else []
    collected: list[Path] = []
    # Scoped rules are inherited so nested .gitignore/.fontguardignore files work.
    scoped: dict[Path, list[tuple[Path, pathspec.GitIgnoreSpec]]] = {}

    def walk_error(error: OSError) -> None:
        raise error

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        current = Path(directory)
        rules = list(scoped.get(current.parent, []))
        for name in (".gitignore", ".fontguardignore"):
            ignore = current / name
            if ignore.is_file():
                rules.append(
                    (
                        current,
                        pathspec.GitIgnoreSpec.from_lines(
                            ignore.read_text(encoding="utf-8-sig").splitlines()
                        ),
                    )
                )
        scoped[current] = rules

        dirs[:] = sorted(
            d
            for d in dirs
            if d not in EXCLUDED
            and not (current / d).is_symlink()
            and not is_ignored(current / d, rules, True)
        )
        for name in sorted(files):
            path = current / name
            if not path.is_symlink() and registry.get(path) and not is_ignored(path, rules):
                collected.append(path)
    return sorted(collected)


class Scanner:
    def __init__(
        self,
        *,
        database: FontDatabase | None = None,
        registry: AnalyzerRegistry | None = None,
        config: Config | None = None,
        workers: int = 4,
        cache: bool = True,
    ) -> None:
        self.database = database or FontDatabase()
        self.registry = registry or AnalyzerRegistry.default()
        self.config = config or Config()
        if not 1 <= workers <= 64:
            raise ValueError("workers must be between 1 and 64.")
        self.workers = workers
        self.cache = cache

    def scan(
        self,
        target: Path,
        *,
        usage: UsageContext = UsageContext.UNKNOWN,
        fail_on: list[RiskLevel] | None = None,
        baseline: Path | None = None,
        git_diff: str | None = None,
    ) -> ScanResult:
        target = target.resolve()
        if not target.exists():
            raise ValueError(f"Scan target does not exist: {target}")
        root = target if target.is_dir() else target.parent
        result = ScanResult(root=str(root))
        paths = collect_files(root, target, self.registry)
        if target.is_file() and not paths:
            raise ValueError(f"Unsupported file format: {target.suffix}")
        if git_diff is not None:
            changed = git_changed(root, git_diff)
            paths = [path for path in paths if path in changed]
        baseline_ids = read_baseline(baseline)
        approvals = read_approvals(root / "fontguard.lock")
        cache_dir = root / ".fontguard-cache"
        if self.cache:
            try:
                cache_dir.mkdir(exist_ok=True)
            except OSError as exc:
                result.diagnostics.append(
                    Diagnostic(
                        file=".fontguard-cache",
                        severity="warning",
                        message=f"Cache unavailable: {exc}",
                    )
                )
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            for path, analysis, hit in self._analyzed_files(paths, root, cache_dir, pool):
                result.files_scanned += 1
                result.cache_hits += int(hit)
                result.diagnostics.extend(analysis.diagnostics)
                for raw in analysis.fonts:
                    raw.source_file = path.relative_to(root).as_posix()
                    for evidence in raw.evidence:
                        evidence_path = Path(evidence.file)
                        if evidence_path.is_absolute() and evidence_path.is_relative_to(root):
                            evidence.file = evidence_path.relative_to(root).as_posix()
                    raw.usage_context = usage
                    font = evaluate_font(raw, self.database, self.config.policy)
                    approval = next(
                        (
                            a
                            for a in approvals.approved_fonts
                            if a.sha256 == font.sha256 and usage in a.usages
                        ),
                        None,
                    )
                    # Organization approvals cannot override an explicit policy prohibition.
                    if approval and font.rule not in {
                        "denied-font",
                        "font-not-allowed",
                        "license-not-allowed",
                    }:
                        font.approval = {
                            "reason": approval.reason,
                            "approved_by": approval.approved_by,
                        }
                        font.risk_level = RiskLevel.LOW
                        font.risk_reason = (
                            "Organization approval recorded for this hash and usage; "
                        )
                        font.risk_reason += "FontGuard does not verify license ownership."
                        font.rule = "organization-approval"
                    font.fingerprint = fingerprint(font)
                    font.baselined = font.fingerprint in baseline_ids
                    result.fonts.append(font)
        result.diagnostics = [
            d.model_copy(update={"file": self._relative(d.file, root)}) for d in result.diagnostics
        ]
        # One observation per source/hash/name; preserve every location as evidence.
        unique: dict[tuple[str, str, str, str], int] = {}
        merged: list[DetectedFont] = []
        for font in result.fonts:
            key = (
                font.source_file,
                font.sha256 or "",
                exact_font_name(font.canonical_name),
                font.rule,
            )
            if key in unique:
                existing = merged[unique[key]]
                existing.evidence.extend(e for e in font.evidence if e not in existing.evidence)
            else:
                unique[key] = len(merged)
                merged.append(font)
        result.fonts = merged
        result.summary = {
            level.value.lower(): sum(f.risk_level == level for f in result.fonts)
            for level in RiskLevel
        }
        thresholds = failure_levels(fail_on if fail_on is not None else self.config.policy.fail_on)
        if any(f.risk_level in thresholds and not f.baselined for f in result.fonts):
            result.status = "failed"
        if any(d.severity == "error" for d in result.diagnostics):
            result.status = "error"
        return result

    def _analyzed_files(
        self, paths: list[Path], root: Path, cache_dir: Path, pool: ThreadPoolExecutor
    ) -> Iterator[tuple[Path, AnalysisResult, bool]]:
        # Bound outstanding futures for very large repositories. PyMuPDF parsing
        # stays on the calling thread; independent non-PDF analyzers run in workers.
        batch_size = self.workers * 4
        for offset in range(0, len(paths), batch_size):
            chunk = paths[offset : offset + batch_size]
            pending = {
                path: pool.submit(self._analyze, path, root, cache_dir)
                for path in chunk
                if not isinstance(self.registry.get(path), PDFAnalyzer)
            }
            for path in chunk:
                analysis, hit = (
                    pending[path].result()
                    if path in pending
                    else self._analyze(path, root, cache_dir)
                )
                yield path, analysis, hit

    @staticmethod
    def _relative(file: str, root: Path) -> str:
        path = Path(file)
        return (
            path.relative_to(root).as_posix()
            if path.is_absolute() and (path.is_relative_to(root))
            else file
        )

    def _analyze(self, path: Path, root: Path, cache_dir: Path) -> tuple[AnalysisResult, bool]:
        try:
            if path.stat().st_size > MAX_FILE_SIZE:
                raise ValueError("File exceeds 256 MiB limit; scan incomplete.")
            analyzer = self.registry.get(path)
            if analyzer is None:
                return AnalysisResult(), False
            digest = file_sha256(path)
            stat = path.stat()
            key_parts = [
                CACHE_VERSION,
                str(root),
                str(path),
                str(stat.st_mtime_ns),
                str(stat.st_size),
                digest,
                type(analyzer).__module__,
                type(analyzer).__qualname__,
            ]
            text = ""
            if isinstance(analyzer, CSSAnalyzer):
                text = path.read_text(encoding="utf-8-sig")
                # Invalidate CSS when an unchanged declaration points at a changed font.
                for match in URL.finditer(text):
                    parts = urlsplit(match.group(2))
                    reference = (path.parent / unquote(parts.path)).resolve()
                    if not parts.scheme and not parts.netloc and reference.is_relative_to(root):
                        key_parts.append(str(reference))
                        if reference.is_file() and reference.stat().st_size <= MAX_FILE_SIZE:
                            key_parts.append(file_sha256(reference))
            key = hashlib.sha256("\0".join(key_parts).encode()).hexdigest()
            cache_file = cache_dir / (key + ".json")
            if self.cache and cache_file.is_file():
                try:
                    return AnalysisResult.model_validate_json(
                        cache_file.read_text(encoding="utf-8")
                    ), True
                except (ValueError, OSError):
                    pass
            analysis = (
                analyze_text(path, text, root=root)
                if isinstance(analyzer, CSSAnalyzer)
                else analyzer.analyze(path)
            )
            if self.cache and not analysis.diagnostics and cache_dir.is_dir():
                try:
                    temporary = cache_file.with_suffix(".tmp")
                    temporary.write_text(analysis.model_dump_json(), encoding="utf-8")
                    temporary.replace(cache_file)
                except OSError:
                    pass
            return analysis, False
        except Exception as exc:
            return AnalysisResult(diagnostics=[Diagnostic(file=str(path), message=str(exc))]), False

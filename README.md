# FontGuard

Font license compliance scanner for developers and designers.

Find fonts. Identify licenses. Enforce font policies in CI.

Local First · Offline First · Open Source · CLI First · CI Friendly

```sh
fontguard scan .
fontguard scan poster.pdf --usage commercial_design
fontguard scan ./website --usage webfont --fail-on high --format sarif --output fontguard.sarif
```

FontGuard 0.2.0 scans local files without accounts, uploads or a server. It reports
font metadata, likely identity, license sources and organization policy conflicts.
Commercial font detection does not prove absence of a purchased license.

## Installation

Python **3.11+**. This version has **not been published to PyPI**; `pip install
fontguard` may resolve an unrelated package. Install from this checkout:

```sh
git clone https://github.com/hengweiyv/FontGuard.git
cd FontGuard
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install .
fontguard --version
```

Or `pipx install .` / `uv tool install .`. Dependency installation needs internet
unless you supply a wheelhouse. Scans and database validation work offline.
After publication and confirming name availability, the intended commands are
`pip install fontguard`, `pipx install fontguard` and `uv tool install fontguard`.

## Quick Start

```sh
fontguard scan examples/site.css --usage commercial_design --no-cache
```

The sample finds Source Han Sans, Noto Sans and an unknown brand font. The first
two have recorded OFL permissions; the unknown font requires investigation.
Use `--usage webfont` to see redistribution conditions. Without `--usage`,
identified fonts require REVIEW because intended use is unspecified.

## CLI

```sh
fontguard scan PATH --usage webfont --fail-on high
fontguard scan . --format json --output report.json
fontguard scan . --format html --output report.html
fontguard scan . --fail-on high --fail-on unknown
fontguard scan . --baseline .fontguard-baseline.json
fontguard scan . --git-diff
fontguard scan . --git-diff origin/main
fontguard scan . --config company.yml --database ./data --workers 4 --no-cache
fontguard baseline create . --usage webfont
fontguard database validate
fontguard allow assets/brand.ttf --usage webfont --reason "Enterprise license recorded" --approved-by legal-team
```

Exit codes: **0** passed, **1** selected risks found, **2** incomplete scan, invalid
config/database or I/O error. Errors appear in JSON/SARIF too. Corrupt files and
password-protected PDFs cannot silently pass. Repeated CLI `--fail-on` values
replace configured thresholds:

| Threshold | Findings causing exit 1 |
| --- | --- |
| high (default) | HIGH |
| review | REVIEW, HIGH |
| low | LOW, REVIEW, HIGH |
| safe | SAFE, LOW, REVIEW, HIGH |
| unknown | UNKNOWN only |

UNKNOWN is independent: use `--fail-on high --fail-on unknown` to block both.
Summary counts are source/font observations, not globally unique font families.
Usage contexts: `unknown`, `personal`, `commercial_design`, `print`, `advertising`,
`website`, `webfont`, `video`, `logo`, `ebook`, `document_embedding`, `app_embedding`,
`software_distribution`, `font_redistribution`. `website` means site design;
select `webfont` when publishing font files for browser use. Intent is explicit;
embedding evidence does not automatically select a usage.

## Supported Formats

| Target | Evidence |
| --- | --- |
| TTF, OTF, WOFF, WOFF2 | Name IDs 0–14 (selected), 16/17, SHA256, OS/2 fsType |
| PDF | Base font name, subset prefix, page, xref, embedded bytes and readable metadata |
| DOCX, PPTX | ZIP/XML declarations in content, styles, tables, slides, masters, themes |
| SVG | font-family attributes and CSS declarations |
| CSS, SCSS, LESS | font-family, @font-face, local font URLs |
| HTML, Vue, JS/TS, JSX/TSX, Svelte | CSS, common literal fontFamily properties, font paths |
| Directory | Recursive extension filtering and scoped ignore rules |

Web analysis uses conservative static extraction, not a full CSS/JS compiler.
Dynamic expressions, CSS `font` shorthand and complex nested rules may need manual
review. Generic CSS families are ignored. `@font-face` aliases resolve to font
metadata when the local reference stays within the scan root. Remote, data and
root-relative URLs are not fetched. Unverified filename references remain UNKNOWN.
PDF Type 1/CFF-only metadata may be limited. Office results include declared but
unused fallback/theme fonts; obfuscated Office embedded fonts and exact theme-to-run
resolution are not decoded. Outlined and rasterized text cannot be identified.
GUI, visual font recognition, PSD, Figma and video are future extensions.

## Risk Model

| Risk | Meaning |
| --- | --- |
| SAFE | Recorded license permits the specified usage for the matched identity |
| LOW | License conditions apply, or scoped organization approval is recorded |
| REVIEW | License verification required, or usage unspecified |
| HIGH | Explicit permission or organization policy conflict |
| UNKNOWN | Identity or relevant permissions unconfirmed |

Name matching has a confidence and is **not proof of provenance**. Metadata license
text is preserved but never automatically trusted as a curated license fact.
SHA256 is preferred when the database provides a hash. Renaming a font file does
not change internal identity/hash; rewriting metadata changes the hash and can
defeat name matching. The database contains 2,052 families and 8 verified binary
hashes. Windows-supplied proprietary fonts generally require REVIEW of software
entitlement and extended rights; an unlisted commercial font remains UNKNOWN.

## Policy

Auto-discovered at the scan root (single file: its parent), `.fontguard.yml`:

```yaml
version: 1
policy:
  fail_on: [HIGH, UNKNOWN]
  allowed_licenses: [OFL-1.1, Apache-2.0]
  denied_fonts: [Example Font]
  allowed_fonts: []
  unknown_font:
    action: unknown # unknown | review | high
```

Nonempty `allowed_fonts` is an exclusive allowlist; inclusion does not prove
license ownership. Denial takes priority. Licenses outside an active license
allowlist produce HIGH. Unknown licenses remain UNKNOWN unless escalated by
`unknown_font.action`. Invalid/misspelled fields fail closed.

Each traversed directory's `.gitignore` and `.fontguardignore` are read, with the
latter taking priority at the same level. Git-style patterns and negation work;
ignored parents are pruned, so re-include a parent before its children. `.git`,
`.venv`, `node_modules`, `vendor` and tool caches are always skipped. Explicit
single-file targets bypass ignores. Directory traversal skips symlinks.

Default cache: `.fontguard-cache/`. `--no-cache` works on read-only mounts and CI.
Caching avoids repeated parsing but still hashes file contents. CSS dependencies
invalidate cached results when font bytes change. Remove the cache to reclaim old
versions; v0.1 has no automatic eviction. Protect cache contents in trusted projects.

## Baselines and approvals

```sh
fontguard baseline create . --usage webfont
fontguard scan . --usage webfont --baseline .fontguard-baseline.json --fail-on review
```

Baselined findings remain visible but do not fail the selected threshold. New hashes,
source paths, usage, risk, license or rules produce new findings. Incomplete scans
cannot create baselines. Review baseline changes in Git.

`fontguard allow` writes `fontguard.lock` with hash, usage, reason and approver.
It records organization assertions and does not verify purchase. Approvals become
LOW and cannot override explicit font/license prohibitions. Place the lock at the
scan root or choose `--lock` when recording it.

## CI

```yaml
- name: Scan fonts
  run: fontguard scan . --usage webfont --fail-on high --format sarif --output fontguard.sarif --no-cache
- name: Upload SARIF
  if: always()
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: fontguard.sarif
```

See [complete workflow](examples/github-actions.yml). GitHub requires
`security-events: write` and Code Scanning availability. The composite action at
`.github/actions/fontguard` installs from its checkout. GitLab/Jenkins can run the
same CLI and archive JSON/SARIF; exit codes control job status.

`--git-diff` selects staged/working-tree differences from HEAD plus untracked files.
An explicit base uses the merge base with HEAD plus working-tree/untracked changes.
Fetch that ref in CI. Deleted files are omitted. Font-only changes do not rescan
unchanged CSS; full scans are needed after policy/database/approval changes and to
reevaluate all references.

Pre-commit hook id: `fontguard` in `.pre-commit-hooks.yaml`. It runs a full scan and
honors local policy. Pin your published repository to a reviewed revision.
Docker (no image has been published):

```sh
docker build -t fontguard-local .
docker run --rm -v "$PWD:/workspace:ro" fontguard-local scan /workspace --usage webfont --no-cache
```

## Database

Community YAML: `data/fonts`, `data/licenses`, `data/vendors`, bundled in wheels.
There are **2,052 family records**: 2,020 verified Google Fonts families, the
separately curated Source Han Sans family, and 31 Windows-distributed families.
The Noto Sans record is enriched from the official catalogue rather than duplicated.
Each imported Google family has its own downloaded and checked license file,
metadata, immutable upstream commit URL and provenance hashes. Eleven unverified
or retired upstream entries are explicitly excluded. Chinese examples include
Noto Sans/Serif SC/TC, Long Cang, Ma Shan Zheng, ZCOOL and Windows font aliases
such as 微软雅黑, 宋体, 黑体, 楷体 and 等线.

Literal names match first; style normalization retains region suffixes before any
general fallback. Ambiguous normalized keys are excluded from fallback matching.
This keeps Noto Sans, Noto Sans SC and Noto Sans TC separate in identity, policy,
deduplication and baseline fingerprints. Imported ambiguous aliases are omitted
and documented rather than assigned to an arbitrary family.

`--database` selects a complete custom database. Validation checks schema, IDs,
literal alias collisions, license/vendor references, sources and hashes. It does
not fetch URLs. See [database provenance](docs/font-database.md) for import commands,
licensing scope, exclusions and verified binary hashes.

## Development and Contributing

```sh
python -m pip install -e '.[dev]'
pytest
ruff check .
ruff format --check .
mypy
fontguard database validate
python -m build
```

See [CONTRIBUTING](CONTRIBUTING.md), [architecture](docs/architecture.md), and
[SECURITY](SECURITY.md). Plugins are registered via the Python API or installed
entry points enabled with `--plugins`. CI is configured for Windows/macOS/Linux,
Python 3.11–3.13; this is not a claim that remote CI has already run.
See [local verification record](docs/verification.md) for the completed checks.
See [server verification](docs/server-verification.md) for the Linux/Docker run.

## License

Original code and database records: **Apache-2.0**, chosen for its explicit patent
grant and suitability for enterprise/community tooling. Third-party fonts retain
their licenses. **PyMuPDF/MuPDF uses AGPL or an Artifex commercial license**; its
terms apply to PDF-enabled dependency bundles and Docker images. See [NOTICE](NOTICE),
[Apache license](https://www.apache.org/licenses/LICENSE-2.0) and
[PyMuPDF license](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright).

## Disclaimer

FontGuard is a **license compliance assistance tool**, not a lawyer. Reports are
not legal advice or determinations of infringement. Detection, curated facts and
usage declarations can be incomplete. Commercial fonts may already be licensed.
Verify actual font provenance, license texts, contractual scope and conditions.

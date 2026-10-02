# Initial local prototype verification — 2026-10-02

[简体中文](verification.zh-CN.md) | **English** | [Home](../README.en.md)

Host: Windows, Python 3.12.14 from the Codex bundled runtime, isolated project
`.venv`. This did not replace the user's global Python installation.

Completed checks:

- `python -m pytest -q`: 63 tests passed.
- `python -m ruff check .` and `python -m ruff format --check .`: passed.
- `python -m mypy`: strict checking passed for 36 library source files.
- `fontguard database validate`: 2 official-source font records validated.
- `python -m pip check`: no broken dependency requirements.
- `python -m build`: wheel and source archive built successfully.
- Wheel installed offline with `pip install --no-index --no-deps --target
  artifacts/wheel-install dist/fontguard-0.1.0-py3-none-any.whl`.
- `python tests/release_smoke.py artifacts/wheel-install`: confirmed imports from
  the installed wheel directory and its bundled database, not editable source.
  Dependencies were reused from the development environment for this smoke test.
  Network connection attempts were prohibited during scans. JSON, SARIF, HTML and
  terminal outputs passed; operational exit codes 0, 1 and 2 were verified.
- SARIF validated against the vendored complete OASIS 2.1.0 schema, including
  baseline suppressions. Both tests and release smoke run offline.
- Full project CLI scan with `--usage webfont --fail-on high --no-cache` completed.

Analyzer tests generate original TTF, OTF, WOFF and WOFF2 font binaries and real
PDFs with embedded and standard fonts. Office tests use synthetic ZIP/XML fixture
packages to exercise theme, style and Asian-font declarations; they do not claim
visual verification in Word or PowerPoint. Tests also cover malformed XML, missing
font references, encrypted PDFs, cache dependency invalidation, scoped ignores,
policy precedence, baseline changes, scoped hash approvals, Git diff and Unicode
CLI output.

Generated local reports are in `artifacts/sample-report.*`; release archives are
in `dist/`. These output directories are ignored by Git and the scanner.

Not executed here: Docker build/run (Docker unavailable), remote GitHub Actions,
GitHub SARIF upload, Linux/macOS runtime tests, PyPI publication or registry image
publication. Those workflows/configurations are prepared, not claimed as deployed.
The initial prototype database contained only Source Han Sans and Noto Sans;
unlisted fonts remain unknown until evidence-backed records are contributed.

## Expanded 0.2.0 local validation

- Database: 2,052 families, 5,837 literal names/aliases and eight verified binary
  SHA256 values. Forty-five ambiguous normalized keys are excluded from fallback.
- `python -m pytest -q --tb=short`: 72 tests passed in 60.18 seconds on Windows,
  including three HTML inline-style policy regressions added during server testing.
- Ruff lint/format checks passed for source, tests and maintainer scripts.
- Strict mypy passed for all 36 library source files.
- Catalogue import, regional-family identity, policy/dedup/baseline isolation and
  Protobuf apostrophe escaping have regression tests.
- Server/Docker verification is recorded separately in `server-verification.md`.
- Final packaging uses Hatchling 1.32.4 with `python -m build --no-isolation`;
  installed-wheel offline scans and full SARIF validation passed. An additional
  isolated build attempt encountered TLS/index download errors for its build
  dependencies; the local installed backend was used for the release archives.

## Public repository CI

Release commit `d082897020e4f54da7521da829cbd35239842bcc` passed all 10 jobs in
[GitHub Actions](https://github.com/hengweiyv/FontGuard/actions/runs/36964651723):
Windows/macOS/Linux with Python 3.11/3.12/3.13, plus source-built Docker and offline
tests. Dependency installation and isolated builds succeeded in CI. This does
not claim GitHub Code Scanning SARIF upload verification, PyPI publication or
container-registry publication.

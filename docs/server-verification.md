# FontGuard 0.2.0 server verification

[简体中文](server-verification.zh-CN.md) | **English** | [Home](../README.en.md)

Verification date: 2026-10-02. Tests run on an Ubuntu 24.04 server in isolated
Docker containers based on `python:3.11-slim`. No application ports are published.
Runtime scans use `--network=none`; dependency installation during image building
requires network access. The host's production application configuration is not
part of the test setup.

## Results

The runtime image identified eight actual upstream TTF files after their filenames
were changed to company-prefixed names. All eight identities matched the recorded
SHA256 values. The binary provenance is in `data/imports/verified-hashes.json`.

- Python 3.11.17: **72 tests passed in 40.50 seconds**, network disabled.
- Real-file acceptance: **passed** for TTF, WOFF, WOFF2, subset/embedded PDF,
  native DOCX, native PPTX, CSS, HTML and SVG.
- All eight real renamed TTF files matched their exact recorded hashes.
- Cache reuse, baseline suppression/new findings and policy denial: **passed**.
- Terminal/JSON CLI exit codes 0, 1 and 2 and full SARIF schema: **passed**.
- Runtime image: **passed**, eight actual fonts scanned offline under the
  512 MiB/one-CPU test limits.

Native-file acceptance initially exposed an HTML inline-style boundary defect:
without a final CSS semicolon, following markup was included in the font name.
The parser was fixed, the analysis cache version advanced and three policy/line
regression cases added. All results above are from the corrected wheel and fresh
acceptance directory. The final server images installed that wheel offline into
the previously built dependency images; GitHub CI builds the checked-in Dockerfile
from source separately.

## Reproduce

Build the release source archive and obtain the eight test fonts explicitly:

```sh
python -m pip install '.[dev]'
python scripts/fetch_test_fonts.py
python -m build
tar -czf artifacts/e2e-fonts.tar.gz -C artifacts/e2e fonts
```

Copy `dist/fontguard-0.2.0.tar.gz`, `artifacts/e2e-fonts.tar.gz` and
`scripts/server_test.sh` to a dedicated server test directory, then run:

```sh
sh server_test.sh "$HOME/fontguard-tests/2026-10-02"
```

The script builds a separate test image, runs pytest with a 1 GiB memory limit and
one CPU, and creates native PDF, DOCX and PPTX files along with converted WOFF and
WOFF2 files. Acceptance also exercises local CSS font resolution, HTML, SVG,
cache reuse, baseline changes, policy denial, malformed fonts, CLI exit codes and
full SARIF schema validation. The runtime scan has a 512 MiB memory limit and
one CPU. These limits are test settings, not measured minimum requirements or
throughput claims.

Reports are retained in the printed acceptance directory. Each rerun uses a fresh
directory so prior cache or policy files cannot affect the result. No font binaries
are included in the published repository or release archives.

## Cleanup of this server test run

At the server owner's request, the dedicated test directory was removed after
acceptance, including fonts, native fixtures, cache, reports, archives and scripts.
FontGuard images, their build intermediates and the newly pulled Python 3.11 base
image were also removed: 25 image records in total. The existing 23 containers
retained their state, with 15 running; existing volumes and networks were unchanged.
Production service configuration was not modified. Local reports and the public
GitHub project remain. This record documents completed testing; it does not imply
that the test environment is still installed on the server.

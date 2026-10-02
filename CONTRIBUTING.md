# Contributing

[简体中文](CONTRIBUTING.zh-CN.md) | **English** | [Home](README.en.md)

Use Python 3.11 or newer. Create a virtual environment and install `pip install -e '.[dev]'`.

Before submitting a change, run:

```sh
pytest
ruff check .
ruff format --check .
mypy
fontguard database validate
python -m build
```

Add regression tests for behavior changes. Keep scanning offline. Analyzers return
observations and evidence; they must not decide organization policy or announce
infringement. See [architecture](docs/architecture.md) for plugin contracts.

To contribute font data, add YAML under `data/fonts/`, reference a license and
vendor in their directories, and include authoritative source URLs and a real
verification date. Prefer official license files, then official repositories,
vendor websites and official documentation over third-party data. Do not invent
hashes, purchase status or commercial permissions. Add alias tests. Database
validation rejects conflicting literal aliases, duplicate IDs, invalid
licenses, malformed hashes and missing sources. Aliases equivalent within one
record are intentional. Normalization collisions caused by meaningful region or
family tokens disable fallback matching; they never pick an arbitrary record.

Include no proprietary fonts, license keys or private documents in contributions.
Tests generate their own synthetic fonts and Office/PDF fixtures.
Explicit maintainer acceptance downloads retain real upstream binaries only in
ignored `artifacts/`. Keep Chinese and English documentation synchronized when
changing commands, supported behavior or licensing rules. See
[database provenance](docs/font-database.md) for the bulk-import workflow.

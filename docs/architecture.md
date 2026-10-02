# Architecture and extension contract

`Scanner → AnalyzerRegistry → raw AnalysisResult → FontIdentityEngine →
License Engine → Policy Engine → approvals → baseline → reporter`.

All contracts are Pydantic models in `core/models.py`. Analyzers preserve source
locations and raw metadata. Font identity prefers SHA256, then PostScript name,
full name, family and aliases. Normalization removes style/locale tokens, PDF
subset prefixes and file extensions. It only maps the explicit traditional `體`
variant; broad Chinese translation and fuzzy matching are deliberately excluded.
Literal aliases are checked before style-normalized names preserving locales,
then before the general normalized fallback. Ambiguous fallback keys do not match.
Distinct regional families retain distinct identity, policy and baseline keys.
Name matching is not proof of provenance. Unknown metadata does not become
trusted license data simply because its name table contains license text.

YAML database records store facts, per-usage permissions and sources. Risk is
computed at scan time; changing policy or the database reevaluates cached raw
observations. No network is used during scans or database validation.

## Analyzer plugins

Implement a stateless, thread-safe `Analyzer`:

```python
from pathlib import Path
from fontguard.analyzers.base import Analyzer
from fontguard.core.models import AnalysisResult


class SubtitleAnalyzer(Analyzer):
    extensions = frozenset({".ass"})

    def analyze(self, path: Path) -> AnalysisResult:
        # Parse the subtitle and return DetectedFont objects with Evidence.
        return AnalysisResult()
```

Register with `registry.register(SubtitleAnalyzer())` for Python API use, or
publish a factory in the `fontguard.analyzers` Python entry-point group. CLI loads
installed plugins only with `--plugins`. First registered matching analyzer wins;
custom registries allow replacing defaults. Override `supports` for unusual files.
Plugins must perform no remote requests and enforce parser resource limits.

Files are extension-filtered before scheduling; ignored directories are pruned.
Threads parallelize independent files in bounded batches; PDF parsing stays on
the calling thread because PyMuPDF is not thread-safe. Cache keys include path, mtime, size, SHA256,
analyzer name and version. CSS keys also include local referenced font hashes.
Unchanged files are still hashed; the cache saves parsing work, not all disk I/O.
`--no-cache` leaves no cache directory. Cache format changes must bump the version.
Remove `.fontguard-cache` to reclaim old versions; no automatic eviction in v0.1.

Fingerprints include relative source, font hash/name, rule, risk, usage and license.
Baselines retain findings in reports but exclude matching fingerprints from CI
failure. A severity/rule/usage/hash change produces a new finding. Approvals are
scoped by actual hash and usage, never name; explicit organization prohibitions
take priority. These records document organization assertions, not legal evidence.

# Changelog

## 0.2.0 — 2026-10-02

- Expanded the offline database to 2,052 evidence-backed font families with
  immutable Google Fonts sources and Windows distribution documentation.
- Added eight verified binary SHA256 fingerprints and reproducible import scripts.
- Kept regional families distinct; omitted ambiguous imported aliases and disabled
  ambiguous normalized fallbacks.
- Corrected policy, deduplication and baseline identity for regional-family changes.
- Added containerized native DOCX/PPTX/PDF and actual-font acceptance scripts.
- Corrected HTML inline-style boundaries so a missing final CSS semicolon cannot
  hide a font from organization policy; invalidated earlier analysis caches.

Baseline fingerprints changed to retain family identity; recreate baselines after
review when upgrading from the unpublished 0.1.0 prototype. No purchase status is
inferred by the Windows font records.

## 0.1.0 — 2026-10-02

Initial local CLI prototype: analyzers, risk/policy engines, reports, cache,
baselines, approvals and CI configuration. This prototype was not published.

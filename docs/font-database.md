# Database provenance and scope

[简体中文](font-database.zh-CN.md) | **English** | [Home](../README.en.md)

FontGuard 0.2.0 contains 2,052 font-family records, not 2,052 independently verified
binary builds. It has eight exact SHA256 fingerprints of representative upstream
TTF files. Name matching and version/provenance checks remain necessary for other
font binaries.

## Official Google Fonts import

Repository: https://github.com/google/fonts

Pinned snapshot: `9710da1eacb3be272583c3224dcb70f9da6eadbb`.

The complete Git tree contained 2,031 family metadata files. The importer downloaded
each candidate's `METADATA.pb` and its own license text, checked that the declared
license and file agree, and imported 2,020 verified families. Google Fonts catalogue
is identified as the distributor, not presumed to be the designer or copyright
owner. The provenance manifest retains credited designers and font filenames.
The separately curated Noto Sans record was enriched rather than duplicated.
Source Han Sans keeps its direct Adobe source.

The import supports OFL-1.1, Apache-2.0 and Ubuntu-font-1.0. Authoring/rendered output
permissions are distinguished from distribution/embedding conditions. Exact
conditions still depend on the original license and any Reserved Font Names.
Third-party fonts have not been relicensed as Apache-2.0 by FontGuard.

`data/imports/google-fonts.json` records the immutable source commit, per-family
metadata/license SHA256, source paths, excluded entries and removed ambiguous
aliases. Eleven upstream entries were excluded due to missing per-family license
files or a retired `_todelist` duplicate. Protobuf C-style escaped names are parsed
without executing code. Ambiguous full-name aliases are omitted before validation.

Maintainer import (network access is explicit):

```sh
mkdir -p artifacts
curl -fsSL 'https://api.github.com/repos/google/fonts/git/trees/9710da1eacb3be272583c3224dcb70f9da6eadbb?recursive=1' -o artifacts/google-fonts-tree.json
python scripts/import_google_fonts.py --tree artifacts/google-fonts-tree.json --allow-exclusions
python scripts/fetch_test_fonts.py
fontguard database validate
```

Obtain the complete upstream tree from the GitHub Git Trees API and retain its
commit SHA. Importing is a maintainer operation; normal scans never update data or
contact Google. Review YAML and provenance changes before committing an update.

`data/imports/verified-hashes.json` records the exact source URL, byte size and SHA256
for eight real fonts: Kosugi, Roboto Slab, JetBrains Mono, Lato, Lobster, Long Cang,
Noto Sans and Ubuntu. Test binaries stay in ignored `artifacts/`, outside the
published source repository. Existing hashes are preserved across re-imports.

## Windows-distributed fonts

31 common Windows font families cite their official Microsoft typography pages
and Microsoft's Windows font redistribution FAQ. Chinese aliases cover Microsoft
YaHei, Microsoft JhengHei, SimSun/NSimSun, SimHei, KaiTi, FangSong and DengXian.
The distributor label does not assert that Microsoft owns every included font.

`LicenseRef-Windows-Fonts` is a local license reference describing Windows software
terms and potential extended rights, not an invented SPDX open-source license.
The facts apply to Windows-supplied versions only. Creating rendered commercial
output with appropriately licensed software can be allowed; software entitlement
cannot be verified from a document, so these uses require REVIEW. Merely naming a
font in a CSS font stack is allowed; self-hosting font files, app embedding and
redistribution require separate verification. Document embedding flags and the
authoring software also matter. No Windows font binaries are downloaded or
redistributed by the importer.

Source: https://learn.microsoft.com/en-us/typography/fonts/font-faq

`data/imports/windows-fonts.json` retains source-page hashes and verification dates.
`scripts/import_windows_fonts.py` is the reproducible maintainer importer.

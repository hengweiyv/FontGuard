"""Curate Windows-distributed families from official Microsoft typography pages.

No Microsoft font binaries are downloaded or redistributed. Permissions are
scoped to the documented Windows distribution, never all fonts sharing a name.
"""

import hashlib
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import yaml

FAMILIES = [
    ("Arial", "arial", ["ArialMT"]),
    ("Times New Roman", "times-new-roman", ["TimesNewRomanPSMT"]),
    ("Courier New", "courier-new", ["CourierNewPSMT"]),
    ("Verdana", "verdana", []),
    ("Tahoma", "tahoma", []),
    ("Trebuchet MS", "trebuchet-ms", []),
    ("Georgia", "georgia", []),
    ("Calibri", "calibri", []),
    ("Cambria", "cambria", []),
    ("Candara", "candara", []),
    ("Consolas", "consolas", []),
    ("Corbel", "corbel", []),
    ("Constantia", "constantia", []),
    ("Segoe UI", "segoe-ui", []),
    ("Microsoft YaHei", "microsoft-yahei", ["微软雅黑", "微軟雅黑"]),
    ("Microsoft YaHei UI", "microsoft-yahei", ["微软雅黑 UI"]),
    ("Microsoft JhengHei", "microsoft-jhenghei", ["微软正黑体", "微軟正黑體"]),
    ("SimSun", "simsun", ["宋体", "宋體"]),
    ("NSimSun", "simsun", ["新宋体", "新宋體"]),
    ("SimHei", "simhei", ["黑体", "黑體"]),
    ("KaiTi", "kaiti", ["楷体", "楷體"]),
    ("FangSong", "fangsong", ["仿宋"]),
    ("DengXian", "dengxian", ["等线", "等線"]),
    ("Malgun Gothic", "malgun-gothic", []),
    ("Meiryo", "meiryo", []),
    ("Yu Gothic", "yu-gothic", []),
    ("MS Gothic", "ms-gothic", []),
    ("MS Mincho", "ms-mincho", []),
    ("Comic Sans MS", "comic-sans-ms", []),
    ("Impact", "impact", []),
    ("Palatino Linotype", "palatino-linotype", []),
]


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    faq = "https://learn.microsoft.com/en-us/typography/fonts/font-faq"
    cache = root / "artifacts/windows-font-sources"
    cache.mkdir(parents=True, exist_ok=True)

    def fetch_page(slug: str) -> tuple[str, bytes]:
        url = f"https://learn.microsoft.com/en-us/typography/font-list/{slug}"
        path = cache / (slug + ".html")
        if not path.is_file():
            request = urllib.request.Request(url, headers={"User-Agent": "FontGuard-data-import"})
            path.write_bytes(urllib.request.urlopen(request, timeout=45).read())
        content = path.read_bytes()
        if b"Products that supply this font" not in content or b"Windows" not in content:
            raise ValueError(f"Cannot verify documented Windows distribution: {slug}")
        return slug, content

    with ThreadPoolExecutor(max_workers=6) as pool:
        pages = dict(pool.map(fetch_page, sorted({slug for _, slug, _ in FAMILIES})))
    permissions = {
        u: "requires_license"
        for u in [
            "personal",
            "commercial_design",
            "print",
            "advertising",
            "video",
            "logo",
            "ebook",
            "document_embedding",
            "app_embedding",
            "software_distribution",
            "font_redistribution",
            "webfont",
        ]
    }
    permissions["website"] = "allowed"
    sources = []
    directory = root / "data/fonts/windows"
    directory.mkdir(parents=True, exist_ok=True)
    for name, slug, aliases in FAMILIES:
        url = f"https://learn.microsoft.com/en-us/typography/font-list/{slug}"
        record = {
            "id": "windows-" + name.lower().replace(" ", "-"),
            "name": name,
            "aliases": aliases,
            "vendor": "Microsoft Windows font distribution",
            "license": {
                "type": "LicenseRef-Windows-Fonts",
                "conditions": [
                    "Windows-supplied versions only; verify software entitlement and provenance.",
                    "CSS naming is allowed; self-hosting and redistribution need separate rights.",
                    "Document embedding depends on font embedding flags and authoring software.",
                    "Rendered output may be allowed; software licensing is not verified.",
                ],
            },
            "usage": permissions,
            "sources": [
                {"type": "official_documentation", "url": faq},
                {"type": "official_vendor", "url": url},
            ],
            "verified_at": date.today().isoformat(),
        }
        (directory / (record["id"] + ".yaml")).write_text(
            yaml.safe_dump(record, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
        sources.append(
            {"name": name, "url": url, "page_sha256": hashlib.sha256(pages[slug]).hexdigest()}
        )
    for path, value in [
        (
            root / "data/licenses/windows-fonts.yaml",
            {
                "id": "LicenseRef-Windows-Fonts",
                "name": "Windows-supplied fonts: software terms and extended rights",
                "sources": [{"type": "official_documentation", "url": faq}],
            },
        ),
        (
            root / "data/vendors/windows.yaml",
            {
                "id": "windows-distribution",
                "name": "Microsoft Windows font distribution",
                "url": "https://learn.microsoft.com/en-us/typography/",
            },
        ),
    ]:
        path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    (root / "data/imports/windows-fonts.json").write_text(
        json.dumps(
            {
                "verified_at": date.today().isoformat(),
                "families_verified": len(FAMILIES),
                "sources": sources,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Verified {len(FAMILIES)} Windows-distributed families; no font binaries redistributed")


if __name__ == "__main__":
    main()

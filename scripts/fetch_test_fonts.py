"""Download representative official binaries and record verified exact hashes."""

import hashlib
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote

import yaml


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "data/imports/google-fonts.json").read_text(encoding="utf-8"))
    commit = manifest["commit"]
    wanted = {
        "ofl/lato",
        "ofl/lobster",
        "ofl/notosans",
        "ofl/longcang",
        "apache/robotoslab",
        "apache/kosugi",
        "ufl/ubuntu",
        "ofl/jetbrainsmono",
    }
    families = [f for f in manifest["families"] if f["directory"] in wanted]
    directory = root / "artifacts/e2e/fonts"
    directory.mkdir(parents=True, exist_ok=True)

    def download(family: dict) -> dict:
        filenames = family["font_files"]
        filename = next((n for n in filenames if "Regular" in n), filenames[0])
        path = f"{family['directory']}/{filename}"
        url = f"https://raw.githubusercontent.com/google/fonts/{commit}/" + quote(path, safe="/")
        local = directory / ("company-" + family["directory"].replace("/", "-") + ".ttf")
        if not local.exists():
            request = urllib.request.Request(url, headers={"User-Agent": "FontGuard-real-tests"})
            local.write_bytes(urllib.request.urlopen(request, timeout=120).read())
        return {
            "name": family["name"],
            "file": local.name,
            "source_url": url,
            "sha256": hashlib.sha256(local.read_bytes()).hexdigest(),
            "size": local.stat().st_size,
        }

    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(download, families))
    paths = list((root / "data/fonts").rglob("*.yaml"))
    names = {}
    for path in paths:
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
        names[record["name"]] = (path, record)
    for sample in records:
        path, record = names[sample["name"]]
        record["hashes"] = sorted(set(record.get("hashes", []) + [sample["sha256"]]))
        write = yaml.safe_dump(record, sort_keys=False, allow_unicode=True)
        path.write_text(write, encoding="utf-8")
    (root / "data/imports/verified-hashes.json").write_text(
        json.dumps({"repository_commit": commit, "samples": records}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"Downloaded {len(records)} actual fonts, {sum(r['size'] for r in records)} bytes")


if __name__ == "__main__":
    main()

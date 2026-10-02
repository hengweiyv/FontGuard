"""Reproducible maintainer import from a pinned official Google Fonts snapshot.

This script uses the network explicitly. Normal FontGuard scans remain offline.
It imports metadata and license texts, never downloads the whole binary repository.
"""

import argparse
import ast
import hashlib
import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from urllib.parse import quote

import yaml

PERMISSIONS = {
    "personal": "allowed",
    "commercial_design": "allowed",
    "print": "allowed",
    "advertising": "allowed",
    "website": "allowed",
    "video": "allowed",
    "logo": "allowed",
    "webfont": "conditional",
    "ebook": "conditional",
    "document_embedding": "conditional",
    "app_embedding": "conditional",
    "software_distribution": "conditional",
    "font_redistribution": "conditional",
}
LICENSES = {
    "ofl": ("OFL", "OFL-1.1", "OFL.txt"),
    "apache": ("APACHE2", "Apache-2.0", "LICENSE.txt"),
    "ufl": ("UFL", "Ubuntu-font-1.0", "LICENCE.txt"),
}
CONDITIONS = {
    "OFL-1.1": [
        "Retain copyright and license notices when distributing font software.",
        "Respect Reserved Font Names on modifications; font software cannot be sold alone.",
    ],
    "Apache-2.0": [
        "Retain license/copyright notices, applicable NOTICE contents and change notices.",
        "Trademark rights are not granted by the license.",
    ],
    "Ubuntu-font-1.0": [
        "Redistribute font software under the Ubuntu Font Licence with its notices.",
        "Respect modified-version naming rules; font software cannot be sold alone.",
    ],
}


def write_yaml(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def fetch(url: str, cache: Path) -> bytes:
    if cache.is_file():
        return cache.read_bytes()
    cache.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(4):
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "FontGuard-data-import/0.1"}
            )
            with urllib.request.urlopen(request, timeout=45) as response:
                content = response.read()
            cache.write_bytes(content)
            return content
        except (OSError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("Unreachable")


def quoted_values(text: str, key: str, *, top_level: bool = False) -> list[str]:
    indentation = "" if top_level else r"\s*"
    matches = re.findall(rf'(?m)^{indentation}{key}:\s*("(?:\\.|[^"\\])*")', text)
    values = []
    for value in matches:
        try:
            values.append(json.loads(value))
        except json.JSONDecodeError:
            # Protobuf text permits C-style escapes such as \\' in N'Ko names.
            parsed = ast.literal_eval(value)
            if not isinstance(parsed, str):
                raise ValueError("Metadata value must be a string") from None
            values.append(parsed)
    return values


def sanitize_aliases(project: Path) -> list[dict[str, object]]:
    from fontguard.identity.engine import exact_font_name

    records = [
        (file, yaml.safe_load(file.read_text(encoding="utf-8")))
        for file in sorted((project / "data/fonts").rglob("*.yaml"))
    ]
    owners: dict[str, set[str]] = {}
    for _, record in records:
        for name in [record["name"], *record.get("aliases", [])]:
            owners.setdefault(exact_font_name(name), set()).add(record["id"])
    excluded = []
    for file, record in records:
        aliases = record.get("aliases", [])
        removed = [a for a in aliases if len(owners[exact_font_name(a)]) > 1]
        if removed:
            record["aliases"] = [a for a in aliases if a not in removed]
            write_yaml(file, record)
            excluded.append({"id": record["id"], "ambiguous_aliases": removed})
    return excluded


def import_snapshot(
    project: Path, tree_file: Path, workers: int, *, allow_exclusions: bool = False
) -> None:
    tree = json.loads(tree_file.read_text(encoding="utf-8"))
    if tree.get("truncated") or not re.fullmatch(r"[0-9a-f]{40}", tree["sha"]):
        raise ValueError("Require a complete Git tree and immutable commit SHA.")
    commit = tree["sha"]
    entries = {entry["path"]: entry for entry in tree["tree"]}
    metadata_paths = sorted(
        path
        for path in entries
        if path.endswith("/METADATA.pb") and path.split("/", 1)[0] in LICENSES
    )
    base = f"https://raw.githubusercontent.com/google/fonts/{commit}/"
    cache = project / "artifacts" / "upstream" / commit

    def read_family(metadata_path: str) -> dict[str, object]:
        directory = metadata_path.rsplit("/", 1)[0]
        if "_todelist" in directory:
            raise ValueError("Retired upstream duplicate marked _todelist; excluded")
        category = directory.split("/", 1)[0]
        expected, license_id, expected_file = LICENSES[category]
        license_candidates = [
            f"{directory}/{name}"
            for name in (expected_file, "OFL.txt", "LICENSE.txt", "LICENCE.txt")
            if f"{directory}/{name}" in entries
        ]
        if not license_candidates:
            raise ValueError(f"No official license file: {directory}")
        license_path = license_candidates[0]
        metadata = fetch(base + quote(metadata_path, safe="/"), cache / metadata_path)
        license_bytes = fetch(base + quote(license_path, safe="/"), cache / license_path)
        text = metadata.decode("utf-8")
        license_text = license_bytes.decode("utf-8-sig").casefold()
        actual = quoted_values(text, "license", top_level=True)
        if actual != [expected]:
            raise ValueError(f"License metadata disagrees with directory: {directory}: {actual}")
        markers = {
            "OFL-1.1": "sil open font license",
            "Apache-2.0": "apache license",
            "Ubuntu-font-1.0": "ubuntu font licen",
        }
        if markers[license_id] not in license_text:
            raise ValueError(f"License file does not confirm expected license: {directory}")
        name = quoted_values(text, "name", top_level=True)[0]
        aliases = sorted(
            set(
                quoted_values(text, "post_script_name")
                + quoted_values(text, "full_name")
                + quoted_values(text, "display_name", top_level=True)
            )
            - {name}
        )
        return {
            "directory": directory,
            "name": name,
            "aliases": aliases,
            "license": license_id,
            "license_path": license_path,
            "metadata_path": metadata_path,
            "metadata_sha256": hashlib.sha256(metadata).hexdigest(),
            "license_sha256": hashlib.sha256(license_bytes).hexdigest(),
            "designers": quoted_values(text, "designer", top_level=True),
            "font_files": quoted_values(text, "filename"),
        }

    families = []
    errors = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {pool.submit(read_family, path): path for path in metadata_paths}
        for done, future in enumerate(as_completed(pending), 1):
            try:
                families.append(future.result())
            except Exception as exc:
                errors.append({"path": pending[future], "error": str(exc)})
            if done % 100 == 0 or done == len(pending):
                print(f"Verified {done}/{len(pending)} families; errors={len(errors)}", flush=True)
    if errors:
        (project / "artifacts" / "import-errors.json").write_text(
            json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if not allow_exclusions:
            raise ValueError(f"Import incomplete: {len(errors)} errors; no records written.")
        print(
            f"Excluding {len(errors)} unverified upstream entries; see import-errors.json",
            flush=True,
        )
    existing = {}
    for file in (project / "data" / "fonts").rglob("*.yaml"):
        record = yaml.safe_load(file.read_text(encoding="utf-8"))
        existing[record["name"].casefold()] = (file, record)
    imported = []
    for family in sorted(families, key=lambda f: str(f["directory"])):
        directory = str(family["directory"])
        name = str(family["name"])
        license_id = str(family["license"])
        metadata_url = f"https://github.com/google/fonts/blob/{commit}/{family['metadata_path']}"
        license_url = f"https://github.com/google/fonts/blob/{commit}/{family['license_path']}"
        if name.casefold() in existing:
            file, record = existing[name.casefold()]
            if record["license"]["type"] != license_id:
                raise ValueError(f"Existing license mismatch: {name}")
            record["aliases"] = sorted(set(record.get("aliases", []) + list(family["aliases"])))
            record["sources"] = [
                s for s in record["sources"] if "google/fonts/blob/" not in s["url"]
            ]
        else:
            file = project / "data" / "fonts" / "google" / (directory.replace("/", "-") + ".yaml")
            record = {
                "id": "gf-" + directory.replace("/", "-"),
                "name": name,
                "aliases": family["aliases"],
                "vendor": "Google Fonts catalogue",
                "license": {"type": license_id, "conditions": CONDITIONS[license_id]},
                "usage": PERMISSIONS,
                "sources": [],
            }
        record["sources"].extend(
            [
                {"type": "official_license", "url": license_url},
                {"type": "official_repository", "url": metadata_url},
            ]
        )
        record["verified_at"] = date.today().isoformat()
        write_yaml(file, record)
        imported.append(family)
    write_yaml(
        project / "data" / "vendors" / "google-fonts.yaml",
        {
            "id": "google-fonts",
            "name": "Google Fonts catalogue",
            "url": "https://github.com/google/fonts",
        },
    )
    for license_id, name, url in [
        ("Apache-2.0", "Apache License 2.0", "https://www.apache.org/licenses/LICENSE-2.0"),
        ("Ubuntu-font-1.0", "Ubuntu Font Licence 1.0", "https://ubuntu.com/legal/font-licence"),
    ]:
        write_yaml(
            project / "data" / "licenses" / (license_id.lower() + ".yaml"),
            {"id": license_id, "name": name, "sources": [{"type": "official_license", "url": url}]},
        )
    manifest = project / "data" / "imports" / "google-fonts.json"
    manifest.parent.mkdir(exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "repository": "https://github.com/google/fonts",
                "commit": commit,
                "verified_at": date.today().isoformat(),
                "families_verified": len(imported),
                "excluded": errors,
                "omitted_ambiguous_aliases": sanitize_aliases(project),
                "families": imported,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Imported {len(imported)} verified families from {commit}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--project", type=Path, default=Path("."))
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument(
        "--allow-exclusions",
        action="store_true",
        help="Import only verified families; preserve rejected entries in manifest",
    )
    args = parser.parse_args()
    import_snapshot(
        args.project.resolve(), args.tree, args.workers, allow_exclusions=args.allow_exclusions
    )

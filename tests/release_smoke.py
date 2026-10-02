"""Verify an installed wheel without accidentally importing the editable source."""

import json
import socket
import sys
from pathlib import Path

import jsonschema


def verify(install_directory: Path) -> None:
    project = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(install_directory.resolve()))
    import fontguard
    from fontguard.cli.main import main
    from fontguard.database.loader import default_data_path

    assert Path(fontguard.__file__).is_relative_to(install_directory.resolve())
    assert default_data_path().is_relative_to(install_directory.resolve())

    def deny_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("Network connection attempted during offline wheel smoke test")

    socket.socket.connect = deny_network
    artifacts = project / "artifacts"
    artifacts.mkdir(exist_ok=True)
    sample = project / "examples" / "site.css"
    assert main(["database", "validate"]) == 0
    for format in ("json", "sarif", "html", "terminal"):
        output = artifacts / ("sample-report." + format)
        assert (
            main(
                [
                    "scan",
                    str(sample),
                    "--usage",
                    "commercial_design",
                    "--fail-on",
                    "high",
                    "--format",
                    format,
                    "--output",
                    str(output),
                    "--no-cache",
                ]
            )
            == 0
        )
    payload = json.loads((artifacts / "sample-report.json").read_text(encoding="utf-8"))
    assert payload["summary"] == {"safe": 2, "low": 0, "review": 0, "high": 0, "unknown": 1}
    schema = json.loads(
        (project / "tests" / "schemas" / "sarif-2.1.0.json").read_text(encoding="utf-8")
    )
    sarif = json.loads((artifacts / "sample-report.sarif").read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(sarif)
    assert (
        main(
            [
                "scan",
                str(sample),
                "--fail-on",
                "unknown",
                "--format",
                "json",
                "--output",
                str(artifacts / "unknown-failure.json"),
                "--no-cache",
            ]
        )
        == 1
    )
    assert (
        main(
            [
                "scan",
                str(artifacts / "missing.pdf"),
                "--format",
                "json",
                "--output",
                str(artifacts / "scan-error.json"),
                "--no-cache",
            ]
        )
        == 2
    )
    print(
        json.dumps(
            {
                "wheel_module": fontguard.__file__,
                "database": str(default_data_path()),
                "offline_scan": "passed",
                "sarif_schema": "passed",
                "exit_codes": [0, 1, 2],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    verify(Path(sys.argv[1]))

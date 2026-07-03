from __future__ import annotations

from pathlib import Path
from typing import Any

from scenario_forge.artifacts.package_writer import write_yaml_artifact


def write_suite_manifest(suite_root: Path, suite_id: str, packages: list[dict[str, Any]]) -> Path:
    return write_yaml_artifact(
        suite_root / "suite_manifest.yaml",
        {
            "schema_version": "scenario-suite/v0.2",
            "suite_id": suite_id,
            "packages": packages,
        },
    )

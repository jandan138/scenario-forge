from __future__ import annotations

from pathlib import Path
from typing import Any

from scenario_forge.artifacts.package_writer import write_yaml_artifact


def adapter_report_yaml(
    status: str,
    entrypoints: dict[str, str],
    blockers: tuple[str, ...],
    artifacts: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema_version": "ebench-adapter-report/v0.1",
        "adapter": "ebench",
        "status": status,
        "entrypoints": entrypoints,
        "blockers": list(blockers),
        "artifacts": list(artifacts),
    }


def write_adapter_report(
    out_dir: str | Path,
    status: str,
    entrypoints: dict[str, str],
    blockers: tuple[str, ...],
    artifacts: tuple[str, ...],
) -> Path:
    return write_yaml_artifact(
        Path(out_dir) / "adapter_report.yaml",
        adapter_report_yaml(status, entrypoints, blockers, artifacts),
    )

from __future__ import annotations

from pathlib import Path
from typing import Any

from scenario_forge.package import PackageManifest

EBENCH_EXPORT_SCHEMA_VERSION = "ebench-scenario-export/v0.1"


def package_export_yaml(
    manifest: PackageManifest,
    out_dir: Path,
    primary_success_metric: dict[str, Any],
) -> dict[str, Any]:
    hints = primary_success_metric.get("adapter_hints", {})
    ebench_hints = hints.get("ebench", {}) if isinstance(hints, dict) else {}
    success_metric = str(ebench_hints.get("success_metric", primary_success_metric["id"]))
    return {
        "schema_version": EBENCH_EXPORT_SCHEMA_VERSION,
        "source_package": {
            "package_id": manifest.package_id,
            "schema_version": manifest.schema_version,
            "targets": list(manifest.targets),
        },
        "entrypoints": {
            "scene_usd": _relative(out_dir, manifest.entrypoints["scene_usd"]),
            "task": _relative(out_dir, manifest.entrypoints["task"]),
            "robot": _relative(out_dir, manifest.entrypoints["robot"]),
            "metrics": _relative(out_dir, manifest.entrypoints["metrics"]),
        },
        "assets": {
            "asset_lock": _relative(out_dir, manifest.assets["lock"]),
        },
        "runtime_hints": {
            "simulator": "usd_capable",
            "reset_policy": "deterministic",
            "max_episode_steps": 300,
            "success_metric": success_metric,
            "success_predicate": primary_success_metric.get("predicate", "object_in_zone"),
        },
        "adapter_validation": {
            "status": "passed",
            "report": "adapter_report.yaml",
        },
    }


def task_entrypoint_yaml(
    manifest: PackageManifest,
    primary_success_metric: dict[str, Any],
    task_data: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "ebench-task-entrypoint/v0.1",
        "package_id": manifest.package_id,
        "task_id": task_data.get("task_id", manifest.package_id),
        "task_family": task_data.get("task_family", "unspecified"),
        "instruction": task_data.get("instruction", ""),
        "success_metric": primary_success_metric["id"],
        "metric_role": primary_success_metric.get("role"),
        "bindings": task_data.get("bindings", {}),
    }


def _relative(out_dir: Path, package_relative_path: str) -> str:
    return str(Path("../..") / package_relative_path).replace("\\", "/")

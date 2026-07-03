from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scenario_forge.adapters.ebench.report import write_adapter_report
from scenario_forge.adapters.ebench.schema import package_export_yaml, task_entrypoint_yaml
from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.package import PackageError, load_package_manifest, validate_package
from scenario_forge.task.metrics import find_primary_success_metric


class EBenchExportError(ValueError):
    """Raised when an EBench export gate fails."""


@dataclass(frozen=True)
class EBenchExportResult:
    ok: bool
    output_dir: Path
    artifacts: tuple[Path, ...]
    blockers: tuple[str, ...]


def export_ebench_package(
    package_dir: str | Path,
    out_dir: str | Path | None = None,
) -> EBenchExportResult:
    root = Path(package_dir)
    output_dir = Path(out_dir) if out_dir is not None else root / "adapters" / "ebench"
    output_dir.mkdir(parents=True, exist_ok=True)

    blockers = _package_export_blockers(root)
    if blockers:
        _write_failed_package_report(root, output_dir, blockers)
        raise EBenchExportError("; ".join(blockers))

    manifest = load_package_manifest(root)
    primary_metric = find_primary_success_metric(root / manifest.entrypoints["metrics"])
    assert primary_metric is not None
    task_data = _load_yaml(root / manifest.entrypoints["task"])
    entrypoints = _adapter_entrypoints(manifest)

    package_path = write_yaml_artifact(output_dir / "package.yaml", package_export_yaml(manifest, output_dir, primary_metric))
    task_entrypoint_path = write_yaml_artifact(
        output_dir / "task_entrypoint.yaml",
        task_entrypoint_yaml(manifest, primary_metric, task_data),
    )
    report_path = write_adapter_report(
        output_dir,
        status="passed",
        entrypoints=entrypoints,
        blockers=(),
        artifacts=("package.yaml", "task_entrypoint.yaml", "adapter_report.yaml"),
    )
    return EBenchExportResult(
        ok=True,
        output_dir=output_dir,
        artifacts=(package_path, task_entrypoint_path, report_path),
        blockers=(),
    )


def export_ebench_suite(suite_dir: str | Path) -> EBenchExportResult:
    root = Path(suite_dir)
    manifest_path = root / "suite_manifest.yaml"
    output_dir = root / "adapters" / "ebench"
    output_dir.mkdir(parents=True, exist_ok=True)
    if not manifest_path.exists():
        blockers = ("Missing suite manifest: suite_manifest.yaml",)
        report_path = write_adapter_report(output_dir, "failed", {}, blockers, ("adapter_report.yaml",))
        return EBenchExportResult(False, output_dir, (report_path,), blockers)

    suite_manifest = _load_yaml(manifest_path)
    raw_packages = suite_manifest.get("packages")
    blockers: list[str] = []
    task_index: list[dict[str, Any]] = []
    if not isinstance(raw_packages, list):
        blockers.append("Suite manifest field 'packages' must be a list")
    else:
        for index, item in enumerate(raw_packages):
            if not isinstance(item, dict):
                blockers.append(f"Suite package entry {index} must be a mapping")
                continue
            package_path = item.get("path")
            package_id = item.get("package_id")
            if not isinstance(package_path, str) or not isinstance(package_id, str):
                blockers.append(f"Suite package entry {index} requires package_id and path")
                continue
            task_index.append(
                {
                    "package_id": package_id,
                    "path": package_path,
                    "split": item.get("split", "default"),
                    "difficulty": item.get("difficulty", "unspecified"),
                    "task_family": item.get("task_family", "unspecified"),
                    "adapter_package": str(Path(package_path) / "adapters" / "ebench" / "package.yaml"),
                }
            )

    status = "failed" if blockers else "passed"
    suite_export_path = write_yaml_artifact(
        output_dir / "suite_export.yaml",
        {
            "schema_version": "ebench-suite-export/v0.1",
            "source_suite": suite_manifest.get("suite_id", root.name),
            "status": status,
            "task_index": "task_index.yaml",
        },
    )
    task_index_path = write_yaml_artifact(
        output_dir / "task_index.yaml",
        {"schema_version": "ebench-task-index/v0.1", "tasks": task_index},
    )
    report_path = write_adapter_report(
        output_dir,
        status=status,
        entrypoints={"suite_manifest": "suite_manifest.yaml", "task_index": "adapters/ebench/task_index.yaml"},
        blockers=tuple(blockers),
        artifacts=("suite_export.yaml", "task_index.yaml", "adapter_report.yaml"),
    )
    return EBenchExportResult(
        ok=not blockers,
        output_dir=output_dir,
        artifacts=(suite_export_path, task_index_path, report_path),
        blockers=tuple(blockers),
    )


def _package_export_blockers(root: Path) -> tuple[str, ...]:
    try:
        manifest = load_package_manifest(root)
    except PackageError as exc:
        return (str(exc),)

    blockers: list[str] = []
    if "ebench" not in manifest.targets:
        blockers.append("Package manifest does not target ebench")

    report = validate_package(root)
    blockers.extend(report.messages)

    required_paths = {
        "scene_usd": manifest.entrypoints.get("scene_usd"),
        "task": manifest.entrypoints.get("task"),
        "robot": manifest.entrypoints.get("robot"),
        "metrics": manifest.entrypoints.get("metrics"),
        "asset_lock": manifest.assets.get("lock"),
    }
    for relative_path in required_paths.values():
        if relative_path is not None and not (root / relative_path).exists():
            blockers.append(f"Missing required EBench file: {relative_path}")

    metrics_path = manifest.entrypoints.get("metrics")
    if metrics_path is None or find_primary_success_metric(root / metrics_path) is None:
        blockers.append("Missing primary success metric")

    return _dedupe(blockers)


def _write_failed_package_report(root: Path, output_dir: Path, blockers: tuple[str, ...]) -> Path:
    try:
        manifest = load_package_manifest(root)
        entrypoints = _adapter_entrypoints(manifest)
    except PackageError:
        entrypoints = {}
    return write_adapter_report(
        output_dir,
        status="failed",
        entrypoints=entrypoints,
        blockers=blockers,
        artifacts=("adapter_report.yaml",),
    )


def _adapter_entrypoints(manifest: Any) -> dict[str, str]:
    return {
        "scene_usd": manifest.entrypoints["scene_usd"],
        "task": manifest.entrypoints["task"],
        "robot": manifest.entrypoints["robot"],
        "metrics": manifest.entrypoints["metrics"],
        "asset_lock": manifest.assets["lock"],
        "validation_report": manifest.validation["report"],
    }


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _dedupe(messages: list[str]) -> tuple[str, ...]:
    deduped: list[str] = []
    for message in messages:
        if message not in deduped:
            deduped.append(message)
    return tuple(deduped)

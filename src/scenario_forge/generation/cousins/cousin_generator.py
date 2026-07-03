from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import copytree, rmtree
from typing import Any

import yaml

from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.generation.cousins.cousin_plan import COUSIN_PLAN_SCHEMA_VERSION
from scenario_forge.package import load_package_manifest
from scenario_forge.scene.usd_compiler import compile_usd_scene


class CousinGenerationError(ValueError):
    """Raised when cousin packages cannot be generated."""


@dataclass(frozen=True)
class CousinGenerationResult:
    suite_root: Path
    package_count: int
    packages: tuple[Path, ...]


def generate_cousin_packages(
    base_package: str | Path,
    cousin_plan_path: str | Path,
    out_dir: str | Path,
) -> CousinGenerationResult:
    base_root = Path(base_package)
    plan = _load_plan(Path(cousin_plan_path))
    count = _cousin_count(plan)
    suite_root = Path(out_dir)
    packages_root = suite_root / "packages"
    packages_root.mkdir(parents=True, exist_ok=True)
    base_manifest = load_package_manifest(base_root)

    packages: list[Path] = []
    suite_entries: list[dict[str, Any]] = []
    for index in range(count):
        cousin_id = f"{base_manifest.package_id}_cousin_{index:03d}"
        cousin_root = packages_root / cousin_id
        if cousin_root.exists():
            rmtree(cousin_root)
        copytree(base_root, cousin_root)
        _rewrite_package_id(cousin_root, cousin_id)
        _perturb_scene_instances(cousin_root, index)
        _write_variation(cousin_root, plan, base_manifest.package_id, cousin_id)
        compile_usd_scene(
            package_root=cousin_root,
            instances_path=cousin_root / "scene" / "instances.yaml",
            asset_lock_path=cousin_root / "locks" / "asset_lock.yaml",
            out_path=cousin_root / "scene" / "main.usda",
        )
        packages.append(cousin_root)
        suite_entries.append(
            {
                "package_id": cousin_id,
                "path": str(cousin_root),
                "split": "cousin",
                "difficulty": "medium",
                "task_family": _task_family(cousin_root),
            }
        )

    write_yaml_artifact(
        suite_root / "suite_manifest.yaml",
        {
            "schema_version": "scenario-suite/v0.2",
            "suite_id": f"{base_manifest.package_id}_cousins",
            "packages": suite_entries,
        },
    )
    return CousinGenerationResult(
        suite_root=suite_root,
        package_count=len(packages),
        packages=tuple(packages),
    )


def _load_plan(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise CousinGenerationError(f"Cousin plan must be a mapping: {path}")
    if data.get("schema_version") != COUSIN_PLAN_SCHEMA_VERSION:
        raise CousinGenerationError("Unsupported cousin plan schema_version")
    return data


def _cousin_count(plan: dict[str, Any]) -> int:
    cousins = plan.get("cousins")
    if not isinstance(cousins, dict) or not isinstance(cousins.get("count"), int):
        raise CousinGenerationError("Cousin plan field 'cousins.count' must be an integer")
    return int(cousins["count"])


def _rewrite_package_id(root: Path, package_id: str) -> None:
    manifest = _load_yaml(root / "manifest.yaml")
    manifest["package_id"] = package_id
    write_yaml_artifact(root / "manifest.yaml", manifest)


def _perturb_scene_instances(root: Path, index: int) -> None:
    path = root / "scene" / "instances.yaml"
    data = _load_yaml(path)
    raw_instances = data.get("instances", [])
    if not isinstance(raw_instances, list):
        raise CousinGenerationError("scene instances must be a list")
    offset = round(0.02 * (index + 1), 4)
    for raw_instance in raw_instances:
        if not isinstance(raw_instance, dict):
            continue
        pose = raw_instance.get("pose")
        if isinstance(pose, dict):
            xyz = pose.get("xyz")
            if isinstance(xyz, list) and len(xyz) == 3 and isinstance(xyz[1], int | float):
                xyz[1] = round(float(xyz[1]) + offset, 4)
    write_yaml_artifact(path, data)


def _write_variation(
    root: Path,
    plan: dict[str, Any],
    base_package_id: str,
    cousin_package_id: str,
) -> None:
    axes = plan.get("variation_axes", [])
    write_yaml_artifact(
        root / "provenance" / "cousin_variation.yaml",
        {
            "schema_version": "cousin-variation/v0.1",
            "base_package": base_package_id,
            "cousin_package": cousin_package_id,
            "variation_axes": axes if isinstance(axes, list) else [],
            "constraints": plan.get("constraints", []),
        },
    )


def _task_family(root: Path) -> str:
    task = _load_yaml(root / "task" / "task.yaml")
    value = task.get("task_family", "unspecified")
    return value if isinstance(value, str) else "unspecified"


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise CousinGenerationError(f"YAML artifact must be a mapping: {path}")
    return data

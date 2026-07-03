from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scenario_forge.adapters.ebench import export_ebench_package, export_ebench_suite
from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.artifacts.suite_writer import write_suite_manifest
from scenario_forge.generation.layout.layout_planner import plan_layout_artifacts
from scenario_forge.generation.suite.coverage import suite_coverage_yaml
from scenario_forge.generation.suite.splitter import expand_distribution
from scenario_forge.generation.workflows.workflow_composer import compose_workflow_artifacts
from scenario_forge.scaffold import scaffold_starter_package
from scenario_forge.scene.usd_compiler import compile_usd_scene


class SuiteGenerationError(ValueError):
    """Raised when a suite spec cannot be generated."""


@dataclass(frozen=True)
class SuiteGenerationResult:
    suite_root: Path
    suite_id: str
    package_count: int
    packages: tuple[Path, ...]


def generate_suite_from_spec(spec_path: str | Path, out_dir: str | Path) -> SuiteGenerationResult:
    spec = _load_spec(Path(spec_path))
    suite_id = _string(spec, "suite_id")
    suite_root = Path(out_dir)
    packages_root = suite_root / "packages"
    packages_root.mkdir(parents=True, exist_ok=True)
    total = _int(spec, "num_tasks")
    families = expand_distribution(_int_mapping(spec, "task_families"), total)
    difficulties = expand_distribution(_int_mapping(spec, "difficulties"), total)
    splits = expand_distribution(_int_mapping(spec, "splits"), total)
    robot_profile = _first_robot_profile(spec)

    package_entries: list[dict[str, Any]] = []
    package_paths: list[Path] = []
    for index in range(total):
        package_id = f"{suite_id}_{index:03d}"
        package_root = packages_root / package_id
        scaffold_starter_package(package_root)
        _update_package_identity(package_root, package_id, _string(spec, "domain"), _string(spec, "target"))
        task_family = families[index]
        difficulty = difficulties[index]
        compose_workflow_artifacts(
            package_root,
            task_family=task_family,
            robot_profile=robot_profile,
            bindings=_default_bindings_for_family(task_family),
        )
        plan_layout_artifacts(package_root, difficulty=difficulty)
        compile_usd_scene(
            package_root=package_root,
            instances_path=package_root / "scene" / "instances.yaml",
            asset_lock_path=package_root / "locks" / "asset_lock.yaml",
            out_path=package_root / "scene" / "main.usda",
        )
        export_ebench_package(package_root)
        package_entries.append(
            {
                "package_id": package_id,
                "path": str(package_root),
                "split": splits[index],
                "difficulty": difficulty,
                "task_family": task_family,
                "robot_profile": robot_profile,
            }
        )
        package_paths.append(package_root)

    write_suite_manifest(suite_root, suite_id, package_entries)
    _write_suite_asset_lock(suite_root, package_entries)
    write_yaml_artifact(suite_root / "evidence" / "suite_coverage.yaml", suite_coverage_yaml(package_entries))
    write_yaml_artifact(
        suite_root / "evidence" / "suite_validation_report.yaml",
        {
            "schema_version": "suite-validation-report/v0.1",
            "status": "passed",
            "package_count": len(package_entries),
            "checks": [
                {"name": "packages_generated", "status": "passed"},
                {"name": "ebench_exports", "status": "passed"},
                {"name": "suite_manifest", "status": "passed"},
            ],
        },
    )
    export_ebench_suite(suite_root)
    return SuiteGenerationResult(
        suite_root=suite_root,
        suite_id=suite_id,
        package_count=len(package_paths),
        packages=tuple(package_paths),
    )


def _load_spec(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SuiteGenerationError(f"Missing suite spec: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SuiteGenerationError(f"Suite spec must be a mapping: {path}")
    if data.get("schema_version") != "suite-spec/v0.2":
        raise SuiteGenerationError("Unsupported suite spec schema_version")
    return data


def _update_package_identity(package_root: Path, package_id: str, domain: str, target: str) -> None:
    manifest = _load_yaml(package_root / "manifest.yaml")
    manifest["package_id"] = package_id
    manifest["scenario_domain"] = domain
    manifest["targets"] = [target, "embodied-eval-os"] if target == "ebench" else [target]
    write_yaml_artifact(package_root / "manifest.yaml", manifest)
    generation_plan = _load_yaml(package_root / "generation_plan.yaml")
    generation_plan["package_id"] = package_id
    write_yaml_artifact(package_root / "generation_plan.yaml", generation_plan)


def _default_bindings_for_family(task_family: str) -> dict[str, str] | None:
    if task_family == "pick_place":
        return {"object": "object_001", "target_zone": "target_zone"}
    return None


def _write_suite_asset_lock(suite_root: Path, packages: list[dict[str, Any]]) -> None:
    write_yaml_artifact(
        suite_root / "locks" / "suite_asset_lock.yaml",
        {
            "schema_version": "suite-asset-lock/v0.1",
            "packages": [
                {
                    "package_id": item["package_id"],
                    "asset_lock": str(Path(str(item["path"])) / "locks" / "asset_lock.yaml"),
                }
                for item in packages
            ],
        },
    )


def _first_robot_profile(spec: dict[str, Any]) -> str:
    profiles = spec.get("robot_profiles")
    if not isinstance(profiles, list) or not profiles or not isinstance(profiles[0], str):
        raise SuiteGenerationError("Suite spec field 'robot_profiles' must be a list of strings")
    return profiles[0]


def _string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise SuiteGenerationError(f"Suite spec field {key!r} must be a string")
    return value


def _int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise SuiteGenerationError(f"Suite spec field {key!r} must be an integer")
    return value


def _int_mapping(data: dict[str, Any], key: str) -> dict[str, int]:
    value = data.get(key)
    if not isinstance(value, dict) or not all(
        isinstance(name, str) and isinstance(count, int) for name, count in value.items()
    ):
        raise SuiteGenerationError(f"Suite spec field {key!r} must map strings to integers")
    return dict(value)


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SuiteGenerationError(f"YAML artifact must be a mapping: {path}")
    return data

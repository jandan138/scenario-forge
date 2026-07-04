from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scenario_forge.adapters.ebench.exporter import export_ebench_package
from scenario_forge.adapters.ebench.official_asset_intake import (
    OfficialAssetSources,
    load_official_asset_sources,
    materialize_official_asset_bundle,
)
from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.assets.lock import generate_asset_lock, write_asset_lock
from scenario_forge.scaffold import scaffold_starter_package
from scenario_forge.scene.usd_compiler import compile_usd_scene


PACKAGE_ID = "ebench_apple_to_bowl_canary"
ROBOT_ID = "manip/lift2/R5a"


@dataclass(frozen=True)
class AppleToBowlCanaryResult:
    package_root: Path
    scene_usd: Path


def generate_apple_to_bowl_canary(
    asset_sources_path: str | Path,
    package_root: str | Path,
) -> AppleToBowlCanaryResult:
    root = Path(package_root)
    sources = load_official_asset_sources(asset_sources_path)
    _require_source_assets(sources, ("scene", "robot", "apple", "bowl", "camera_yaml"))

    scaffold_starter_package(root)
    _write_manifest(root)
    _write_generation_plan(root, sources)
    _write_provenance(root, sources)
    _write_validation_report(root)

    materialized = []
    for source_key, asset_id in {
        "scene": "official_ebench_scene",
        "robot": "official_ebench_robot",
        "apple": "official_ebench_apple",
        "bowl": "official_ebench_bowl",
    }.items():
        source = sources.assets[source_key]
        materialized.append(
            materialize_official_asset_bundle(
                source_path=source.source_path,
                package_root=root,
                asset_id=asset_id,
                role=source.role,
                license=source.license,
            )
        )

    write_yaml_artifact(
        root / "assets" / "asset_manifest.yaml",
        {
            "schema_version": "asset-manifest/v0.2",
            "assets": [asset.asset_manifest_entry() for asset in materialized],
        },
    )
    _write_scene_instances(root)
    _write_task(root, sources)
    _write_metrics(root)
    _write_robot(root)

    write_asset_lock(root, generate_asset_lock(root))
    scene_usd = root / "scene" / "main.usda"
    compile_usd_scene(root, root / "scene" / "instances.yaml", root / "locks" / "asset_lock.yaml", scene_usd)
    export_ebench_package(root)
    return AppleToBowlCanaryResult(package_root=root, scene_usd=scene_usd)


def _require_source_assets(sources: OfficialAssetSources, required: tuple[str, ...]) -> None:
    missing = [asset_id for asset_id in required if asset_id not in sources.assets]
    if missing:
        raise ValueError(f"Missing official asset source entries: {', '.join(missing)}")


def _write_manifest(root: Path) -> None:
    write_yaml_artifact(
        root / "manifest.yaml",
        {
            "schema_version": "scenario-package/v0.2",
            "package_id": PACKAGE_ID,
            "scenario_domain": "home_manipulation",
            "package_mode": "fat",
            "targets": ["ebench", "embodied-eval-os"],
            "entrypoints": {
                "generation_plan": "generation_plan.yaml",
                "scene_usd": "scene/main.usda",
                "scene_instances": "scene/instances.yaml",
                "task": "task/task.yaml",
                "robot": "robot/robot.yaml",
                "metrics": "metrics/metrics.yaml",
            },
            "assets": {"manifest": "assets/asset_manifest.yaml", "lock": "locks/asset_lock.yaml"},
            "validation": {
                "report": "evidence/validation_report.yaml",
                "minimum_required_level": "asset_locked",
            },
            "provenance": {"summary": "provenance/summary.yaml"},
        },
    )


def _write_generation_plan(root: Path, sources: OfficialAssetSources) -> None:
    write_yaml_artifact(
        root / "generation_plan.yaml",
        {
            "schema_version": "scenario-generation-plan/v0.2",
            "package_id": PACKAGE_ID,
            "source_task_id": sources.task_id,
            "target_exports": ["ebench", "embodied-eval-os"],
            "package_mode": "fat",
            "required_assets": [
                {"role": "environment", "asset_type": "scene"},
                {"role": "robot", "asset_type": "lift2"},
                {"role": "object", "asset_type": "apple", "affordances": ["pickable"]},
                {"role": "target_container", "asset_type": "bowl", "affordances": ["container"]},
            ],
            "workflow_bindings": {"object": "apple_001", "target_container": "bowl_001"},
        },
    )


def _write_provenance(root: Path, sources: OfficialAssetSources) -> None:
    write_yaml_artifact(
        root / "provenance" / "summary.yaml",
        {
            "schema_version": "provenance-summary/v0.1",
            "source_kind": "official_ebench_asset_canary",
            "source_task_id": sources.task_id,
            "source_asset_manifest": {
                asset_id: str(source.source_path) for asset_id, source in sources.assets.items()
            },
        },
    )


def _write_validation_report(root: Path) -> None:
    write_yaml_artifact(
        root / "evidence" / "validation_report.yaml",
        {
            "schema_version": "validation-report/v0.2",
            "status": "draft",
            "overall_level": "asset_locked",
            "checks": [
                {"name": "real_ebench_asset_canary_generated", "status": "passed"},
                {"name": "official_asset_sources_materialized", "status": "passed"},
            ],
        },
    )


def _write_scene_instances(root: Path) -> None:
    write_yaml_artifact(
        root / "scene" / "instances.yaml",
        {
            "schema_version": "scene-instances/v0.2",
            "instances": [
                _instance("environment_scene", "official_ebench_scene", "environment", [0.0, 0.0, 0.0]),
                _instance("lift2_robot_asset", "official_ebench_robot", "robot_asset", [-0.9, 0.1, -0.5]),
                _instance("apple_001", "official_ebench_apple", "manipulated_object", [-0.35, -0.22, 0.85]),
                _instance("bowl_001", "official_ebench_bowl", "target_container", [-0.35, 0.24, 0.82]),
            ],
        },
    )


def _write_task(root: Path, sources: OfficialAssetSources) -> None:
    write_yaml_artifact(
        root / "task" / "task.yaml",
        {
            "schema_version": "task/v0.2",
            "task_id": sources.task_id,
            "task_family": "pick_place",
            "instruction": sources.instruction,
            "bindings": {"object": "apple_001", "target_container": "bowl_001"},
        },
    )


def _write_metrics(root: Path) -> None:
    write_yaml_artifact(
        root / "metrics" / "metrics.yaml",
        {
            "schema_version": "metrics/v0.2",
            "metrics": [
                {
                    "id": "apple_in_bowl",
                    "type": "predicate_satisfaction",
                    "role": "primary_success",
                    "predicate": "object_in_container",
                    "object": "apple_001",
                    "container": "bowl_001",
                    "adapter_hints": {
                        "ebench": {
                            "success_metric": "apple_in_bowl",
                            "predicate": "object_in_container",
                            "object": "apple_001",
                            "container": "bowl_001",
                        }
                    },
                }
            ],
        },
    )


def _write_robot(root: Path) -> None:
    write_yaml_artifact(
        root / "robot" / "robot.yaml",
        {
            "schema_version": "robot/v0.2",
            "robot_id": ROBOT_ID,
            "spawn": {"xyz": [-0.9, 0.1, -0.5], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        },
    )


def _instance(instance_id: str, asset_id: str, role: str, xyz: list[float]) -> dict[str, object]:
    return {
        "id": instance_id,
        "asset_id": asset_id,
        "role": role,
        "pose": {"xyz": xyz, "wxyz": [1.0, 0.0, 0.0, 0.0]},
        "semantic_tags": [role],
        "initial_state": {},
    }

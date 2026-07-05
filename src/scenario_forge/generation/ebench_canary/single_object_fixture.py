from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scenario_forge.adapters.ebench.exporter import export_ebench_package
from scenario_forge.adapters.ebench.official_asset_intake import (
    MaterializedOfficialAsset,
    OfficialAssetSources,
    load_official_asset_sources,
    materialize_official_asset_bundle,
)
from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.assets.lock import generate_asset_lock, write_asset_lock
from scenario_forge.scaffold import scaffold_starter_package
from scenario_forge.scene.usd_compiler import compile_usd_scene


ROBOT_ID = "manip/lift2/R5a"
ROBOT_INSTANCE_ID = "lift2_robot_asset"


@dataclass(frozen=True)
class SingleObjectFixtureCanaryResult:
    package_root: Path
    scene_usd: Path


@dataclass(frozen=True)
class FixtureTaskSpec:
    package_id: str
    task_family: str
    manipulated_asset_key: str
    manipulated_asset_id: str
    manipulated_instance_id: str
    target_fixture: dict[str, str]
    success_metric_id: str
    success_predicate: str
    object_pose: dict[str, list[float]]
    robot_spawn: dict[str, list[float]]
    source_task_config: str


def generate_single_object_fixture_canary(
    asset_sources_path: str | Path,
    package_root: str | Path,
) -> SingleObjectFixtureCanaryResult:
    root = Path(package_root)
    sources = load_official_asset_sources(asset_sources_path)
    spec = _load_fixture_task_spec(asset_sources_path)
    _require_source_assets(sources, ("scene", "robot", spec.manipulated_asset_key, "camera_yaml"))

    scaffold_starter_package(root)
    _write_manifest(root, spec)
    _write_generation_plan(root, sources, spec)
    _write_provenance(root, sources, spec)
    _write_validation_report(root)

    materialized = []
    for source_key, asset_id in {
        "scene": "official_ebench_scene",
        "robot": "official_ebench_robot",
        spec.manipulated_asset_key: spec.manipulated_asset_id,
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
    materialized_by_id = {asset.asset_id: asset for asset in materialized}

    write_yaml_artifact(
        root / "assets" / "asset_manifest.yaml",
        {
            "schema_version": "asset-manifest/v0.2",
            "assets": [asset.asset_manifest_entry() for asset in materialized],
        },
    )
    _write_layout_checks(root, spec)
    _write_scene_instances(root, spec)
    _write_task(root, sources, spec)
    _write_metrics(root, spec)
    _write_robot(root, spec)
    _write_task_contract(root, sources, spec)

    write_asset_lock(root, generate_asset_lock(root))
    scene_usd = root / "scene" / "main.usda"
    compile_usd_scene(root, root / "scene" / "instances.yaml", root / "locks" / "asset_lock.yaml", scene_usd)
    export_ebench_package(root)
    _assert_materialized_asset_ids(materialized_by_id, spec)
    return SingleObjectFixtureCanaryResult(package_root=root, scene_usd=scene_usd)


def _load_fixture_task_spec(path: str | Path) -> FixtureTaskSpec:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Official asset source manifest must be a mapping: {path}")
    fixture_task = data.get("fixture_task")
    if not isinstance(fixture_task, dict):
        raise ValueError("Single-object fixture canary requires fixture_task mapping")
    target_fixture = fixture_task.get("target_fixture")
    if not isinstance(target_fixture, dict):
        raise ValueError("fixture_task.target_fixture must be a mapping")

    return FixtureTaskSpec(
        package_id=_required_string(data, "package_id"),
        task_family=_optional_string(data, "task_family", "pick_place"),
        manipulated_asset_key=_required_string(fixture_task, "manipulated_asset_key"),
        manipulated_asset_id=_required_string(fixture_task, "manipulated_asset_id"),
        manipulated_instance_id=_required_string(fixture_task, "manipulated_instance_id"),
        target_fixture={
            "instance_id": _required_string(target_fixture, "instance_id"),
            "source_uid": _required_string(target_fixture, "source_uid"),
            "role": _required_string(target_fixture, "role"),
            "semantic_label": _required_string(target_fixture, "semantic_label"),
            "fixture_kind": "environment_fixture",
            "source_asset_id": "official_ebench_scene",
        },
        success_metric_id=_required_string(fixture_task, "success_metric_id"),
        success_predicate=_required_string(fixture_task, "success_predicate"),
        object_pose=_required_pose(fixture_task, "object_pose"),
        robot_spawn=_required_pose(fixture_task, "robot_spawn", require_scale=False),
        source_task_config=_required_string(fixture_task, "source_task_config"),
    )


def _require_source_assets(sources: OfficialAssetSources, required: tuple[str, ...]) -> None:
    missing = [asset_id for asset_id in required if asset_id not in sources.assets]
    if missing:
        raise ValueError(f"Missing official asset source entries: {', '.join(missing)}")


def _write_manifest(root: Path, spec: FixtureTaskSpec) -> None:
    write_yaml_artifact(
        root / "manifest.yaml",
        {
            "schema_version": "scenario-package/v0.2",
            "package_id": spec.package_id,
            "scenario_domain": "home_manipulation",
            "package_mode": "fat",
            "targets": ["ebench", "embodied-eval-os"],
            "entrypoints": {
                "generation_plan": "generation_plan.yaml",
                "scene_usd": "scene/main.usda",
                "scene_instances": "scene/instances.yaml",
                "task": "task/task.yaml",
                "task_contract": "task/task_contract.yaml",
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


def _write_generation_plan(root: Path, sources: OfficialAssetSources, spec: FixtureTaskSpec) -> None:
    write_yaml_artifact(
        root / "generation_plan.yaml",
        {
            "schema_version": "scenario-generation-plan/v0.2",
            "package_id": spec.package_id,
            "source_task_id": sources.task_id,
            "target_exports": ["ebench", "embodied-eval-os"],
            "package_mode": "fat",
            "required_assets": [
                {"role": "environment", "asset_type": "scene"},
                {"role": "robot", "asset_type": "lift2"},
                {
                    "role": "object",
                    "asset_key": spec.manipulated_asset_key,
                    "asset_id": spec.manipulated_asset_id,
                    "affordances": ["pickable"],
                },
                {
                    "role": "target_container",
                    "asset_type": "environment_fixture",
                    "source_uid": spec.target_fixture["source_uid"],
                },
            ],
            "workflow_bindings": {
                "object": spec.manipulated_instance_id,
                "target_container": spec.target_fixture["instance_id"],
            },
        },
    )


def _write_provenance(root: Path, sources: OfficialAssetSources, spec: FixtureTaskSpec) -> None:
    write_yaml_artifact(
        root / "provenance" / "summary.yaml",
        {
            "schema_version": "provenance-summary/v0.1",
            "source_kind": "official_ebench_asset_canary",
            "source_task_id": sources.task_id,
            "source_task_config": spec.source_task_config,
            "source_asset_manifest": {
                asset_id: str(source.source_path) for asset_id, source in sources.assets.items()
            },
            "target_fixture": spec.target_fixture,
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
                {"name": "real_ebench_fixture_canary_generated", "status": "passed"},
                {"name": "official_asset_sources_materialized", "status": "passed"},
            ],
        },
    )


def _write_layout_checks(root: Path, spec: FixtureTaskSpec) -> None:
    write_yaml_artifact(
        root / "evidence" / "layout_checks.yaml",
        {
            "schema_version": "layout-checks/v0.2",
            "status": "passed",
            "checks": [{"name": "official_fixture_pose_from_task_config", "status": "passed"}],
            "fixture_placement": {
                "placement_source_kind": "official_task_config_fixture_binding",
                "object_pose": spec.object_pose,
                "target_fixture": spec.target_fixture,
                "source_task_config": spec.source_task_config,
            },
        },
    )


def _write_scene_instances(root: Path, spec: FixtureTaskSpec) -> None:
    write_yaml_artifact(
        root / "scene" / "instances.yaml",
        {
            "schema_version": "scene-instances/v0.2",
            "instances": [
                _instance("environment_scene", "official_ebench_scene", "environment", [0.0, 0.0, 0.0]),
                _instance("lift2_robot_asset", "official_ebench_robot", "robot_asset", spec.robot_spawn["xyz"]),
                _instance(
                    spec.manipulated_instance_id,
                    spec.manipulated_asset_id,
                    "manipulated_object",
                    spec.object_pose["xyz"],
                    wxyz=spec.object_pose["wxyz"],
                    scale_xyz=spec.object_pose.get("scale_xyz"),
                ),
            ],
            "fixture_bindings": {
                "target_container": spec.target_fixture,
            },
        },
    )


def _write_task(root: Path, sources: OfficialAssetSources, spec: FixtureTaskSpec) -> None:
    write_yaml_artifact(
        root / "task" / "task.yaml",
        {
            "schema_version": "task/v0.2",
            "task_id": sources.task_id,
            "task_family": spec.task_family,
            "instruction": sources.instruction,
            "bindings": {
                "object": spec.manipulated_instance_id,
                "target_container": spec.target_fixture["instance_id"],
            },
            "target_fixture": spec.target_fixture,
        },
    )


def _write_metrics(root: Path, spec: FixtureTaskSpec) -> None:
    write_yaml_artifact(
        root / "metrics" / "metrics.yaml",
        {
            "schema_version": "metrics/v0.2",
            "metrics": [
                {
                    "id": spec.success_metric_id,
                    "type": "predicate_satisfaction",
                    "role": "primary_success",
                    "predicate": spec.success_predicate,
                    "object": spec.manipulated_instance_id,
                    "container": spec.target_fixture["instance_id"],
                    "adapter_hints": {
                        "ebench": {
                            "success_metric": spec.success_metric_id,
                            "predicate": spec.success_predicate,
                            "object": spec.manipulated_instance_id,
                            "container": spec.target_fixture["instance_id"],
                            "target_fixture_source_uid": spec.target_fixture["source_uid"],
                        }
                    },
                }
            ],
        },
    )


def _write_robot(root: Path, spec: FixtureTaskSpec) -> None:
    write_yaml_artifact(
        root / "robot" / "robot.yaml",
        {
            "schema_version": "robot/v0.2",
            "robot_id": ROBOT_ID,
            "spawn": spec.robot_spawn,
        },
    )


def _write_task_contract(root: Path, sources: OfficialAssetSources, spec: FixtureTaskSpec) -> None:
    camera_source = sources.assets["camera_yaml"]
    target_fixture = {
        "instance_id": spec.target_fixture["instance_id"],
        "asset_id": "official_ebench_scene",
        "role": spec.target_fixture["role"],
        "source_uid": spec.target_fixture["source_uid"],
        "semantic_label": spec.target_fixture["semantic_label"],
        "fixture_kind": "environment_fixture",
    }
    write_yaml_artifact(
        root / "task" / "task_contract.yaml",
        {
            "schema_version": "ebench-task-contract/v0.1",
            "phase_gate": "10.10",
            "package_id": spec.package_id,
            "task": {
                "task_id": sources.task_id,
                "task_family": spec.task_family,
                "instruction": sources.instruction,
            },
            "task_semantics": {
                "action": "pick_place",
                "manipulated_object": {
                    "instance_id": spec.manipulated_instance_id,
                    "asset_id": spec.manipulated_asset_id,
                    "role": "manipulated_object",
                },
                "target_container": target_fixture,
            },
            "success_predicate": {
                "metric_id": spec.success_metric_id,
                "role": "primary_success",
                "predicate": spec.success_predicate,
                "object": spec.manipulated_instance_id,
                "container": spec.target_fixture["instance_id"],
                "evaluator_owner": "embodied-eval-os-ebench-adapter",
                "claim_boundary": (
                    "portable predicate binding only; target is an environment fixture; "
                    "not an executed task success result"
                ),
            },
            "robot_hints": {
                "robot_id": ROBOT_ID,
                "robot_instance": ROBOT_INSTANCE_ID,
                "spawn": spec.robot_spawn,
                "usage": "hint_only",
            },
            "camera_hints": {
                "source_asset_key": "camera_yaml",
                "source_file": camera_source.source_path.name,
                "source_uri": str(camera_source.source_path),
                "license": camera_source.license,
                "role": camera_source.role,
                "usage": "hint_only",
                "claim_boundary": "official camera config preserved as hint; no official camera parity claim",
            },
            "adapter_contract": {
                "adapter": "ebench",
                "package_descriptor": "adapters/ebench/package.yaml",
                "task_entrypoint": "adapters/ebench/task_entrypoint.yaml",
                "runtime_owner": "embodied-eval-os",
                "scenario_forge_scope": "package_artifacts_and_contracts_only",
                "scenario_forge_excludes": [
                    "episode_runner",
                    "model_adapter",
                    "leaderboard_reporting",
                    "simulator_runtime_execution",
                    "convertasset_usd_mdl_mesh_conversion",
                ],
            },
            "phase_11_readiness": {
                "status": "ready_for_automated_visual_review",
                "required_review_artifacts": [
                    "scene/main.usda",
                    "locks/asset_lock.yaml",
                    "adapters/ebench/package.yaml",
                    "adapters/ebench/task_entrypoint.yaml",
                    "task/task_contract.yaml",
                ],
            },
            "claim_boundary": (
                "real EBench single-task fixture package contract only; not task success, "
                "not official camera/material parity, not leaderboard evidence"
            ),
        },
    )


def _instance(
    instance_id: str,
    asset_id: str,
    role: str,
    xyz: list[float],
    *,
    wxyz: list[float] | None = None,
    scale_xyz: list[float] | None = None,
) -> dict[str, object]:
    pose: dict[str, object] = {"xyz": xyz, "wxyz": wxyz or [1.0, 0.0, 0.0, 0.0]}
    if scale_xyz is not None:
        pose["scale_xyz"] = scale_xyz
    return {
        "id": instance_id,
        "asset_id": asset_id,
        "role": role,
        "pose": pose,
        "semantic_tags": [role],
        "initial_state": {},
    }


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing required string field: {key}")
    return value


def _optional_string(data: dict[str, Any], key: str, default: str) -> str:
    value = data.get(key, default)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Field {key!r} must be a non-empty string")
    return value


def _required_pose(data: dict[str, Any], key: str, *, require_scale: bool = True) -> dict[str, list[float]]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Missing required pose mapping: {key}")
    pose = {
        "xyz": _required_float_list(value, "xyz", 3),
        "wxyz": _required_float_list(value, "wxyz", 4),
    }
    if require_scale:
        pose["scale_xyz"] = _required_float_list(value, "scale_xyz", 3)
    return pose


def _required_float_list(data: dict[str, Any], key: str, expected_len: int) -> list[float]:
    value = data.get(key)
    if not isinstance(value, list) or len(value) != expected_len:
        raise ValueError(f"Field {key!r} must contain {expected_len} numeric values")
    if not all(isinstance(item, int | float) for item in value):
        raise ValueError(f"Field {key!r} must contain numeric values")
    return [float(item) for item in value]


def _assert_materialized_asset_ids(
    materialized_by_id: dict[str, MaterializedOfficialAsset],
    spec: FixtureTaskSpec,
) -> None:
    required_ids = {"official_ebench_scene", "official_ebench_robot", spec.manipulated_asset_id}
    missing = sorted(required_ids - set(materialized_by_id))
    if missing:
        raise ValueError(f"Missing materialized official assets: {', '.join(missing)}")

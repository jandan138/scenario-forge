from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.assets.checksum import compute_sha256
from scenario_forge.assets.lock import generate_asset_lock, write_asset_lock
from scenario_forge.generation.layout.constraints import (
    LayoutConstraintError,
    load_layout_constraints,
)
from scenario_forge.generation.layout.reachability import first_unreachable_instance
from scenario_forge.generation.layout.safety import safety_spacing_findings
from scenario_forge.scene.instance_binding import SceneInstanceError, load_scene_instances


class LayoutPlanError(ValueError):
    """Raised when deterministic layout planning fails."""


@dataclass(frozen=True)
class LayoutPlanResult:
    package_root: Path
    difficulty: str
    instance_count: int
    artifacts: tuple[Path, ...]


def plan_layout_artifacts(
    package_root: str | Path,
    difficulty: str = "easy",
    domain_pack_dir: str | Path | None = None,
) -> LayoutPlanResult:
    root = Path(package_root)
    generation_plan = _load_yaml(root / "generation_plan.yaml")
    required_assets = _required_assets(generation_plan)
    bindings = _string_mapping(generation_plan.get("workflow_bindings", {}), "workflow_bindings")

    try:
        constraints = load_layout_constraints(domain_pack_dir)
    except LayoutConstraintError as exc:
        raise LayoutPlanError(str(exc)) from exc
    profile = constraints.difficulty_profiles.get(difficulty)
    if profile is None:
        raise LayoutPlanError(f"Unsupported difficulty: {difficulty}")

    existing_instances = _existing_instances(root)
    instances = _build_instances(required_assets, bindings, existing_instances, constraints.workspace, profile)
    layout = _layout_yaml(difficulty, constraints.workspace, profile, required_assets, instances)
    report = _layout_report(instances, constraints.workspace)
    artifacts = [
        write_yaml_artifact(root / "scene" / "layout.yaml", layout),
        write_yaml_artifact(
            root / "scene" / "instances.yaml",
            {"schema_version": "scene-instances/v0.2", "instances": instances},
        ),
        write_yaml_artifact(root / "evidence" / "layout_checks.yaml", report),
    ]
    _ensure_asset_manifest_and_lock(root, instances, required_assets)
    artifacts.append(root / "assets" / "asset_manifest.yaml")
    artifacts.append(root / "locks" / "asset_lock.yaml")

    if report["status"] != "passed":
        first_failed = next(
            check for check in report["checks"] if isinstance(check, dict) and check["status"] == "failed"
        )
        raise LayoutPlanError(str(first_failed["reason"]))
    return LayoutPlanResult(
        package_root=root,
        difficulty=difficulty,
        instance_count=len(instances),
        artifacts=tuple(artifacts),
    )


def _required_assets(generation_plan: dict[str, Any]) -> list[dict[str, Any]]:
    raw_assets = generation_plan.get("required_assets")
    if not isinstance(raw_assets, list) or not all(isinstance(item, dict) for item in raw_assets):
        raise LayoutPlanError("generation_plan.yaml must include required_assets")
    return [dict(item) for item in raw_assets]


def _build_instances(
    required_assets: list[dict[str, Any]],
    bindings: dict[str, str],
    existing_instances: dict[str, dict[str, Any]],
    workspace: Any,
    profile: Any,
) -> list[dict[str, Any]]:
    distance = profile.target_distance_range_m[0]
    object_x = min(max(0.45, workspace.x_min), workspace.x_max - distance)
    object_y = 0.0
    instances: list[dict[str, Any]] = []
    for index, asset in enumerate(required_assets):
        role = _asset_role(asset)
        instance_id = bindings.get(role, f"{role}_001")
        existing = existing_instances.get(instance_id, {})
        asset_id = str(existing.get("asset_id", f"{role}_asset"))
        xyz = _role_xyz(role, index, object_x, object_y, workspace.z, distance)
        instances.append(
            {
                "id": instance_id,
                "asset_id": asset_id,
                "role": _instance_role(role),
                "pose": {"xyz": xyz, "wxyz": [1.0, 0.0, 0.0, 0.0]},
                "semantic_tags": _semantic_tags(role, asset),
                "initial_state": {},
            }
        )
    return instances


def _role_xyz(role: str, index: int, object_x: float, object_y: float, z: float, distance: float) -> list[float]:
    if _is_target_role(role):
        return [round(object_x + distance, 4), object_y, z]
    y = object_y + (0.08 * index)
    return [round(object_x, 4), round(y, 4), z]


def _is_target_role(role: str) -> bool:
    return role in {"target_zone", "prep_zone", "target_container"} or role.startswith("target")


def _instance_role(role: str) -> str:
    if role in {"object", "sample_container", "source_container"}:
        return "manipulated_object"
    if _is_target_role(role):
        return "target_region"
    return role


def _semantic_tags(role: str, asset: dict[str, Any]) -> list[str]:
    tags = [role]
    affordances = asset.get("affordances", [])
    if isinstance(affordances, list):
        tags.extend(str(affordance) for affordance in affordances)
    if _is_target_role(role):
        tags.extend(["zone", "target"])
    if role in {"object", "sample_container", "source_container"}:
        tags.append("pickable")
    return sorted(set(tags))


def _layout_yaml(
    difficulty: str,
    workspace: Any,
    profile: Any,
    required_assets: list[dict[str, Any]],
    instances: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "scene-layout/v0.2",
        "difficulty": difficulty,
        "workspace": {
            "x_range_m": [workspace.x_min, workspace.x_max],
            "y_range_m": [workspace.y_min, workspace.y_max],
            "z_m": workspace.z,
        },
        "difficulty_profile": {
            "clutter_level": profile.clutter_level,
            "target_distance_range_m": list(profile.target_distance_range_m),
            "occlusion": profile.occlusion,
            "distractor_count": profile.distractor_count,
        },
        "required_assets": required_assets,
        "placements": [
            {
                "role": instance["role"],
                "instance_id": instance["id"],
                "asset_id": instance["asset_id"],
                "xyz": instance["pose"]["xyz"],
            }
            for instance in instances
        ],
    }


def _layout_report(instances: list[dict[str, Any]], workspace: Any) -> dict[str, Any]:
    reachability_reason = first_unreachable_instance(instances, workspace)
    reachability = {
        "name": "robot_workspace_reachability",
        "status": "failed" if reachability_reason else "passed",
    }
    if reachability_reason:
        reachability["reason"] = reachability_reason
    checks = [reachability, *safety_spacing_findings()]
    return {
        "schema_version": "layout-checks/v0.2",
        "status": "failed" if any(check["status"] == "failed" for check in checks) else "passed",
        "checks": checks,
    }


def _ensure_asset_manifest_and_lock(
    root: Path, instances: list[dict[str, Any]], required_assets: list[dict[str, Any]]
) -> None:
    existing_assets = _load_asset_manifest_entries(root)
    required_by_role = {_asset_role(asset): asset for asset in required_assets}
    for instance in instances:
        asset_id = str(instance["asset_id"])
        if asset_id in existing_assets:
            continue
        role = _role_from_instance(instance)
        asset = required_by_role.get(role, {"asset_type": role})
        usd_path = root / "assets" / "generated" / asset_id / "model.usd"
        usd_path.parent.mkdir(parents=True, exist_ok=True)
        usd_path.write_text(_placeholder_usd(asset_id), encoding="utf-8")
        relative_usd = usd_path.relative_to(root).as_posix()
        existing_assets[asset_id] = {
            "asset_id": asset_id,
            "role": str(instance.get("role", role)),
            "asset_type": str(asset.get("asset_type", role)),
            "canonical_usd": relative_usd,
            "license": "Apache-2.0",
            "sha256": compute_sha256(usd_path),
        }
    write_yaml_artifact(
        root / "assets" / "asset_manifest.yaml",
        {"schema_version": "asset-manifest/v0.2", "assets": list(existing_assets.values())},
    )
    write_asset_lock(root, generate_asset_lock(root))


def _load_asset_manifest_entries(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "assets" / "asset_manifest.yaml"
    if not path.exists():
        return {}
    data = _load_yaml(path)
    assets = data.get("assets", [])
    if not isinstance(assets, list):
        return {}
    return {
        str(asset["asset_id"]): dict(asset)
        for asset in assets
        if isinstance(asset, dict) and isinstance(asset.get("asset_id"), str)
    }


def _existing_instances(root: Path) -> dict[str, dict[str, Any]]:
    try:
        instances = load_scene_instances(root / "scene" / "instances.yaml")
    except SceneInstanceError:
        return {}
    return {
        instance.instance_id: {
            "asset_id": instance.asset_id,
            "role": instance.role,
            "semantic_tags": list(instance.semantic_tags),
        }
        for instance in instances
    }


def _asset_role(asset: dict[str, Any]) -> str:
    role = asset.get("role")
    if not isinstance(role, str) or not role:
        raise LayoutPlanError("required_assets entries must include a role")
    return role


def _role_from_instance(instance: dict[str, Any]) -> str:
    tags = instance.get("semantic_tags", [])
    if isinstance(tags, list) and tags:
        return str(tags[0])
    return str(instance.get("role", "scene_object"))


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise LayoutPlanError(f"Missing YAML artifact: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise LayoutPlanError(f"YAML artifact must be a mapping: {path}")
    return data


def _placeholder_usd(default_prim: str) -> str:
    return (
        "#usda 1.0\n"
        "(\n"
        f'    defaultPrim = "{default_prim}"\n'
        ")\n"
        "\n"
        f'def Xform "{default_prim}"\n'
        "{\n"
        "}\n"
    )


def _string_mapping(value: Any, field: str) -> dict[str, str]:
    if value == {}:
        return {}
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in value.items()
    ):
        raise LayoutPlanError(f"generation_plan.yaml field {field!r} must map strings to strings")
    return dict(value)

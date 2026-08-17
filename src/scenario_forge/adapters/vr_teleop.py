"""Formal eBench VR-teleop export from a compiled Scenario Forge recipe."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping

import yaml

from scenario_forge.adapters.isaac41_vr600_profile import (
    PROFILE_ID,
    SOURCE_CONTRACT,
    physx_scene_config,
    vr_robot_contact_config,
)
from scenario_forge.assets.manifest import AssetManifestEntry, load_asset_manifest
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.package import validate_package


VR_TASK_ID = "scientific_workbench_pour_flask_to_cylinder"


class VRTeleopExportError(ValueError):
    pass


@dataclass(frozen=True)
class VRTeleopExportResult:
    output_dir: Path
    scene_usd: Path
    task_config: Path
    parity_manifest: Path


def _legacy_pour_objects(
    task_objects: list[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], Mapping[str, Any]] | None:
    sources = [item for item in task_objects if item.get("role") == "source_container"]
    targets = [item for item in task_objects if item.get("role") == "target_container"]
    if len(task_objects) == 2 and len(sources) == 1 and len(targets) == 1:
        return sources[0], targets[0]
    return None


def _task_dependency_roles(
    task_objects: list[Mapping[str, Any]],
    *,
    legacy_pour_objects: tuple[Mapping[str, Any], Mapping[str, Any]] | None,
) -> dict[str, str]:
    if legacy_pour_objects is not None:
        source, target = legacy_pour_objects
        return {
            _string(source.get("id"), "source.id"): "source_container",
            _string(target.get("id"), "target.id"): "target_container",
        }
    return {
        _string(item.get("id"), "task object.id"): (
            "objects/" + _string(item.get("id"), "task object.id")
        )
        for item in task_objects
    }


def _referenced_asset_roles(
    environment: AssetManifestEntry,
    table: AssetManifestEntry,
    task_objects: list[Mapping[str, Any]],
    task_assets: Mapping[str, AssetManifestEntry],
    context_objects: list[Mapping[str, Any]],
    *,
    legacy_pour_objects: tuple[Mapping[str, Any], Mapping[str, Any]] | None,
) -> dict[str, AssetManifestEntry]:
    dependency_roles = _task_dependency_roles(
        task_objects,
        legacy_pour_objects=legacy_pour_objects,
    )
    result = {"environment": environment, "table": table}
    for object_id, dependency_role in dependency_roles.items():
        result[dependency_role] = task_assets[object_id]
    for item in context_objects:
        object_id = _string(item.get("id"), "context object.id")
        result[f"context/{object_id}"] = task_assets[object_id]
    return result


def export_vr_teleop_package(
    package_dir: str | Path,
    out_dir: str | Path,
    *,
    task_id: str = VR_TASK_ID,
) -> VRTeleopExportResult:
    """Emit a relocatable VR directory with one scene USD and one config snippet."""
    package_root = Path(package_dir)
    validation = validate_package(package_root)
    if not validation.ok:
        raise VRTeleopExportError(
            "compiled Scenario Forge package is invalid: "
            + "; ".join(validation.messages)
        )
    try:
        raw = yaml.safe_load((package_root / "scenario.yaml").read_text(encoding="utf-8"))
        scenario = ScenarioSpec.from_mapping(raw).to_mapping()
    except (OSError, yaml.YAMLError, ValueError) as exc:
        raise VRTeleopExportError(f"cannot load canonical scenario recipe: {exc}") from exc
    robot = _mapping(scenario.get("robot"), "scenario.robot")
    if robot.get("profile_ref") != PROFILE_ID:
        raise VRTeleopExportError(
            f"VR r2 export requires shared profile {PROFILE_ID!r}"
        )
    objects = [_mapping(item, "scenario.objects") for item in scenario.get("objects", [])]
    table = _one_object_by_role(objects, "table")
    scene_objects = [item for item in objects if item is not table]
    context_objects = [item for item in scene_objects if item.get("role") == "context_prop"]
    task_objects = [item for item in scene_objects if item.get("role") != "context_prop"]
    if not task_objects:
        raise VRTeleopExportError("VR export requires at least one non-table task object")
    legacy_pour_objects = _legacy_pour_objects(task_objects)
    manifest = load_asset_manifest(package_root)
    assets = {item.asset_id: item for item in manifest.assets}
    environment_id = _string(
        _mapping(scenario.get("scene"), "scenario.scene").get("asset_id"),
        "scenario.scene.asset_id",
    )
    environment = _asset(assets, environment_id)
    table_asset = _asset(assets, _string(table.get("asset_id"), "table.asset_id"))
    task_assets = {
        _string(item.get("id"), "task object.id"): _asset(
            assets,
            _string(item.get("asset_id"), "task object.asset_id"),
        )
        for item in scene_objects
    }
    scene_mapping = _mapping(scenario.get("scene"), "scenario.scene")
    composition_mode = scene_mapping.get("composition_mode", "referenced_assets")
    producer_entrypoint: Mapping[str, Any] | None = None
    if composition_mode == "producer_entrypoint":
        if legacy_pour_objects is None:
            raise VRTeleopExportError(
                "producer entrypoint VR export currently requires one source and one target container"
            )
        if any(
            item.get("instance_mode") != "embedded_scene_prim"
            or item.get("asset_id") != environment_id
            for item in objects
        ):
            raise VRTeleopExportError(
                "producer entrypoint objects must be embedded in the scene asset"
            )
        producer_entrypoint = _interactive_producer_entrypoint(environment, "vr")
    else:
        _require_static_support_table(table_asset)

    output = Path(out_dir)
    output_parent = output.parent
    output_parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise VRTeleopExportError(f"VR output already exists: {output}")
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output_parent))
    try:
        asset_roles = (
            {"scene": environment}
            if producer_entrypoint is not None
            else _referenced_asset_roles(
                environment,
                table_asset,
                task_objects,
                task_assets,
                context_objects,
                legacy_pour_objects=legacy_pour_objects,
            )
        )
        for role, asset in asset_roles.items():
            source_root = (package_root / asset.canonical_usd).parent
            if not source_root.is_dir():
                raise VRTeleopExportError(
                    f"compiled asset closure is missing for {asset.asset_id!r}"
                )
            shutil.copytree(source_root, staging / "deps" / role)

        scene_path = staging / "scene.usd"
        scene_path.write_text(
            (
                _producer_entrypoint_scene_usda(producer_entrypoint)
                if producer_entrypoint is not None
                else _scene_usda(
                    scenario=scenario,
                    table=table,
                    task_objects=scene_objects,
                    dependency_roles={
                        **_task_dependency_roles(
                            task_objects,
                            legacy_pour_objects=legacy_pour_objects,
                        ),
                        **{
                            _string(item.get("id"), "context object.id"): (
                                "context/" + _string(item.get("id"), "context object.id")
                            )
                            for item in context_objects
                        },
                    },
                    environment=environment,
                )
            ),
            encoding="utf-8",
        )
        config_path = staging / "task_config.py"
        config_path.write_text(
            _task_config_python(
                task_id=task_id,
                robot=robot,
                objects=scene_objects,
                object_prim_paths=(
                    None
                    if producer_entrypoint is None
                    else [
                        _string(
                            _mapping(
                                producer_entrypoint.get("object_prims"),
                                "vr entrypoint.object_prims",
                            ).get(role),
                            f"vr entrypoint.object_prims.{role}",
                        )
                        for role in ("source_container", "target_container")
                    ]
                ),
            ),
            encoding="utf-8",
        )
        parity_path = staging / "parity_manifest.json"
        scenario_bytes = (package_root / "scenario.yaml").read_bytes()
        table_contract = (
            None if producer_entrypoint is not None else _static_support_contract(table_asset)
        )
        parity = {
            "schema_version": "scenario-forge-vr-ebench-parity/v0.1",
            "status": "pass_with_declared_exception",
            "canonical_scenario_id": scenario["scenario_id"],
            "canonical_scenario_sha256": "sha256:" + sha256(scenario_bytes).hexdigest(),
            "vr_task_id": task_id,
            "shared_runtime_profile": PROFILE_ID,
            "source_contract": SOURCE_CONTRACT,
            "equivalence": {
                "environment": "same_asset_and_pose",
                "table_static_support": (
                    "producer_entrypoint_same_authored_prim"
                    if producer_entrypoint is not None
                    else "same_asset_and_pose"
                ),
                "task_objects": (
                    "producer_entrypoint_same_authored_prims_and_physics"
                    if producer_entrypoint is not None
                    else "same_assets_poses_and_physics"
                ),
                "context_props": "same_assets_poses_and_physics_in_randomizable_object_list",
                "robot_model": "same_runtime_robot_type",
                "robot_base_pose": "same",
                "physx_scene_config": "same_shared_profile",
                "robot_material_and_offsets": "same_shared_profile",
            },
            "static_support_contract": (
                {
                    "authority": "producer_entrypoint",
                    "consumer_authored_collider": False,
                }
                if table_contract is None
                else {
                    "profile_id": table_contract["profile_id"],
                    "profile_revision": table_contract["profile_revision"],
                    "collider_paths": [
                        item["prim_path"] for item in table_contract["colliders"]
                    ],
                    "qualification": table_contract["qualification"],
                }
            ),
            "allowed_exceptions": [
                {
                    "id": "robot_joint_initialization",
                    "status": "accepted",
                    "reason": (
                        "The Feishu VR config contract exposes robot base pose but no joint-position field; "
                        "the shared robot model and contact/PhysX profile remain identical."
                    ),
                }
            ],
            "claims_forbidden": [
                "Complete pouring policy success is established by this adapter export.",
                "Liquid-transfer benchmark success is established by this adapter export.",
            ],
            "artifacts": {
                "scene_usd": {"path": "scene.usd", "sha256": _digest(scene_path)},
                "task_config": {"path": "task_config.py", "sha256": _digest(config_path)},
            },
        }
        parity_path.write_text(
            json.dumps(parity, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        staging.rename(output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return VRTeleopExportResult(
        output_dir=output,
        scene_usd=output / "scene.usd",
        task_config=output / "task_config.py",
        parity_manifest=output / "parity_manifest.json",
    )


def _scene_usda(
    *,
    scenario: Mapping[str, Any],
    table: Mapping[str, Any],
    task_objects: list[Mapping[str, Any]],
    dependency_roles: Mapping[str, str],
    environment: AssetManifestEntry,
) -> str:
    scene = _mapping(scenario.get("scene"), "scenario.scene")
    scene_pose = _mapping(scene.get("pose"), "scenario.scene.pose")
    environment_root = _string(
        environment.metadata.get("root_prim_path", scene.get("root_prim_path")),
        "environment.root_prim_path",
    )
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "World"',
        "    metersPerUnit = 1",
        "    kilogramsPerUnit = 1",
        '    upAxis = "Z"',
        "    timeCodesPerSecond = 60",
        "    framesPerSecond = 60",
        ")",
        "",
        'def Xform "World"',
        "{",
        '    def Xform "background" (',
        f"        prepend references = @deps/environment/asset.usd@<{environment_root}>",
        "    )",
        "    {",
        *_pose_lines(scene_pose, indent=8),
        "    }",
        "",
    ]
    for wrapper, role, item in [
        ("table", "table", table),
        *[
            (
                object_id,
                dependency_roles[object_id],
                item,
            )
            for item in task_objects
            for object_id in [_string(item.get("id"), "task object.id")]
        ],
    ]:
        source_prim = _string(item.get("source_prim_path"), f"{wrapper}.source_prim_path")
        pose = _mapping(item.get("pose"), f"{wrapper}.pose")
        vr_wrapper = wrapper if wrapper == "table" else _vr_prim_name(wrapper)
        lines.extend(
            [
                f'    def Xform "{vr_wrapper}" (',
                f"        prepend references = @deps/{role}/asset.usd@<{source_prim}>",
                "    )",
                "    {",
                *_pose_lines(pose, indent=8),
                "    }",
                "",
            ]
        )
    lines.extend(
        [
            '    def DomeLight "vr_direct_open_light"',
            "    {",
            "        color3f inputs:color = (1, 1, 1)",
            "        float inputs:exposure = 0",
            "        float inputs:intensity = 750",
            "    }",
            "}",
            "",
        ]
    )
    return "\n".join(lines)


def _pose_lines(pose: Mapping[str, Any], *, indent: int) -> list[str]:
    prefix = " " * indent
    xyz = _number_list(pose.get("xyz"), 3, "pose.xyz")
    wxyz = _number_list(pose.get("wxyz"), 4, "pose.wxyz")
    scale = _number_list(pose.get("scale_xyz", [1.0, 1.0, 1.0]), 3, "pose.scale_xyz")
    return [
        f"{prefix}double3 xformOp:translate = {_usd_tuple(xyz)}",
        f"{prefix}quatd xformOp:orient = {_usd_tuple(wxyz)}",
        f"{prefix}double3 xformOp:scale = {_usd_tuple(scale)}",
        f'{prefix}uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient", "xformOp:scale"]',
    ]


def _task_config_python(
    *,
    task_id: str,
    robot: Mapping[str, Any],
    objects: list[Mapping[str, Any]],
    object_prim_paths: list[str] | None = None,
) -> str:
    spawn = _mapping(robot.get("spawn"), "scenario.robot.spawn")
    object_names = [
        _vr_prim_name(_string(item.get("id"), "task object.id")) for item in objects
    ]
    randomization_groups: dict[str, list[str]] = {}
    for item, object_name in zip(objects, object_names, strict=True):
        metadata = item.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise VRTeleopExportError("task object.metadata must be a mapping")
        group = metadata.get("vr_randomization_group", object_name)
        if not isinstance(group, str) or not group:
            raise VRTeleopExportError(
                "task object.metadata.vr_randomization_group must be a non-empty string"
            )
        randomization_groups.setdefault(group, []).append(object_name)
    config: dict[str, Any] = {
        "scene_usd_file_path": {
            "scene1": "__SCENE_PATH__",
        },
        "obj_prim_list": object_prim_paths
        or [f"/World/_scene/{object_name}" for object_name in object_names],
        "layout_randomization": {
            "table": "table",
            "objects": [
                {
                    "objs": grouped_names,
                    "mode": "local",
                    "yaw_range_degrees": [0.0, 0.0],
                    "x_offset_range": [-0.01, 0.01],
                    "y_offset_range": [-0.01, 0.01],
                }
                for grouped_names in randomization_groups.values()
            ],
        },
        "robot_cfg": {
            "position": _number_list(spawn.get("xyz"), 3, "robot.spawn.xyz"),
            "orientation": _number_list(spawn.get("wxyz"), 4, "robot.spawn.wxyz"),
        },
        "physx_scene_cfg": physx_scene_config(),
        **vr_robot_contact_config(),
    }
    body = _python_literal(config, indent=0).replace(
        '"__SCENE_PATH__"',
        f'str(_ASSETS_DIR / "scenes/{task_id}/scene.usd")',
    )
    return (
        "# Merge this TASKS entry into\n"
        "# exts.vr_teleop/exts/vr_teleop/constants/tasks.py.\n"
        "# This handoff is also a syntactically valid standalone Python module.\n"
        "TASKS = {\n"
        f"    {json.dumps(task_id)}: {body},\n"
        "}\n"
    )


def _vr_prim_name(object_id: str) -> str:
    """Return the single-prefix VR object name required by the collection runtime."""
    result = object_id
    while result.startswith("obj_obj_"):
        result = result[4:]
    return result if result.startswith("obj_") else f"obj_{result}"


def _python_literal(value: Any, *, indent: int) -> str:
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = []
        for key, item in value.items():
            items.append(
                " " * (indent + 4)
                + json.dumps(str(key))
                + ": "
                + _python_literal(item, indent=indent + 4)
                + ","
            )
        return "{\n" + "\n".join(items) + "\n" + " " * indent + "}"
    if isinstance(value, list):
        if not value:
            return "[]"
        return (
            "[\n"
            + "\n".join(
                " " * (indent + 4)
                + _python_literal(item, indent=indent + 4)
                + ","
                for item in value
            )
            + " " * indent
            + "]"
        )
    if isinstance(value, float) and value == float("inf"):
        return 'float("inf")'
    if isinstance(value, str):
        return json.dumps(value)
    return repr(value)


def _require_static_support_table(asset: AssetManifestEntry) -> None:
    if asset.role != "static_support_object":
        raise VRTeleopExportError(
            "VR r2 table must use a static_support_object ConvertAsset package"
        )
    contract = _static_support_contract(asset)
    if contract.get("status") != "pass":
        raise VRTeleopExportError("table static support contract did not pass")
    qualification = _mapping(contract.get("qualification"), "table.qualification")
    if qualification.get("status") != "pass" or qualification.get("probe_count") != 6:
        raise VRTeleopExportError("table six-probe static support qualification did not pass")


def _static_support_contract(asset: AssetManifestEntry) -> Mapping[str, Any]:
    upstream = _mapping(asset.metadata.get("upstream_package"), "table.upstream_package")
    metadata = _mapping(upstream.get("metadata"), "table.upstream_package.metadata")
    return _mapping(metadata.get("static_support_contract"), "table.static_support_contract")


def _interactive_producer_entrypoint(
    asset: AssetManifestEntry, target: str
) -> Mapping[str, Any]:
    if asset.role != "interactive_composed_scene":
        raise VRTeleopExportError(
            "producer entrypoint scene must use interactive_composed_scene asset"
        )
    upstream = _mapping(asset.metadata.get("upstream_package"), "scene.upstream_package")
    if upstream.get("producer") != "LabUtopia":
        raise VRTeleopExportError("interactive scene producer must be LabUtopia")
    metadata = _mapping(upstream.get("metadata"), "scene.upstream_package.metadata")
    entrypoints = _mapping(metadata.get("entrypoints"), "scene.entrypoints")
    entrypoint = _mapping(entrypoints.get(target), f"scene.entrypoints.{target}")
    if entrypoint.get("status") != "qualified":
        raise VRTeleopExportError(f"producer {target} entrypoint is not qualified")
    if entrypoint.get("hidden_cube_overlay_applied") is not True:
        raise VRTeleopExportError(f"producer {target} entrypoint lacks required overlay")
    if entrypoint.get("physics_hz") != 60:
        raise VRTeleopExportError("VR producer entrypoint must be 60 Hz")
    return entrypoint


def _producer_entrypoint_scene_usda(entrypoint: Mapping[str, Any]) -> str:
    path = entrypoint.get("path")
    if not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts:
        raise VRTeleopExportError("producer entrypoint path must be package-relative")
    return "\n".join(
        [
            "#usda 1.0",
            "(",
            '    defaultPrim = "World"',
            "    metersPerUnit = 1",
            "    kilogramsPerUnit = 1",
            "    timeCodesPerSecond = 60",
            "    framesPerSecond = 60",
            '    upAxis = "Z"',
            f"    subLayers = [@deps/scene/{path}@]",
            ")",
            "",
        ]
    )


def _one_object_by_role(objects: list[Mapping[str, Any]], role: str) -> Mapping[str, Any]:
    matches = [item for item in objects if item.get("role") == role]
    if len(matches) != 1:
        raise VRTeleopExportError(f"VR r2 requires exactly one {role!r} object")
    return matches[0]


def _asset(assets: Mapping[str, AssetManifestEntry], asset_id: str) -> AssetManifestEntry:
    try:
        return assets[asset_id]
    except KeyError as exc:
        raise VRTeleopExportError(f"missing compiled asset {asset_id!r}") from exc


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise VRTeleopExportError(f"{field} must be a mapping")
    return value


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise VRTeleopExportError(f"{field} must be a non-empty string")
    return value


def _number_list(value: Any, length: int, field: str) -> list[float]:
    if not isinstance(value, list) or len(value) != length:
        raise VRTeleopExportError(f"{field} must contain {length} numbers")
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise VRTeleopExportError(f"{field} must contain numbers") from exc


def _usd_tuple(values: list[float]) -> str:
    return "(" + ", ".join(format(item, ".15g") for item in values) + ")"


def _digest(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()

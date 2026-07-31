from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from pathlib import PurePosixPath
import pickle
import re
import shutil
import tempfile
from typing import Any, Mapping, cast

import yaml

from scenario_forge.adapters.ebench.preview import write_genmanip_preview_request
from scenario_forge.assets.manifest import AssetManifestEntry, load_asset_manifest
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.package import (
    PackageError,
    PackageManifest,
    load_package_manifest,
    validate_package,
)


_GENMANIP_RANGE = "manip/default/sr_based_genmanip_range"
_GENMANIP_AXIS_ALIGN = "manip/default/sr_based_genmanip_axis_align"
_GENMANIP_RELATIONSHIP = "manip/default/sr_based_genmanip_relationship"
_GENMANIP_FRAME_AWARE = "manip/default/scenario_forge_runtime_predicate"
_ROBOT_PROFILE = "manip/lift2/R5a"
_TABLE_LAYOUT_UID = "00000000000000000000000000000000"
_USD_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PICKLE_PROTOCOL = 4
_RUNTIME_CONTRACT_SCHEMA_V01 = "scenario-forge-genmanip-runtime-contract/v0.1"
_RUNTIME_CONTRACT_SCHEMA_V02 = "scenario-forge-genmanip-runtime-contract/v0.2"
_RUNTIME_CONTRACT_SCHEMA_V03 = "scenario-forge-genmanip-runtime-contract/v0.3"
_RUNTIME_CONTRACT_SCHEMA_V04 = "scenario-forge-genmanip-runtime-contract/v0.4"
_RUNTIME_CONTRACT_SCHEMA_V05 = "scenario-forge-genmanip-runtime-contract/v0.5"
_RUNTIME_CONTRACT_SCHEMA_V06 = "scenario-forge-genmanip-runtime-contract/v0.6"
_ARTICULATION_CONTRACT_SCHEMA_V01 = (
    "scenario-forge-articulation-contract/v0.1"
)
_GENMANIP_UNBOUNDED_DOF_RANGE = (-100_000_000.0, 100_000_000.0)
_EXACT_PREDICATE_TYPES = frozenset(
    {
        "named_frames_relative_pose_reached",
        "named_frame_tilt_angle_reached",
        "object_returned_to_post_warmup_pose",
    }
)
_FRAME_REFERENCE_FIELDS = frozenset(
    {"source_frame", "target_frame", "object_frame", "relative_to_frame"}
)


class GenManipExportError(ValueError):
    """Raised when a package cannot be mapped to the supported GenManip contract."""


@dataclass(frozen=True)
class GenManipExportResult:
    output_dir: Path
    artifacts: tuple[Path, ...]


@dataclass(frozen=True)
class _RuntimeObjectBinding:
    scenario_object_id: str
    runtime_uid: str
    wrapper_name: str
    state_prim_path: str
    is_table: bool


@dataclass(frozen=True)
class _ArticulationDofBinding:
    semantic_joint: str
    joint_prim: str
    part_path: str
    dof_index: int
    reset_value: float
    states: Mapping[str, tuple[float, float]]


@dataclass(frozen=True)
class _ArticulationObjectBinding:
    root_prim_path: str
    runtime_units: Mapping[str, str]
    dofs: tuple[_ArticulationDofBinding, ...]

    @property
    def reset_joint_positions(self) -> list[float]:
        return [item.reset_value for item in self.dofs]


def export_genmanip_collected_package(
    package_dir: str | Path,
    out_dir: str | Path | None = None,
    *,
    legacy_v01_transport: bool = False,
) -> GenManipExportResult:
    """Export a compiled Scenario Forge package as a GenManip collected package.

    The JSON episode metadata is authoritative.  ``meta_info.pkl`` is written only
    as a fixed-protocol compatibility encoding of that newly-created JSON-safe
    mapping; this adapter never reads pickle input.
    """

    package_root = Path(package_dir)
    default_output_dir = package_root / "adapters" / "ebench" / "genmanip"
    output_dir = (
        Path(out_dir)
        if out_dir is not None
        else default_output_dir
    )
    resolved_package_root = package_root.resolve()
    resolved_output_dir = output_dir.resolve()
    resolved_default_output_dir = default_output_dir.resolve()
    managed_default = (
        out_dir is None
        or resolved_output_dir == resolved_default_output_dir
    )
    if managed_default:
        current = package_root
        for part in ("adapters", "ebench", "genmanip"):
            current = current / part
            if current.is_symlink():
                raise GenManipExportError(
                    "default adapter path must not traverse a symlink"
                )
        if resolved_package_root not in resolved_output_dir.parents:
            raise GenManipExportError(
                "default adapter path must remain inside package_dir"
            )
    if (
        resolved_output_dir == resolved_package_root
        or resolved_output_dir in resolved_package_root.parents
    ):
        raise GenManipExportError("out_dir must not contain package_dir")
    if (
        resolved_package_root in resolved_output_dir.parents
        and resolved_output_dir != resolved_default_output_dir
    ):
        raise GenManipExportError(
            "out_dir inside package_dir must be the default adapter path"
        )

    manifest = _validated_manifest(package_root)
    raw_scenario = _load_mapping(package_root / "scenario.yaml", "scenario spec")
    try:
        scenario = ScenarioSpec.from_mapping(raw_scenario).to_mapping()
    except ValueError as exc:
        raise GenManipExportError(f"invalid scenario spec: {exc}") from exc
    scenario_schema_version = _required_string(
        scenario,
        "schema_version",
        "scenario spec",
    )
    scenario_id = _required_string(scenario, "scenario_id", "scenario spec")
    _require_usd_identifier(scenario_id, "scenario_id")
    if manifest.package_id != scenario_id:
        raise GenManipExportError(
            "compiled package manifest package_id does not match scenario_id"
        )

    robot = _required_mapping(scenario, "robot", "scenario spec")
    robot_profile = _required_string(robot, "profile_ref", "scenario robot")
    if robot_profile != _ROBOT_PROFILE:
        raise GenManipExportError(
            f"GenManip collected-package export supports {_ROBOT_PROFILE!r}, got {robot_profile!r}"
        )
    success = _required_mapping(scenario, "success", "scenario spec")
    claim_scope = _required_string(success, "claim_scope", "scenario success")

    objects = _object_mappings(scenario)
    object_by_id = {_required_string(item, "id", "scenario object"): item for item in objects}
    table = _table_object(objects)
    scene_source = _required_mapping(scenario, "scene", "scenario spec")
    source_asset_id = _required_string(scene_source, "asset_id", "scenario scene")
    source_root_prim = _required_string(
        scene_source, "root_prim_path", "scenario scene"
    )
    raw_overlay_asset_ids = scene_source.get("overlay_asset_ids", [])
    if not isinstance(raw_overlay_asset_ids, list) or not all(
        isinstance(asset_id, str) and asset_id for asset_id in raw_overlay_asset_ids
    ):
        raise GenManipExportError(
            "scenario scene.overlay_asset_ids must be a list of non-empty strings"
        )
    overlay_asset_ids = list(raw_overlay_asset_ids)
    if len(set(overlay_asset_ids)) != len(overlay_asset_ids):
        raise GenManipExportError("scenario scene.overlay_asset_ids must be unique")
    if source_asset_id in overlay_asset_ids:
        raise GenManipExportError(
            "scenario scene.overlay_asset_ids must not contain scene.asset_id"
        )
    if overlay_asset_ids and scenario_schema_version not in {
        "scenario-spec/v0.2",
        "scenario-spec/v0.3",
        "scenario-spec/v0.4",
        "scenario-spec/v0.5",
        "scenario-spec/v0.6",
    }:
        raise GenManipExportError(
            "scenario scene overlays require scenario-spec/v0.2 or later"
        )
    object_asset_ids = {
        _required_string(item, "asset_id", "scenario object") for item in objects
    }
    overlay_object_conflicts = sorted(
        set(overlay_asset_ids).intersection(object_asset_ids)
    )
    if overlay_object_conflicts:
        raise GenManipExportError(
            "scene overlay assets cannot also be object assets: "
            + ", ".join(overlay_object_conflicts)
        )
    raw_inactive_source_prims = scene_source.get("inactive_prim_paths", [])
    if not isinstance(raw_inactive_source_prims, list) or not all(
        isinstance(path, str) and path for path in raw_inactive_source_prims
    ):
        raise GenManipExportError(
            "scenario scene.inactive_prim_paths must be a list of non-empty strings"
        )
    inactive_source_prims = list(raw_inactive_source_prims)
    raw_world_anchored_source_prims = scene_source.get(
        "world_anchored_prim_paths", []
    )
    if not isinstance(raw_world_anchored_source_prims, list) or not all(
        isinstance(path, str) and path for path in raw_world_anchored_source_prims
    ):
        raise GenManipExportError(
            "scenario scene.world_anchored_prim_paths must be a list of non-empty strings"
        )
    world_anchored_source_prims = list(raw_world_anchored_source_prims)
    source_room_pose = scene_source.get("pose")
    if source_room_pose is not None:
        source_room_pose = _as_mapping(source_room_pose, "scenario scene.pose")
    asset_manifest = load_asset_manifest(package_root)
    _validate_asset_provenance(package_root, manifest, asset_manifest.assets)
    assets_by_id = {asset.asset_id: asset for asset in asset_manifest.assets}
    _require_assets(objects, source_asset_id, overlay_asset_ids, assets_by_id)
    for overlay_asset_id in overlay_asset_ids:
        overlay_asset = assets_by_id[overlay_asset_id]
        if overlay_asset.role != "scene_overlay":
            raise GenManipExportError(
                f"overlay asset {overlay_asset_id!r} role must be 'scene_overlay'"
            )
        overlay_root = overlay_asset.metadata.get("root_prim_path")
        if overlay_root != source_root_prim:
            raise GenManipExportError(
                f"overlay asset {overlay_asset_id!r} root_prim_path must match "
                "scenario scene.root_prim_path"
            )

    _validate_visual_static_object_requirements(objects, assets_by_id, table)
    qualified_object_ids, requires_gpu_dynamics = _qualified_rigid_requirements(
        objects,
        assets_by_id,
    )
    articulation_bindings = _articulation_requirements(objects, assets_by_id)
    if articulation_bindings and scenario_schema_version not in {
        "scenario-spec/v0.5",
        "scenario-spec/v0.6",
    }:
        raise GenManipExportError(
            "articulated_object export requires scenario-spec/v0.5 or v0.6"
        )
    qualified_object_ids.update(articulation_bindings)
    required_exact_object_ids = _exact_success_object_ids(success)
    unqualified_exact_objects = sorted(
        required_exact_object_ids.difference(qualified_object_ids)
    )
    if unqualified_exact_objects:
        raise GenManipExportError(
            "exact frame success requires qualified rigid object packages for: "
            + ", ".join(unqualified_exact_objects)
        )
    goal = _genmanip_goal(
        success,
        object_by_id,
        qualified_object_ids=qualified_object_ids,
        articulation_bindings=articulation_bindings,
    )
    seed = _episode_name(scenario.get("seed", "000"))
    task_name = f"scenario_forge/{scenario_id}"
    usd_name = (
        f"collected_packages/{scenario_id}/assets/scene_usds/"
        f"scenario_forge/{scenario_id}/scene"
    )
    config = _task_config(
        scenario=scenario,
        scenario_id=scenario_id,
        task_name=task_name,
        usd_name=usd_name,
        objects=objects,
        table=table,
        goal=goal,
        requires_gpu_dynamics=requires_gpu_dynamics,
        articulation_bindings=articulation_bindings,
    )
    runtime_contract = _runtime_contract(
        scenario=scenario,
        scenario_id=scenario_id,
        task_name=task_name,
        episode_name=seed,
        objects=objects,
        table=table,
        qualified_object_ids=qualified_object_ids,
        articulation_bindings=articulation_bindings,
    )
    complete_runtime_contract = (
        runtime_contract if legacy_v01_transport else None
    )
    if legacy_v01_transport:
        runtime_contract = _legacy_v01_transport_projection(runtime_contract)
    episode = _episode_metadata(
        scenario=scenario,
        scenario_id=scenario_id,
        task_name=task_name,
        episode_name=seed,
        objects=objects,
        table=table,
        assets_by_id=assets_by_id,
        goal=goal,
        runtime_contract=runtime_contract,
        complete_runtime_contract=complete_runtime_contract,
        qualified_object_ids=qualified_object_ids,
        articulation_bindings=articulation_bindings,
    )

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(
        tempfile.mkdtemp(
            prefix=f".{output_dir.name}.staging-",
            dir=output_dir.parent,
        )
    )
    try:
        _write_collected_package(
            staging_dir=staging_dir,
            package_root=package_root,
            scenario=scenario,
            scenario_id=scenario_id,
            source_asset_id=source_asset_id,
            overlay_asset_ids=overlay_asset_ids,
            source_root_prim=source_root_prim,
            inactive_source_prims=inactive_source_prims,
            world_anchored_source_prims=world_anchored_source_prims,
            source_room_pose=source_room_pose,
            assets_by_id=assets_by_id,
            objects=objects,
            config=config,
            episode=episode,
            task_name=task_name,
            episode_name=seed,
            claim_scope=claim_scope,
        )
        if output_dir.exists():
            shutil.rmtree(output_dir)
        staging_dir.rename(output_dir)
    except Exception:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        raise

    artifacts = tuple(sorted(path for path in output_dir.rglob("*") if path.is_file()))
    return GenManipExportResult(output_dir=output_dir, artifacts=artifacts)


def _validated_manifest(package_root: Path) -> PackageManifest:
    try:
        manifest = load_package_manifest(package_root)
    except PackageError as exc:
        raise GenManipExportError(str(exc)) from exc
    report = validate_package(package_root, require_asset_lock=True)
    if not report.ok:
        raise GenManipExportError("; ".join(report.messages))
    if "ebench" not in manifest.targets:
        raise GenManipExportError("compiled package does not target ebench")
    return manifest


def _validate_asset_provenance(
    package_root: Path,
    package_manifest: PackageManifest,
    assets: tuple[AssetManifestEntry, ...],
) -> None:
    relative = Path(package_manifest.provenance["summary"])
    if relative.is_absolute() or ".." in relative.parts:
        raise GenManipExportError("provenance summary must be package-relative")
    root = package_root.resolve()
    path = (root / relative).resolve()
    if root not in path.parents or not path.is_file():
        raise GenManipExportError("provenance summary escapes package or is missing")
    provenance = _load_mapping(path, "package provenance")
    raw_assets = provenance.get("assets")
    if not isinstance(raw_assets, list):
        raise GenManipExportError("package provenance assets must be a list")
    provenance_by_id: dict[str, Mapping[str, Any]] = {}
    for raw_asset in raw_assets:
        item = _as_mapping(raw_asset, "package provenance asset")
        asset_id = _required_string(item, "asset_id", "package provenance asset")
        if asset_id in provenance_by_id:
            raise GenManipExportError(
                f"duplicate package provenance asset: {asset_id}"
            )
        provenance_by_id[asset_id] = item

    if set(provenance_by_id) != {asset.asset_id for asset in assets}:
        raise GenManipExportError("asset manifest/provenance asset IDs do not match")
    for asset in assets:
        item = provenance_by_id[asset.asset_id]
        expected = {
            "canonical_usd": asset.canonical_usd,
            "sha256": asset.sha256,
            "license": asset.license,
            "redistributable": bool(asset.metadata.get("redistributable", True)),
        }
        for field, value in expected.items():
            if item.get(field) != value:
                raise GenManipExportError(
                    f"asset manifest/provenance {field} mismatch for {asset.asset_id}"
                )


def _write_collected_package(
    *,
    staging_dir: Path,
    package_root: Path,
    scenario: Mapping[str, Any],
    scenario_id: str,
    source_asset_id: str,
    overlay_asset_ids: list[str],
    source_root_prim: str,
    inactive_source_prims: list[str],
    world_anchored_source_prims: list[str],
    source_room_pose: Mapping[str, Any] | None,
    assets_by_id: Mapping[str, AssetManifestEntry],
    objects: list[Mapping[str, Any]],
    config: dict[str, Any],
    episode: dict[str, Any],
    task_name: str,
    episode_name: str,
    claim_scope: str,
) -> None:
    scene_dir = (
        staging_dir
        / "assets"
        / "scene_usds"
        / "scenario_forge"
        / scenario_id
    )
    scene_dir.mkdir(parents=True, exist_ok=True)
    source_bundle = scene_dir / "source_bundle"
    shutil.copytree(package_root / "assets", source_bundle)
    table = _table_object(objects)
    table_asset_id = _required_string(table, "asset_id", "table object")
    table_asset = assets_by_id[table_asset_id]
    if table_asset.role == "static_object":
        runtime_dir = source_bundle / "scenario_forge_runtime"
        runtime_dir.mkdir()
        (runtime_dir / "table.usd").write_text(
            _runtime_table_preload_usda(table_asset, table),
            encoding="utf-8",
        )

    scene_text = _scene_usda(
        scenario_id=scenario_id,
        source_asset_id=source_asset_id,
        overlay_asset_ids=overlay_asset_ids,
        source_root_prim=source_root_prim,
        inactive_source_prims=inactive_source_prims,
        world_anchored_source_prims=world_anchored_source_prims,
        source_room_pose=source_room_pose,
        assets_by_id=assets_by_id,
        objects=objects,
    )
    (scene_dir / "scene.usda").write_text(scene_text, encoding="utf-8")

    tasks_dir = staging_dir / "tasks"
    _write_yaml(tasks_dir / "config.yaml", config)
    episode_dir = tasks_dir / task_name / episode_name
    episode_dir.mkdir(parents=True, exist_ok=True)
    canonical_episode = _json_safe_copy(episode)
    _write_json(episode_dir / "episode_metadata.json", canonical_episode)
    with (episode_dir / "meta_info.pkl").open("wb") as handle:
        pickle.dump(canonical_episode, handle, protocol=_PICKLE_PROTOCOL)

    _write_yaml(staging_dir / "cameras" / "fixed_camera_lift2.yml", _camera_config())

    source_assets = [
        {
            "asset_id": asset.asset_id,
            "canonical_usd": _asset_reference(asset),
            "sha256": asset.sha256,
            "license": asset.license,
            "redistributable": bool(asset.metadata.get("redistributable", False)),
            **(
                {"upstream_package": asset.metadata["upstream_package"]}
                if "upstream_package" in asset.metadata
                else {}
            ),
        }
        for asset in sorted(assets_by_id.values(), key=lambda item: item.asset_id)
    ]
    package_manifest = {
        "schema_version": "scenario-forge-genmanip-collected-package/v0.1",
        "package_id": scenario_id,
        "source_package": {
            "schema_version": "scenario-package/v0.2",
            "package_id": scenario_id,
        },
        "claim_scope": claim_scope,
        "success_contract": _json_safe_copy(
            _required_mapping(scenario, "success", "scenario spec")
        ),
        "success_contract_role": (
            "authoritative_semantic_contract_with_native_articulation_status"
            if _success_uses_articulation_predicates(
                _required_mapping(scenario, "success", "scenario spec")
            )
            else (
                "authoritative_semantic_contract_with_explicit_diagnostic_projection"
                if _success_uses_exact_predicates(
                    _required_mapping(scenario, "success", "scenario spec")
                )
                else "validated_projection_of_semantic_contract"
            )
        ),
        "semantic_contract": {
            "authority": "episode_metadata",
            "path": f"tasks/{task_name}/{episode_name}/episode_metadata.json",
            "json_pointer": (
                "/task_data/scenario_forge_runtime_contract_v05"
                if "scenario_forge_runtime_contract_v05"
                in _required_mapping(
                    episode,
                    "task_data",
                    "episode metadata",
                )
                else "/task_data/scenario_forge_runtime_contract"
            ),
        },
        "entrypoints": {
            "task_config": "tasks/config.yaml",
            "episode_metadata": (
                f"tasks/{task_name}/{episode_name}/episode_metadata.json"
            ),
            "genmanip_episode_metadata": (
                f"tasks/{task_name}/{episode_name}/meta_info.pkl"
            ),
            "scene_usd": (
                f"assets/scene_usds/scenario_forge/{scenario_id}/scene.usda"
            ),
            "camera_config": "cameras/fixed_camera_lift2.yml",
            "render_request": "evidence/render_request.yaml",
        },
        "runtime_requirements": {
            "runtime": "GenManip-Sim",
            "robot_profile": _ROBOT_PROFILE,
            "robot_injection": "config_only",
            "task_dir": f"collected_packages/{scenario_id}/tasks",
            "registered_metrics": [
                _GENMANIP_RANGE,
                _GENMANIP_AXIS_ALIGN,
                *(
                    [_GENMANIP_RELATIONSHIP]
                    if _success_uses_articulation_predicates(
                        _required_mapping(scenario, "success", "scenario spec")
                    )
                    else []
                ),
                *(
                    [_GENMANIP_FRAME_AWARE]
                    if _success_uses_exact_predicates(
                        _required_mapping(scenario, "success", "scenario spec")
                    )
                    else []
                ),
            ],
            "action_contract": _action_contract(),
        },
        "source_assets": source_assets,
        "validation_scope": {
            "static_package": True,
            "simulator_smoke": False,
            "policy_success": False,
            "liquid_transfer": False,
        },
    }
    _write_json(staging_dir / "package_manifest.json", package_manifest)
    write_genmanip_preview_request(staging_dir)


def _task_config(
    *,
    scenario: Mapping[str, Any],
    scenario_id: str,
    task_name: str,
    usd_name: str,
    objects: list[Mapping[str, Any]],
    table: Mapping[str, Any],
    goal: list[list[list[dict[str, Any]]]],
    requires_gpu_dynamics: bool,
    articulation_bindings: Mapping[str, _ArticulationObjectBinding],
) -> dict[str, Any]:
    robot = _required_mapping(scenario, "robot", "scenario spec")
    spawn = _required_mapping(robot, "spawn", "scenario robot")
    position = _number_list(spawn.get("xyz"), 3, "scenario robot spawn.xyz")
    table_id = _required_string(table, "id", "table object")
    object_config: dict[str, dict[str, Any]] = {}
    for item in objects:
        object_id = _required_string(item, "id", "scenario object")
        if object_id == table_id:
            continue
        config_item: dict[str, Any] = {
            "type": "existed_object",
            "uid_list": [object_id],
        }
        articulation = articulation_bindings.get(object_id)
        if articulation is not None:
            config_item.update(
                {
                    "is_articulated": True,
                    "target_positions": articulation.reset_joint_positions,
                    "articulation_info": {
                        "is_articulated": True,
                        "part": {
                            dof.semantic_joint: dof.part_path
                            for dof in articulation.dofs
                        },
                    },
                }
            )
        object_config[object_id] = config_item
    articulation_config = {
        object_id: {
            "is_articulated": True,
            "target_positions": binding.reset_joint_positions,
        }
        for object_id, binding in articulation_bindings.items()
    }
    evaluation = {
        "task_name": task_name,
        "usd_name": usd_name,
        "table_uid": "table",
        "mode": "manual",
        "num_test": 1,
        "num_steps": _positive_int(scenario.get("max_steps"), "scenario max_steps"),
        "physics_dt": 1.0 / 60.0,
        "rendering_dt": 1.0 / 60.0,
        "robots": [{"type": _ROBOT_PROFILE, "position": position}],
        "domain_randomization": {
            "cameras": {
                "type": "fixed",
                "config_path": (
                    f"saved/assets/collected_packages/{scenario_id}/"
                    "cameras/fixed_camera_lift2.yml"
                ),
            },
            "random_environment": {
                "has_wall": False,
                "hdr": False,
                "robot_base_position": False,
                "robot_eepose": False,
                "table_texture": False,
                "table_type": False,
                "wall_texture": False,
            },
        },
        "generation_config": {
            "action_path": {"mode": "manual", "robot": 0},
            "goal": goal,
            "articulation": articulation_config,
            "mode": "manual",
            "planner": "curobo",
        },
        "object_config": object_config,
        "preprocess_config": [],
        "layout_config": {"ignored_objects": []},
        "instruction": _required_string(scenario, "instruction", "scenario spec"),
        "action_contract": _action_contract(),
    }
    if requires_gpu_dynamics:
        evaluation["physics_scene_config"] = {"EnableGPUDynamics": True}
    return {"demonstration_configs": [], "evaluation_configs": [evaluation]}


def _episode_metadata(
    *,
    scenario: Mapping[str, Any],
    scenario_id: str,
    task_name: str,
    episode_name: str,
    objects: list[Mapping[str, Any]],
    table: Mapping[str, Any],
    assets_by_id: Mapping[str, AssetManifestEntry],
    goal: list[list[list[dict[str, Any]]]],
    runtime_contract: Mapping[str, Any],
    complete_runtime_contract: Mapping[str, Any] | None,
    qualified_object_ids: set[str],
    articulation_bindings: Mapping[str, _ArticulationObjectBinding],
) -> dict[str, Any]:
    initial_layout: dict[str, Any] = {}
    table_id = _required_string(table, "id", "table object")
    for item in objects:
        binding = _runtime_object_binding(
            scenario_id=scenario_id,
            item=item,
            table_id=table_id,
        )
        object_id = binding.scenario_object_id
        asset_id = _required_string(item, "asset_id", f"scenario object {object_id}")
        asset = assets_by_id[asset_id]
        pose = _required_mapping(item, "pose", f"scenario object {object_id}")
        base_layout = {
            "position": _number_list(pose.get("xyz"), 3, f"{object_id}.pose.xyz"),
            "orientation": _number_list(
                pose.get("wxyz"), 4, f"{object_id}.pose.wxyz"
            ),
            "scale": _number_list(
                pose.get("scale_xyz", [1.0, 1.0, 1.0]),
                3,
                f"{object_id}.pose.scale_xyz",
            ),
            "prim_path": binding.state_prim_path,
        }
        articulation = articulation_bindings.get(object_id)
        if articulation is not None:
            initial_layout[binding.runtime_uid] = {
                "type": "articulation",
                **base_layout,
                "joint_positions": articulation.reset_joint_positions,
            }
            continue
        initial_layout[binding.runtime_uid] = {
            "type": "object",
            **base_layout,
            "path": (
                _genmanip_collected_table_preload_path(scenario_id)
                if binding.is_table and asset.role == "static_object"
                else ""
            ),
            "add_colliders": object_id not in qualified_object_ids,
            "add_rigid_body": (
                not binding.is_table and object_id not in qualified_object_ids
            ),
            "is_articulation_part": False,
        }

    robot = _required_mapping(scenario, "robot", "scenario spec")
    spawn = _required_mapping(robot, "spawn", "scenario robot")
    initial_layout["lift2"] = {
        "type": "robot",
        "position": _number_list(spawn.get("xyz"), 3, "scenario robot spawn.xyz"),
        "orientation": _number_list(
            spawn.get("wxyz"), 4, "scenario robot spawn.wxyz"
        ),
        "joint_positions": _lift2_default_joint_positions(),
    }
    task_data = {
        "instruction": _required_string(scenario, "instruction", "scenario spec"),
        "goal": goal,
        "initial_scene_graph": None,
        "initial_layout": initial_layout,
        "scenario_forge_runtime_contract": _json_safe_copy(runtime_contract),
    }
    if complete_runtime_contract is not None:
        task_data["scenario_forge_runtime_contract_v05"] = _json_safe_copy(
            complete_runtime_contract
        )
    return {
        "schema_version": "genmanip-episode-metadata/v0.1",
        "task_name": task_name,
        "episode_name": episode_name,
        "task_data": task_data,
    }


def _runtime_object_binding(
    *,
    scenario_id: str,
    item: Mapping[str, Any],
    table_id: str,
) -> _RuntimeObjectBinding:
    object_id = _required_string(item, "id", "scenario object")
    is_table = object_id == table_id
    wrapper_name = "obj_table" if is_table else f"obj_{object_id}"
    _require_usd_identifier(wrapper_name, f"wrapper for {object_id}")
    return _RuntimeObjectBinding(
        scenario_object_id=object_id,
        runtime_uid=_TABLE_LAYOUT_UID if is_table else object_id,
        wrapper_name=wrapper_name,
        state_prim_path=f"/World/{scenario_id}/{wrapper_name}",
        is_table=is_table,
    )


def _runtime_contract(
    *,
    scenario: Mapping[str, Any],
    scenario_id: str,
    task_name: str,
    episode_name: str,
    objects: list[Mapping[str, Any]],
    table: Mapping[str, Any],
    qualified_object_ids: set[str],
    articulation_bindings: Mapping[str, _ArticulationObjectBinding],
) -> dict[str, Any]:
    table_id = _required_string(table, "id", "table object")
    contract_objects: list[dict[str, Any]] = []
    available_frames: set[str] = set()
    for item in objects:
        binding = _runtime_object_binding(
            scenario_id=scenario_id,
            item=item,
            table_id=table_id,
        )
        object_id = binding.scenario_object_id
        raw_frames = item.get("named_frames", {})
        frames_mapping = _as_mapping(
            raw_frames,
            f"scenario object {object_id}.named_frames",
        )
        named_frames: dict[str, dict[str, list[float]]] = {}
        for raw_frame_id, raw_pose in frames_mapping.items():
            if not isinstance(raw_frame_id, str) or not raw_frame_id:
                raise GenManipExportError(
                    f"scenario object {object_id}.named_frames keys must be non-empty strings"
                )
            if "." in raw_frame_id:
                raise GenManipExportError(
                    f"named frame id {raw_frame_id!r} must not contain '.'"
                )
            pose = _as_mapping(
                raw_pose,
                f"scenario object {object_id}.named_frames.{raw_frame_id}",
            )
            if "scale_xyz" in pose:
                raise GenManipExportError(
                    f"named frame {object_id}.{raw_frame_id} must not declare scale_xyz"
                )
            xyz = _finite_number_list(
                pose.get("xyz"),
                3,
                f"named frame {object_id}.{raw_frame_id}.xyz",
            )
            wxyz = _finite_number_list(
                pose.get("wxyz"),
                4,
                f"named frame {object_id}.{raw_frame_id}.wxyz",
            )
            if sum(value * value for value in wxyz) == 0.0:
                raise GenManipExportError(
                    f"named frame {object_id}.{raw_frame_id} must use a non-zero quaternion"
                )
            named_frames[raw_frame_id] = {"xyz": xyz, "wxyz": wxyz}
            available_frames.add(f"{object_id}.{raw_frame_id}")

        pose = _required_mapping(item, "pose", f"scenario object {object_id}")
        contract_object = {
                "scenario_object_id": object_id,
                "role": _required_string(item, "role", f"scenario object {object_id}"),
                "source_prim_path": _required_string(
                    item,
                    "source_prim_path",
                    f"scenario object {object_id}",
                ),
                "runtime_uid": binding.runtime_uid,
                "state_prim_path": binding.state_prim_path,
                "initial_pose": _runtime_initial_pose(pose, object_id),
                "named_frames": named_frames,
            }
        if object_id in qualified_object_ids:
            contract_object["physics_authoring"] = {
                "owner": "convert_asset_package",
                "local_colliders": False,
                "local_rigid_body": False,
                "local_mass": False,
            }
        articulation = articulation_bindings.get(object_id)
        if articulation is not None:
            contract_object["articulation"] = {
                "root_prim_path": articulation.root_prim_path,
                "runtime_units": dict(articulation.runtime_units),
                "dof_mapping": [
                    {
                        "semantic_joint": dof.semantic_joint,
                        "joint_prim": dof.joint_prim,
                        "dof_index": dof.dof_index,
                    }
                    for dof in articulation.dofs
                ],
                "reset_joint_positions": articulation.reset_joint_positions,
                "states": {
                    dof.semantic_joint: {
                        state: list(value_range)
                        for state, value_range in dof.states.items()
                    }
                    for dof in articulation.dofs
                },
            }
        contract_objects.append(contract_object)

    robot = _required_mapping(scenario, "robot", "scenario spec")
    raw_actors = robot.get("actors")
    if not isinstance(raw_actors, list) or not raw_actors:
        raise GenManipExportError("scenario robot.actors must be a non-empty list")
    actors = [
        _json_safe_copy(_as_mapping(actor, "scenario robot actor"))
        for actor in raw_actors
    ]
    raw_steps = scenario.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise GenManipExportError("scenario steps must be a non-empty list")
    steps = [_json_safe_copy(_as_mapping(step, "scenario step")) for step in raw_steps]
    raw_invariants = scenario.get("invariants", [])
    if not isinstance(raw_invariants, list):
        raise GenManipExportError("scenario invariants must be a list")
    invariants = [
        _json_safe_copy(_as_mapping(invariant, "scenario invariant"))
        for invariant in raw_invariants
    ]
    success = _required_mapping(scenario, "success", "scenario spec")
    _validate_frame_references(steps, available_frames, "scenario steps")
    _validate_frame_references(success, available_frames, "scenario success")
    exact_success = _success_uses_exact_predicates(success)
    scenario_schema_version = _required_string(
        scenario,
        "schema_version",
        "scenario spec",
    )
    qualified_rigid_object_ids = qualified_object_ids.difference(
        articulation_bindings
    )
    if (
        qualified_rigid_object_ids
        and not exact_success
        and scenario_schema_version
        not in {"scenario-spec/v0.5", "scenario-spec/v0.6"}
    ):
        raise GenManipExportError(
            "qualified rigid objects require the exact ordered success contract"
        )
    exact_runtime_contract_schema = (
        _RUNTIME_CONTRACT_SCHEMA_V06
        if scenario_schema_version == "scenario-spec/v0.6"
        else (
            _RUNTIME_CONTRACT_SCHEMA_V05
            if scenario_schema_version == "scenario-spec/v0.5"
            else (
                _RUNTIME_CONTRACT_SCHEMA_V04
                if scenario_schema_version == "scenario-spec/v0.4"
                else (
                    _RUNTIME_CONTRACT_SCHEMA_V03
                    if scenario_schema_version == "scenario-spec/v0.3"
                    else _RUNTIME_CONTRACT_SCHEMA_V02
                )
            )
        )
    )
    execution: dict[str, Any] = {
        "native_goal_role": (
            "native_articulation_status_with_diagnostic_compatibility_projection"
            if articulation_bindings
            else "diagnostic_compatibility_projection"
        ),
        "frame_aware_metric_active": False,
        "process_invariants_evaluated": False,
    }
    raw_rubric = success.get("progress_rubric")
    if isinstance(raw_rubric, Mapping):
        rubric_items = raw_rubric.get("items")
        if isinstance(rubric_items, list):
            execution["progress_rubric"] = {
                "scored_here": False,
                "unevaluated_metric_ids": [
                    str(item["id"])
                    for item in rubric_items
                    if isinstance(item, Mapping) and isinstance(item.get("id"), str)
                ],
            }
    contract = {
        "schema_version": (
            exact_runtime_contract_schema
            if qualified_object_ids or exact_success or articulation_bindings
            else _RUNTIME_CONTRACT_SCHEMA_V01
        ),
        "contract_status": "transport_only",
        "scenario_id": scenario_id,
        "task_name": task_name,
        "episode_name": episode_name,
        "coordinate_convention": {
            "translation_unit": "meter",
            "quaternion_order": "wxyz",
            "named_frame_pose_relative_to": "state_prim_path",
            "transform_direction": "state_prim_from_named_frame",
            "frame_scale_allowed": False,
        },
        "execution": execution,
        "robot": {
            "profile_ref": _required_string(robot, "profile_ref", "scenario robot"),
            "robot_index": 0,
            "actors": actors,
        },
        "objects": contract_objects,
        "steps": steps,
        "invariants": invariants,
        "success": _json_safe_copy(success),
    }
    return cast(dict[str, Any], _json_safe_copy(contract))


def _legacy_v01_transport_projection(
    complete_contract: Mapping[str, Any],
) -> dict[str, Any]:
    if complete_contract.get("schema_version") != _RUNTIME_CONTRACT_SCHEMA_V05:
        raise GenManipExportError(
            "legacy_v01_transport requires a scenario-spec/v0.5 runtime contract"
        )
    projection = _json_safe_copy(complete_contract)
    projection["schema_version"] = _RUNTIME_CONTRACT_SCHEMA_V01
    projection["execution"] = {
        "native_goal_role": "diagnostic_compatibility_projection",
        "frame_aware_metric_active": False,
        "process_invariants_evaluated": False,
    }
    projection["objects"] = [
        {
            key: value
            for key, value in _as_mapping(
                raw_object,
                "v0.1 compatibility projection object",
            ).items()
            if key not in {"physics_authoring", "articulation"}
        }
        for raw_object in projection["objects"]
    ]
    return cast(dict[str, Any], _json_safe_copy(projection))


def _runtime_initial_pose(
    pose: Mapping[str, Any], object_id: str
) -> dict[str, list[float]]:
    label = f"scenario object {object_id} initial pose"
    xyz = _finite_number_list(pose.get("xyz"), 3, f"{label}.xyz")
    wxyz = _finite_number_list(pose.get("wxyz"), 4, f"{label}.wxyz")
    if sum(value * value for value in wxyz) == 0.0:
        raise GenManipExportError(
            f"{label} must use a non-zero quaternion"
        )
    result = {"xyz": xyz, "wxyz": wxyz}
    if "scale_xyz" in pose:
        result["scale_xyz"] = _finite_number_list(
            pose.get("scale_xyz"),
            3,
            f"{label}.scale_xyz",
        )
    return result


def _validate_frame_references(
    value: object,
    available_frames: set[str],
    label: str,
) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            child_label = f"{label}.{key}"
            if key in _FRAME_REFERENCE_FIELDS:
                if not isinstance(item, str) or item not in available_frames:
                    raise GenManipExportError(
                        f"{child_label} references unknown named frame {item!r}"
                    )
            _validate_frame_references(item, available_frames, child_label)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_frame_references(item, available_frames, f"{label}[{index}]")


def _finite_number_list(value: object, length: int, label: str) -> list[float]:
    result = _number_list(value, length, label)
    if not all(math.isfinite(item) for item in result):
        raise GenManipExportError(f"{label} must contain finite numbers")
    return result


def _genmanip_goal(
    success: Mapping[str, Any],
    object_by_id: Mapping[str, Mapping[str, Any]],
    *,
    qualified_object_ids: set[str],
    articulation_bindings: Mapping[str, _ArticulationObjectBinding],
) -> list[list[list[dict[str, Any]]]]:
    operator = _required_string(success, "operator", "scenario success")
    if operator != "all":
        raise GenManipExportError(
            "GenManip export requires scenario success.operator to be 'all'"
        )
    raw_predicates = success.get("predicates")
    if not isinstance(raw_predicates, list) or not raw_predicates:
        raise GenManipExportError("scenario success.predicates must be a non-empty list")
    predicates = sorted(
        (_as_mapping(item, "success predicate") for item in raw_predicates),
        key=lambda item: _non_negative_int(
            item.get("sequence_index"), "success predicate sequence_index"
        ),
    )
    stages: list[list[list[dict[str, Any]]]] = []
    for predicate in predicates:
        predicate_type = _required_string(predicate, "type", "success predicate")
        parameters = _required_mapping(predicate, "parameters", "success predicate")
        if predicate_type in _EXACT_PREDICATE_TYPES:
            projection = _required_mapping(
                parameters,
                "diagnostic_compatibility_projection",
                "success predicate",
            )
            predicate_type = _required_string(
                projection,
                "type",
                "diagnostic_compatibility_projection",
            )
            parameters = _required_mapping(
                projection,
                "parameters",
                "diagnostic_compatibility_projection",
            )
        if predicate_type == "relative_pose_reached":
            metrics = _relative_pose_metrics(
                parameters,
                articulation_bindings,
            )
        elif predicate_type == "object_at_initial_pose":
            metrics = _initial_pose_metrics(
                parameters,
                object_by_id,
                articulation_bindings,
            )
        elif predicate_type == "articulation_joint_state_reached":
            metrics = [
                _articulation_joint_state_metric(
                    parameters,
                    articulation_bindings,
                )
            ]
        else:
            raise GenManipExportError(
                f"unsupported GenManip success predicate type: {predicate_type}"
            )
        for metric in metrics:
            referenced_uids = {
                metric.get("obj1_uid"),
                metric.get("obj2_uid"),
                metric.get("another_obj2_uid"),
            }
            if referenced_uids.intersection(qualified_object_ids):
                metric["not_set_mass"] = True
        stages.append([metrics])
    return stages


def _success_uses_exact_predicates(success: Mapping[str, Any]) -> bool:
    raw_predicates = success.get("predicates")
    if not isinstance(raw_predicates, list):
        return False
    return any(
        isinstance(predicate, Mapping)
        and predicate.get("type") in _EXACT_PREDICATE_TYPES
        for predicate in raw_predicates
    )


def _success_uses_articulation_predicates(success: Mapping[str, Any]) -> bool:
    raw_predicates = success.get("predicates")
    if not isinstance(raw_predicates, list):
        return False
    return any(
        isinstance(predicate, Mapping)
        and predicate.get("type") == "articulation_joint_state_reached"
        for predicate in raw_predicates
    )


def _exact_success_object_ids(success: Mapping[str, Any]) -> set[str]:
    raw_predicates = success.get("predicates")
    if not isinstance(raw_predicates, list):
        return set()
    result: set[str] = set()
    for raw_predicate in raw_predicates:
        if not isinstance(raw_predicate, Mapping):
            continue
        predicate_type = raw_predicate.get("type")
        if predicate_type not in _EXACT_PREDICATE_TYPES:
            continue
        parameters = _required_mapping(
            raw_predicate,
            "parameters",
            "exact success predicate",
        )
        frame_fields: tuple[str, ...]
        object_fields: tuple[str, ...]
        if predicate_type == "named_frames_relative_pose_reached":
            frame_fields = ("source_frame", "target_frame")
            object_fields = ()
        elif predicate_type == "named_frame_tilt_angle_reached":
            frame_fields = ("object_frame",)
            object_fields = ()
        else:
            frame_fields = ()
            object_fields = ("object",)
        for field in frame_fields:
            frame_ref = parameters.get(field)
            if not isinstance(frame_ref, str) or "." not in frame_ref:
                raise GenManipExportError(
                    f"exact success predicate {field} must be an object frame reference"
                )
            result.add(frame_ref.rpartition(".")[0])
        for field in object_fields:
            result.add(
                _required_string(parameters, field, "exact success predicate")
            )
    return result


def _qualified_rigid_requirements(
    objects: list[Mapping[str, Any]],
    assets_by_id: Mapping[str, AssetManifestEntry],
) -> tuple[set[str], bool]:
    qualified: set[str] = set()
    requires_gpu_dynamics = False
    for item in objects:
        object_id = _required_string(item, "id", "scenario object")
        asset_id = _required_string(item, "asset_id", f"scenario object {object_id}")
        asset = assets_by_id[asset_id]
        if asset.role != "rigid_object":
            continue
        upstream = _as_mapping(
            asset.metadata.get("upstream_package"),
            f"rigid object asset {asset_id}.upstream_package",
        )
        if upstream.get("producer") != "ConvertAsset":
            raise GenManipExportError(
                f"rigid object asset {asset_id!r} must be owned by ConvertAsset"
            )
        upstream_metadata = _required_mapping(
            upstream,
            "metadata",
            f"rigid object asset {asset_id}.upstream_package",
        )
        interaction = _required_mapping(
            upstream_metadata,
            "interaction_contract",
            f"rigid object asset {asset_id}",
        )
        if interaction.get("schema_version") != "aan.interaction_contract.v1":
            raise GenManipExportError(
                f"rigid object asset {asset_id!r} has unsupported interaction_contract"
            )
        if _interaction_requires_gpu_dynamics(interaction, asset_id):
            requires_gpu_dynamics = True
        source_prim = _required_string(
            item,
            "source_prim_path",
            f"scenario object {object_id}",
        )
        if interaction.get("asset_entry_prim") != source_prim:
            raise GenManipExportError(
                f"scenario object {object_id} source_prim_path must equal its "
                "interaction_contract asset_entry_prim"
            )
        contract_frames = _required_mapping(
            interaction,
            "named_frames",
            f"rigid object asset {asset_id}.interaction_contract",
        )
        scenario_frames = _as_mapping(
            item.get("named_frames", {}),
            f"scenario object {object_id}.named_frames",
        )
        for frame_name, raw_pose in scenario_frames.items():
            if frame_name not in contract_frames:
                raise GenManipExportError(
                    f"scenario object {object_id} named frame {frame_name!r} is not "
                    "authoritative in its interaction_contract"
                )
            contract_frame = _as_mapping(
                contract_frames[frame_name],
                f"interaction_contract named frame {frame_name}",
            )
            pose = _as_mapping(raw_pose, f"scenario object {object_id}.{frame_name}")
            if pose.get("xyz") != contract_frame.get("translation_body_local_usd"):
                raise GenManipExportError(
                    f"scenario object {object_id} named frame {frame_name!r} translation "
                    "must match its interaction_contract"
                )
            if pose.get("wxyz") != contract_frame.get("rotation_body_local_wxyz"):
                raise GenManipExportError(
                    f"scenario object {object_id} named frame {frame_name!r} rotation "
                    "must match its interaction_contract"
                )
        qualified.add(object_id)
    return qualified, requires_gpu_dynamics


def _articulation_requirements(
    objects: list[Mapping[str, Any]],
    assets_by_id: Mapping[str, AssetManifestEntry],
) -> dict[str, _ArticulationObjectBinding]:
    bindings: dict[str, _ArticulationObjectBinding] = {}
    for item in objects:
        object_id = _required_string(item, "id", "scenario object")
        asset_id = _required_string(item, "asset_id", f"scenario object {object_id}")
        asset = assets_by_id[asset_id]
        if asset.role != "articulated_object":
            continue
        upstream = _as_mapping(
            asset.metadata.get("upstream_package"),
            f"articulated object asset {asset_id}.upstream_package",
        )
        if upstream.get("producer") != "ConvertAsset":
            raise GenManipExportError(
                f"articulated object asset {asset_id!r} must be owned by ConvertAsset"
            )
        upstream_metadata = _required_mapping(
            upstream,
            "metadata",
            f"articulated object asset {asset_id}.upstream_package",
        )
        contract = _required_mapping(
            upstream_metadata,
            "articulation_contract",
            f"articulated object asset {asset_id}",
        )
        if contract.get("schema_version") != _ARTICULATION_CONTRACT_SCHEMA_V01:
            raise GenManipExportError(
                f"articulated object asset {asset_id!r} has unsupported "
                "articulation_contract"
            )
        closure = _required_mapping(
            upstream_metadata,
            "articulation_closure",
            f"articulated object asset {asset_id}",
        )
        if closure.get("status") != "pass":
            raise GenManipExportError(
                f"articulated object asset {asset_id!r} articulation_closure "
                "must have status 'pass'"
            )
        source_prim = _required_string(
            item,
            "source_prim_path",
            f"scenario object {object_id}",
        )
        if contract.get("asset_entry_prim") != source_prim:
            raise GenManipExportError(
                f"scenario object {object_id} source_prim_path must equal its "
                "articulation_contract asset_entry_prim"
            )
        root_prim = _required_string(
            contract,
            "articulation_root_prim",
            f"articulated object asset {asset_id}.articulation_contract",
        )
        runtime_units = _required_mapping(
            contract,
            "runtime_units",
            f"articulated object asset {asset_id}.articulation_contract",
        )
        expected_runtime_units = {
            "revolute": "radian",
            "prismatic": "meter",
        }
        if dict(runtime_units) != expected_runtime_units:
            raise GenManipExportError(
                f"articulated object asset {asset_id!r} runtime_units must be "
                "{'revolute': 'radian', 'prismatic': 'meter'}"
            )
        if root_prim != source_prim and not root_prim.startswith(source_prim + "/"):
            raise GenManipExportError(
                f"articulated object asset {asset_id!r} articulation root must "
                "be within asset_entry_prim"
            )
        roots = _mapping_list(
            closure.get("articulation_roots"),
            f"articulated object asset {asset_id}.articulation_closure.articulation_roots",
        )
        if len(roots) != 1 or roots[0].get("prim_path") != root_prim:
            raise GenManipExportError(
                f"articulated object asset {asset_id!r} articulation root is "
                "inconsistent with articulation_closure"
            )
        contract_frames = _required_mapping(
            contract,
            "named_frames",
            f"articulated object asset {asset_id}.articulation_contract",
        )
        scenario_frames = _as_mapping(
            item.get("named_frames", {}),
            f"scenario object {object_id}.named_frames",
        )
        for frame_name, raw_pose in scenario_frames.items():
            if frame_name not in contract_frames:
                raise GenManipExportError(
                    f"scenario object {object_id} named frame {frame_name!r} is not "
                    "authoritative in its articulation_contract"
                )
            frame_label = (
                f"articulated object asset {asset_id}.articulation_contract."
                f"named_frames.{frame_name}"
            )
            contract_frame = _as_mapping(contract_frames[frame_name], frame_label)
            parent_prim = _required_string(
                contract_frame,
                "parent_prim",
                frame_label,
            )
            if parent_prim != root_prim:
                raise GenManipExportError(
                    f"scenario object {object_id} named frame {frame_name!r} "
                    "parent_prim must equal the articulation root"
                )
            if contract_frame.get("authoritative") is not True:
                raise GenManipExportError(
                    f"scenario object {object_id} named frame {frame_name!r} must "
                    "be authoritative in its articulation_contract"
                )
            pose = _as_mapping(
                raw_pose,
                f"scenario object {object_id}.named_frames.{frame_name}",
            )
            scenario_xyz = _finite_number_list(
                pose.get("xyz"),
                3,
                f"scenario object {object_id}.named_frames.{frame_name}.xyz",
            )
            contract_xyz = _finite_number_list(
                contract_frame.get("translation_parent_local_m"),
                3,
                f"{frame_label}.translation_parent_local_m",
            )
            if scenario_xyz != contract_xyz:
                raise GenManipExportError(
                    f"scenario object {object_id} named frame {frame_name!r} "
                    "translation must match its articulation_contract"
                )
            scenario_wxyz = _finite_number_list(
                pose.get("wxyz"),
                4,
                f"scenario object {object_id}.named_frames.{frame_name}.wxyz",
            )
            contract_wxyz = _finite_number_list(
                contract_frame.get("rotation_parent_local_wxyz"),
                4,
                f"{frame_label}.rotation_parent_local_wxyz",
            )
            if scenario_wxyz != contract_wxyz:
                raise GenManipExportError(
                    f"scenario object {object_id} named frame {frame_name!r} "
                    "rotation must match its articulation_contract"
                )

        raw_dof_mapping = _mapping_list(
            closure.get("dof_mapping"),
            f"articulated object asset {asset_id}.articulation_closure.dof_mapping",
        )
        if not raw_dof_mapping:
            raise GenManipExportError(
                f"articulated object asset {asset_id!r} dof_mapping must not be empty"
            )
        dof_by_prim: dict[str, int] = {}
        for raw_dof in raw_dof_mapping:
            joint_prim = _required_string(
                raw_dof,
                "joint_prim",
                f"articulated object asset {asset_id}.dof_mapping",
            )
            dof_index = _non_negative_int(
                raw_dof.get("dof_index"),
                f"articulated object asset {asset_id}.dof_mapping.dof_index",
            )
            if joint_prim in dof_by_prim or dof_index in dof_by_prim.values():
                raise GenManipExportError(
                    f"articulated object asset {asset_id!r} dof_mapping must "
                    "use unique joint paths and indices"
                )
            dof_by_prim[joint_prim] = dof_index
        if sorted(dof_by_prim.values()) != list(range(len(dof_by_prim))):
            raise GenManipExportError(
                f"articulated object asset {asset_id!r} dof_mapping indices "
                "must be contiguous from 0"
            )

        reset_prims: set[str] = set()
        for raw_reset in _mapping_list(
            closure.get("reset_values"),
            f"articulated object asset {asset_id}.articulation_closure.reset_values",
        ):
            joint_prim = _required_string(
                raw_reset,
                "joint_prim",
                f"articulated object asset {asset_id}.reset_values",
            )
            reset_record = _required_mapping(
                raw_reset,
                "reset_value",
                f"articulated object asset {asset_id}.reset_values",
            )
            if reset_record.get("status") != "pass":
                raise GenManipExportError(
                    f"articulated object asset {asset_id!r} reset value for "
                    f"{joint_prim!r} must have status 'pass'"
                )
            reset_value = _number(
                reset_record.get("value"),
                f"articulated object asset {asset_id}.reset_values.value",
            )
            if not math.isfinite(reset_value) or joint_prim in reset_prims:
                raise GenManipExportError(
                    f"articulated object asset {asset_id!r} reset values must "
                    "be finite and unique"
                )
            reset_prims.add(joint_prim)
        if reset_prims != set(dof_by_prim):
            raise GenManipExportError(
                f"articulated object asset {asset_id!r} reset_values must cover "
                "every dof_mapping entry"
            )

        semantic_joints = _required_mapping(
            contract,
            "joints",
            f"articulated object asset {asset_id}.articulation_contract",
        )
        semantic_by_index: dict[int, _ArticulationDofBinding] = {}
        for semantic_joint, raw_semantic in semantic_joints.items():
            if not isinstance(semantic_joint, str) or not semantic_joint:
                raise GenManipExportError(
                    f"articulated object asset {asset_id!r} semantic joint names "
                    "must be non-empty strings"
                )
            _require_usd_identifier(
                semantic_joint,
                f"articulated object asset {asset_id} semantic joint",
            )
            semantic = _as_mapping(
                raw_semantic,
                f"articulated object asset {asset_id}.joints.{semantic_joint}",
            )
            joint_prim = _required_string(
                semantic,
                "joint_prim",
                f"articulated object asset {asset_id}.joints.{semantic_joint}",
            )
            if joint_prim not in dof_by_prim:
                raise GenManipExportError(
                    f"articulated object asset {asset_id!r} semantic joint "
                    f"{semantic_joint!r} is missing from dof_mapping"
                )
            dof_index = dof_by_prim[joint_prim]
            if dof_index in semantic_by_index:
                raise GenManipExportError(
                    f"articulated object asset {asset_id!r} semantic joints "
                    "must map to unique DOFs"
                )
            part_prim = _required_string(
                semantic,
                "part_prim",
                f"articulated object asset {asset_id}.joints.{semantic_joint}",
            )
            part_path = "/" + "/".join(
                _relative_prim_parts(root_prim, part_prim)
            )
            raw_states = _required_mapping(
                semantic,
                "states",
                f"articulated object asset {asset_id}.joints.{semantic_joint}",
            )
            states: dict[str, tuple[float, float]] = {}
            for state_name, raw_range in raw_states.items():
                if not isinstance(state_name, str) or not state_name:
                    raise GenManipExportError(
                        f"articulated object asset {asset_id!r} state names "
                        "must be non-empty strings"
                    )
                state_range = _finite_number_list(
                    raw_range,
                    2,
                    f"articulated object asset {asset_id} state {state_name}",
                )
                if state_range[0] > state_range[1]:
                    raise GenManipExportError(
                        f"articulated object asset {asset_id!r} state "
                        f"{state_name!r} lower bound exceeds upper bound"
                    )
                states[state_name] = (state_range[0], state_range[1])
            if not states:
                raise GenManipExportError(
                    f"articulated object asset {asset_id!r} semantic joint "
                    f"{semantic_joint!r} must declare states"
                )
            runtime_reset_value = _number(
                semantic.get("runtime_reset_value"),
                f"articulated object asset {asset_id}.joints."
                f"{semantic_joint}.runtime_reset_value",
            )
            if not math.isfinite(runtime_reset_value):
                raise GenManipExportError(
                    f"articulated object asset {asset_id!r} semantic joint "
                    f"{semantic_joint!r} runtime_reset_value must be finite"
                )
            semantic_by_index[dof_index] = _ArticulationDofBinding(
                semantic_joint=semantic_joint,
                joint_prim=joint_prim,
                part_path=part_path,
                dof_index=dof_index,
                reset_value=runtime_reset_value,
                states=states,
            )
        if set(semantic_by_index) != set(range(len(dof_by_prim))):
            raise GenManipExportError(
                f"articulated object asset {asset_id!r} articulation_contract "
                "joints must cover every dof_mapping entry"
            )
        bindings[object_id] = _ArticulationObjectBinding(
            root_prim_path=root_prim,
            runtime_units=expected_runtime_units,
            dofs=tuple(
                semantic_by_index[index] for index in range(len(semantic_by_index))
            ),
        )
    return bindings


def _validate_visual_static_object_requirements(
    objects: list[Mapping[str, Any]],
    assets_by_id: Mapping[str, AssetManifestEntry],
    table: Mapping[str, Any],
) -> None:
    """Route a visual-static table through GenManip's native static-table path.

    GenManip gives non-table objects generic colliders and a generic rigid body.
    A ConvertAsset ``visual_static_object`` is intentionally nonphysical, so this
    adapter supports it only for the declared table.  The collected scene leaves
    that table uninstantiated so ``recovery_scene`` preloads the package root,
    preserves its dependency scope, and applies GenManip's existing static-table
    collider policy without adding a rigid body.
    """

    table_id = _required_string(table, "id", "table object")
    for item in objects:
        object_id = _required_string(item, "id", "scenario object")
        asset_id = _required_string(item, "asset_id", f"scenario object {object_id}")
        asset = assets_by_id[asset_id]
        if asset.role == "static_object" and object_id != table_id:
            raise GenManipExportError(
                "visual_static_object asset "
                f"{asset_id!r} may only be bound to the declared table "
                f"{table_id!r}; non-table objects would receive GenManip's "
                "default rigid-body behavior"
            )
        if asset.role == "static_object":
            _runtime_table_preload_usda(asset, item)


def _interaction_requires_gpu_dynamics(
    interaction: Mapping[str, Any],
    asset_id: str,
) -> bool:
    raw_colliders = interaction.get("collider_prims")
    if not isinstance(raw_colliders, list):
        raise GenManipExportError(
            f"rigid object asset {asset_id}.interaction_contract.collider_prims "
            "must be a list"
        )
    return any(
        collider.get("collision_enabled") is True
        and collider.get("observed_approximation") == "sdf"
        for collider in (
            _as_mapping(
                raw_collider,
                f"rigid object asset {asset_id}.interaction_contract.collider_prims",
            )
            for raw_collider in raw_colliders
        )
    )


def _articulation_joint_state_metric(
    parameters: Mapping[str, Any],
    articulation_bindings: Mapping[str, _ArticulationObjectBinding],
) -> dict[str, Any]:
    object_id = _required_string(
        parameters,
        "object",
        "articulation joint state predicate",
    )
    articulation = articulation_bindings.get(object_id)
    if articulation is None:
        raise GenManipExportError(
            "articulation joint state predicate references object "
            f"{object_id!r} without a qualified articulation_contract"
        )
    semantic_joint = _required_string(
        parameters,
        "joint",
        "articulation joint state predicate",
    )
    state_name = _required_string(
        parameters,
        "state",
        "articulation joint state predicate",
    )
    target_dof = next(
        (
            dof
            for dof in articulation.dofs
            if dof.semantic_joint == semantic_joint
        ),
        None,
    )
    if target_dof is None:
        raise GenManipExportError(
            f"articulation joint state predicate joint {semantic_joint!r} is "
            f"not declared by object {object_id!r}"
        )
    state_range = target_dof.states.get(state_name)
    if state_range is None:
        raise GenManipExportError(
            f"articulation joint state predicate state {state_name!r} is not "
            f"declared for {object_id!r}.{semantic_joint}"
        )
    candidate = [
        (
            list(state_range)
            if dof.dof_index == target_dof.dof_index
            else list(_GENMANIP_UNBOUNDED_DOF_RANGE)
        )
        for dof in articulation.dofs
    ]
    return {
        "type": _GENMANIP_RELATIONSHIP,
        "obj1_uid": object_id,
        "status": [candidate],
    }


def _relative_pose_metrics(
    parameters: Mapping[str, Any],
    articulation_bindings: Mapping[str, _ArticulationObjectBinding],
) -> list[dict[str, Any]]:
    object_id = _required_string(parameters, "object", "relative pose predicate")
    relative_to = _required_string(
        parameters, "relative_to", "relative pose predicate"
    )
    raw_ranges = _required_mapping(parameters, "xyz_range", "relative pose predicate")
    metric_range: dict[str, Any] = {
        "type": _GENMANIP_RANGE,
        "obj1_uid": object_id,
        "x_type": "relative",
        "y_type": "relative",
        "z_type": "relative",
        "x_range": _number_list(raw_ranges.get("x"), 2, "xyz_range.x"),
        "y_range": _number_list(raw_ranges.get("y"), 2, "xyz_range.y"),
        "z_range": _number_list(raw_ranges.get("z"), 2, "xyz_range.z"),
        "x_rel_object_uid": relative_to,
        "y_rel_object_uid": relative_to,
        "z_rel_object_uid": relative_to,
    }
    metrics = [metric_range]
    raw_alignment = parameters.get("axis_alignment")
    if raw_alignment is not None:
        alignment = _as_mapping(raw_alignment, "relative pose axis_alignment")
        axis_target_uid = _axis_target_uid(
            object_id=relative_to,
            semantic_part=alignment.get("relative_to_part"),
            part_field="relative_to_part",
            articulation_bindings=articulation_bindings,
        )
        metrics.append(
            {
                "type": _GENMANIP_AXIS_ALIGN,
                "obj1_uid": object_id,
                "obj2_uid": axis_target_uid,
                "obj1_axis": _required_string(
                    alignment, "object_axis", "axis_alignment"
                ),
                "obj2_axis": _required_string(
                    alignment, "target_axis", "axis_alignment"
                ),
                "comparison": _required_string(
                    alignment, "comparison", "axis_alignment"
                ),
                "threshold_deg": _number(
                    alignment.get("threshold_deg"), "axis_alignment.threshold_deg"
                ),
            }
        )
    return metrics


def _initial_pose_metrics(
    parameters: Mapping[str, Any],
    object_by_id: Mapping[str, Mapping[str, Any]],
    articulation_bindings: Mapping[str, _ArticulationObjectBinding],
) -> list[dict[str, Any]]:
    object_id = _required_string(parameters, "object", "initial pose predicate")
    if object_id not in object_by_id:
        raise GenManipExportError(f"initial pose predicate references unknown object {object_id}")
    pose = _required_mapping(object_by_id[object_id], "pose", f"object {object_id}")
    xyz = _number_list(pose.get("xyz"), 3, f"object {object_id}.pose.xyz")
    tolerance = _number_list(
        parameters.get("xyz_tolerance"), 3, "initial pose predicate.xyz_tolerance"
    )
    metric_range: dict[str, Any] = {
        "type": _GENMANIP_RANGE,
        "obj1_uid": object_id,
        "x_type": "absolute",
        "y_type": "absolute",
        "z_type": "absolute",
        "x_range": [xyz[0] - tolerance[0], xyz[0] + tolerance[0]],
        "y_range": [xyz[1] - tolerance[1], xyz[1] + tolerance[1]],
        "z_range": [xyz[2] - tolerance[2], xyz[2] + tolerance[2]],
    }
    metrics = [metric_range]
    relative_axis_object = parameters.get("relative_axis_object")
    relative_axis_part = parameters.get("relative_axis_part")
    max_axis_error = parameters.get("max_axis_error_deg")
    if (
        relative_axis_object is not None
        or relative_axis_part is not None
        or max_axis_error is not None
    ):
        if not isinstance(relative_axis_object, str) or not relative_axis_object:
            raise GenManipExportError(
                "initial pose predicate.relative_axis_object must be a non-empty string"
            )
        axis_target_uid = _axis_target_uid(
            object_id=relative_axis_object,
            semantic_part=relative_axis_part,
            part_field="relative_axis_part",
            articulation_bindings=articulation_bindings,
        )
        metrics.append(
            {
                "type": _GENMANIP_AXIS_ALIGN,
                "obj1_uid": object_id,
                "obj2_uid": axis_target_uid,
                "obj1_axis": _optional_axis(parameters, "object_axis", "z"),
                "obj2_axis": _optional_axis(parameters, "target_axis", "z"),
                "comparison": "<=",
                "threshold_deg": _number(
                    max_axis_error, "initial pose predicate.max_axis_error_deg"
                ),
            }
        )
    return metrics


def _axis_target_uid(
    *,
    object_id: str,
    semantic_part: object,
    part_field: str,
    articulation_bindings: Mapping[str, _ArticulationObjectBinding],
) -> str:
    articulation = articulation_bindings.get(object_id)
    if articulation is None:
        if semantic_part is not None:
            raise GenManipExportError(
                f"{part_field} may only be used when axis target "
                f"{object_id!r} is articulated"
            )
        return object_id
    if semantic_part is None:
        raise GenManipExportError(
            f"{part_field} is required when axis target {object_id!r} "
            "is articulated"
        )
    if not isinstance(semantic_part, str) or not semantic_part:
        raise GenManipExportError(f"{part_field} must be a non-empty string")
    if semantic_part not in {
        dof.semantic_joint for dof in articulation.dofs
    }:
        raise GenManipExportError(
            f"unknown articulation part {semantic_part!r} for axis target "
            f"{object_id!r}"
        )
    return f"{object_id}_{semantic_part}"


def _optional_axis(parameters: Mapping[str, Any], key: str, default: str) -> str:
    value = parameters.get(key, default)
    if not isinstance(value, str) or value not in {"x", "y", "z", "-x", "-y", "-z"}:
        raise GenManipExportError(
            f"initial pose predicate.{key} must be a signed USD axis"
        )
    return value


def _scene_usda(
    *,
    scenario_id: str,
    source_asset_id: str,
    overlay_asset_ids: list[str],
    source_root_prim: str,
    inactive_source_prims: list[str],
    world_anchored_source_prims: list[str],
    source_room_pose: Mapping[str, Any] | None,
    assets_by_id: Mapping[str, AssetManifestEntry],
    objects: list[Mapping[str, Any]],
) -> str:
    _require_usd_identifier(scenario_id, "scenario_id")
    scene_asset_ids = [*overlay_asset_ids, source_asset_id]
    source_references = [
        _asset_reference(assets_by_id[asset_id]) for asset_id in scene_asset_ids
    ]
    source_override_tree: dict[str, Any] = {}
    for item in objects:
        source_prim = _required_string(item, "source_prim_path", "scenario object")
        parts = _relative_prim_parts(source_root_prim, source_prim)
        _add_source_override(source_override_tree, parts, inactive=True)
    for source_prim in inactive_source_prims:
        _add_source_override(
            source_override_tree,
            _relative_prim_parts(source_root_prim, source_prim),
            inactive=True,
        )
    for source_prim in world_anchored_source_prims:
        _add_source_override(
            source_override_tree,
            _relative_prim_parts(source_root_prim, source_prim),
            world_anchored=True,
        )
    _add_source_override(source_override_tree, ("PhysicsScene",), inactive=True)

    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "World"',
        "    metersPerUnit = 1",
        '    upAxis = "Z"',
        ")",
        "",
        'def Xform "World"',
        "{",
        f'    def Xform "{scenario_id}"',
        "    {",
        '        def Xform "room" (',
        "            prepend references = [",
        *[
            f"                @{reference}@<{source_root_prim}>,"
            for reference in source_references
        ],
        "            ]",
        "        )",
        "        {",
    ]
    if source_room_pose is not None:
        xyz = _number_list(source_room_pose.get("xyz"), 3, "scenario scene.pose.xyz")
        wxyz = _number_list(
            source_room_pose.get("wxyz"), 4, "scenario scene.pose.wxyz"
        )
        scale = _number_list(
            source_room_pose.get("scale_xyz", [1.0, 1.0, 1.0]),
            3,
            "scenario scene.pose.scale_xyz",
        )
        lines.extend(
            [
                f"            double3 xformOp:translate = {_usd_tuple(xyz)}",
                (
                    "            quatd xformOp:orient = "
                    f"({_format_number(wxyz[0])}, {_format_number(wxyz[1])}, "
                    f"{_format_number(wxyz[2])}, {_format_number(wxyz[3])})"
                ),
                f"            double3 xformOp:scale = {_usd_tuple(scale)}",
                (
                    '            uniform token[] xformOpOrder = ["!resetXformStack!", '
                    '"xformOp:translate", "xformOp:orient", "xformOp:scale"]'
                ),
            ]
        )
    lines.extend(_source_override_lines(source_override_tree, indent=12))
    lines.extend(["        }", ""])

    table_id = _required_string(_table_object(objects), "id", "table object")
    for item in objects:
        binding = _runtime_object_binding(
            scenario_id=scenario_id,
            item=item,
            table_id=table_id,
        )
        object_id = binding.scenario_object_id
        wrapper_name = binding.wrapper_name
        asset_id = _required_string(item, "asset_id", f"scenario object {object_id}")
        if binding.is_table and assets_by_id[asset_id].role == "static_object":
            continue
        source_prim = _required_string(
            item, "source_prim_path", f"scenario object {object_id}"
        )
        pose = _required_mapping(item, "pose", f"scenario object {object_id}")
        xyz = _number_list(pose.get("xyz"), 3, f"{object_id}.pose.xyz")
        wxyz = _number_list(pose.get("wxyz"), 4, f"{object_id}.pose.wxyz")
        scale = _number_list(
            pose.get("scale_xyz", [1.0, 1.0, 1.0]),
            3,
            f"{object_id}.pose.scale_xyz",
        )
        lines.extend(
            [
                f'        def Xform "{wrapper_name}" (',
                (
                    "            prepend references = "
                    f"@{_asset_reference(assets_by_id[asset_id])}@<{source_prim}>"
                ),
                "        )",
                "        {",
                f"            double3 xformOp:translate = {_usd_tuple(xyz)}",
                (
                    "            quatd xformOp:orient = "
                    f"({_format_number(wxyz[0])}, {_format_number(wxyz[1])}, "
                    f"{_format_number(wxyz[2])}, {_format_number(wxyz[3])})"
                ),
                f"            double3 xformOp:scale = {_usd_tuple(scale)}",
                (
                    '            uniform token[] xformOpOrder = ["!resetXformStack!", '
                    '"xformOp:translate", "xformOp:orient", "xformOp:scale"]'
                ),
            ]
        )
        lines.extend(
            _material_binding_lines(
                item,
                material_root=f"/World/{scenario_id}/room/Looks",
                indent=12,
            )
        )
        lines.extend(["        }", ""])
    lines.extend(
        [
            "    }",
            "}",
            "",
            'def PhysicsScene "physicsScene"',
            "{",
            "}",
            "",
        ]
    )
    return "\n".join(lines)


def _material_binding_lines(
    item: Mapping[str, Any], *, material_root: str, indent: int
) -> list[str]:
    metadata = item.get("metadata")
    if metadata is None:
        return []
    metadata_mapping = _as_mapping(metadata, "scenario object metadata")
    raw_bindings = metadata_mapping.get("material_bindings")
    if raw_bindings is None:
        return []
    bindings = _as_mapping(raw_bindings, "scenario object material_bindings")
    tree: dict[str, Any] = {}
    for raw_prim_path, raw_material_path in bindings.items():
        if not isinstance(raw_prim_path, str) or not raw_prim_path:
            raise GenManipExportError("material binding prim paths must be non-empty strings")
        if not isinstance(raw_material_path, str) or not raw_material_path:
            raise GenManipExportError("material binding targets must be non-empty strings")
        prim_parts = tuple(part for part in raw_prim_path.split("/") if part)
        material_parts = tuple(part for part in raw_material_path.split("/") if part)
        if not prim_parts or not material_parts:
            raise GenManipExportError("material binding paths must be relative USD paths")
        if raw_prim_path.startswith("/") or raw_material_path.startswith("/"):
            raise GenManipExportError("material binding paths must be relative USD paths")
        for part in (*prim_parts, *material_parts):
            _require_usd_identifier(part, "material binding path component")
        node = tree
        for part in prim_parts:
            child = node.setdefault(part, {})
            if not isinstance(child, dict):
                raise GenManipExportError("conflicting material binding prim paths")
            node = child
        if "__material__" in node:
            raise GenManipExportError(f"duplicate material binding for {raw_prim_path}")
        node["__material__"] = "/".join(material_parts)
    return _render_material_binding_tree(tree, material_root=material_root, indent=indent)


def _render_material_binding_tree(
    tree: Mapping[str, Any], *, material_root: str, indent: int
) -> list[str]:
    lines: list[str] = []
    prefix = " " * indent
    for name in sorted(key for key in tree if key != "__material__"):
        child = _as_mapping(tree[name], "material binding prim tree")
        lines.extend([f'{prefix}over "{name}"', f"{prefix}{{"])
        material = child.get("__material__")
        if material is not None:
            if not isinstance(material, str):
                raise GenManipExportError("invalid internal material binding target")
            lines.append(
                f"{prefix}    rel material:binding = <{material_root}/{material}>"
            )
        lines.extend(
            _render_material_binding_tree(
                child,
                material_root=material_root,
                indent=indent + 4,
            )
        )
        lines.append(f"{prefix}}}")
    return lines


def _source_override_lines(tree: Mapping[str, Any], indent: int) -> list[str]:
    lines: list[str] = []
    prefix = " " * indent
    for name in sorted(tree):
        _require_usd_identifier(name, "source prim component")
        children = tree[name]
        if not isinstance(children, Mapping):
            raise GenManipExportError("invalid internal source override prim tree")
        inactive = bool(children.get("__inactive__"))
        world_anchored = bool(children.get("__world_anchored__"))
        nested = {
            key: value
            for key, value in children.items()
            if key not in {"__inactive__", "__world_anchored__"}
        }
        if inactive:
            lines.extend(
                [
                    f'{prefix}over "{name}" (',
                    f"{prefix}    active = false",
                    f"{prefix})",
                    f"{prefix}{{",
                ]
            )
        else:
            lines.extend([f'{prefix}over "{name}"', f"{prefix}{{"])
        if world_anchored:
            lines.append(
                f'{prefix}    uniform token[] xformOpOrder = ["!resetXformStack!", '
                '"xformOp:translate", "xformOp:orient", "xformOp:scale"]'
            )
        lines.extend(_source_override_lines(nested, indent + 4))
        lines.append(f"{prefix}}}")
    return lines


def _add_source_override(
    tree: dict[str, Any],
    parts: tuple[str, ...],
    *,
    inactive: bool = False,
    world_anchored: bool = False,
) -> None:
    node = tree
    for part in parts:
        child = node.setdefault(part, {})
        if not isinstance(child, dict):
            raise GenManipExportError("invalid internal source override prim tree")
        node = child
    if inactive:
        node["__inactive__"] = True
    if world_anchored:
        node["__world_anchored__"] = True


def _relative_prim_parts(root_prim: str, source_prim: str) -> tuple[str, ...]:
    root_parts = tuple(part for part in root_prim.split("/") if part)
    source_parts = tuple(part for part in source_prim.split("/") if part)
    if not root_prim.startswith("/") or not source_prim.startswith("/"):
        raise GenManipExportError("USD prim paths must be absolute")
    if source_parts[: len(root_parts)] != root_parts or len(source_parts) <= len(root_parts):
        raise GenManipExportError(
            f"source prim {source_prim!r} is not below scene root {root_prim!r}"
        )
    parts = source_parts[len(root_parts) :]
    for part in parts:
        _require_usd_identifier(part, "source prim component")
    return parts


def _asset_reference(asset: AssetManifestEntry) -> str:
    path = PurePosixPath(asset.canonical_usd)
    if (
        path.is_absolute()
        or len(path.parts) < 2
        or path.parts[0] != "assets"
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != asset.canonical_usd
    ):
        raise GenManipExportError(
            "asset canonical_usd must be a normalized path below assets/: "
            f"{asset.canonical_usd}"
        )
    relative = PurePosixPath(*path.parts[1:])
    return (PurePosixPath("source_bundle") / relative).as_posix()


def _genmanip_collected_table_preload_path(scenario_id: str) -> str:
    return (
        PurePosixPath("collected_packages")
        / scenario_id
        / "assets"
        / "scene_usds"
        / "scenario_forge"
        / scenario_id
        / "source_bundle"
        / "scenario_forge_runtime"
        / "table.usd"
    ).as_posix()


def _runtime_table_preload_usda(
    asset: AssetManifestEntry,
    table: Mapping[str, Any],
) -> str:
    root_prim = asset.metadata.get("root_prim_path")
    if not isinstance(root_prim, str) or not root_prim:
        raise GenManipExportError(
            f"visual-static table asset {asset.asset_id!r} is missing root_prim_path"
        )
    source_prim = _required_string(table, "source_prim_path", "table object")
    scope_parts = _relative_prim_parts(root_prim, source_prim)
    source_reference = PurePosixPath(_asset_reference(asset))
    relative_reference = PurePosixPath("..", *source_reference.parts[1:])
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "Asset"',
        "    metersPerUnit = 1",
        '    upAxis = "Z"',
        ")",
        "",
        'def Xform "Asset" (',
        (
            "    prepend references = "
            f"@{relative_reference.as_posix()}@<{root_prim}>"
        ),
        ")",
        "{",
        "    uniform token[] xformOpOrder = []",
        "",
        *_runtime_preload_scope_reset_lines(scope_parts, indent=4),
        "}",
        "",
    ]
    return "\n".join(lines)


def _runtime_preload_scope_reset_lines(
    parts: tuple[str, ...],
    *,
    indent: int,
) -> list[str]:
    if not parts:
        return []
    name = parts[0]
    _require_usd_identifier(name, "runtime preload scope component")
    prefix = " " * indent
    lines = [
        f'{prefix}over "{name}"',
        f"{prefix}{{",
        f"{prefix}    uniform token[] xformOpOrder = []",
    ]
    if len(parts) > 1:
        lines.append("")
        lines.extend(
            _runtime_preload_scope_reset_lines(parts[1:], indent=indent + 4)
        )
    lines.append(f"{prefix}}}")
    return lines


def _require_assets(
    objects: list[Mapping[str, Any]],
    source_asset_id: str,
    overlay_asset_ids: list[str],
    assets_by_id: Mapping[str, AssetManifestEntry],
) -> None:
    required = {source_asset_id, *overlay_asset_ids}
    required.update(_required_string(item, "asset_id", "scenario object") for item in objects)
    missing = sorted(required.difference(assets_by_id))
    if missing:
        raise GenManipExportError(f"asset manifest is missing assets: {', '.join(missing)}")


def _table_object(objects: list[Mapping[str, Any]]) -> Mapping[str, Any]:
    tables = [
        item
        for item in objects
        if item.get("role") == "table" or item.get("id") == "table"
    ]
    if len(tables) != 1:
        raise GenManipExportError("scenario must define exactly one table object")
    return tables[0]


def _object_mappings(scenario: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = scenario.get("objects")
    if not isinstance(raw, list) or not raw:
        raise GenManipExportError("scenario objects must be a non-empty list")
    result = [_as_mapping(item, "scenario object") for item in raw]
    object_ids = [_required_string(item, "id", "scenario object") for item in result]
    if len(set(object_ids)) != len(object_ids):
        raise GenManipExportError("scenario object ids must be unique")
    return result


def _camera_config() -> dict[str, Any]:
    return {
        "overlook_camera": {
            "exists": True,
            "frequency": 60,
            "name": "overlook_camera",
            "camera_params": [647.04, 646.34, 639.1, 364.36],
            "position": [0.3, 0.0, 1.5],
            "orientation": [0.70106, 0.0923, -0.0923, -0.70106],
            "prim_path": "/lift2/lift2/lift2/base_link/Camera_overlook",
            "resolution": [1280, 720],
            "pixel_size": 3.0,
            "f_number": 2.0,
            "focus_distance": 0.6,
            "with_distance": False,
            "with_semantic": False,
            "with_bbox2d": False,
            "with_bbox3d": False,
            "with_motion_vector": False,
            "camera_axes": "usd",
        }
    }


def _action_contract() -> dict[str, Any]:
    return {
        "action_shape": [16],
        "base_motion_shape": [3],
        "arm_action_shape": [8, 8],
        "robot_profile": _ROBOT_PROFILE,
    }


def _lift2_default_joint_positions() -> list[float]:
    single_arm = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.044, 0.044]
    return single_arm + single_arm


def _episode_name(value: object) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        if value < 0:
            raise GenManipExportError("scenario seed must be non-negative")
        return f"{value:03d}"
    if isinstance(value, str) and value:
        episode_name = value.zfill(3) if value.isdigit() else value
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", episode_name) is None:
            raise GenManipExportError(
                "scenario seed must be a portable package path segment"
            )
        return episode_name
    raise GenManipExportError("scenario seed must be a string or integer")


def _load_mapping(path: Path, label: str) -> Mapping[str, Any]:
    if not path.is_file():
        raise GenManipExportError(f"missing {label}: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return _as_mapping(data, label)


def _as_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GenManipExportError(f"{label} must be a mapping")
    return value


def _mapping_list(value: object, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise GenManipExportError(f"{label} must be a list")
    return [
        _as_mapping(item, f"{label}[{index}]")
        for index, item in enumerate(value)
    ]


def _required_mapping(
    data: Mapping[str, Any], key: str, label: str
) -> Mapping[str, Any]:
    return _as_mapping(data.get(key), f"{label}.{key}")


def _required_string(data: Mapping[str, Any], key: str, label: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise GenManipExportError(f"{label}.{key} must be a non-empty string")
    return value


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GenManipExportError(f"{label} must be a number")
    return float(value)


def _number_list(value: object, length: int, label: str) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise GenManipExportError(f"{label} must contain {length} numbers")
    return [_number(item, label) for item in value]


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise GenManipExportError(f"{label} must be a positive integer")
    return value


def _non_negative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GenManipExportError(f"{label} must be a non-negative integer")
    return value


def _require_usd_identifier(value: str, label: str) -> None:
    if _USD_IDENTIFIER.fullmatch(value) is None:
        raise GenManipExportError(f"{label} is not a portable USD identifier: {value!r}")


def _format_number(value: float) -> str:
    text = format(value, ".15g")
    return "0" if text == "-0" else text


def _usd_tuple(values: list[float]) -> str:
    return "(" + ", ".join(_format_number(value) for value in values) + ")"


def _json_safe_copy(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, allow_nan=False, sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise GenManipExportError("generated episode metadata is not JSON-safe") from exc


def _write_yaml(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(dict(data), sort_keys=False), encoding="utf-8")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )

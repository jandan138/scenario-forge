#!/usr/bin/env python3
"""Build the Task 12 rack-to-rotor alias GenManip bundle and runtime contract."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_task11_r9_genmanip_validation_bundle as r9_adapter  # noqa: E402
from scripts import generate_task12_alias_centrifuge_rack_to_rotor as alias  # noqa: E402
from scripts import generate_scientific_workbench_task11_vr_static as base  # noqa: E402


DEFAULT_PACKAGE = alias.DEFAULT_OUT
DEFAULT_OUT = DEFAULT_PACKAGE / "adapters/ebench/genmanip"
TASK_NAME = "scenario_forge/task12_alias_centrifuge_rack_to_rotor"


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _pose(stage, path: str) -> dict[str, list[float]]:
    from pxr import UsdGeom

    matrix = UsdGeom.XformCache().GetLocalToWorldTransform(stage.GetPrimAtPath(path))
    point = matrix.ExtractTranslation()
    quat = matrix.ExtractRotationQuat()
    imag = quat.GetImaginary()
    return {
        "xyz": [float(point[index]) for index in range(3)],
        "wxyz": [float(quat.GetReal()), float(imag[0]), float(imag[1]), float(imag[2])],
        "scale_xyz": [1.0, 1.0, 1.0],
    }


def _object(stage, object_id: str, role: str, source: str, runtime_uid: str) -> dict:
    return {
        "scenario_object_id": object_id,
        "role": role,
        "source_prim_path": source,
        "runtime_uid": runtime_uid,
        "state_prim_path": source.replace("/World/", "/World/_scene/"),
        "initial_pose": _pose(stage, source),
        "named_frames": {},
        "physics_authoring": {
            "owner": "convert_asset_package",
            "local_colliders": False,
            "local_rigid_body": False,
            "local_mass": False,
        },
    }


def _progress_item(
    item_id: str, weight: float, condition_type: str, parameters: dict, *, terminal=False
) -> dict:
    return {
        "id": item_id,
        "weight": weight,
        "temporal": {"kind": "terminal" if terminal else "instant"},
        "condition": {"type": condition_type, "parameters": parameters},
    }


def _contract(stage, target_local_xyz: list[float]) -> dict:
    target_ranges = {
        axis: [center - tolerance, center + tolerance]
        for axis, center, tolerance in zip(
            ("x", "y", "z"), target_local_xyz, (0.005, 0.005, 0.01), strict=True
        )
    }
    progress = [
        _progress_item(
            "open_button_pressed",
            0.10,
            "articulation_joint_state_reached",
            {"object": "centrifuge", "joint": "lid_open_button_joint", "state": "pressed"},
        ),
        _progress_item(
            "lid_open_hold",
            0.15,
            "articulation_joint_state_reached",
            {"object": "centrifuge", "joint": "lid_hinge_joint", "state": "open_hold"},
        ),
        _progress_item(
            "target_tube_lifted_from_rack",
            0.20,
            "object_lifted",
            {"object": "target_tube", "minimum_delta_z_m": 0.03},
        ),
        _progress_item(
            "target_tube_inserted_in_rotor",
            0.25,
            "relative_pose_reached",
            {
                "object": "target_tube",
                "relative_to": "centrifuge",
                "xyz_range": target_ranges,
                "axis_alignment": {
                    "object_axis": "z",
                    "target_axis": "socket_18_axis",
                    "comparison": "<=",
                    "threshold_deg": 15.0,
                },
            },
        ),
        _progress_item(
            "target_tube_released_stable",
            0.15,
            "object_released_on_support",
            {"object": "target_tube", "support": "centrifuge", "minimum_hold_seconds": 1.0},
        ),
        _progress_item(
            "stop_button_pressed",
            0.10,
            "articulation_joint_state_reached",
            {"object": "centrifuge", "joint": "stop_button_joint", "state": "pressed"},
        ),
        _progress_item(
            "terminal_tube_stable_and_power_off",
            0.05,
            "articulation_joint_state_reached",
            {"object": "centrifuge", "joint": "power_state", "state": "off"},
            terminal=True,
        ),
    ]
    ids = [item["id"] for item in progress]
    return {
        "schema_version": "scenario-forge-genmanip-runtime-contract/v0.6",
        "contract_status": "transport_only",
        "scenario_id": alias.ALIAS_ID,
        "task_name": TASK_NAME,
        "episode_name": "001",
        "coordinate_convention": {
            "translation_unit": "meter",
            "quaternion_order": "wxyz",
            "named_frame_pose_relative_to": "state_prim_path",
            "transform_direction": "state_prim_from_named_frame",
            "frame_scale_allowed": False,
        },
        "execution": {
            "native_goal_role": "native_articulation_status_with_diagnostic_compatibility_projection",
            "frame_aware_metric_active": False,
            "process_invariants_evaluated": False,
            "progress_rubric": {"scored_here": False, "unevaluated_metric_ids": ids},
        },
        "robot": {
            "profile_ref": "manip/lift2/R5a",
            "robot_index": 0,
            "actors": [
                {
                    "id": "operation_arm",
                    "end_effector": "left_gripper",
                    "capabilities": ["press", "pick", "insert", "release"],
                }
            ],
        },
        "objects": [
            _object(stage, "centrifuge", "centrifuge", "/World/obj_centrifuge", "centrifuge"),
            _object(stage, "target_tube", "centrifuge_tube", "/World/obj_primary_tube", "primary_tube"),
            _object(stage, "balance_tube", "balance_tube", "/World/obj_balance_tube", "balance_tube"),
            _object(stage, "tube_rack", "tube_rack", "/World/obj_mixed_rack", "mixed_rack"),
        ],
        "steps": [
            {"id": "press_open", "skill": "press", "actors": ["operation_arm"], "parameters": {"object": "centrifuge", "control": "OPEN"}},
            {"id": "pick_target_tube", "skill": "pick", "actors": ["operation_arm"], "parameters": {"object": "target_tube", "from": alias.TARGET_RACK_SLOT}, "depends_on": ["press_open"]},
            {"id": "insert_target_tube", "skill": "insert", "actors": ["operation_arm"], "parameters": {"object": "target_tube", "target": f"rotor_socket_{alias.TARGET_ROTOR_SOCKET}"}, "depends_on": ["pick_target_tube"]},
            {"id": "press_stop", "skill": "press", "actors": ["operation_arm"], "parameters": {"object": "centrifuge", "control": "STOP"}, "depends_on": ["insert_target_tube"]},
        ],
        "invariants": [],
        "success": {
            "operator": "all",
            "claim_scope": "transport_contract_only_not_robot_success",
            "predicates": [
                {
                    "id": "tube_inserted_in_rotor_socket_18",
                    "type": "relative_pose_reached",
                    "sequence_index": 0,
                    "parameters": {"object": "target_tube", "relative_to": "centrifuge", "xyz_range": target_ranges},
                },
                {
                    "id": "stop_pressed",
                    "type": "articulation_joint_state_reached",
                    "sequence_index": 1,
                    "parameters": {"object": "centrifuge", "joint": "stop_button_joint", "state": "pressed"},
                },
            ],
            "progress_rubric": {
                "aggregation": {"type": "weighted_progress_score", "normalization": "declared_sum", "inactive_treatment": "zero", "primary_metric_id": "target_tube_inserted_in_rotor"},
                "items": progress,
            },
        },
    }


def build(package: Path, out: Path) -> Path:
    from pxr import Usd

    package = package.resolve()
    out = out.resolve()
    output = r9_adapter.build(package, r9_adapter.legacy.DEFAULT_BASE, out)
    old_scene = output / "assets/scene_usds/scenario_forge/task11_r9"
    new_scene = output / "assets/scene_usds/scenario_forge/task12_alias"
    shutil.move(str(old_scene), str(new_scene))
    old_source = output / "assets/task11_r9_source"
    new_source = output / "assets/task12_alias_source"
    shutil.move(str(old_source), str(new_source))
    wrapper = new_scene / "scene.usda"
    stage = Usd.Stage.Open(str(wrapper))
    stage.GetPrimAtPath("/World/_scene").GetReferences().ClearReferences()
    stage.GetPrimAtPath("/World/_scene").GetReferences().AddReference(
        "../../../task12_alias_source/scene.usd", "/World"
    )
    stage.GetPrimAtPath("/World/_scene/obj_table").GetReferences().ClearReferences()
    stage.GetPrimAtPath("/World/_scene/obj_table").GetReferences().AddReference(
        "../../../task12_alias_source/scene.usd", "/World/table"
    )
    stage.GetRootLayer().Save()
    old_tasks = output / "tasks/scenario_forge/task11_r9"
    new_tasks = output / "tasks/scenario_forge/task12_alias"
    shutil.move(str(old_tasks), str(new_tasks))
    shutil.move(str(new_tasks / "002"), str(new_tasks / "001"))

    source_stage = Usd.Stage.Open(str(package / "vr/scene.usd"))
    profile = json.loads(
        (package / "vr/deps/centrifuge/articulation/device_profile.json").read_text()
    )
    socket = profile["tube_sockets"][alias.TARGET_ROTOR_SOCKET]
    target_local_xyz = [
        float(base.ROTOR_ORIGIN[index])
        + float(socket["inserted_bottom_rotor_local_m"][index])
        for index in range(3)
    ]
    contract = _contract(source_stage, target_local_xyz)
    schema = json.loads(
        (ROOT / "src/scenario_forge/schemas/jsonschema/scenario-forge-genmanip-runtime-contract-v0.6.schema.json").read_text()
    )
    jsonschema.validate(contract, schema)

    config_path = output / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    evaluation = config["evaluation_configs"][0]
    evaluation["task_name"] = TASK_NAME
    evaluation["usd_name"] = "assets/scene_usds/scenario_forge/task12_alias/scene"
    evaluation["instruction"] = alias.INSTRUCTION
    final_world = _pose(source_stage, "/World/obj_centrifuge")["xyz"]
    final_world = [final_world[index] + target_local_xyz[index] for index in range(3)]
    evaluation["generation_config"]["goal"] = [
        [
            [
                {
                    "type": "manip/default/sr_based_genmanip_range",
                    "obj1_uid": "primary_tube",
                    "x_type": "absolute",
                    "y_type": "absolute",
                    "z_type": "absolute",
                    "x_range": [final_world[0] - 0.005, final_world[0] + 0.005],
                    "y_range": [final_world[1] - 0.005, final_world[1] + 0.005],
                    "z_range": [final_world[2] - 0.01, final_world[2] + 0.01],
                    "not_set_mass": True,
                }
            ]
        ]
    ]
    config_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True))

    episode_path = new_tasks / "001/episode_metadata.json"
    episode = json.loads(episode_path.read_text())
    episode["episode_name"] = "001"
    episode["task_data"]["instruction"] = alias.INSTRUCTION
    episode["task_data"]["goal"] = evaluation["generation_config"]["goal"]
    episode["task_data"]["scenario_forge_runtime_contract"] = contract
    episode_path.write_text(json.dumps(episode, indent=2, sort_keys=True) + "\n")

    manifest = {
        "schema_version": "scenario-forge.task12-alias-genmanip/v1",
        "scenario_id": alias.ALIAS_ID,
        "alias_task_number": 12,
        "canonical_catalog_modified": False,
        "source_scene_sha256": _sha(package / "vr/scene.usd"),
        "adapter_local_scene_sha256": _sha(new_source / "scene.usd"),
        "scene_usd": "assets/scene_usds/scenario_forge/task12_alias/scene.usda",
        "source_scene_copy": "assets/task12_alias_source/scene.usd",
        "runtime_contract_schema": contract["schema_version"],
        "claims": {
            "nonempty_native_goal": True,
            "task02_metadata_removed": True,
            "robot_free_transfer_oracle_success": False,
            "robot_policy_success": False,
            "task_success": False,
            "benchmark_success": False,
        },
    }
    (output / "package_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    (output / "scenario.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "scenario-forge.task12-alias-scenario/v1",
                "scenario_id": alias.ALIAS_ID,
                "scene_usd": manifest["scene_usd"],
                "source_scene_copy": manifest["source_scene_copy"],
                "config": "config.yaml",
                "episode": "tasks/scenario_forge/task12_alias/001/episode_metadata.json",
                "status": "adapter_smoke_pending",
                "claims": manifest["claims"],
            },
            sort_keys=False,
            allow_unicode=True,
        )
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(build(args.package, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

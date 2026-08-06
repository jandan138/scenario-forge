from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from scenario_forge.core.scenario import ScenarioSpec


REPO_ROOT = Path(__file__).resolve().parents[1]
_V01_SCHEMA_SHA256 = "958e0a9fe13ed93fc195fb54753427616705e3569adda3239b4c188c85b1a0d9"


def _scenario_mapping() -> dict[str, object]:
    return {
        "schema_version": "scenario-spec/v0.1",
        "scenario_id": "scientific_workbench_bimanual_pour",
        "domain": "scientific_workbench",
        "task_family": "bimanual_pour",
        "instruction": (
            "Hold the graduated cylinder with the auxiliary arm, pour from the "
            "conical flask with the operating arm, then return the flask."
        ),
        "scene": {
            "asset_id": "scientific_workbench_environment",
            "root_prim_path": "/World",
            "inactive_prim_paths": ["/World/Cube"],
            "world_anchored_prim_paths": ["/World/background_fixture"],
            "pose": {
                "xyz": [-1.0, 2.0, 0.0],
                "wxyz": [1.0, 0.0, 0.0, 0.0],
            },
        },
        "objects": [
            {
                "id": "table",
                "asset_id": "scientific_workbench_environment",
                "source_prim_path": "/World/table",
                "role": "table",
                "pose": {
                    "xyz": [0.24, 0.0, 0.0],
                    "wxyz": [0.0, 1.0, 0.0, 0.0],
                    "scale_xyz": [0.006, 0.005, 0.004],
                },
                "metadata": {"material_bindings": {"surface": "TableMat"}},
            },
            {
                "id": "obj_conical_bottle03",
                "asset_id": "scientific_workbench_environment",
                "source_prim_path": "/World/conical_bottle03",
                "role": "source_container",
                "pose": {
                    "xyz": [0.32, 0.12, 0.81],
                    "wxyz": [0.6532815, 0.6532815, 0.2705981, 0.2705981],
                },
                "named_frames": {
                    "opening": {"xyz": [0.0, 0.0, 0.18], "wxyz": [1.0, 0.0, 0.0, 0.0]}
                },
                "metadata": {"material_bindings": {"mesh": "GlassFlask"}},
            },
            {
                "id": "obj_graduated_cylinder_03",
                "asset_id": "scientific_workbench_environment",
                "source_prim_path": "/World/graduated_cylinder_03",
                "role": "target_container",
                "pose": {
                    "xyz": [0.32, -0.18, 0.81],
                    "wxyz": [0.7071068, 0.7071068, 0.0, 0.0],
                },
                "named_frames": {
                    "opening": {"xyz": [0.0, 0.0, 0.20], "wxyz": [1.0, 0.0, 0.0, 0.0]}
                },
                "metadata": {"material_bindings": {"mesh": "GlassCylinder"}},
            },
        ],
        "robot": {
            "profile_ref": "manip/lift2/R5a",
            "spawn": {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]},
            "actors": [
                {
                    "id": "auxiliary_arm",
                    "end_effector": "left",
                    "capabilities": ["grasp", "hold"],
                },
                {
                    "id": "operating_arm",
                    "end_effector": "right",
                    "capabilities": [
                        "grasp",
                        "lift",
                        "align",
                        "tilt",
                        "place",
                        "release",
                    ],
                },
            ],
        },
        "steps": [
            {
                "id": "grasp_target",
                "skill": "grasp_and_hold",
                "actors": ["auxiliary_arm"],
                "parameters": {"object": "obj_graduated_cylinder_03"},
            },
            {
                "id": "lift_source",
                "skill": "lift",
                "actors": ["operating_arm"],
                "parameters": {"object": "obj_conical_bottle03"},
                "depends_on": ["grasp_target"],
            },
            {
                "id": "align_openings",
                "skill": "align_openings",
                "actors": ["auxiliary_arm", "operating_arm"],
                "parameters": {
                    "source_frame": "obj_conical_bottle03.opening",
                    "target_frame": "obj_graduated_cylinder_03.opening",
                },
                "depends_on": ["lift_source"],
            },
            {
                "id": "tilt_pour",
                "skill": "tilt_pour",
                "actors": ["operating_arm"],
                "parameters": {"object": "obj_conical_bottle03", "min_tilt_deg": 40.0},
                "depends_on": ["align_openings"],
            },
            {
                "id": "place_source",
                "skill": "place_on_surface",
                "actors": ["operating_arm"],
                "parameters": {"object": "obj_conical_bottle03"},
                "depends_on": ["tilt_pour"],
            },
        ],
        "invariants": [
            {
                "id": "target_held_during_pour",
                "type": "maintain_grasp",
                "actor": "auxiliary_arm",
                "object": "obj_graduated_cylinder_03",
                "from_step": "grasp_target",
                "through_step": "tilt_pour",
            }
        ],
        "success": {
            "operator": "all",
            "claim_scope": "kinematic_proxy",
            "predicates": [
                {
                    "id": "pour_pose_reached",
                    "type": "relative_pose_reached",
                    "sequence_index": 0,
                    "parameters": {
                        "object": "obj_conical_bottle03",
                        "relative_to": "obj_graduated_cylinder_03",
                        "xyz_range": {
                            "x": [-0.08, 0.08],
                            "y": [-0.08, 0.08],
                            "z": [0.10, 0.30],
                        },
                        "axis_alignment": {
                            "object_axis": "y",
                            "target_axis": "y",
                            "comparison": ">=",
                            "threshold_deg": 40.0,
                        },
                    },
                },
                {
                    "id": "source_returned",
                    "type": "object_at_initial_pose",
                    "sequence_index": 1,
                    "parameters": {
                        "object": "obj_conical_bottle03",
                        "xyz_tolerance": [0.06, 0.06, 0.06],
                        "relative_axis_object": "obj_graduated_cylinder_03",
                        "object_axis": "y",
                        "target_axis": "y",
                        "max_axis_error_deg": 15.0,
                    },
                },
            ],
        },
        "max_steps": 1500,
        "seed": "000",
    }


def test_v07_supports_producer_entrypoint_scene_with_embedded_objects() -> None:
    data = _scenario_mapping()
    data["schema_version"] = "scenario-spec/v0.7"
    scene = data["scene"]
    assert isinstance(scene, dict)
    scene["composition_mode"] = "producer_entrypoint"
    objects = data["objects"]
    assert isinstance(objects, list)
    for item in objects:
        assert isinstance(item, dict)
        item["asset_id"] = scene["asset_id"]
        item["instance_mode"] = "embedded_scene_prim"

    spec = ScenarioSpec.from_mapping(data)

    assert spec.scene.composition_mode == "producer_entrypoint"
    assert {item.instance_mode for item in spec.objects} == {"embedded_scene_prim"}
    assert spec.to_mapping()["scene"]["composition_mode"] == "producer_entrypoint"
    schema = json.loads(
        (
            REPO_ROOT
            / "src/scenario_forge/schemas/jsonschema/scenario-spec-v0.7.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert list(Draft202012Validator(schema).iter_errors(data)) == []


def test_v07_round_trips_optional_robot_initial_joint_positions() -> None:
    data = _scenario_mapping()
    data["schema_version"] = "scenario-spec/v0.7"
    robot = data["robot"]
    assert isinstance(robot, dict)
    robot["initial_joint_positions"] = [0.0] * 12 + [0.044] * 4

    spec = ScenarioSpec.from_mapping(data)

    assert spec.robot.initial_joint_positions == (0.0,) * 12 + (0.044,) * 4
    assert spec.to_mapping()["robot"]["initial_joint_positions"] == robot[
        "initial_joint_positions"
    ]
    schema = json.loads(
        (
            REPO_ROOT
            / "src/scenario_forge/schemas/jsonschema/scenario-spec-v0.7.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert list(Draft202012Validator(schema).iter_errors(data)) == []


@pytest.mark.parametrize("bad", [[], [0.0, float("inf")]])
def test_v07_rejects_invalid_robot_initial_joint_positions(bad: list[float]) -> None:
    data = _scenario_mapping()
    data["schema_version"] = "scenario-spec/v0.7"
    robot = data["robot"]
    assert isinstance(robot, dict)
    robot["initial_joint_positions"] = bad

    with pytest.raises(ValueError, match="initial_joint_positions"):
        ScenarioSpec.from_mapping(data)


def test_v07_embedded_object_must_belong_to_scene_asset() -> None:
    data = _scenario_mapping()
    data["schema_version"] = "scenario-spec/v0.7"
    scene = data["scene"]
    assert isinstance(scene, dict)
    scene["composition_mode"] = "producer_entrypoint"
    objects = data["objects"]
    assert isinstance(objects, list)
    item = objects[1]
    assert isinstance(item, dict)
    item["instance_mode"] = "embedded_scene_prim"
    item["asset_id"] = "different_asset"

    with pytest.raises(ValueError, match="embedded_scene_prim.*scene.asset_id"):
        ScenarioSpec.from_mapping(data)


def _scenario_mapping_v02(
    overlay_asset_ids: object = (
        "drying_box_03_dynamic_profile",
        "scientific_workbench_material_overlay",
    ),
) -> dict[str, object]:
    data = _scenario_mapping()
    data["schema_version"] = "scenario-spec/v0.2"
    scene = dict(data["scene"])  # type: ignore[arg-type]
    scene["overlay_asset_ids"] = (
        list(overlay_asset_ids)
        if isinstance(overlay_asset_ids, tuple)
        else overlay_asset_ids
    )
    data["scene"] = scene
    return data


def _scenario_mapping_v03(
    overlay_asset_ids: object = (
        "drying_box_03_dynamic_profile",
        "scientific_workbench_material_overlay",
    ),
) -> dict[str, object]:
    data = _scenario_mapping_v02(overlay_asset_ids)
    data["schema_version"] = "scenario-spec/v0.3"
    steps = [dict(step) for step in data["steps"]]  # type: ignore[index]
    tilt = dict(steps[3])
    tilt["parameters"] = {
        **dict(tilt["parameters"]),
        "min_tilt_deg": 70.0,
    }
    steps[3] = tilt
    data["steps"] = steps
    data["success"] = _exact_bimanual_success_v03()
    return data


def _exact_bimanual_success() -> dict[str, object]:
    return {
        "operator": "all",
        "claim_scope": "kinematic_proxy",
        "predicates": [
            {
                "id": "openings_aligned",
                "type": "named_frames_relative_pose_reached",
                "sequence_index": 0,
                "parameters": {
                    "source_frame": "obj_conical_bottle03.opening",
                    "target_frame": "obj_graduated_cylinder_03.opening",
                    "horizontal_error_max_m": 0.02,
                    "signed_height_range_m": [0.02, 0.05],
                    "source_normal_axis": "z",
                    "target_normal_axis": "z",
                    "normal_angle_max_deg": 10.0,
                    "bounds": "inclusive",
                    "diagnostic_compatibility_projection": {
                        "type": "relative_pose_reached",
                        "parameters": {
                            "object": "obj_conical_bottle03",
                            "relative_to": "obj_graduated_cylinder_03",
                            "xyz_range": {
                                "x": [-0.08, 0.08],
                                "y": [-0.08, 0.08],
                                "z": [0.10, 0.30],
                            },
                        },
                    },
                },
            },
            {
                "id": "source_tilted",
                "type": "named_frame_tilt_angle_reached",
                "sequence_index": 1,
                "parameters": {
                    "object_frame": "obj_conical_bottle03.opening",
                    "world_axis": "z",
                    "angle_range_deg": [40.0, 80.0],
                    "bounds": "inclusive",
                    "diagnostic_compatibility_projection": {
                        "type": "relative_pose_reached",
                        "parameters": {
                            "object": "obj_conical_bottle03",
                            "relative_to": "obj_graduated_cylinder_03",
                            "xyz_range": {
                                "x": [-0.08, 0.08],
                                "y": [-0.08, 0.08],
                                "z": [0.10, 0.30],
                            },
                            "axis_alignment": {
                                "object_axis": "y",
                                "target_axis": "y",
                                "comparison": ">=",
                                "threshold_deg": 40.0,
                            },
                        },
                    },
                },
            },
            {
                "id": "source_returned",
                "type": "object_returned_to_post_warmup_pose",
                "sequence_index": 2,
                "parameters": {
                    "object": "obj_conical_bottle03",
                    "translation_error_max_m": 0.06,
                    "rotation_error_max_deg": 15.0,
                    "bounds": "inclusive",
                    "diagnostic_compatibility_projection": {
                        "type": "object_at_initial_pose",
                        "parameters": {
                            "object": "obj_conical_bottle03",
                            "xyz_tolerance": [0.06, 0.06, 0.06],
                            "relative_axis_object": "obj_graduated_cylinder_03",
                            "object_axis": "y",
                            "target_axis": "y",
                            "max_axis_error_deg": 15.0,
                        },
                    },
                },
            },
        ],
    }


def _v03_relative_pose_predicate(
    *,
    predicate_id: str,
    sequence_index: int,
    nominal_angle_deg: float,
    polar_angle_range_deg: list[float],
) -> dict[str, object]:
    half_angle = math.radians(nominal_angle_deg) / 2.0
    return {
        "id": predicate_id,
        "type": "named_frames_relative_pose_reached",
        "sequence_index": sequence_index,
        "parameters": {
            "source_frame": "obj_conical_bottle03.opening",
            "target_frame": "obj_graduated_cylinder_03.opening",
            "target_frame_from_source_frame_nominal_pose": {
                "xyz": [0.0, 0.0175, 0.0425],
                "wxyz": [math.cos(half_angle), math.sin(half_angle), 0.0, 0.0],
            },
            "source_origin_in_target_frame_range_m": {
                "x": [-0.005, 0.005],
                "y": [0.015, 0.020],
                "z": [0.035, 0.050],
            },
            "source_normal_axis": "z",
            "target_normal_axis": "z",
            "source_normal_polar_angle_range_deg": polar_angle_range_deg,
            "source_normal_azimuth_range_deg": [-95.0, -85.0],
            "bounds": "inclusive",
            "diagnostic_compatibility_projection": {
                "type": "relative_pose_reached",
                "parameters": {
                    "object": "obj_conical_bottle03",
                    "relative_to": "obj_graduated_cylinder_03",
                    "xyz_range": {
                        "x": [-0.08, 0.08],
                        "y": [-0.08, 0.08],
                        "z": [0.10, 0.30],
                    },
                },
            },
        },
    }


def _exact_bimanual_success_v03() -> dict[str, object]:
    return {
        "operator": "all",
        "claim_scope": "kinematic_proxy",
        "predicates": [
            _v03_relative_pose_predicate(
                predicate_id="opening_prepour_pose_reached",
                sequence_index=0,
                nominal_angle_deg=58.0,
                polar_angle_range_deg=[55.0, 60.0],
            ),
            _v03_relative_pose_predicate(
                predicate_id="opening_pour_pose_reached",
                sequence_index=1,
                nominal_angle_deg=75.0,
                polar_angle_range_deg=[70.0, 80.0],
            ),
            {
                "id": "source_returned",
                "type": "object_returned_to_post_warmup_pose",
                "sequence_index": 2,
                "parameters": {
                    "object": "obj_conical_bottle03",
                    "translation_error_max_m": 0.06,
                    "rotation_error_max_deg": 15.0,
                    "bounds": "inclusive",
                    "diagnostic_compatibility_projection": {
                        "type": "object_at_initial_pose",
                        "parameters": {
                            "object": "obj_conical_bottle03",
                            "xyz_tolerance": [0.06, 0.06, 0.06],
                            "relative_axis_object": "obj_graduated_cylinder_03",
                            "object_axis": "y",
                            "target_axis": "y",
                            "max_axis_error_deg": 15.0,
                        },
                    },
                },
            },
        ],
    }


def _progress_rubric() -> dict[str, object]:
    return {
        "aggregation": {
            "type": "weighted_progress_score",
            "normalization": "declared_sum",
            "inactive_treatment": "zero",
            "primary_metric_id": "openings_aligned_while_grasped",
        },
        "items": [
            {
                "id": "source_lifted",
                "weight": 0.20,
                "temporal": {"kind": "instant"},
                "condition": {
                    "type": "object_lifted",
                    "parameters": {
                        "object": "obj_conical_bottle03",
                        "support_surface": "table",
                        "min_clearance_m": 0.01,
                        "held_by": "operating_arm",
                    },
                },
                "source_ref": {"item": "时序1"},
            },
            {
                "id": "openings_aligned_while_grasped",
                "weight": 0.30,
                "temporal": {
                    "kind": "sustained",
                    "window": {"from_step": "align_openings", "through_step": "tilt_pour"},
                },
                "condition": {
                    "type": "pose_while_grasped",
                    "parameters": {
                        "grasp": {"actor": "operating_arm", "object": "obj_conical_bottle03"},
                        "predicate": {
                            "type": "named_frames_relative_pose_reached",
                            "parameters": {
                                "source_frame": "obj_conical_bottle03.opening",
                                "target_frame": "obj_graduated_cylinder_03.opening",
                            },
                        },
                    },
                },
                "source_ref": {"item": "时序2"},
            },
            {
                "id": "liquid_transfer_majority",
                "weight": 0.20,
                "active": False,
                "requires": ["liquid_sim.contained_volume_ratio"],
                "temporal": {"kind": "terminal"},
                "condition": {
                    "type": "liquid_transfer_ratio",
                    "parameters": {
                        "source": "obj_conical_bottle03",
                        "target": "obj_graduated_cylinder_03",
                        "ratio_threshold": 0.5,
                        "measurement": "containment_ledger",
                        "initial_snapshot": "episode_start",
                    },
                },
                "source_ref": {"item": "终帧-转移比例过半"},
            },
            {
                "id": "liquid_transfer_complete",
                "weight": 0.20,
                "active": False,
                "requires": ["liquid_sim.contained_volume_ratio"],
                "temporal": {"kind": "terminal"},
                "condition": {
                    "type": "liquid_transfer_ratio",
                    "parameters": {
                        "source": "obj_conical_bottle03",
                        "target": "obj_graduated_cylinder_03",
                        "ratio_threshold": 0.9,
                        "measurement": "containment_ledger",
                        "initial_snapshot": "episode_start",
                    },
                },
                "source_ref": {"item": "终帧-转移比例达全阈值"},
            },
            {
                "id": "source_returned_released",
                "weight": 0.10,
                "temporal": {"kind": "terminal"},
                "condition": {
                    "type": "object_released_on_support",
                    "parameters": {
                        "object": "obj_conical_bottle03",
                        "support_surface": "table",
                        "upright_max_tilt_deg": 15.0,
                        "region": {
                            "center": [0.32, 0.12, 0.81],
                            "half_extents": [0.06, 0.06, 0.06],
                        },
                        "released": True,
                    },
                },
                "source_ref": {"item": "终帧-归还并释放"},
            },
        ],
    }


def _scenario_mapping_v04() -> dict[str, object]:
    data = _scenario_mapping_v03([])
    data["schema_version"] = "scenario-spec/v0.4"
    scene = dict(data["scene"])  # type: ignore[arg-type]
    scene.pop("overlay_asset_ids", None)
    data["scene"] = scene
    success = dict(data["success"])  # type: ignore[arg-type]
    success["progress_rubric"] = _progress_rubric()
    data["success"] = success
    return data


def _scenario_mapping_v05() -> dict[str, object]:
    data = _scenario_mapping_v02([])
    data["schema_version"] = "scenario-spec/v0.5"
    scene = dict(data["scene"])  # type: ignore[arg-type]
    scene.pop("overlay_asset_ids")
    data["scene"] = scene
    success = dict(data["success"])  # type: ignore[arg-type]
    predicates = [dict(item) for item in success["predicates"]]  # type: ignore[index]
    relative_parameters = dict(predicates[0]["parameters"])  # type: ignore[arg-type]
    relative_alignment = dict(relative_parameters["axis_alignment"])  # type: ignore[arg-type]
    relative_alignment["relative_to_part"] = "rotor"
    relative_parameters["axis_alignment"] = relative_alignment
    predicates[0]["parameters"] = relative_parameters
    initial_parameters = dict(predicates[1]["parameters"])  # type: ignore[arg-type]
    initial_parameters["relative_axis_part"] = "rotor"
    predicates[1]["parameters"] = initial_parameters
    predicates.append(
        {
            "id": "centrifuge_lid_closed",
            "type": "articulation_joint_state_reached",
            "sequence_index": 2,
            "parameters": {
                "object": "obj_graduated_cylinder_03",
                "joint": "lid",
                "state": "closed",
            },
        }
    )
    success["predicates"] = predicates
    data["success"] = success
    return data


def _scenario_mapping_v06() -> dict[str, object]:
    data = _scenario_mapping_v05()
    data["schema_version"] = "scenario-spec/v0.6"
    success = dict(data["success"])  # type: ignore[arg-type]
    predicates = [dict(item) for item in success["predicates"][:2]]  # type: ignore[index]
    relative_parameters = dict(predicates[0]["parameters"])  # type: ignore[arg-type]
    relative_alignment = dict(relative_parameters["axis_alignment"])  # type: ignore[arg-type]
    relative_alignment.pop("relative_to_part")
    relative_parameters["axis_alignment"] = relative_alignment
    predicates[0]["parameters"] = relative_parameters
    initial_parameters = dict(predicates[1]["parameters"])  # type: ignore[arg-type]
    initial_parameters.pop("relative_axis_part")
    predicates[1]["parameters"] = initial_parameters
    success["predicates"] = predicates
    rubric = _progress_rubric()
    items = [dict(item) for item in rubric["items"]]
    for item in items:
        item.setdefault("active", True)
    items[-1] = {
        **items[-1],
        "active": True,
        "condition": {
            "type": "motion_trajectory_completed",
            "parameters": {
                "object": "obj_conical_bottle03",
                "trajectory_id": "shake_mix",
                "min_cycles": 2,
            },
        },
    }
    rubric["items"] = items
    success["progress_rubric"] = rubric
    data["success"] = success
    return data


def test_scenario_spec_round_trips_bimanual_roles_and_invariant() -> None:
    spec = ScenarioSpec.from_mapping(_scenario_mapping())

    assert spec.robot.profile_ref == "manip/lift2/R5a"
    assert [actor.actor_id for actor in spec.robot.actors] == [
        "auxiliary_arm",
        "operating_arm",
    ]
    assert spec.steps[2].actors == ("auxiliary_arm", "operating_arm")
    assert spec.invariants[0].through_step == "tilt_pour"
    assert spec.success.claim_scope == "kinematic_proxy"
    assert spec.scene.inactive_prim_paths == ("/World/Cube",)
    assert spec.scene.world_anchored_prim_paths == ("/World/background_fixture",)
    assert spec.scene.pose is not None
    assert spec.scene.pose.xyz == (-1.0, 2.0, 0.0)
    assert spec.to_mapping() == _scenario_mapping()


def test_scenario_spec_v02_round_trips_scene_overlays_strongest_first() -> None:
    data = _scenario_mapping_v02()

    spec = ScenarioSpec.from_mapping(data)

    assert spec.schema_version == "scenario-spec/v0.2"
    assert spec.scene.overlay_asset_ids == (
        "drying_box_03_dynamic_profile",
        "scientific_workbench_material_overlay",
    )
    assert spec.to_mapping() == data


def test_scenario_spec_v01_without_scene_overlays_still_round_trips() -> None:
    data = _scenario_mapping()

    spec = ScenarioSpec.from_mapping(data)

    assert spec.schema_version == "scenario-spec/v0.1"
    assert spec.scene.overlay_asset_ids == ()
    assert "overlay_asset_ids" not in spec.to_mapping()["scene"]  # type: ignore[operator]


def test_scenario_spec_v01_rejects_scene_overlays() -> None:
    data = _scenario_mapping()
    scene = dict(data["scene"])  # type: ignore[arg-type]
    scene["overlay_asset_ids"] = ["drying_box_03_dynamic_profile"]
    data["scene"] = scene

    with pytest.raises(ValueError, match="overlay_asset_ids"):
        ScenarioSpec.from_mapping(data)


@pytest.mark.parametrize(
    "overlay_asset_ids",
    [
        "drying_box_03_dynamic_profile",
        [],
        ["drying_box_03_dynamic_profile", "drying_box_03_dynamic_profile"],
        ["scientific_workbench_environment"],
    ],
)
def test_scenario_spec_v02_rejects_invalid_scene_overlays(
    overlay_asset_ids: object,
) -> None:
    data = _scenario_mapping_v02(overlay_asset_ids)

    with pytest.raises(ValueError, match="scene.overlay_asset_ids"):
        ScenarioSpec.from_mapping(data)


@pytest.mark.parametrize("operator", ["all", "any"])
def test_scenario_spec_accepts_declared_success_operators(operator: str) -> None:
    data = _scenario_mapping()
    success = dict(data["success"])  # type: ignore[arg-type]
    success["operator"] = operator
    data["success"] = success

    assert ScenarioSpec.from_mapping(data).success.operator == operator


def test_scenario_spec_rejects_unknown_success_operator() -> None:
    data = _scenario_mapping()
    success = dict(data["success"])  # type: ignore[arg-type]
    success["operator"] = "xor"
    data["success"] = success

    with pytest.raises(ValueError, match="success.operator"):
        ScenarioSpec.from_mapping(data)


def test_scenario_spec_rejects_unknown_step_actor() -> None:
    data = _scenario_mapping()
    steps = list(data["steps"])  # type: ignore[arg-type]
    steps[0] = {**steps[0], "actors": ["third_arm"]}
    data["steps"] = steps

    with pytest.raises(ValueError, match="unknown actor third_arm"):
        ScenarioSpec.from_mapping(data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("scenario_id", "../outside"),
        ("scenario_id", "/absolute"),
        ("seed", "../../outside"),
        ("seed", "/absolute"),
        ("seed", -1),
    ],
)
def test_scenario_spec_rejects_unsafe_package_path_segments(
    field: str, value: object
) -> None:
    data = _scenario_mapping()
    data[field] = value

    with pytest.raises(ValueError, match=field):
        ScenarioSpec.from_mapping(data)


def test_scenario_spec_schema_artifact_exists_and_parses() -> None:
    path = REPO_ROOT / "src/scenario_forge/schemas/jsonschema/scenario-spec-v0.1.schema.json"

    schema = json.loads(path.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schema_version"]["const"] == "scenario-spec/v0.1"
    assert {"scene", "objects", "robot", "steps", "success"}.issubset(schema["required"])
    assert "inactive_prim_paths" in schema["$defs"]["sceneSource"]["properties"]
    assert "world_anchored_prim_paths" in schema["$defs"]["sceneSource"]["properties"]
    assert schema["$defs"]["sceneSource"]["properties"]["pose"] == {
        "$ref": "#/$defs/pose"
    }
    assert "liquid_transfer_claim_allowed" not in schema["$defs"]["success"]["properties"]


def test_scenario_spec_v02_schema_declares_unique_scene_overlays_without_mutating_v01() -> None:
    v01_path = (
        REPO_ROOT
        / "src/scenario_forge/schemas/jsonschema/scenario-spec-v0.1.schema.json"
    )
    v02_path = (
        REPO_ROOT
        / "src/scenario_forge/schemas/jsonschema/scenario-spec-v0.2.schema.json"
    )

    assert v02_path.is_file()
    v01_schema = json.loads(v01_path.read_text(encoding="utf-8"))
    v02_schema = json.loads(v02_path.read_text(encoding="utf-8"))
    overlay_schema = v02_schema["$defs"]["sceneSource"]["properties"][
        "overlay_asset_ids"
    ]

    assert v02_schema["properties"]["schema_version"]["const"] == "scenario-spec/v0.2"
    assert overlay_schema["type"] == "array"
    assert overlay_schema["minItems"] == 1
    assert overlay_schema["uniqueItems"] is True
    assert overlay_schema["items"] == {"$ref": "#/$defs/nonEmptyString"}
    assert "overlay_asset_ids" not in v01_schema["$defs"]["sceneSource"]["properties"]
    assert sha256(v01_path.read_bytes()).hexdigest() == _V01_SCHEMA_SHA256


def test_golden_bimanual_pour_example_is_a_valid_scenario_spec() -> None:
    path = REPO_ROOT / "examples/scientific_workbench/bimanual_pour/scenario.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    spec = ScenarioSpec.from_mapping(data)

    assert spec.schema_version == "scenario-spec/v0.4"
    assert spec.scenario_id == "scientific_workbench_bimanual_pour"
    assert len(spec.steps) == 5
    assert spec.invariants[0].invariant_type == "maintain_grasp"
    assert spec.steps[3].parameters["min_tilt_deg"] == 70.0
    predicates = spec.success.predicates
    assert [predicate.predicate_type for predicate in predicates] == [
        "named_frames_relative_pose_reached",
        "named_frames_relative_pose_reached",
        "object_returned_to_post_warmup_pose",
    ]
    assert predicates[0].parameters[
        "source_normal_polar_angle_range_deg"
    ] == [55.0, 60.0]
    assert predicates[1].parameters[
        "source_normal_polar_angle_range_deg"
    ] == [70.0, 80.0]
    rubric = spec.success.progress_rubric
    assert rubric is not None
    assert rubric.aggregation["normalization"] == "declared_sum"
    weights = {item.item_id: item.weight for item in rubric.items}
    assert weights == {
        "source_lifted": 0.20,
        "openings_aligned_while_grasped": 0.30,
        "liquid_transfer_majority": 0.20,
        "liquid_transfer_complete": 0.20,
        "source_returned_released": 0.10,
    }
    inactive = {item.item_id for item in rubric.items if not item.active}
    assert inactive == {"liquid_transfer_majority", "liquid_transfer_complete"}
    for item in rubric.items:
        assert item.source_ref["document_revision"] == 1549


def test_v02_round_trips_explicit_ordered_bimanual_success_contract() -> None:
    data = _scenario_mapping_v02([])
    scene = dict(data["scene"])  # type: ignore[arg-type]
    scene.pop("overlay_asset_ids", None)
    data["scene"] = scene
    data["success"] = _exact_bimanual_success()

    spec = ScenarioSpec.from_mapping(data)

    assert [predicate.predicate_type for predicate in spec.success.predicates] == [
        "named_frames_relative_pose_reached",
        "named_frame_tilt_angle_reached",
        "object_returned_to_post_warmup_pose",
    ]
    assert [predicate.sequence_index for predicate in spec.success.predicates] == [0, 1, 2]
    assert spec.to_mapping() == data


def test_v03_round_trips_two_ordered_relative_pose_stages() -> None:
    data = _scenario_mapping_v03([])
    scene = dict(data["scene"])  # type: ignore[arg-type]
    scene.pop("overlay_asset_ids", None)
    data["scene"] = scene

    spec = ScenarioSpec.from_mapping(data)

    assert spec.schema_version == "scenario-spec/v0.3"
    assert [predicate.predicate_type for predicate in spec.success.predicates] == [
        "named_frames_relative_pose_reached",
        "named_frames_relative_pose_reached",
        "object_returned_to_post_warmup_pose",
    ]
    assert [predicate.sequence_index for predicate in spec.success.predicates] == [0, 1, 2]
    assert spec.to_mapping() == data


@pytest.mark.parametrize(
    ("predicate_index", "field", "value", "message"),
    [
        (
            0,
            "source_normal_polar_angle_range_deg",
            [60.0, 55.0],
            "source_normal_polar_angle_range_deg",
        ),
        (
            0,
            "source_normal_azimuth_range_deg",
            [-181.0, -85.0],
            "source_normal_azimuth_range_deg",
        ),
        (
            0,
            "source_origin_in_target_frame_range_m",
            {"x": [0.005, -0.005], "y": [0.015, 0.020], "z": [0.035, 0.050]},
            "source_origin_in_target_frame_range_m.x",
        ),
        (
            0,
            "normal_angle_max_deg",
            10.0,
            "unexpected field|normal_angle_max_deg",
        ),
    ],
)
def test_v03_rejects_invalid_relative_pose_contract_fields(
    predicate_index: int,
    field: str,
    value: object,
    message: str,
) -> None:
    data = _scenario_mapping_v03([])
    scene = dict(data["scene"])  # type: ignore[arg-type]
    scene.pop("overlay_asset_ids", None)
    data["scene"] = scene
    success = _exact_bimanual_success_v03()
    predicates = list(success["predicates"])  # type: ignore[arg-type]
    predicate = dict(predicates[predicate_index])
    parameters = dict(predicate["parameters"])  # type: ignore[arg-type]
    parameters[field] = value
    predicate["parameters"] = parameters
    predicates[predicate_index] = predicate
    success["predicates"] = predicates
    data["success"] = success

    with pytest.raises(ValueError, match=message):
        ScenarioSpec.from_mapping(data)


def test_v03_rejects_nominal_pose_outside_success_range() -> None:
    data = _scenario_mapping_v03([])
    scene = dict(data["scene"])  # type: ignore[arg-type]
    scene.pop("overlay_asset_ids", None)
    data["scene"] = scene
    success = _exact_bimanual_success_v03()
    predicates = list(success["predicates"])  # type: ignore[arg-type]
    predicate = dict(predicates[0])
    parameters = dict(predicate["parameters"])  # type: ignore[arg-type]
    nominal = dict(parameters["target_frame_from_source_frame_nominal_pose"])  # type: ignore[arg-type]
    nominal["xyz"] = [0.0, 0.021, 0.0425]
    parameters["target_frame_from_source_frame_nominal_pose"] = nominal
    predicate["parameters"] = parameters
    predicates[0] = predicate
    success["predicates"] = predicates
    data["success"] = success

    with pytest.raises(ValueError, match="nominal.*inside"):
        ScenarioSpec.from_mapping(data)


def test_v03_rejects_legacy_success_shape() -> None:
    data = _scenario_mapping_v03([])
    scene = dict(data["scene"])  # type: ignore[arg-type]
    scene.pop("overlay_asset_ids", None)
    data["scene"] = scene
    data["success"] = _scenario_mapping()["success"]

    with pytest.raises(ValueError, match="v0.3.*exact ordered bimanual"):
        ScenarioSpec.from_mapping(data)


def test_v03_rejects_return_object_that_differs_from_relative_pose_source() -> None:
    data = _scenario_mapping_v03([])
    scene = dict(data["scene"])  # type: ignore[arg-type]
    scene.pop("overlay_asset_ids", None)
    data["scene"] = scene
    success = _exact_bimanual_success_v03()
    predicates = list(success["predicates"])  # type: ignore[arg-type]
    returned = dict(predicates[2])
    parameters = dict(returned["parameters"])  # type: ignore[arg-type]
    parameters["object"] = "obj_graduated_cylinder_03"
    returned["parameters"] = parameters
    predicates[2] = returned
    success["predicates"] = predicates
    data["success"] = success

    with pytest.raises(ValueError, match="return object.*source frame object"):
        ScenarioSpec.from_mapping(data)


def test_v03_rejects_mismatched_relative_pose_frames_between_stages() -> None:
    data = _scenario_mapping_v03([])
    scene = dict(data["scene"])  # type: ignore[arg-type]
    scene.pop("overlay_asset_ids", None)
    data["scene"] = scene
    success = _exact_bimanual_success_v03()
    predicates = list(success["predicates"])  # type: ignore[arg-type]
    pour = dict(predicates[1])
    parameters = dict(pour["parameters"])  # type: ignore[arg-type]
    parameters["target_frame"] = "obj_conical_bottle03.opening"
    pour["parameters"] = parameters
    predicates[1] = pour
    success["predicates"] = predicates
    data["success"] = success

    with pytest.raises(ValueError, match="pre-pour and pour predicates.*same frames"):
        ScenarioSpec.from_mapping(data)


def test_v03_rejects_nominal_orientation_outside_normal_gate() -> None:
    data = _scenario_mapping_v03([])
    scene = dict(data["scene"])  # type: ignore[arg-type]
    scene.pop("overlay_asset_ids", None)
    data["scene"] = scene
    success = _exact_bimanual_success_v03()
    predicates = list(success["predicates"])  # type: ignore[arg-type]
    pre_pour = dict(predicates[0])
    parameters = dict(pre_pour["parameters"])  # type: ignore[arg-type]
    nominal = dict(parameters["target_frame_from_source_frame_nominal_pose"])  # type: ignore[arg-type]
    half_angle = math.radians(45.0) / 2.0
    nominal["wxyz"] = [math.cos(half_angle), math.sin(half_angle), 0.0, 0.0]
    parameters["target_frame_from_source_frame_nominal_pose"] = nominal
    pre_pour["parameters"] = parameters
    predicates[0] = pre_pour
    success["predicates"] = predicates
    data["success"] = success

    with pytest.raises(ValueError, match="nominal source-normal polar angle.*inside"):
        ScenarioSpec.from_mapping(data)


@pytest.mark.parametrize(
    ("predicate_index", "field", "value", "message"),
    [
        (0, "horizontal_error_max_m", -0.01, "horizontal_error_max_m"),
        (0, "signed_height_range_m", [0.05, 0.02], "signed_height_range_m"),
        (0, "normal_angle_max_deg", 181.0, "normal_angle_max_deg"),
        (0, "source_normal_axis", "world_z", "source_normal_axis"),
        (1, "world_axis", "y", "world_axis"),
        (1, "angle_range_deg", [80.0, 40.0], "angle_range_deg"),
        (2, "translation_error_max_m", -0.01, "translation_error_max_m"),
        (2, "rotation_error_max_deg", 181.0, "rotation_error_max_deg"),
        (2, "bounds", "exclusive", "bounds"),
    ],
)
def test_v02_rejects_invalid_explicit_bimanual_predicate_bounds(
    predicate_index: int,
    field: str,
    value: object,
    message: str,
) -> None:
    data = _scenario_mapping_v02([])
    scene = dict(data["scene"])  # type: ignore[arg-type]
    scene.pop("overlay_asset_ids", None)
    data["scene"] = scene
    success = _exact_bimanual_success()
    predicates = list(success["predicates"])  # type: ignore[arg-type]
    predicate = dict(predicates[predicate_index])
    parameters = dict(predicate["parameters"])  # type: ignore[arg-type]
    parameters[field] = value
    predicate["parameters"] = parameters
    predicates[predicate_index] = predicate
    success["predicates"] = predicates
    data["success"] = success

    with pytest.raises(ValueError, match=message):
        ScenarioSpec.from_mapping(data)


def test_explicit_bimanual_predicates_require_v02_and_contiguous_sequence() -> None:
    data = _scenario_mapping()
    success = _exact_bimanual_success()
    predicates = list(success["predicates"])  # type: ignore[arg-type]
    predicates[1] = {**predicates[1], "sequence_index": 3}  # type: ignore[dict-item]
    success["predicates"] = predicates
    data["success"] = success

    with pytest.raises(ValueError, match="scenario-spec/v0.2|sequence_index"):
        ScenarioSpec.from_mapping(data)


def test_explicit_bimanual_predicates_require_list_order_to_match_sequence() -> None:
    data = _scenario_mapping_v02([])
    scene = dict(data["scene"])  # type: ignore[arg-type]
    scene.pop("overlay_asset_ids", None)
    data["scene"] = scene
    success = _exact_bimanual_success()
    predicates = list(success["predicates"])  # type: ignore[arg-type]
    success["predicates"] = [predicates[1], predicates[0], predicates[2]]
    data["success"] = success

    with pytest.raises(ValueError, match="list order|sequence_index"):
        ScenarioSpec.from_mapping(data)


def test_v02_json_schema_validates_exact_predicate_parameter_shapes() -> None:
    data = _scenario_mapping_v02([])
    scene = dict(data["scene"])  # type: ignore[arg-type]
    scene.pop("overlay_asset_ids", None)
    data["scene"] = scene
    data["success"] = _exact_bimanual_success()
    schema_path = (
        REPO_ROOT
        / "src/scenario_forge/schemas/jsonschema/scenario-spec-v0.2.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    validator.validate(data)
    invalid = json.loads(json.dumps(data))
    invalid["success"]["predicates"][0]["parameters"]["unexpected"] = True
    errors = list(validator.iter_errors(invalid))
    assert errors
    assert any(
        nested.validator == "additionalProperties"
        for error in errors
        for nested in error.context
    )


def test_v02_json_schema_rejects_reordered_exact_success_and_accepts_legacy() -> None:
    schema_path = (
        REPO_ROOT
        / "src/scenario_forge/schemas/jsonschema/scenario-spec-v0.2.schema.json"
    )
    validator = Draft202012Validator(
        json.loads(schema_path.read_text(encoding="utf-8"))
    )
    legacy = _scenario_mapping_v02([])
    legacy_scene = dict(legacy["scene"])  # type: ignore[arg-type]
    legacy_scene.pop("overlay_asset_ids", None)
    legacy["scene"] = legacy_scene

    validator.validate(legacy)

    reordered = json.loads(json.dumps(legacy))
    reordered["success"] = _exact_bimanual_success()
    predicates = reordered["success"]["predicates"]
    predicates[0], predicates[1] = predicates[1], predicates[0]

    assert list(validator.iter_errors(reordered))


@pytest.mark.parametrize(
    "wxyz",
    [
        [2.0, 0.0, 0.0, 0.0],
        [float("nan"), 0.0, 0.0, 0.0],
    ],
)
def test_scenario_spec_rejects_runtime_incompatible_pose_quaternions(
    wxyz: list[float],
) -> None:
    data = _scenario_mapping()
    objects = [dict(item) for item in data["objects"]]  # type: ignore[index]
    source = dict(objects[1])
    named_frames = dict(source["named_frames"])
    opening = dict(named_frames["opening"])
    opening["wxyz"] = wxyz
    named_frames["opening"] = opening
    source["named_frames"] = named_frames
    objects[1] = source
    data["objects"] = objects

    with pytest.raises(ValueError, match="wxyz.*unit quaternion|finite"):
        ScenarioSpec.from_mapping(data)


def test_v04_round_trips_progress_rubric() -> None:
    data = _scenario_mapping_v04()

    spec = ScenarioSpec.from_mapping(data)

    assert spec.schema_version == "scenario-spec/v0.4"
    rubric = spec.success.progress_rubric
    assert rubric is not None
    assert rubric.aggregation["normalization"] == "declared_sum"
    assert rubric.aggregation["inactive_treatment"] == "zero"
    assert [item.item_id for item in rubric.items] == [
        "source_lifted",
        "openings_aligned_while_grasped",
        "liquid_transfer_majority",
        "liquid_transfer_complete",
        "source_returned_released",
    ]
    assert rubric.items[2].active is False
    assert rubric.items[2].requires == ("liquid_sim.contained_volume_ratio",)
    assert rubric.items[1].temporal["kind"] == "sustained"
    assert spec.to_mapping()["success"]["progress_rubric"]["items"][0]["weight"] == 0.20


def test_v04_without_rubric_keeps_exact_success_only() -> None:
    data = _scenario_mapping_v04()
    success = dict(data["success"])  # type: ignore[arg-type]
    success.pop("progress_rubric")
    data["success"] = success

    spec = ScenarioSpec.from_mapping(data)

    assert spec.success.progress_rubric is None


def test_v03_rejects_progress_rubric() -> None:
    data = _scenario_mapping_v03([])
    scene = dict(data["scene"])  # type: ignore[arg-type]
    scene.pop("overlay_asset_ids", None)
    data["scene"] = scene
    success = dict(data["success"])  # type: ignore[arg-type]
    success["progress_rubric"] = _progress_rubric()
    data["success"] = success

    with pytest.raises(ValueError, match="progress_rubric"):
        ScenarioSpec.from_mapping(data)


def test_v04_rejects_weight_sum_not_one() -> None:
    data = _scenario_mapping_v04()
    success = dict(data["success"])  # type: ignore[arg-type]
    rubric = dict(success["progress_rubric"])
    items = [dict(item) for item in rubric["items"]]
    items[0]["weight"] = 0.10
    rubric["items"] = items
    success["progress_rubric"] = rubric
    data["success"] = success

    with pytest.raises(ValueError, match="weight"):
        ScenarioSpec.from_mapping(data)


def test_v04_rejects_duplicate_rubric_ids() -> None:
    data = _scenario_mapping_v04()
    success = dict(data["success"])  # type: ignore[arg-type]
    rubric = dict(success["progress_rubric"])
    items = [dict(item) for item in rubric["items"]]
    items[1]["id"] = "source_lifted"
    rubric["items"] = items
    success["progress_rubric"] = rubric
    data["success"] = success

    with pytest.raises(ValueError, match="duplicate"):
        ScenarioSpec.from_mapping(data)


def test_v04_rejects_unknown_temporal_kind() -> None:
    data = _scenario_mapping_v04()
    success = dict(data["success"])  # type: ignore[arg-type]
    rubric = dict(success["progress_rubric"])
    items = [dict(item) for item in rubric["items"]]
    items[0]["temporal"] = {"kind": "periodic"}
    rubric["items"] = items
    success["progress_rubric"] = rubric
    data["success"] = success

    with pytest.raises(ValueError, match="temporal"):
        ScenarioSpec.from_mapping(data)


def test_v04_sustained_window_must_reference_known_steps_in_order() -> None:
    for window, match in (
        ({"from_step": "missing", "through_step": "tilt_pour"}, "unknown step"),
        ({"from_step": "tilt_pour", "through_step": "align_openings"}, "ends before"),
    ):
        data = _scenario_mapping_v04()
        success = dict(data["success"])  # type: ignore[arg-type]
        rubric = dict(success["progress_rubric"])
        items = [dict(item) for item in rubric["items"]]
        items[1]["temporal"] = {"kind": "sustained", "window": window}
        rubric["items"] = items
        success["progress_rubric"] = rubric
        data["success"] = success

        with pytest.raises(ValueError, match=match):
            ScenarioSpec.from_mapping(data)


def test_v04_rejects_unknown_condition_object_and_actor() -> None:
    data = _scenario_mapping_v04()
    success = dict(data["success"])  # type: ignore[arg-type]
    rubric = dict(success["progress_rubric"])
    items = [dict(item) for item in rubric["items"]]
    lifted = dict(items[0])
    condition = dict(lifted["condition"])
    parameters = dict(condition["parameters"])
    parameters["object"] = "obj_missing"
    condition["parameters"] = parameters
    lifted["condition"] = condition
    items[0] = lifted
    grasped = dict(items[1])
    grasped_condition = dict(grasped["condition"])
    grasped_parameters = dict(grasped_condition["parameters"])
    grasped_parameters["grasp"] = {"actor": "missing_arm", "object": "obj_conical_bottle03"}
    grasped_condition["parameters"] = grasped_parameters
    grasped["condition"] = grasped_condition
    items[1] = grasped
    rubric["items"] = items
    success["progress_rubric"] = rubric
    data["success"] = success

    with pytest.raises(ValueError, match="unknown object"):
        ScenarioSpec.from_mapping(data)

    items[0] = _progress_rubric()["items"][0]
    rubric["items"] = items

    with pytest.raises(ValueError, match="unknown actor"):
        ScenarioSpec.from_mapping(data)


def test_v04_rejects_grasp_condition_duplicated_by_invariant() -> None:
    data = _scenario_mapping_v04()
    invariants = [dict(data["invariants"][0])]  # type: ignore[index]
    invariants.append(
        {
            "id": "source_held_during_pour",
            "type": "maintain_grasp",
            "actor": "operating_arm",
            "object": "obj_conical_bottle03",
            "from_step": "lift_source",
            "through_step": "tilt_pour",
        }
    )
    data["invariants"] = invariants

    with pytest.raises(ValueError, match="progress rubric"):
        ScenarioSpec.from_mapping(data)


def test_v04_json_schema_validates_rubric_and_rejects_bad_weight() -> None:
    schema = json.loads(
        (
            REPO_ROOT
            / "src/scenario_forge/schemas/jsonschema/scenario-spec-v0.4.schema.json"
        ).read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(schema)

    assert not list(validator.iter_errors(_scenario_mapping_v04()))

    bad = _scenario_mapping_v04()
    success = dict(bad["success"])  # type: ignore[arg-type]
    rubric = dict(success["progress_rubric"])
    items = [dict(item) for item in rubric["items"]]
    items[0]["weight"] = 1.5
    rubric["items"] = items
    success["progress_rubric"] = rubric
    bad["success"] = success

    assert list(validator.iter_errors(bad))


def test_v05_round_trips_legacy_and_articulation_success_predicates() -> None:
    data = _scenario_mapping_v05()

    spec = ScenarioSpec.from_mapping(data)

    assert spec.schema_version == "scenario-spec/v0.5"
    assert [item.predicate_type for item in spec.success.predicates] == [
        "relative_pose_reached",
        "object_at_initial_pose",
        "articulation_joint_state_reached",
    ]
    assert spec.success.predicates[-1].parameters == {
        "object": "obj_graduated_cylinder_03",
        "joint": "lid",
        "state": "closed",
    }
    assert spec.success.predicates[0].parameters["axis_alignment"] == {
        "object_axis": "y",
        "target_axis": "y",
        "comparison": ">=",
        "threshold_deg": 40.0,
        "relative_to_part": "rotor",
    }
    assert spec.success.predicates[1].parameters["relative_axis_part"] == "rotor"
    assert spec.to_mapping() == data


@pytest.mark.parametrize(
    ("parameters", "message"),
    [
        ({"joint": "lid", "state": "closed"}, "object"),
        (
            {
                "object": "unknown_centrifuge",
                "joint": "lid",
                "state": "closed",
            },
            "unknown object",
        ),
        (
            {
                "object": "obj_graduated_cylinder_03",
                "joint": "",
                "state": "closed",
            },
            "joint",
        ),
        (
            {
                "object": "obj_graduated_cylinder_03",
                "joint": "lid",
                "state": "",
            },
            "state",
        ),
        (
            {
                "object": "obj_graduated_cylinder_03",
                "joint": "lid",
                "state": "closed",
                "runtime_dof_index": 2,
            },
            "unexpected",
        ),
    ],
)
def test_v05_rejects_invalid_articulation_semantic_references(
    parameters: dict[str, object],
    message: str,
) -> None:
    data = _scenario_mapping_v05()
    success = dict(data["success"])  # type: ignore[arg-type]
    predicates = [dict(item) for item in success["predicates"]]  # type: ignore[index]
    articulation = dict(predicates[-1])
    articulation["parameters"] = parameters
    predicates[-1] = articulation
    success["predicates"] = predicates
    data["success"] = success

    with pytest.raises(ValueError, match=message):
        ScenarioSpec.from_mapping(data)


def test_articulation_success_predicate_requires_v05() -> None:
    data = _scenario_mapping_v05()
    data["schema_version"] = "scenario-spec/v0.2"

    with pytest.raises(ValueError, match="scenario-spec/v0.5"):
        ScenarioSpec.from_mapping(data)


@pytest.mark.parametrize(
    ("predicate_index", "field_path", "value", "message"),
    [
        (0, ("axis_alignment", "relative_to_part"), "", "relative_to_part"),
        (1, ("relative_axis_part",), "", "relative_axis_part"),
    ],
)
def test_v05_rejects_empty_articulation_axis_part_references(
    predicate_index: int,
    field_path: tuple[str, ...],
    value: object,
    message: str,
) -> None:
    data = _scenario_mapping_v05()
    success = dict(data["success"])  # type: ignore[arg-type]
    predicates = [dict(item) for item in success["predicates"]]  # type: ignore[index]
    parameters = dict(predicates[predicate_index]["parameters"])  # type: ignore[arg-type]
    if len(field_path) == 2:
        nested = dict(parameters[field_path[0]])  # type: ignore[arg-type]
        nested[field_path[1]] = value
        parameters[field_path[0]] = nested
    else:
        parameters[field_path[0]] = value
    predicates[predicate_index]["parameters"] = parameters
    success["predicates"] = predicates
    data["success"] = success

    with pytest.raises(ValueError, match=message):
        ScenarioSpec.from_mapping(data)


def test_relative_axis_part_requires_relative_axis_object() -> None:
    data = _scenario_mapping_v05()
    success = dict(data["success"])  # type: ignore[arg-type]
    predicates = [dict(item) for item in success["predicates"]]  # type: ignore[index]
    parameters = dict(predicates[1]["parameters"])  # type: ignore[arg-type]
    parameters.pop("relative_axis_object")
    predicates[1]["parameters"] = parameters
    success["predicates"] = predicates
    data["success"] = success

    with pytest.raises(ValueError, match="relative_axis_object"):
        ScenarioSpec.from_mapping(data)


def test_v05_json_schema_accepts_only_supported_generic_predicates() -> None:
    schema = json.loads(
        (
            REPO_ROOT
            / "src/scenario_forge/schemas/jsonschema/scenario-spec-v0.5.schema.json"
        ).read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(schema)
    data = _scenario_mapping_v05()

    assert not list(validator.iter_errors(data))

    bad_parameters = json.loads(json.dumps(data))
    bad_parameters["success"]["predicates"][-1]["parameters"]["runtime_dof_index"] = 2
    assert list(validator.iter_errors(bad_parameters))

    unsupported = json.loads(json.dumps(data))
    unsupported["success"]["predicates"][-1]["type"] = "liquid_transfer_ratio"
    assert list(validator.iter_errors(unsupported))

    empty_part = json.loads(json.dumps(data))
    empty_part["success"]["predicates"][0]["parameters"]["axis_alignment"][
        "relative_to_part"
    ] = ""
    assert list(validator.iter_errors(empty_part))


def test_v06_combines_generic_success_and_weighted_progress_rubric() -> None:
    data = _scenario_mapping_v06()

    spec = ScenarioSpec.from_mapping(data)

    assert spec.schema_version == "scenario-spec/v0.6"
    assert spec.success.progress_rubric is not None
    assert spec.success.progress_rubric.items[-1].condition["type"] == (
        "motion_trajectory_completed"
    )
    assert spec.to_mapping() == data


def test_v06_json_schema_validates_generic_predicates_and_rubric() -> None:
    schema_path = (
        REPO_ROOT
        / "src/scenario_forge/schemas/jsonschema/scenario-spec-v0.6.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(_scenario_mapping_v06())

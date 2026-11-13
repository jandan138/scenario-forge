from __future__ import annotations

import pytest

from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.layout.relational_solver import (
    RELATIONAL_LAYOUT_SPEC_SCHEMA_VERSION,
    solve_relational_tabletop_layout,
)
from scenario_forge.generation.spec_composer import (
    OUT_OF_DOMAIN_TASK_DRAFT_SCHEMA_VERSION,
    SpecComposerError,
    compose_scenario_spec_from_solved_layout,
)


def _sample_layout_and_draft() -> tuple[dict[str, object], dict[str, object]]:
    layout_spec = {
        "schema_version": RELATIONAL_LAYOUT_SPEC_SCHEMA_VERSION,
        "seed": 11,
        "table": {
            "x_range_m": [-1.0, 1.0],
            "y_range_m": [-0.40, 0.40],
            "surface_z_m": 0.755,
            "min_edge_clearance_m": 0.10,
        },
        "robot_xy": [0.0, -1.02],
        "objects": [
            {
                "id": "espresso_machine",
                "role": "articulated_appliance",
                "footprint_xy_m": [0.245, 0.36],
                "region": "center",
                "facing": "robot",
                "robot_side_exception": "360mm body spans centerline for front spout clearance.",
                "kinematic_clearance_volumes": [
                    {
                        "id": "drip_tray_pullout",
                        "joint": "drip_tray",
                        "local_xy_bounds_m": {"x": [-0.09, 0.09], "y": [-0.23, -0.18]},
                    }
                ],
            },
            {
                "id": "espresso_cup",
                "role": "task_object",
                "footprint_xy_m": [0.068, 0.068],
                "region": "left",
                "facing": "robot",
            },
            {
                "id": "coffee_capsule",
                "role": "task_object",
                "footprint_xy_m": [0.038, 0.038],
                "region": "right",
                "facing": "robot",
            },
            {
                "id": "milk_jug_prop",
                "role": "context_prop",
                "footprint_xy_m": [0.09, 0.09],
                "region": "far_context",
                "facing": "robot",
            },
        ],
        "relations": [
            {"subject": "espresso_cup", "predicate": "left_of", "reference": "espresso_machine"},
            {"subject": "coffee_capsule", "predicate": "right_of", "reference": "espresso_machine"},
        ],
    }

    task_draft = {
        "schema_version": OUT_OF_DOMAIN_TASK_DRAFT_SCHEMA_VERSION,
        "scenario_id": "specialty_coffee_bar_creatista_capsule_brew",
        "domain": "specialty_coffee_bar",
        "task_family": "multi_dof_appliance_operation",
        "instruction": (
            "拉出咖啡机接水托杯架并将浓缩杯正立放到出水口下方；抬起顶部压杆打开胶囊舱，"
            "投入咖啡胶囊后压下压杆闭锁，最后旋转前面板选档旋钮至萃取档位。"
        ),
        "scene": {
            "asset_id": "car_room_kitchen_coffee_bar_v1",
            "root_prim_path": "/World",
            "pose": {
                "xyz": [0.0, -1.0, 0.0],
                "wxyz": [1.0, 0.0, 0.0, 0.0],
            },
        },
        "table": {
            "id": "table",
            "asset_id": "scientific_workbench_ebench_table_static_support",
            "source_prim_path": "/World/table",
            "pose": {
                "xyz": [0.0, 0.0, 0.0],
                "wxyz": [1.0, 0.0, 0.0, 0.0],
            },
        },
        "object_bindings": {
            "espresso_machine": {
                "asset_id": "ood_nespresso_creatista_plus_bne800",
                "source_prim_path": "/World/NespressoCreatistaPlus",
                "role": "articulated_appliance",
                "named_frames": {
                    "cup_spout_target": {
                        "xyz": [0.0, -0.155, 0.038],
                        "wxyz": [1.0, 0.0, 0.0, 0.0],
                    },
                    "capsule_chamber_target": {
                        "xyz": [0.0, -0.055, 0.255],
                        "wxyz": [1.0, 0.0, 0.0, 0.0],
                    },
                },
            },
            "espresso_cup": {
                "asset_id": "ood_espresso_cup_ceramic",
                "source_prim_path": "/World/EspressoCup",
                "role": "target_container",
            },
            "coffee_capsule": {
                "asset_id": "ood_coffee_capsule_aluminum",
                "source_prim_path": "/World/CoffeeCapsule",
                "role": "consumable_capsule",
            },
            "milk_jug_prop": {
                "asset_id": "ood_milk_pitcher_context",
                "source_prim_path": "/World/MilkPitcher",
                "role": "context_prop",
            },
        },
        "robot": {
            "profile_ref": "manip/lift2/R5a_isaac41_vr600_v1",
            "spawn": {
                "xyz": [0.0, -1.02, 0.31],
                "wxyz": [0.7071067812, 0.0, 0.0, 0.7071067812],
            },
            "actors": [
                {
                    "id": "operating_arm",
                    "end_effector": "left",
                    "capabilities": ["pull", "grasp", "lift", "place", "release"],
                },
                {
                    "id": "auxiliary_arm",
                    "end_effector": "right",
                    "capabilities": ["open", "grasp", "insert", "close", "rotate", "release"],
                },
            ],
        },
        "steps": [
            {
                "id": "extend_drip_tray",
                "skill": "open_articulated_part",
                "actors": ["operating_arm"],
                "parameters": {
                    "object": "espresso_machine",
                    "joint": "drip_tray",
                    "target_state": "extended",
                },
            },
            {
                "id": "place_cup_under_spout",
                "skill": "place",
                "actors": ["operating_arm"],
                "parameters": {
                    "object": "espresso_cup",
                    "target": "espresso_machine",
                    "target_frame": "espresso_machine.cup_spout_target",
                },
                "depends_on": ["extend_drip_tray"],
            },
            {
                "id": "open_brew_lever",
                "skill": "open_articulated_part",
                "actors": ["auxiliary_arm"],
                "parameters": {
                    "object": "espresso_machine",
                    "joint": "brew_lever",
                    "target_state": "open",
                },
                "depends_on": ["place_cup_under_spout"],
            },
            {
                "id": "insert_capsule",
                "skill": "insert",
                "actors": ["auxiliary_arm"],
                "parameters": {
                    "object": "coffee_capsule",
                    "target": "espresso_machine",
                    "target_frame": "espresso_machine.capsule_chamber_target",
                },
                "depends_on": ["open_brew_lever"],
            },
            {
                "id": "lock_brew_lever",
                "skill": "close_articulated_part",
                "actors": ["auxiliary_arm"],
                "parameters": {
                    "object": "espresso_machine",
                    "joint": "brew_lever",
                    "target_state": "locked",
                },
                "depends_on": ["insert_capsule"],
            },
            {
                "id": "turn_select_dial",
                "skill": "rotate",
                "actors": ["auxiliary_arm"],
                "parameters": {
                    "object": "espresso_machine",
                    "joint": "select_dial",
                    "target_state": "active",
                },
                "depends_on": ["lock_brew_lever"],
            },
        ],
        "success": {
            "operator": "all",
            "claim_scope": "state_proxy",
            "predicates": [
                {
                    "id": "drip_tray_extended",
                    "type": "articulation_joint_state_reached",
                    "sequence_index": 0,
                    "parameters": {
                        "object": "espresso_machine",
                        "joint": "drip_tray",
                        "state": "extended",
                    },
                },
                {
                    "id": "cup_placed_under_spout",
                    "type": "relative_pose_reached",
                    "sequence_index": 1,
                    "parameters": {
                        "object": "espresso_cup",
                        "relative_to": "espresso_machine",
                        "xyz_range": {
                            "x": [-0.03, 0.03],
                            "y": [-0.19, -0.12],
                            "z": [0.02, 0.07],
                        },
                        "axis_alignment": {
                            "object_axis": "z",
                            "target_axis": "z",
                            "comparison": "<=",
                            "threshold_deg": 12.0,
                        },
                    },
                },
                {
                    "id": "capsule_loaded_in_chamber",
                    "type": "relative_pose_reached",
                    "sequence_index": 2,
                    "parameters": {
                        "object": "coffee_capsule",
                        "relative_to": "espresso_machine",
                        "xyz_range": {
                            "x": [-0.025, 0.025],
                            "y": [-0.085, -0.025],
                            "z": [0.225, 0.285],
                        },
                    },
                },
                {
                    "id": "brew_lever_locked",
                    "type": "articulation_joint_state_reached",
                    "sequence_index": 3,
                    "parameters": {
                        "object": "espresso_machine",
                        "joint": "brew_lever",
                        "state": "locked",
                    },
                },
                {
                    "id": "select_dial_active",
                    "type": "articulation_joint_state_reached",
                    "sequence_index": 4,
                    "parameters": {
                        "object": "espresso_machine",
                        "joint": "select_dial",
                        "state": "active",
                    },
                },
            ],
            "progress_rubric": {
                "aggregation": {
                    "type": "weighted_progress_score",
                    "normalization": "declared_sum",
                    "inactive_treatment": "zero",
                    "primary_metric_id": "select_dial_active_stage",
                },
                "items": [
                    {
                        "id": "tray_extended_stage",
                        "weight": 0.15,
                        "temporal": {"kind": "terminal"},
                        "condition": {
                            "type": "articulation_joint_state_reached",
                            "parameters": {
                                "object": "espresso_machine",
                                "joint": "drip_tray",
                                "state": "extended",
                            },
                        },
                        "source_ref": {"stage": 1, "spec": "nespresso-creatista-plus-bne800"},
                    },
                    {
                        "id": "cup_placed_stage",
                        "weight": 0.25,
                        "temporal": {"kind": "terminal"},
                        "condition": {
                            "type": "relative_pose_reached",
                            "parameters": {
                                "object": "espresso_cup",
                                "relative_to": "espresso_machine",
                            },
                        },
                        "source_ref": {"stage": 2, "spec": "nespresso-creatista-plus-bne800"},
                    },
                    {
                        "id": "capsule_loaded_stage",
                        "weight": 0.25,
                        "temporal": {"kind": "terminal"},
                        "condition": {
                            "type": "relative_pose_reached",
                            "parameters": {
                                "object": "coffee_capsule",
                                "relative_to": "espresso_machine",
                            },
                        },
                        "source_ref": {"stage": 3, "spec": "nespresso-creatista-plus-bne800"},
                    },
                    {
                        "id": "lever_locked_stage",
                        "weight": 0.20,
                        "temporal": {"kind": "terminal"},
                        "condition": {
                            "type": "articulation_joint_state_reached",
                            "parameters": {
                                "object": "espresso_machine",
                                "joint": "brew_lever",
                                "state": "locked",
                            },
                        },
                        "source_ref": {"stage": 4, "spec": "nespresso-creatista-plus-bne800"},
                    },
                    {
                        "id": "select_dial_active_stage",
                        "weight": 0.15,
                        "temporal": {"kind": "terminal"},
                        "condition": {
                            "type": "articulation_joint_state_reached",
                            "parameters": {
                                "object": "espresso_machine",
                                "joint": "select_dial",
                                "state": "active",
                            },
                        },
                        "source_ref": {"stage": 5, "spec": "nespresso-creatista-plus-bne800"},
                    },
                ],
            },
        },
        "max_steps": 1800,
        "seed": "001",
    }
    return layout_spec, task_draft


def test_compose_scenario_spec_from_solved_layout_emits_valid_v06_spec() -> None:
    layout_spec, task_draft = _sample_layout_and_draft()
    solved = solve_relational_tabletop_layout(layout_spec)
    assert solved.status == "solved"

    spec = compose_scenario_spec_from_solved_layout(task_draft, solved)
    assert isinstance(spec, ScenarioSpec)
    assert spec.schema_version == "scenario-spec/v0.6"
    assert spec.domain == "specialty_coffee_bar"
    assert len(spec.objects) == 5  # table + 4 solved objects

    by_id = {obj.object_id: obj for obj in spec.objects}
    assert by_id["table"].role == "table"
    assert by_id["milk_jug_prop"].metadata is not None
    assert "tabletop_placement_exception" in by_id["milk_jug_prop"].metadata


def test_compose_rejects_unsolved_layout_or_missing_binding() -> None:
    layout_spec, task_draft = _sample_layout_and_draft()
    solved = solve_relational_tabletop_layout(layout_spec)
    bad_draft = dict(task_draft)
    bad_bindings = dict(task_draft["object_bindings"])  # type: ignore[arg-type]
    bad_bindings.pop("coffee_capsule")
    bad_draft["object_bindings"] = bad_bindings

    with pytest.raises(SpecComposerError, match="coffee_capsule"):
        compose_scenario_spec_from_solved_layout(bad_draft, solved)

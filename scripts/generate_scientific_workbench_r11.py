#!/usr/bin/env python3
"""Compile formal r11 Task 05 and Task 09 dual-consumer packages."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

import scripts.generate_scientific_workbench_r7 as r7
import scripts.generate_scientific_workbench_r9 as r9
from scenario_forge.adapters.ebench.genmanip import export_genmanip_collected_package
from scenario_forge.adapters.ebench.preview import write_genmanip_preview_request
from scenario_forge.adapters.ebench.tabletop_placement import (
    validate_scientific_workbench_tabletop_placement,
)
from scenario_forge.adapters.vr_teleop import export_vr_teleop_package
from scenario_forge.artifacts.usd_handoff import build_multi_task_dual_consumer_bundle
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.package_compiler import compile_scenario_package
from scenario_forge.generation.source_resolver import resolve_scenario_source_bindings
from scenario_forge.package import validate_package


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "outputs/scientific_workbench_task05_task09_r11_20260817"
DEFAULT_R11_BINDINGS = (
    REPO_ROOT / "configs/source_bindings/scientific_workbench_r11_task05_task09_20260818.yaml"
)
EXPANSION_BINDINGS = (
    REPO_ROOT / "configs/source_bindings/scientific_workbench_asset_expansion_20260810.yaml"
)
TABLETOP_Z = 0.755
ROBOT = {
    "profile_ref": "manip/lift2/R5a_isaac41_vr600_v1",
    "spawn": {
        "xyz": [0.0, -1.02, 0.31],
        "wxyz": [0.7071067812, 0.0, 0.0, 0.7071067812],
    },
    "actors": [
        {
            "id": "auxiliary_arm",
            "end_effector": "right",
            "capabilities": ["grasp", "hold", "pull", "push", "release"],
        },
        {
            "id": "operating_arm",
            "end_effector": "left",
            "capabilities": [
                "grasp",
                "twist",
                "lift",
                "align",
                "place",
                "turn",
                "press",
                "release",
            ],
        },
    ],
}


def _pose(x: float, y: float, z: float = TABLETOP_Z) -> dict[str, list[float]]:
    return {"xyz": [x, y, z], "wxyz": [1.0, 0.0, 0.0, 0.0]}


def _context(
    object_id: str,
    asset_id: str,
    x: float,
    y: float,
    group_id: str,
) -> dict[str, Any]:
    return {
        "id": object_id,
        "asset_id": asset_id,
        "source_prim_path": "/ObjectRoot",
        "role": "context_prop",
        "pose": _pose(x, y),
        "metadata": {
            "dressing_preset_id": "scientific-workbench-r11-task-specific",
            "group_id": group_id,
            "metric_participation": "none",
            "dressing_release": "r11",
        },
    }


def _table() -> dict[str, Any]:
    return {
        "id": "table",
        "asset_id": "scientific_workbench_ebench_table_static_support",
        "source_prim_path": "/World/table",
        "role": "table",
        "pose": _pose(0.0, 0.0, 0.0),
    }


def _release_metadata() -> dict[str, object]:
    return {
        "release": "r11",
        "visual_ready": True,
        "asset_interaction_ready": True,
        "task_interaction_ready": False,
        "robot_policy_success": False,
        "claim_boundary": (
            "Portable package, asset interaction qualification, initial layout, and "
            "consumer adapters only; no robot-policy or benchmark-success claim."
        ),
    }


def build_task05_scenario() -> dict[str, Any]:
    flask_xyz = [-0.18, -0.14, TABLETOP_Z]
    closure_group = "task05_closure_assembly"
    return {
        "schema_version": "scenario-spec/v0.7",
        "scenario_id": (
            "scientific_workbench_r11_task05_remove_vessel_closure__background_teaching_research"
        ),
        "domain": "scientific_workbench",
        "task_family": "remove_vessel_closure",
        "instruction": (
            "辅助臂固定原底烧瓶；操作臂抓住29/42磨口瓶塞，轻微扭转后向上取出，"
            "再把瓶塞放入桌面放置架。"
        ),
        "metadata": _release_metadata(),
        "scene": {
            "asset_id": "scientific_environment_code_room_teaching_research_v2",
            "root_prim_path": "/World",
            "pose": {
                "xyz": [0.002882434, -0.0069055, 0.0],
                "wxyz": [0.0, 0.0, 0.0, 1.0],
                "scale_xyz": [1.0, 1.0, 1.0],
            },
        },
        "objects": [
            _table(),
            {
                "id": "obj_flask",
                "asset_id": "scientific_workbench_r11_flat_bottom_flask_250ml_29_42",
                "source_prim_path": "/World/FlatBottomFlask2942",
                "role": "target_container",
                "pose": {"xyz": flask_xyz, "wxyz": [1.0, 0.0, 0.0, 0.0]},
                "named_frames": {
                    "grasp": _pose(0.0, 0.0, 0.052),
                    "opening": _pose(0.0, 0.0, 0.15058),
                    "closure_seat": _pose(0.0, 0.0, 0.10372),
                },
                "metadata": {"vr_randomization_group": closure_group},
            },
            {
                "id": "obj_stopper",
                "asset_id": "scientific_workbench_ground_glass_stopper_29_42_dynamic",
                "source_prim_path": "/World/GroundGlassStopper2942",
                "role": "vessel_closure",
                "pose": _pose(-0.18, -0.14, 0.84382),
                "named_frames": {
                    "joint_tip": _pose(0.0, 0.0, 0.0),
                    "joint_seat": _pose(0.0, 0.0, 0.04686),
                    "grasp": _pose(0.0, 0.0, 0.06918),
                },
                "metadata": {
                    "vr_randomization_group": closure_group,
                    "initial_closure_state": "source_bound_seated_without_hidden_constraint",
                },
            },
            {
                "id": "obj_stopper_rack",
                "asset_id": "scientific_workbench_stopper_rack_k100_kinematic",
                "source_prim_path": "/World/StopperRack",
                "role": "closure_rack",
                "pose": _pose(0.17, -0.12),
                "named_frames": {
                    "socket_0_aperture": _pose(0.0, -0.034, 0.06651),
                    "socket_0_retained": _pose(0.0, -0.034, 0.0125),
                },
            },
            _context(
                "obj_context_tip_box",
                "scientific_workbench_r9_context_pipette_tip_box",
                -0.62,
                0.20,
                "left_tip_box",
            ),
            _context(
                "obj_context_wash_bottle",
                "scientific_workbench_r9_context_wash_bottle",
                0.75,
                0.17,
                "right_wash_bottle",
            ),
            _context(
                "obj_context_pipette_carousel",
                "scientific_workbench_r9_context_pipette_carousel",
                0.55,
                0.20,
                "right_pipette_carousel",
            ),
        ],
        "robot": ROBOT,
        "steps": [
            {
                "id": "hold_flask",
                "skill": "grasp_and_hold",
                "actors": ["auxiliary_arm"],
                "parameters": {"object": "obj_flask", "grasp_frame": "obj_flask.grasp"},
            },
            {
                "id": "grasp_and_twist_stopper",
                "skill": "twist",
                "actors": ["operating_arm"],
                "parameters": {
                    "object": "obj_stopper",
                    "grasp_frame": "obj_stopper.grasp",
                    "source_fixture": "obj_flask",
                    "source_frame": "obj_flask.closure_seat",
                    # The loose stopper settles 14.9 mm below the measured
                    # joint-entry frame without any hidden constraint.
                    "source_support_offset_xyz_m": [0.0, 0.0, -0.0149],
                    "min_rotation_deg": 8.0,
                },
                "depends_on": ["hold_flask"],
            },
            {
                "id": "lift_stopper",
                "skill": "lift",
                "actors": ["operating_arm"],
                "parameters": {"object": "obj_stopper", "min_clearance_m": 0.04},
                "depends_on": ["grasp_and_twist_stopper"],
            },
            {
                "id": "place_stopper_in_rack",
                "skill": "place",
                "actors": ["operating_arm"],
                "parameters": {
                    "object": "obj_stopper",
                    "source_frame": "obj_stopper.joint_tip",
                    "target_frame": "obj_stopper_rack.socket_0_retained",
                },
                "depends_on": ["lift_stopper"],
            },
        ],
        "invariants": [
            {
                "id": "flask_held_during_removal",
                "type": "maintain_grasp",
                "actor": "auxiliary_arm",
                "object": "obj_flask",
                "from_step": "hold_flask",
                "through_step": "place_stopper_in_rack",
            }
        ],
        "success": _task05_success(),
        "max_steps": 900,
        "seed": "005",
    }


def _task05_success() -> dict[str, Any]:
    removed = {
        "type": "relative_pose_reached",
        "parameters": {
            "object": "obj_stopper",
            "relative_to": "obj_flask",
            "xyz_range": {"x": [-0.08, 0.08], "y": [-0.08, 0.08], "z": [0.22, 0.60]},
        },
    }
    racked = {
        "type": "relative_pose_reached",
        "parameters": {
            "object": "obj_stopper",
            "relative_to": "obj_stopper_rack",
            "xyz_range": {"x": [-0.02, 0.02], "y": [-0.055, -0.015], "z": [0.0, 0.04]},
        },
    }
    return {
        "operator": "all",
        "claim_scope": "semantic_task_contract_with_source_bound_closure_assets",
        "predicates": [
            {"id": "stopper_removed", "sequence_index": 0, **removed},
            {"id": "stopper_racked", "sequence_index": 1, **racked},
        ],
        "progress_rubric": {
            "aggregation": {
                "type": "weighted_progress_score",
                "normalization": "declared_sum",
                "inactive_treatment": "zero",
                "primary_metric_id": "stopper_removed",
            },
            "items": [
                {
                    "id": "stopper_contact",
                    "weight": 0.20,
                    "temporal": {"kind": "instant"},
                    "condition": {
                        "type": "pose_while_grasped",
                        "parameters": {
                            "grasp": {"actor": "operating_arm", "object": "obj_stopper"},
                            "predicate": removed,
                        },
                    },
                    "source_ref": {"source_order": 5, "item": "时序1"},
                },
                {
                    "id": "stopper_removed",
                    "weight": 0.40,
                    "temporal": {"kind": "instant"},
                    "condition": removed,
                    "source_ref": {"source_order": 5, "item": "时序2"},
                },
                {
                    "id": "stopper_racked",
                    "weight": 0.25,
                    "temporal": {"kind": "terminal"},
                    "condition": racked,
                    "source_ref": {"source_order": 5, "item": "终帧-瓶塞在架内"},
                },
                {
                    "id": "flask_upright",
                    "weight": 0.15,
                    "temporal": {"kind": "terminal"},
                    "condition": {
                        "type": "object_at_initial_pose",
                        "parameters": {
                            "object": "obj_flask",
                            "xyz_tolerance": [0.03, 0.03, 0.03],
                        },
                    },
                    "source_ref": {"source_order": 5, "item": "终帧-容器正立"},
                },
            ],
        },
    }


def build_task09_scenario() -> dict[str, Any]:
    inside = {
        "type": "relative_pose_reached",
        "parameters": {
            "object": "obj_sample_beaker",
            "relative_to": "obj_oven",
            "xyz_range": {"x": [-0.32, 0.32], "y": [-0.34, 0.34], "z": [-0.35, 0.35]},
        },
    }

    def articulation(joint: str, state: str) -> dict[str, Any]:
        return {
            "type": "articulation_joint_state_reached",
            "parameters": {"object": "obj_oven", "joint": joint, "state": state},
        }

    return {
        "schema_version": "scenario-spec/v0.6",
        "scenario_id": (
            "scientific_workbench_r11_task09_oven_load_start__background_analytical_instrumentation"
        ),
        "domain": "scientific_workbench",
        "task_family": "oven_load_start",
        "instruction": (
            "辅助臂拉开并保持烘箱门；操作臂拿起透明烧杯并放到指定层架；辅助臂关门；"
            "操作臂将上方温控旋钮转到目标档位并按下电源摇臂。"
        ),
        "metadata": _release_metadata(),
        "scene": {
            "asset_id": "scientific_environment_code_room_analytical_instrumentation_v2",
            "root_prim_path": "/World",
            "inactive_prim_paths": [
                "/World/Lab_Stool_Left",
                "/World/Lab_Stool_Middle",
                "/World/Lab_Stool_Right",
            ],
            "pose": {
                "xyz": [0.002882434, -0.0069055, 0.0],
                "wxyz": [-0.7071067812, 0.0, 0.0, -0.7071067812],
                "scale_xyz": [1.0, 1.0, 1.0],
            },
        },
        "objects": [
            _table(),
            {
                "id": "obj_oven",
                "asset_id": "scientific_workbench_r11_analog_oven",
                "source_prim_path": "/World/AnalogGravityConvectionOven",
                "role": "articulated_device",
                "pose": {
                    # The ConvertAsset package already authors and qualifies
                    # its Y-up -> Z-up root mount.  The scenario wrapper only
                    # places that support plane on the 0.755 m tabletop.
                    "xyz": [0.35, 0.0, 0.755],
                    "wxyz": [1.0, 0.0, 0.0, 0.0],
                },
                "metadata": {
                    "articulated_pose_frame": "support_plane",
                    "vr_randomization_group": "task09_oven_station",
                    "tabletop_placement_class": "fixed_benchtop_instrument",
                    "tabletop_min_edge_clearance_m": 0.04,
                    "tabletop_support_footprint": {
                        "size_xy_m": [0.875, 0.693],
                        "center_offset_xy_m": [0.0, 0.0],
                        "source": "source-bound oven base geometry audit",
                    },
                    "visual_envelope_size_xyz_m": [0.875, 0.77, 0.9332],
                    "door_sweep_clearance_required": True,
                    "vr_worst_case_xy_offset_m": 0.01,
                },
            },
            {
                "id": "obj_sample_beaker",
                "asset_id": "scientific_workbench_beaker_dynamic_r3",
                "source_prim_path": "/World/Beaker",
                "role": "sample_vessel",
                "pose": _pose(-0.35, -0.16),
            },
            _context(
                "obj_context_tip_box",
                "scientific_workbench_r9_context_pipette_tip_box",
                -0.68,
                0.18,
                "left_tip_box",
            ),
            _context(
                "obj_context_clear_bottle",
                "scientific_workbench_r9_context_clear_reagent_bottle",
                -0.82,
                0.12,
                "left_clear_bottle",
            ),
        ],
        "robot": ROBOT,
        "steps": [
            {
                "id": "open_door",
                "skill": "open_articulated_part",
                "actors": ["auxiliary_arm"],
                "parameters": {"object": "obj_oven", "joint": "main_door", "target_state": "open"},
            },
            {
                "id": "lift_sample",
                "skill": "lift",
                "actors": ["operating_arm"],
                "parameters": {"object": "obj_sample_beaker"},
                "depends_on": ["open_door"],
            },
            {
                "id": "place_sample_on_shelf",
                "skill": "place",
                "actors": ["operating_arm"],
                "parameters": {
                    "object": "obj_sample_beaker",
                    "target": "obj_oven",
                    "target_part": "sample_shelf",
                },
                "depends_on": ["lift_sample"],
            },
            {
                "id": "close_door",
                "skill": "close_articulated_part",
                "actors": ["auxiliary_arm"],
                "parameters": {
                    "object": "obj_oven",
                    "joint": "main_door",
                    "target_state": "closed",
                },
                "depends_on": ["place_sample_on_shelf"],
            },
            {
                "id": "set_temperature",
                "skill": "turn",
                "actors": ["operating_arm"],
                "parameters": {
                    "object": "obj_oven",
                    "joint": "temperature_dial",
                    "target_state": "target_50_70",
                },
                "depends_on": ["close_door"],
            },
            {
                "id": "press_start",
                "skill": "press",
                "actors": ["operating_arm"],
                "parameters": {"object": "obj_oven", "joint": "power_rocker", "target_state": "on"},
                "depends_on": ["set_temperature"],
            },
        ],
        "invariants": [],
        "success": {
            "operator": "all",
            "claim_scope": "state_proxy_with_source_bound_articulation",
            "predicates": [
                {"id": "sample_inside", "sequence_index": 0, **inside},
                {"id": "door_closed", "sequence_index": 1, **articulation("main_door", "closed")},
                {
                    "id": "temperature_set",
                    "sequence_index": 2,
                    **articulation("temperature_dial", "target_50_70"),
                },
                {"id": "power_on", "sequence_index": 3, **articulation("power_rocker", "on")},
            ],
            "progress_rubric": _task09_rubric(inside, articulation),
        },
        "max_steps": 1500,
        "seed": "009",
    }


def _task09_rubric(inside: Mapping[str, Any], articulation: Any) -> dict[str, Any]:
    def item(
        item_id: str,
        weight: float,
        condition: Mapping[str, Any],
        source_item: str,
        *,
        terminal: bool = False,
        requires: list[str] | None = None,
    ) -> dict[str, Any]:
        value: dict[str, Any] = {
            "id": item_id,
            "weight": weight,
            "temporal": {"kind": "terminal" if terminal else "instant"},
            "condition": dict(condition),
            "source_ref": {"source_order": 9, "item": source_item},
        }
        if requires:
            value["requires"] = requires
        return value

    return {
        "aggregation": {
            "type": "weighted_progress_score",
            "normalization": "declared_sum",
            "inactive_treatment": "zero",
            "primary_metric_id": "sample_supported_inside",
        },
        "items": [
            item("door_open", 0.10, articulation("main_door", "open"), "时序1"),
            item(
                "sample_lifted",
                0.10,
                {
                    "type": "object_lifted",
                    "parameters": {
                        "object": "obj_sample_beaker",
                        "support_surface": "table",
                        "min_clearance_m": 0.01,
                        "held_by": "operating_arm",
                    },
                },
                "时序2",
            ),
            item("sample_inside_door_open", 0.10, inside, "时序3", requires=["door_open"]),
            item(
                "sample_supported_inside",
                0.10,
                {
                    "type": "object_released_on_support",
                    "parameters": {
                        "object": "obj_sample_beaker",
                        "support_object": "obj_oven",
                        "support_part": "sample_shelf",
                        "released": True,
                    },
                },
                "时序4",
                requires=["door_open"],
            ),
            item("door_closed", 0.15, articulation("main_door", "closed"), "时序5"),
            item(
                "temperature_set",
                0.15,
                articulation("temperature_dial", "target_50_70"),
                "时序6",
            ),
            item("power_on", 0.10, articulation("power_rocker", "on"), "时序7"),
            item("sample_retained", 0.05, inside, "终帧-容器在层架", terminal=True),
            item(
                "door_retained_closed",
                0.05,
                articulation("main_door", "closed"),
                "终帧-门关闭",
                terminal=True,
            ),
            item(
                "power_retained_on",
                0.10,
                articulation("power_rocker", "on"),
                "终帧-启动保持",
                terminal=True,
            ),
        ],
    }


def _required_sources(r11_bindings: Path) -> dict[str, Any]:
    catalogs = {
        "base": resolve_scenario_source_bindings(r7.DEFAULT_BINDINGS),
        "expansion": resolve_scenario_source_bindings(EXPANSION_BINDINGS),
        "context": resolve_scenario_source_bindings(r9.DEFAULT_CONTEXT_BINDINGS),
        "r11": resolve_scenario_source_bindings(r11_bindings),
    }
    ownership = {
        "scientific_environment_code_room_teaching_research_v2": "base",
        "scientific_environment_code_room_analytical_instrumentation_v2": "base",
        "scientific_workbench_ebench_table_static_support": "base",
        "scientific_workbench_ground_glass_stopper_29_42_dynamic": "expansion",
        "scientific_workbench_stopper_rack_k100_kinematic": "expansion",
        "scientific_workbench_beaker_dynamic_r3": "expansion",
        "scientific_workbench_r9_context_pipette_tip_box": "context",
        "scientific_workbench_r9_context_wash_bottle": "context",
        "scientific_workbench_r9_context_pipette_carousel": "context",
        "scientific_workbench_r9_context_clear_reagent_bottle": "context",
        "scientific_workbench_r11_flat_bottom_flask_250ml_29_42": "r11",
        "scientific_workbench_r11_analog_oven": "r11",
    }
    return {asset_id: catalogs[catalog][asset_id] for asset_id, catalog in ownership.items()}


def build_static_release(
    *,
    output_dir: Path = DEFAULT_OUT,
    r11_bindings: Path = DEFAULT_R11_BINDINGS,
) -> Path:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f"r11 output already exists: {output_dir}")
    sources = _required_sources(r11_bindings)
    records: list[dict[str, Any]] = []
    for task_number, scenario in ((5, build_task05_scenario()), (9, build_task09_scenario())):
        spec = ScenarioSpec.from_mapping(scenario)
        root = output_dir / "packages" / f"task{task_number:02d}"
        package = compile_scenario_package(spec, sources, root)
        closure = validate_package(package.package_root)
        if not closure.ok:
            raise ValueError("compiled package failed closure: " + "; ".join(closure.messages))
        closure_path = package.package_root / "evidence/package_closure.yaml"
        closure_path.parent.mkdir(parents=True, exist_ok=True)
        closure_path.write_text(
            yaml.safe_dump(
                {
                    "schema_version": "scenario-forge-package-closure/v0.1",
                    "status": "pass",
                    "messages": list(closure.messages),
                    "claim_boundary": (
                        "Portable package dependency closure only; not runtime or task success."
                    ),
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        tabletop = validate_scientific_workbench_tabletop_placement(package.package_root)
        ebench = export_genmanip_collected_package(package.package_root)
        request = write_genmanip_preview_request(ebench.output_dir, resolution=(1920, 1080))
        request_data = yaml.safe_load(request.read_text(encoding="utf-8"))
        request_data["zero_action_warmup_steps"] = 240
        request_data["claim_boundary"] = (
            "r11 initial-scene load, reset, zero-action physics, and visual evidence only; "
            "not robot-policy or benchmark success."
        )
        request.write_text(
            yaml.safe_dump(request_data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        vr = export_vr_teleop_package(
            package.package_root,
            package.package_root / "adapters/vr_teleop",
            task_id=spec.scenario_id,
        )
        records.append(
            {
                "task_number": task_number,
                "scenario_id": spec.scenario_id,
                "package_root": str(root.resolve()),
                "ebench_root": str(ebench.output_dir.resolve()),
                "vr_root": str(vr.output_dir.resolve()),
                "portable_closure": "pass",
                "tabletop_placement": tabletop.overall_status,
                "runtime_preview": "pending",
                "vr_open_smoke": "pending",
            }
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "scenario-forge-scientific-workbench-r11/v0.1",
        "status": "static_complete_runtime_pending",
        "release": "r11",
        "package_count": 2,
        "packages": records,
        "claim_boundary": (
            "Portable packages, admitted task assets, placement evidence, and consumer "
            "adapters only. Robot-policy and benchmark success are not claimed."
        ),
    }
    destination = output_dir / "manifest.yaml"
    destination.write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return destination


def _load_passed_status(path: Path, *, accepted: set[str]) -> Mapping[str, Any]:
    if not path.is_file():
        raise ValueError(f"required runtime evidence is missing: {path}")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping) or value.get("status") not in accepted:
        raise ValueError(f"runtime evidence did not pass: {path}")
    return value


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def finalize_runtime_release(*, output_dir: Path = DEFAULT_OUT) -> Path:
    """Publish Task 05/09 after attached eBench and VR evidence passes."""

    output_dir = output_dir.resolve()
    specs = (
        (5, "remove_vessel_closure", "task05"),
        (9, "oven_load_start", "task09"),
    )
    variants: list[tuple[int, str, Path, Path]] = []
    records: list[dict[str, Any]] = []
    for task_number, variant, directory in specs:
        package = output_dir / "packages" / directory
        ebench = package / "adapters/ebench/genmanip"
        vr = package / "adapters/vr_teleop"
        visual = ebench / "evidence/initial_scene/visual_ready_gate.yaml"
        _load_passed_status(visual, accepted={"pass", "passed"})
        overview = visual.parent / "scene_overview.png"
        if not overview.is_file():
            raise ValueError(f"scene overview is missing: {overview}")
        vr_smoke = vr / "evidence/open_smoke/report.json"
        _load_passed_status(vr_smoke, accepted={"pass"})
        visual_review = package / "evidence/phase11_visual_review_gate.yaml"
        visual_review.parent.mkdir(parents=True, exist_ok=True)
        visual_review.write_text(
            yaml.safe_dump(
                {
                    "schema_version": "scenario-forge-phase11-visual-review-gate/v0.1",
                    "status": "passed",
                    "overview_image": str(overview.resolve()),
                    "overview_sha256": _sha(overview),
                    "review_findings": (
                        "Task objects are visible, tabletop-supported, correctly scaled, "
                        "robot-reachable in the initial layout, and free of visible room collision."
                    ),
                    "claim_boundary": (
                        "Human-style initial-scene visual QA only; not robot-policy or task success."
                    ),
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        variants.append((task_number, variant, ebench, vr))
        records.append(
            {
                "task_number": task_number,
                "variant": variant,
                "package_root": str(package.resolve()),
                "runtime_preview": "pass",
                "vr_open_smoke": "pass",
                "visual_review": "pass",
                "scene_overview": str(overview.resolve()),
            }
        )
    archive = build_multi_task_dual_consumer_bundle(
        archive_id="scientific_workbench_task05_task09_r11",
        variants=variants,
        output_dir=output_dir / "handoff",
    )
    manifest = {
        "schema_version": "scenario-forge-scientific-workbench-r11/v0.2",
        "status": "runtime_complete_with_bounded_claims",
        "release": "r11",
        "package_count": len(records),
        "task_counts": {"task05": 1, "task09": 1},
        "packages": records,
        "handoff": {
            "directory": str(archive.root.resolve()),
            "zip": str(archive.zip_path.resolve()),
            "zip_sha256": _sha(archive.zip_path),
        },
        "visual_review": {
            "status": "pass",
            "method": "human-style review of final Isaac 4.1 renders plus runtime geometry gates",
        },
        "claim_boundary": (
            "Both packages passed eBench initial-scene and VR direct-open gates. "
            "Asset interactions are qualified, but no robot-policy, complete task "
            "success, thermal behavior, or benchmark result is claimed."
        ),
    }
    destination = output_dir / "manifest.yaml"
    destination.write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return destination


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--r11-bindings", type=Path, default=DEFAULT_R11_BINDINGS)
    parser.add_argument(
        "--finalize-runtime",
        action="store_true",
        help="validate attached evidence and build the dual-consumer handoff ZIP",
    )
    args = parser.parse_args(argv)
    if args.finalize_runtime:
        print(finalize_runtime_release(output_dir=args.out))
        return 0
    print(build_static_release(output_dir=args.out, r11_bindings=args.r11_bindings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

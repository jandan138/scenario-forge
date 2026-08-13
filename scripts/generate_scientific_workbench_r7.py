#!/usr/bin/env python3
"""Compile the seven immutable r7 packages for scientific tasks 2, 7, and 8."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from scenario_forge.adapters.ebench.genmanip import export_genmanip_collected_package
from scenario_forge.adapters.ebench.preview import run_genmanip_initial_preview, write_genmanip_preview_request
from scenario_forge.adapters.ebench.tabletop_placement import validate_scientific_workbench_tabletop_placement
from scenario_forge.adapters.vr_teleop import export_vr_teleop_package
from scenario_forge.assets.source import LocalUSDAssetSource
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.package_compiler import compile_scenario_package
from scenario_forge.generation.source_resolver import resolve_scenario_source_bindings
from scenario_forge.package import validate_package


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BINDINGS = REPO_ROOT / "configs/source_bindings/scientific_workbench_r7_20260813.yaml"
DEFAULT_OUT = REPO_ROOT / "outputs/scientific_workbench_asset_expansion_20260813_r7_full"
DEFAULT_RENDERER = REPO_ROOT / "scripts/ebench/render_genmanip_initial_preview.py"
DEFAULT_ISAAC_PYTHON = Path("/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-isaacsim41-genmanip-py310/bin/python")
DEFAULT_GENMANIP_ROOT = Path("/cpfs/shared/simulation/zhuzihou/dev/GenManip")
DEFAULT_CUROBO_SRC = Path("/cpfs/shared/simulation/mamengchen/curobo-wbc-backup/src")
DEFAULT_FIT_REPORT = Path("/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/scientific_workbench_r7_task_assets_20260813/packages/test_tube_rack_aluminum/evidence/medium_socket_03_insertion/report.json")

BACKGROUNDS = {
    "example4": ("scientific_environment_code_room_example4_v2", [0.0, 0.0, 0.0, 1.0], []),
    "teaching_research": ("scientific_environment_code_room_teaching_research_v2", [0.0, 0.0, 0.0, 1.0], []),
    "modern_wet_chemistry": ("scientific_environment_code_room_wet_chemistry_v2", [0.0, 0.0, 0.0, 1.0], []),
    "bioclean": ("scientific_environment_code_room_bioclean_v2", [-0.7071067812, 0.0, 0.0, 0.7071067812], []),
    "analytical_instrumentation": ("scientific_environment_code_room_analytical_instrumentation_v2", [-0.7071067812, 0.0, 0.0, 0.7071067812], ["/World/Lab_Stool_Left", "/World/Lab_Stool_Middle", "/World/Lab_Stool_Right"]),
}
TASK7_BACKGROUNDS = ("example4", "teaching_research", "modern_wet_chemistry", "bioclean", "analytical_instrumentation")
RACKED_TASK7_BACKGROUNDS = frozenset({"example4", "teaching_research", "bioclean"})


@dataclass(frozen=True)
class R7Plan:
    task_number: int
    background_id: str
    release_status: str
    score_ceiling: float
    missing_capabilities: tuple[str, ...]
    scenario: dict[str, Any]


def _frame_request(*names: str) -> dict[str, Any]:
    return {name: {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]} for name in names}


def _base(scenario_id: str, instruction: str, background_id: str) -> dict[str, Any]:
    asset_id, wxyz, inactive = BACKGROUNDS[background_id]
    scene: dict[str, Any] = {
        "asset_id": asset_id,
        "root_prim_path": "/World",
        "pose": {"xyz": [0.002882434, -0.0069055, 0.0], "wxyz": wxyz, "scale_xyz": [1.0, 1.0, 1.0]},
    }
    if inactive:
        scene["inactive_prim_paths"] = inactive
    return {
        "schema_version": "scenario-spec/v0.7",
        "scenario_id": scenario_id,
        "domain": "scientific_workbench",
        "instruction": instruction,
        "scene": scene,
        "objects": [{
            "id": "table", "asset_id": "scientific_workbench_ebench_table_static_support",
            "source_prim_path": "/World/table", "role": "table",
            "pose": {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        }],
        "robot": {
            "profile_ref": "manip/lift2/R5a_isaac41_vr600_v1",
            "spawn": {"xyz": [0.0, -1.02, 0.31], "wxyz": [0.7071067812, 0.0, 0.0, 0.7071067812]},
            "actors": [
                {"id": "auxiliary_arm", "end_effector": "right", "capabilities": ["grasp", "hold", "lift", "place", "release"]},
                {"id": "operating_arm", "end_effector": "left", "capabilities": ["grasp", "lift", "align", "tilt", "insert", "stir", "twist", "place", "release"]},
            ],
        },
        "metadata": {
            "release": "r7",
            "ik_preflight": "not_run",
            "ik_claim": "No EOS/GenManip IK or reachability claim is made in r7.",
            "main_asset_policy": "task and metric assets only from 实验室资产库.zip",
            "tabletop_policy": "robot-facing safe side; >=0.10 m edge clearance; no initial overlap",
        },
        "max_steps": 1800,
        "seed": "007",
    }


def _context(asset_id: str, source_prim: str, object_id: str, xyz: list[float], *, socket: int | None = None) -> dict[str, Any]:
    group_id = object_id.rsplit("_s", 1)[0]
    metadata: dict[str, Any] = {
        "metric_participation": "none",
        "vr_participation": "none",
        "dressing_policy": "fixed_background_context",
        "dressing_preset_id": "scientific-workbench-r7-rack-population-v1",
        "group_id": group_id,
    }
    if socket is not None:
        metadata["rack_socket_index"] = socket
    return {
        "id": object_id, "asset_id": asset_id, "source_prim_path": source_prim,
        "role": "context_prop", "pose": {"xyz": xyz, "wxyz": [1.0, 0.0, 0.0, 0.0]},
        "metadata": metadata,
    }


def _rubric(items: list[dict[str, Any]], primary: str) -> dict[str, Any]:
    predicates = []
    for item in items:
        if "returned" not in item["id"] or item.get("active", True) is False:
            continue
        parameters = item["condition"].get("parameters", {})
        object_id = parameters.get("object")
        if isinstance(object_id, str):
            predicates.append({
                "id": item["id"],
                "type": "object_at_initial_pose",
                "sequence_index": len(predicates),
                "parameters": {
                    "object": object_id,
                    "xyz_tolerance": [0.04, 0.04, 0.03],
                },
            })
    for item in items:
        if predicates:
            break
        if item.get("active", True) is False:
            continue
        condition = item["condition"]
        if condition["type"] == "pose_while_grasped":
            condition = condition.get("parameters", {}).get("predicate", condition)
        if condition["type"] not in {
            "articulation_joint_state_reached",
            "object_at_initial_pose",
            "relative_pose_reached",
        }:
            continue
        predicates.append({
            "id": item["id"],
            "type": condition["type"],
            "sequence_index": len(predicates),
            "parameters": condition.get("parameters", {}),
        })
    if not predicates:
        raise ValueError("r7 rubric must contain at least one portable terminal predicate")
    return {"operator": "all", "claim_scope": "r7_semantic_package", "predicates": predicates, "progress_rubric": {"aggregation": {"type": "weighted_progress_score", "normalization": "declared_sum", "inactive_treatment": "zero", "primary_metric_id": primary}, "items": items}}


def _task2() -> dict[str, Any]:
    s = _base("scientific_workbench_r7_task02_pour_cylinder_to_beaker__background_modern_wet_chemistry", "辅助臂固定 325 mL 烧杯；操作臂拿起 250 mL 量筒，对准后倾倒，再将量筒正立放回。", "modern_wet_chemistry")
    s["task_family"] = "bimanual_pour"
    s["seed"] = "002"
    s["objects"] += [
        {"id": "obj_graduated_cylinder", "asset_id": "scientific_workbench_r7_graduated_cylinder_250ml", "source_prim_path": "/World/GraduatedCylinder250ml", "role": "source_container", "pose": {"xyz": [0.16, -0.15, 0.755], "wxyz": [1, 0, 0, 0]}, "named_frames": _frame_request("support", "grasp", "opening", "interior_center")},
        {"id": "obj_beaker", "asset_id": "scientific_workbench_r7_beaker_325ml", "source_prim_path": "/World/Beaker325ml", "role": "target_container", "pose": {"xyz": [-0.16, -0.17, 0.755], "wxyz": [1, 0, 0, 0]}, "named_frames": _frame_request("support", "grasp", "opening", "interior_center")},
    ]
    s["steps"] = [
        {"id": "hold_beaker", "skill": "grasp_and_hold", "actors": ["auxiliary_arm"], "parameters": {"object": "obj_beaker"}},
        {"id": "lift_cylinder", "skill": "lift", "actors": ["operating_arm"], "parameters": {"object": "obj_graduated_cylinder"}, "depends_on": ["hold_beaker"]},
        {"id": "align_openings", "skill": "align_openings", "actors": ["auxiliary_arm", "operating_arm"], "parameters": {"source_frame": "obj_graduated_cylinder.opening", "target_frame": "obj_beaker.opening"}, "depends_on": ["lift_cylinder"]},
        {"id": "tilt_pour", "skill": "tilt_pour", "actors": ["operating_arm"], "parameters": {"object": "obj_graduated_cylinder", "min_tilt_deg": 65.0}, "depends_on": ["align_openings"]},
        {"id": "return_cylinder", "skill": "place_on_surface", "actors": ["operating_arm"], "parameters": {"object": "obj_graduated_cylinder", "support_surface": "table"}, "depends_on": ["tilt_pour"]},
    ]
    s["invariants"] = [{"id": "beaker_held_during_pour", "type": "maintain_grasp", "actor": "auxiliary_arm", "object": "obj_beaker", "from_step": "hold_beaker", "through_step": "tilt_pour"}]
    s["success"] = _rubric([
        {"id": "cylinder_lifted", "weight": 0.2, "temporal": {"kind": "instant"}, "condition": {"type": "object_lifted", "parameters": {"object": "obj_graduated_cylinder", "support_surface": "table", "min_clearance_m": 0.01, "held_by": "operating_arm"}}},
        {"id": "openings_aligned", "weight": 0.3, "temporal": {"kind": "instant"}, "condition": {"type": "pose_while_grasped", "parameters": {"grasp": {"actor": "operating_arm", "object": "obj_graduated_cylinder"}, "predicate": {"type": "relative_pose_reached", "parameters": {"object": "obj_graduated_cylinder", "relative_to": "obj_beaker", "xyz_range": {"x": [-0.1, 0.1], "y": [-0.1, 0.1], "z": [0.12, 0.4]}}}}}},
        {"id": "liquid_transfer_majority", "weight": 0.2, "active": False, "requires": ["liquid_sim.contained_volume_ratio"], "temporal": {"kind": "terminal"}, "condition": {"type": "liquid_transfer_ratio", "parameters": {"source": "obj_graduated_cylinder", "target": "obj_beaker", "ratio_threshold": 0.5}}},
        {"id": "liquid_transfer_complete", "weight": 0.2, "active": False, "requires": ["liquid_sim.contained_volume_ratio"], "temporal": {"kind": "terminal"}, "condition": {"type": "liquid_transfer_ratio", "parameters": {"source": "obj_graduated_cylinder", "target": "obj_beaker", "ratio_threshold": 0.9}}},
        {"id": "cylinder_returned", "weight": 0.1, "temporal": {"kind": "terminal"}, "condition": {"type": "object_released_on_support", "parameters": {"object": "obj_graduated_cylinder", "support_surface": "table", "released": True, "upright_max_tilt_deg": 15.0}}},
    ], "openings_aligned")
    return s


def _task7(background: str) -> dict[str, Any]:
    suffix = "" if background == "example4" else f"__background_{background}"
    s = _base(f"scientific_workbench_r7_task07_glass_rod_stir{suffix}", "辅助臂固定 325 mL 烧杯；操作臂拿起 300 mm 玻璃棒，插入杯内并累计搅拌至少一周，最后放回。", background)
    s["task_family"] = "bimanual_stir"
    s["objects"] += [
        {"id": "obj_beaker", "asset_id": "scientific_workbench_r7_beaker_325ml", "source_prim_path": "/World/Beaker325ml", "role": "target_container", "pose": {"xyz": [-0.15, -0.17, 0.755], "wxyz": [1, 0, 0, 0]}, "named_frames": _frame_request("support", "grasp", "opening", "interior_center")},
        {"id": "obj_glass_rod", "asset_id": "scientific_workbench_r7_glass_stirring_rod_300mm", "source_prim_path": "/World/GlassStirringRod", "role": "stirring_tool", "pose": {"xyz": [-0.10, 0.02, 0.758615], "wxyz": [0.7071067812, 0.7071067812, 0, 0]}, "named_frames": _frame_request("support", "grasp", "working_tip")},
    ]
    if background in RACKED_TASK7_BACKGROUNDS:
        rack_xyz = [0.62, 0.17, 0.755]
        s["objects"].append(_context("scientific_workbench_r7_context_rack", "/World/TubeRack", "context_rack", rack_xyz))
        for socket, x in zip((1, 3, 6), (-0.08303, -0.016606, 0.08303)):
            s["objects"].append(_context("scientific_workbench_r7_glass_test_tube_150mm_context", "/World/GlassTestTube150mm", f"context_glass_tube_s{socket}", [rack_xyz[0] + x, rack_xyz[1], 0.7562], socket=socket))
    s["steps"] = [
        {"id": "hold_beaker", "skill": "grasp_and_hold", "actors": ["auxiliary_arm"], "parameters": {"object": "obj_beaker"}},
        {"id": "pick_rod", "skill": "lift", "actors": ["operating_arm"], "parameters": {"object": "obj_glass_rod", "grasp_frame": "obj_glass_rod.grasp"}, "depends_on": ["hold_beaker"]},
        {"id": "insert_rod", "skill": "insert", "actors": ["operating_arm"], "parameters": {"object": "obj_glass_rod", "source_frame": "obj_glass_rod.working_tip", "target_frame": "obj_beaker.interior_center"}, "depends_on": ["pick_rod"]},
        {"id": "stir_once", "skill": "stir", "actors": ["operating_arm"], "parameters": {"object": "obj_glass_rod", "tracked_frame": "obj_glass_rod.working_tip", "reference_frame": "obj_beaker.interior_center", "trajectory": {"kind": "accumulated_angular_sweep", "min_angle_deg": 360.0, "direction_accumulation": "max_separate_signed"}}, "depends_on": ["insert_rod"]},
        {"id": "return_rod", "skill": "place_on_surface", "actors": ["operating_arm"], "parameters": {"object": "obj_glass_rod", "support_surface": "table"}, "depends_on": ["stir_once"]},
        {"id": "release_beaker", "skill": "release", "actors": ["auxiliary_arm"], "parameters": {"object": "obj_beaker"}, "depends_on": ["return_rod"]},
    ]
    s["invariants"] = [{"id": "beaker_held_during_stir", "type": "maintain_grasp", "actor": "auxiliary_arm", "object": "obj_beaker", "from_step": "hold_beaker", "through_step": "stir_once"}]
    s["success"] = _rubric([
        {"id": "rod_lifted", "weight": 0.15, "temporal": {"kind": "instant"}, "condition": {"type": "object_lifted", "parameters": {"object": "obj_glass_rod", "support_surface": "table", "min_clearance_m": 0.01, "held_by": "operating_arm"}}},
        {"id": "rod_tip_inside", "weight": 0.20, "temporal": {"kind": "instant"}, "condition": {"type": "relative_pose_reached", "parameters": {"object": "obj_glass_rod", "tracked_frame": "obj_glass_rod.working_tip", "relative_to": "obj_beaker"}}},
        {"id": "stirring_trajectory_completed", "weight": 0.35, "temporal": {"kind": "sustained", "window": {"from_step": "insert_rod", "through_step": "stir_once"}}, "condition": {"type": "motion_trajectory_completed", "parameters": {"object": "obj_glass_rod", "tracked_frame": "obj_glass_rod.working_tip", "reference_frame": "obj_beaker.interior_center", "trajectory": {"kind": "accumulated_angular_sweep", "min_angle_deg": 360.0, "direction_accumulation": "max_separate_signed"}}}},
        {"id": "rod_returned", "weight": 0.20, "temporal": {"kind": "terminal"}, "condition": {"type": "object_released_on_support", "parameters": {"object": "obj_glass_rod", "support_surface": "table", "released": True}}},
        {"id": "beaker_stable", "weight": 0.10, "temporal": {"kind": "terminal"}, "condition": {"type": "object_released_on_support", "parameters": {"object": "obj_beaker", "support_surface": "table", "released": True, "upright_max_tilt_deg": 10.0}}},
    ], "stirring_trajectory_completed")
    return s


def _task8() -> dict[str, Any]:
    s = _base("scientific_workbench_r7_task08_tighten_centrifuge_tube_cap__background_bioclean", "操作臂拿起红色管盖，辅助臂从六孔试管架中拿起 15 mL 离心管；对准、套合并执行旋紧动作，最后放回原孔位。", "bioclean")
    s["task_family"] = "bimanual_threaded_closure"
    s["seed"] = "008"
    rack_xyz = [-0.04, -0.16, 0.755]
    task_tube_xyz = [rack_xyz[0] - 0.016606, rack_xyz[1], 0.7562]
    s["objects"] += [
        {"id": "obj_tube_rack", "asset_id": "scientific_workbench_r7_tube_rack", "source_prim_path": "/World/TubeRack", "role": "tube_rack", "pose": {"xyz": rack_xyz, "wxyz": [1, 0, 0, 0]}, "named_frames": _frame_request("support", "medium_socket_01_aperture", "medium_socket_01_inserted_bottom", "medium_socket_03_aperture", "medium_socket_03_inserted_bottom", "medium_socket_06_aperture", "medium_socket_06_inserted_bottom")},
        {"id": "obj_centrifuge_tube", "asset_id": "scientific_workbench_r7_centrifuge_tube_15ml_body", "source_prim_path": "/World/CentrifugeTube15mlBody", "role": "centrifuge_tube", "pose": {"xyz": task_tube_xyz, "wxyz": [1, 0, 0, 0]}, "named_frames": _frame_request("support", "grasp", "closure_seat", "opening"), "metadata": {"rack_socket_index": 3}},
        {"id": "obj_centrifuge_tube_cap", "asset_id": "scientific_workbench_r7_centrifuge_tube_15ml_cap", "source_prim_path": "/World/CentrifugeTube15mlCap", "role": "centrifuge_tube_cap", "pose": {"xyz": [-0.18, 0.01, 0.755], "wxyz": [1, 0, 0, 0]}, "named_frames": _frame_request("support", "grasp", "closure_mate")},
        _context("scientific_workbench_r7_closed_15ml_tube_context", "/World/CentrifugeTube15mlClosed", "context_closed_tube_s1", [rack_xyz[0] - 0.08303, rack_xyz[1], 0.7562], socket=1),
        _context("scientific_workbench_r7_closed_15ml_tube_context", "/World/CentrifugeTube15mlClosed", "context_closed_tube_s6", [rack_xyz[0] + 0.08303, rack_xyz[1], 0.7562], socket=6),
    ]
    s["steps"] = [
        {"id": "pick_cap", "skill": "lift", "actors": ["operating_arm"], "parameters": {"object": "obj_centrifuge_tube_cap", "grasp_frame": "obj_centrifuge_tube_cap.grasp"}},
        {"id": "pick_tube", "skill": "lift", "actors": ["auxiliary_arm"], "parameters": {"object": "obj_centrifuge_tube", "grasp_frame": "obj_centrifuge_tube.grasp"}, "depends_on": ["pick_cap"]},
        {"id": "align_cap", "skill": "align", "actors": ["operating_arm", "auxiliary_arm"], "parameters": {"source_frame": "obj_centrifuge_tube_cap.closure_mate", "target_frame": "obj_centrifuge_tube.closure_seat"}, "depends_on": ["pick_tube"]},
        {"id": "mate_cap", "skill": "insert", "actors": ["operating_arm"], "parameters": {"source_frame": "obj_centrifuge_tube_cap.closure_mate", "target_frame": "obj_centrifuge_tube.closure_seat"}, "depends_on": ["align_cap"]},
        {"id": "twist_cap", "skill": "twist", "actors": ["operating_arm"], "parameters": {"object": "obj_centrifuge_tube_cap", "relative_to": "obj_centrifuge_tube", "axis": "z", "direction": "tighten"}, "depends_on": ["mate_cap"]},
        {"id": "return_tube", "skill": "insert", "actors": ["auxiliary_arm"], "parameters": {"object": "obj_centrifuge_tube", "target_frame": "obj_tube_rack.medium_socket_03_inserted_bottom"}, "depends_on": ["twist_cap"]},
        {"id": "release_tube", "skill": "release", "actors": ["auxiliary_arm", "operating_arm"], "parameters": {"object": "obj_centrifuge_tube"}, "depends_on": ["return_tube"]},
    ]
    s["invariants"] = [{"id": "tube_held_during_closure", "type": "maintain_grasp", "actor": "auxiliary_arm", "object": "obj_centrifuge_tube", "from_step": "pick_tube", "through_step": "twist_cap"}]
    s["success"] = _rubric([
        {"id": "cap_lifted", "weight": 0.10, "temporal": {"kind": "instant"}, "condition": {"type": "object_lifted", "parameters": {"object": "obj_centrifuge_tube_cap", "support_surface": "table", "min_clearance_m": 0.005, "held_by": "operating_arm"}}},
        {"id": "tube_lifted", "weight": 0.10, "temporal": {"kind": "instant"}, "condition": {"type": "object_lifted", "parameters": {"object": "obj_centrifuge_tube", "support_surface": "obj_tube_rack", "min_clearance_m": 0.01, "held_by": "auxiliary_arm"}}},
        {"id": "cap_and_tube_aligned", "weight": 0.15, "temporal": {"kind": "instant"}, "condition": {"type": "relative_pose_reached", "parameters": {"source_frame": "obj_centrifuge_tube_cap.closure_mate", "target_frame": "obj_centrifuge_tube.closure_seat", "axial_gap_m": [0.005, 0.03], "lateral_error_max_m": 0.005, "axis_error_max_deg": 8.0}}},
        {"id": "cap_initially_mated", "weight": 0.15, "temporal": {"kind": "instant"}, "condition": {"type": "relative_pose_reached", "parameters": {"source_frame": "obj_centrifuge_tube_cap.closure_mate", "target_frame": "obj_centrifuge_tube.closure_seat", "axial_gap_m": [-0.002, 0.003], "lateral_error_max_m": 0.004, "contact_required": True}}},
        {"id": "cap_rotated_into_closed_state", "weight": 0.30, "active": False, "requires": ["threaded_closure.relative_rotation_and_axial_engagement"], "temporal": {"kind": "terminal"}, "condition": {"type": "motion_trajectory_completed", "parameters": {"object": "obj_centrifuge_tube_cap", "relative_to": "obj_centrifuge_tube", "trajectory": {"kind": "threaded_closure", "direction": "tighten"}}}},
        {"id": "tube_returned_released", "weight": 0.20, "temporal": {"kind": "terminal"}, "condition": {"type": "object_released_on_support", "parameters": {"object": "obj_centrifuge_tube", "support_surface": "obj_tube_rack", "released": True, "upright_max_tilt_deg": 10.0}}},
    ], "cap_and_tube_aligned")
    return s


def load_r7_plans() -> list[R7Plan]:
    return [
        R7Plan(2, "modern_wet_chemistry", "prototype", 0.60, ("liquid contained-volume metric",), _task2()),
        *[R7Plan(7, background, "canonical_candidate", 1.0, (), _task7(background)) for background in TASK7_BACKGROUNDS],
        R7Plan(8, "bioclean", "canonical_candidate", 0.70, ("threaded closure interaction",), _task8()),
    ]


def _materialize_frames(scenario: Mapping[str, Any], sources: Mapping[str, LocalUSDAssetSource]) -> dict[str, Any]:
    result = deepcopy(dict(scenario))
    for item in result["objects"]:
        requested = item.get("named_frames")
        source = sources.get(item.get("asset_id"))
        if not isinstance(requested, Mapping) or source is None or source.upstream_package is None:
            continue
        contract = source.upstream_package.metadata.get("interaction_contract")
        authoritative = contract.get("named_frames") if isinstance(contract, Mapping) else None
        if not isinstance(authoritative, Mapping):
            raise ValueError(f"missing interaction frames for {item['asset_id']}")
        item["named_frames"] = {
            name: {"xyz": list(authoritative[name]["translation_body_local_usd"]), "wxyz": list(authoritative[name]["rotation_body_local_wxyz"])}
            for name in requested
        }
    return result


def _materialize_rack_population(
    scenario: Mapping[str, Any],
    sources: Mapping[str, LocalUSDAssetSource],
) -> dict[str, Any]:
    """Place populated tubes from the admitted rack's authoritative frames."""
    result = deepcopy(dict(scenario))
    rack = next(
        (item for item in result["objects"] if item["id"] in {"context_rack", "obj_tube_rack"}),
        None,
    )
    if rack is None:
        return result
    source = sources.get(rack["asset_id"])
    upstream = getattr(source, "upstream_package", None)
    contract = upstream.metadata.get("interaction_contract") if upstream is not None else None
    frames = contract.get("named_frames") if isinstance(contract, Mapping) else None
    if not isinstance(frames, Mapping):
        raise ValueError(f"missing authoritative socket frames for {rack['asset_id']}")
    rack_xyz = rack["pose"]["xyz"]
    for item in result["objects"]:
        metadata = item.get("metadata")
        socket = metadata.get("rack_socket_index") if isinstance(metadata, Mapping) else None
        if not isinstance(socket, int):
            continue
        frame_name = f"medium_socket_{socket:02d}_inserted_bottom"
        frame = frames.get(frame_name)
        if not isinstance(frame, Mapping):
            raise ValueError(f"missing authoritative frame {frame_name}")
        offset = frame["translation_body_local_usd"]
        item["pose"]["xyz"] = [float(rack_xyz[i]) + float(offset[i]) for i in range(3)]
        item.setdefault("metadata", {})["pose_source"] = f"{rack['id']}.{frame_name}"
    return result


def _fit_evidence(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("status") != "pass":
        raise ValueError("r7 rack insertion qualification must pass")
    return {"path": str(path.resolve()), "sha256": "sha256:" + sha256(path.read_bytes()).hexdigest(), "status": "pass", "claim_boundary": value.get("claim_boundary")}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bindings", type=Path, default=DEFAULT_BINDINGS)
    parser.add_argument("--fit-report", type=Path, default=DEFAULT_FIT_REPORT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--static-only", action="store_true")
    parser.add_argument("--isaac-python", type=Path, default=DEFAULT_ISAAC_PYTHON)
    parser.add_argument("--genmanip-root", type=Path, default=DEFAULT_GENMANIP_ROOT)
    parser.add_argument("--renderer-script", type=Path, default=DEFAULT_RENDERER)
    parser.add_argument("--curobo-src", type=Path, default=DEFAULT_CUROBO_SRC)
    parser.add_argument("--preview-timeout", type=float, default=900.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sources = resolve_scenario_source_bindings(args.bindings)
    fit = _fit_evidence(args.fit_report)
    records = []
    for plan in load_r7_plans():
        populated = _materialize_rack_population(plan.scenario, sources)
        spec = ScenarioSpec.from_mapping(_materialize_frames(populated, sources))
        root = args.out / "packages" / spec.scenario_id
        package = compile_scenario_package(spec, sources, root)
        closure = validate_package(package.package_root)
        if not closure.ok:
            raise ValueError("compiled package failed closure: " + "; ".join(closure.messages))
        tabletop = validate_scientific_workbench_tabletop_placement(package.package_root)
        export = export_genmanip_collected_package(package.package_root)
        write_genmanip_preview_request(export.output_dir, resolution=(1920, 1080))
        vr = export_vr_teleop_package(package.package_root, package.package_root / "adapters/vr_teleop", task_id=spec.scenario_id)
        preview = "not_run"
        if not args.static_only:
            run_genmanip_initial_preview(export.output_dir, args.isaac_python, args.renderer_script, args.genmanip_root, timeout_seconds=args.preview_timeout, runtime_python_paths=(args.curobo_src,))
            preview = "pass"
        records.append({
            "scenario_id": spec.scenario_id, "task_number": plan.task_number, "background_id": plan.background_id,
            "release_status": plan.release_status, "score_ceiling": plan.score_ceiling,
            "missing_capabilities": list(plan.missing_capabilities), "package_root": str(root.resolve()),
            "ebench_root": str(export.output_dir.resolve()), "vr_root": str(vr.output_dir.resolve()),
            "portable_closure": "pass", "tabletop_placement": tabletop.overall_status,
            "provisional_ik": "not_run", "initial_scene_preview": preview,
        })
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "scenario-forge-scientific-workbench-r7/v0.1",
        "status": "static_complete" if args.static_only else "runtime_preview_complete",
        "release": "r7", "package_count": 7, "tube_rack_fit_qualification": fit, "packages": records,
        "claim_boundary": "Package, adapter, placement, and initial-scene evidence only. IK is not run. Score ceilings are rubric coverage, not policy success rates.",
    }
    (args.out / "manifest.yaml").write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
    for record in records:
        print(f"{record['scenario_id']}: {record['package_root']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

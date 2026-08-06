#!/usr/bin/env python3
"""Generate the temporary LabUtopia PBD beaker-to-beaker task package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scenario_forge.adapters.ebench.genmanip import export_genmanip_collected_package
from scenario_forge.adapters.labutopia import load_labutopia_interactive_scene_handoff
from scenario_forge.adapters.vr_teleop import export_vr_teleop_package
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.package_compiler import compile_scenario_package


SCENARIO_ID = "experimental_lab001_pbd_beaker_to_beaker_pour"
ASSET_ID = "lab001_pbd_beaker_to_beaker_step600"
PACKAGE_ID = "lab001_pbd_beaker_to_beaker_step600_v1"


def scenario_mapping() -> dict[str, Any]:
    prefix = "/World/_scene"
    cup_orientation = [
        0.6532814824381882,
        0.6532814824381882,
        0.2705980500730985,
        0.2705980500730985,
    ]
    return {
        "schema_version": "scenario-spec/v0.7",
        "scenario_id": SCENARIO_ID,
        "domain": "scientific_workbench",
        "task_family": "experimental_single_arm_pbd_pour",
        "instruction": (
            "Use the left arm to grasp beaker2, lift it, align it above beaker1, "
            "tilt to pour, return beaker2 to its original table pose, and release it. "
            "Keep the right arm idle."
        ),
        "scene": {
            "asset_id": ASSET_ID,
            "root_prim_path": "/World",
            "composition_mode": "producer_entrypoint",
        },
        "objects": [
            {
                "id": "table",
                "asset_id": ASSET_ID,
                "source_prim_path": f"{prefix}/obj_table",
                "role": "table",
                "instance_mode": "embedded_scene_prim",
                "pose": {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]},
            },
            {
                "id": "beaker2",
                "asset_id": ASSET_ID,
                "source_prim_path": f"{prefix}/obj_beaker2",
                "role": "source_container",
                "instance_mode": "embedded_scene_prim",
                "pose": {
                    "xyz": [0.295, 0.075, 0.8233382266115852],
                    "wxyz": cup_orientation,
                },
                "named_frames": {
                    "opening": {
                        "xyz": [0.0237621889, -0.0433440953, 0.0904004],
                        "wxyz": [1.0, 0.0, 0.0, 0.0],
                    }
                },
            },
            {
                "id": "beaker1",
                "asset_id": ASSET_ID,
                "source_prim_path": f"{prefix}/obj_beaker1",
                "role": "target_container",
                "instance_mode": "embedded_scene_prim",
                "pose": {
                    "xyz": [0.255, -0.245, 0.8406758673476564],
                    "wxyz": cup_orientation,
                },
                "named_frames": {
                    "opening": {
                        "xyz": [0.0237621889, -0.0433440953, 0.1265606],
                        "wxyz": [1.0, 0.0, 0.0, 0.0],
                    }
                },
            },
        ],
        "robot": {
            "profile_ref": "manip/lift2/R5a_isaac41_vr600_v1",
            "spawn": {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]},
            "actors": [
                {
                    "id": "operating_arm",
                    "end_effector": "left",
                    "capabilities": ["grasp", "lift", "align", "tilt", "place", "release"],
                },
                {
                    "id": "idle_arm",
                    "end_effector": "right",
                    "capabilities": ["idle"],
                },
            ],
        },
        "steps": [
            {"id": "grasp_source", "skill": "grasp", "actors": ["operating_arm"], "parameters": {"object": "beaker2"}},
            {"id": "lift_source", "skill": "lift", "actors": ["operating_arm"], "parameters": {"object": "beaker2"}, "depends_on": ["grasp_source"]},
            {"id": "align_and_pour", "skill": "tilt_pour", "actors": ["operating_arm"], "parameters": {"source": "beaker2", "target": "beaker1", "min_tilt_deg": 50.0}, "depends_on": ["lift_source"]},
            {"id": "return_source", "skill": "place_on_surface", "actors": ["operating_arm"], "parameters": {"object": "beaker2", "target": "table"}, "depends_on": ["align_and_pour"]},
            {"id": "release_source", "skill": "release", "actors": ["operating_arm"], "parameters": {"object": "beaker2"}, "depends_on": ["return_source"]},
        ],
        "invariants": [
            {"id": "right_arm_idle", "type": "remain_idle", "actor": "idle_arm", "object": "table", "from_step": "grasp_source", "through_step": "release_source"}
        ],
        "success": {
            "operator": "all",
            "claim_scope": "geometric_staged_proxy",
            "predicates": [
                {
                    "id": "pour_pose_reached",
                    "type": "relative_pose_reached",
                    "sequence_index": 0,
                    "parameters": {
                        "object": "beaker2",
                        "relative_to": "beaker1",
                        "xyz_range": {"x": [-0.04, 0.04], "y": [-0.04, 0.04], "z": [0.08, 0.18]},
                        "axis_alignment": {"object_axis": "z", "target_axis": "z", "comparison": ">=", "threshold_deg": 50.0},
                    },
                },
                {
                    "id": "source_returned",
                    "type": "object_at_initial_pose",
                    "sequence_index": 1,
                    "parameters": {
                        "object": "beaker2",
                        "xyz_tolerance": [0.035, 0.035, 0.02],
                        "relative_axis_object": "table",
                        "object_axis": "z",
                        "target_axis": "z",
                        "max_axis_error_deg": 15.0,
                    },
                },
            ],
            "progress_rubric": {
                "aggregation": {"type": "weighted_progress_score", "normalization": "active_subset_renormalize", "inactive_treatment": "exclude"},
                "items": [
                    {"id": "source_lifted", "weight": 0.2, "active": True, "temporal": {"kind": "instant"}, "condition": {"type": "object_lifted", "parameters": {"object": "beaker2", "min_height_delta_m": 0.03}}, "source_ref": {"step": "lift_source"}},
                    {"id": "pour_geometric_pose", "weight": 0.35, "active": True, "temporal": {"kind": "instant"}, "condition": {"type": "relative_pose_reached", "parameters": {"object": "beaker2", "relative_to": "beaker1", "xyz_range": {"x": [-0.04, 0.04], "y": [-0.04, 0.04], "z": [0.08, 0.18]} }}, "source_ref": {"step": "align_and_pour"}},
                    {"id": "source_returned_geometric", "weight": 0.25, "active": True, "temporal": {"kind": "terminal"}, "condition": {"type": "object_at_initial_pose", "parameters": {"object": "beaker2", "xyz_tolerance": [0.035, 0.035, 0.02]}}, "source_ref": {"step": "return_source"}},
                    {"id": "release_instruction_only", "weight": 0.1, "active": False, "temporal": {"kind": "terminal"}, "condition": {"type": "object_released_on_support", "parameters": {"object": "beaker2", "support_surface": "table"}}, "source_ref": {"reason": "GenManip has no native release success metric"}},
                    {"id": "liquid_transfer_unscored", "weight": 0.1, "active": False, "temporal": {"kind": "terminal"}, "condition": {"type": "liquid_transfer_ratio", "parameters": {"source": "beaker2", "target": "beaker1", "minimum": 0.5}}, "source_ref": {"reason": "particle transfer scorer is not qualified"}},
                ],
            },
        },
        "max_steps": 2400,
        "seed": "000",
    }


def generate(*, handoff_package: Path, output: Path) -> None:
    manifest = handoff_package / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    handoff = load_labutopia_interactive_scene_handoff(
        handoff_package,
        manifest,
        producer_revision=str(data["producer_revision"]),
        expected_package_id=PACKAGE_ID,
        expected_entrypoints=("native", "genmanip", "vr"),
    )
    source = handoff.to_local_usd_asset_source(
        asset_id=ASSET_ID,
        attribution=("LabUtopia interactive PBD scene",),
    )
    compile_scenario_package(ScenarioSpec.from_mapping(scenario_mapping()), {ASSET_ID: source}, output)
    export_genmanip_collected_package(output)
    export_vr_teleop_package(output, output / "adapters/vr", task_id=SCENARIO_ID)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff-package", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    generate(handoff_package=args.handoff_package.resolve(), output=args.out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

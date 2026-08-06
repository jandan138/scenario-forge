#!/usr/bin/env python3
"""Generate the temporary LabUtopia PBD beaker-to-beaker task package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scenario_forge.adapters.ebench.genmanip import export_genmanip_collected_package
from scenario_forge.adapters.ebench.interactive_workcell_layout import (
    validate_interactive_workcell_layout,
)
from scenario_forge.adapters.labutopia import load_labutopia_interactive_scene_handoff
from scenario_forge.adapters.vr_teleop import export_vr_teleop_package
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.package_compiler import compile_scenario_package


VARIANTS = {
    "source_workbench": {
        "scenario_id": "experimental_pbd_beaker_to_beaker_pour_source_workbench",
        "asset_id": "pbd_beaker_to_beaker_source_workbench",
        "package_id": "lab001_pbd_beaker_to_beaker_source_workbench_v3",
    },
    "ebench_workbench": {
        "scenario_id": "experimental_pbd_beaker_to_beaker_pour_ebench_workbench",
        "asset_id": "pbd_beaker_to_beaker_ebench_workbench",
        "package_id": "lab001_pbd_beaker_to_beaker_ebench_workbench_v3",
    },
}
# Recommended default keeps the complete source workbench.  These aliases are
# retained for small callers that import the generator rather than its CLI.
DEFAULT_VARIANT = "source_workbench"
SCENARIO_ID = str(VARIANTS[DEFAULT_VARIANT]["scenario_id"])
ASSET_ID = str(VARIANTS[DEFAULT_VARIANT]["asset_id"])
PACKAGE_ID = str(VARIANTS[DEFAULT_VARIANT]["package_id"])

_DEFAULT_EMBEDDED_STATES: dict[str, dict[str, Any]] = {
    "support_table": {
        "position_xyz_m": [0.24278806604031, 0.0, 0.0],
        "orientation_wxyz": [0.0, -1.0, 0.0, 0.0],
        "local_scale_xyz": [0.006, 0.005, 0.004000000059604645],
    },
    "source_container": {
        "position_xyz_m": [0.295, 0.075, 0.8233382266115852],
        "orientation_wxyz": [
            0.6532814824381884,
            0.6532814824381882,
            0.2705980500730985,
            0.27059805007309856,
        ],
        "local_scale_xyz": [1.0, 1.0, 1.0],
    },
    "target_container": {
        "position_xyz_m": [0.255, -0.245, 0.8406758673476564],
        "orientation_wxyz": [
            0.6532814824381884,
            0.6532814824381882,
            0.2705980500730985,
            0.27059805007309856,
        ],
        "local_scale_xyz": [1.0, 1.0, 1.0],
    },
}

def scenario_mapping(
    embedded_object_states: dict[str, Any] | None = None,
    *,
    variant_id: str = DEFAULT_VARIANT,
    robot_workspace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        variant = VARIANTS[variant_id]
    except KeyError as exc:
        raise ValueError(f"unsupported workbench variant: {variant_id}") from exc
    prefix = "/World/_scene"
    states = embedded_object_states or _DEFAULT_EMBEDDED_STATES
    workspace = robot_workspace or {
        "profile_ref": "manip/lift2/R5a_isaac41_vr600_v1",
        "spawn_xyz_m": [-1.603353277085724, 0.0, 0.31],
        "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
    }

    def pose(role: str) -> dict[str, list[float]]:
        state = states[role]
        return {
            "xyz": list(state["position_xyz_m"]),
            "wxyz": list(state["orientation_wxyz"]),
            "scale_xyz": list(state["local_scale_xyz"]),
        }
    return {
        "schema_version": "scenario-spec/v0.7",
        "scenario_id": variant["scenario_id"],
        "domain": "scientific_workbench",
        "task_family": "experimental_single_arm_pbd_pour",
        "instruction": (
            "Use the left arm to grasp beaker2, lift it, align it above beaker1, "
            "tilt to pour, return beaker2 to its original table pose, and release it. "
            "Keep the right arm idle."
        ),
        "scene": {
            "asset_id": variant["asset_id"],
            "root_prim_path": "/World",
            "composition_mode": "producer_entrypoint",
        },
        "objects": [
            {
                "id": "table",
                "asset_id": variant["asset_id"],
                "source_prim_path": f"{prefix}/obj_table",
                "role": "table",
                "instance_mode": "embedded_scene_prim",
                "pose": pose("support_table"),
            },
            {
                "id": "beaker2",
                "asset_id": variant["asset_id"],
                "source_prim_path": f"{prefix}/obj_beaker2",
                "role": "source_container",
                "instance_mode": "embedded_scene_prim",
                "pose": pose("source_container"),
                "named_frames": {
                    "opening": {
                        "xyz": [0.0237621889, -0.0433440953, 0.0904004],
                        "wxyz": [1.0, 0.0, 0.0, 0.0],
                    }
                },
            },
            {
                "id": "beaker1",
                "asset_id": variant["asset_id"],
                "source_prim_path": f"{prefix}/obj_beaker1",
                "role": "target_container",
                "instance_mode": "embedded_scene_prim",
                "pose": pose("target_container"),
                "named_frames": {
                    "opening": {
                        "xyz": [0.0237621889, -0.0433440953, 0.1265606],
                        "wxyz": [1.0, 0.0, 0.0, 0.0],
                    }
                },
            },
        ],
        "robot": {
            "profile_ref": workspace["profile_ref"],
            "spawn": {
                "xyz": list(workspace["spawn_xyz_m"]),
                "wxyz": list(workspace["orientation_wxyz"]),
            },
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


def generate(
    *, handoff_package: Path, output: Path, variant_id: str | None = None
) -> None:
    manifest = handoff_package / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    producer_variant = str(data.get("layout", {}).get("variant_id", ""))
    selected_variant = variant_id or producer_variant
    if selected_variant not in VARIANTS or selected_variant != producer_variant:
        raise ValueError(
            "requested workbench variant does not match the producer package: "
            f"requested={selected_variant!r}, producer={producer_variant!r}"
        )
    variant = VARIANTS[selected_variant]
    handoff = load_labutopia_interactive_scene_handoff(
        handoff_package,
        manifest,
        producer_revision=str(data["producer_revision"]),
        expected_package_id=str(variant["package_id"]),
        expected_entrypoints=("native", "genmanip", "vr"),
    )
    source = handoff.to_local_usd_asset_source(
        asset_id=str(variant["asset_id"]),
        attribution=("LabUtopia interactive PBD scene",),
    )
    mapping = scenario_mapping(
        dict(
            handoff.manifest["entrypoints"]["genmanip"][
                "embedded_object_states"
            ]
        ),
        variant_id=selected_variant,
        robot_workspace=dict(handoff.manifest["layout"]["robot_workspace"]),
    )
    compile_scenario_package(
        ScenarioSpec.from_mapping(mapping),
        {str(variant["asset_id"]): source},
        output,
    )
    validate_interactive_workcell_layout(
        package_root=output,
        scenario=mapping,
        handoff_manifest=handoff.manifest,
    )
    export_genmanip_collected_package(output)
    export_vr_teleop_package(
        output,
        output / "adapters/vr",
        task_id=str(variant["scenario_id"]),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff-package", required=True, type=Path)
    parser.add_argument("--variant", choices=sorted(VARIANTS))
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    generate(
        handoff_package=args.handoff_package.resolve(),
        output=args.out.resolve(),
        variant_id=args.variant,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

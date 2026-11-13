#!/usr/bin/env python3
"""Multi-Stage State-Teleport Predicate Canary + Critic-1 120-frame settling gate.

Runs inside Isaac Sim 4.1 + GenManip Python behind a process boundary (one clean
SimulationApp subprocess per collected package) to verify:
1. Critic 1: 120-frame zero-action cold-reset settling (<5 mm drift, <3 deg tilt, no fall-off).
2. Zero false positives at t=0: MetricsManager score == 0.0 AND every leaf metric across all
   stages 0..K-1 evaluates False.
3. Sequential multi-stage state teleportation + physics settling flips stage scores
   monotonically (1/K -> 2/K -> ... -> 1.0) with zero non-convex cavity pop-out.
"""

from __future__ import annotations

import argparse
import copy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import traceback
from typing import Any, Mapping, Sequence

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_ROOT = Path("external_artifacts/out_of_domain_factory_20261112")
DEFAULT_ISAAC_PYTHON = Path(
    "/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/"
    "embodied-eval-os-sim-isaacsim41-genmanip-py310/bin/python"
)
DEFAULT_GENMANIP_ROOT = Path("/cpfs/shared/simulation/zhuzihou/dev/GenManip")
DEFAULT_CUROBO_SRC = Path("/cpfs/shared/simulation/mamengchen/curobo-wbc-backup/src")
TABLE_RUNTIME_ID = "00000000000000000000000000000000"

STAGE_CANARY_PLANS: dict[str, list[dict[str, Any]]] = {
    "specialty_coffee_bar_creatista_prep": [
        {
            "stage_index": 0,
            "name": "extend_drip_tray",
            "kind": "articulation_joint",
            "object_id": "creatista_machine",
            "dof_index": 1,
            "target_value": -0.042,
            "interp_steps": 25,
            "settle_steps": 20,
        },
        {
            "stage_index": 1,
            "name": "place_espresso_cup_on_drip_tray",
            "kind": "rigid_relative_teleport",
            "object_id": "espresso_cup",
            "relative_to": "creatista_machine",
            "offset_xyz_m": [0.0, -0.192, 0.0365],
            "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
            "settle_steps": 35,
            "max_settle_drift_m": 0.012,
        },
        {
            "stage_index": 2,
            "name": "drop_coffee_capsule_into_chute",
            "kind": "rigid_relative_teleport",
            "object_id": "coffee_capsule",
            "relative_to": "creatista_machine",
            "offset_xyz_m": [0.0, -0.100, 0.253],
            "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
            "settle_steps": 35,
            "max_settle_drift_m": 0.012,
        },
        {
            "stage_index": 3,
            "name": "close_brew_lever_over_capsule",
            "kind": "articulation_joint",
            "object_id": "creatista_machine",
            "dof_index": 0,
            "target_value": 0.0,
            "interp_steps": 30,
            "settle_steps": 20,
            "watch_cavity_object": "coffee_capsule",
            "watch_relative_to": "creatista_machine",
            "watch_z_bounds_m": [0.246, 0.268],
        },
        {
            "stage_index": 4,
            "name": "turn_select_dial_to_espresso",
            "kind": "articulation_joint",
            "object_id": "creatista_machine",
            "dof_index": 2,
            "target_value": 1.361356816555577,
            "interp_steps": 25,
            "settle_steps": 20,
        },
    ],
    "electronics_qa_ingun_probe_lock": [
        {
            "stage_index": 0,
            "name": "seat_pcba_in_4rail_pin_nest",
            "kind": "rigid_relative_teleport",
            "object_id": "pcba_carrier_board",
            "relative_to": "ingun_fixture",
            "offset_xyz_m": [0.0, -0.040, 0.1285],
            "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
            "settle_steps": 35,
            "max_settle_drift_m": 0.010,
        },
        {
            "stage_index": 1,
            "name": "close_pressure_hood_over_pcba",
            "kind": "articulation_joint",
            "object_id": "ingun_fixture",
            "dof_index": 0,
            "target_value": 0.0,
            "interp_steps": 30,
            "settle_steps": 20,
            "watch_cavity_object": "pcba_carrier_board",
            "watch_relative_to": "ingun_fixture",
            "watch_z_bounds_m": [0.122, 0.140],
        },
        {
            "stage_index": 2,
            "name": "lock_eccentric_clamp_lever",
            "kind": "articulation_joint",
            "object_id": "ingun_fixture",
            "dof_index": 1,
            "target_value": 0.0,
            "interp_steps": 30,
            "settle_steps": 20,
        },
        {
            "stage_index": 3,
            "name": "flip_mode_toggle_probe_active",
            "kind": "articulation_joint",
            "object_id": "ingun_fixture",
            "dof_index": 2,
            "target_value": -0.3665191429188092,
            "interp_steps": 20,
            "settle_steps": 20,
        },
    ],
    "modern_office_brother_calibrate": [
        {
            "stage_index": 0,
            "name": "load_a5_media_into_open_cassette",
            "kind": "rigid_relative_teleport",
            "object_id": "a5_media_pack",
            "relative_to": "brother_printer",
            "offset_xyz_m": [0.0, -0.261, 0.015],
            "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
            "settle_steps": 35,
            "max_settle_drift_m": 0.012,
        },
        {
            "stage_index": 1,
            "name": "push_cassette_closed_into_hollow_tunnel",
            "kind": "articulation_joint",
            "object_id": "brother_printer",
            "dof_index": 0,
            "target_value": 0.0,
            "drive_effort": 32.0,
            "interp_steps": 90,
            "settle_steps": 25,
            "watch_cavity_object": "a5_media_pack",
            "watch_relative_to": "brother_printer",
            "watch_z_bounds_m": [0.008, 0.030],
        },
        {
            "stage_index": 2,
            "name": "place_calibration_sheet_on_platen",
            "kind": "rigid_relative_teleport",
            "object_id": "calibration_sheet",
            "relative_to": "brother_printer",
            "offset_xyz_m": [0.0, -0.010, 0.283],
            "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
            "settle_steps": 35,
            "max_settle_drift_m": 0.010,
        },
        {
            "stage_index": 3,
            "name": "close_scanner_lid_over_sheet",
            "kind": "articulation_joint",
            "object_id": "brother_printer",
            "dof_index": 1,
            "target_value": 0.0,
            "interp_steps": 30,
            "settle_steps": 20,
            "watch_cavity_object": "calibration_sheet",
            "watch_relative_to": "brother_printer",
            "watch_z_bounds_m": [0.276, 0.292],
        },
    ],
}

STAGE_CANARY_PLANS_R2: dict[str, list[dict[str, Any]]] = {
    "specialty_coffee_bar_creatista_prep": [
        {
            "stage_index": 0,
            "name": "extend_drip_tray",
            "kind": "articulation_joint",
            "object_id": "creatista_machine",
            "joint_name": "DripTrayJoint",
            "target_value": -0.042,
            "interp_steps": 25,
            "settle_steps": 20,
        },
        {
            "stage_index": 1,
            "name": "place_espresso_cup_on_drip_tray",
            "kind": "rigid_relative_teleport",
            "object_id": "espresso_cup",
            "relative_to": "creatista_machine",
            "offset_xyz_m": [0.0, -0.192, 0.0365],
            "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
            "settle_steps": 35,
            "max_settle_drift_m": 0.014,
        },
        {
            "stage_index": 2,
            "name": "drop_coffee_capsule_into_chute",
            "kind": "rigid_relative_teleport",
            "object_id": "coffee_capsule",
            "relative_to": "creatista_machine",
            "offset_xyz_m": [0.0, -0.105, 0.253],
            "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
            "settle_steps": 35,
            "max_settle_drift_m": 0.014,
        },
        {
            "stage_index": 3,
            "name": "close_brew_lever_over_capsule",
            "kind": "articulation_joint",
            "object_id": "creatista_machine",
            "joint_name": "BrewLeverJoint",
            "target_value": 0.0,
            "interp_steps": 30,
            "settle_steps": 20,
            "watch_cavity_object": "coffee_capsule",
            "watch_relative_to": "creatista_machine",
            "watch_z_bounds_m": [0.246, 0.268],
        },
        {
            "stage_index": 4,
            "name": "turn_select_dial_to_espresso",
            "kind": "articulation_joint",
            "object_id": "creatista_machine",
            "joint_name": "SelectDialJoint",
            "target_value": 1.361356816555577,
            "interp_steps": 25,
            "settle_steps": 20,
        },
        {
            "stage_index": 5,
            "name": "press_dial_confirm_brew",
            "kind": "articulation_joint",
            "object_id": "creatista_machine",
            "joint_name": "DialPressJoint",
            "target_value": 0.0024,
            "interp_steps": 18,
            "settle_steps": 20,
        },
    ],
    "electronics_qa_ingun_probe_lock": [
        {
            "stage_index": 0,
            "name": "seat_pcba_in_4rail_pin_nest",
            "kind": "rigid_relative_teleport",
            "object_id": "pcba_carrier_board",
            "relative_to": "ingun_fixture",
            "offset_xyz_m": [0.0, -0.040, 0.1285],
            "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
            "settle_steps": 35,
            "max_settle_drift_m": 0.012,
        },
        {
            "stage_index": 1,
            "name": "close_pressure_hood_over_pcba",
            "kind": "articulation_joint",
            "object_id": "ingun_fixture",
            "joint_name": "PressureHoodJoint",
            "target_value": 0.0,
            "interp_steps": 30,
            "settle_steps": 20,
            "watch_cavity_object": "pcba_carrier_board",
            "watch_relative_to": "ingun_fixture",
            "watch_z_bounds_m": [0.122, 0.140],
        },
        {
            "stage_index": 2,
            "name": "lock_u_gantry_clamp_lever",
            "kind": "articulation_joint",
            "object_id": "ingun_fixture",
            "joint_name": "ClampLeverJoint",
            "target_value": 0.0,
            "interp_steps": 30,
            "settle_steps": 20,
        },
        {
            "stage_index": 3,
            "name": "flip_mode_toggle_probe_active",
            "kind": "articulation_joint",
            "object_id": "ingun_fixture",
            "joint_name": "ModeToggleJoint",
            "target_value": -0.3665191429188092,
            "interp_steps": 20,
            "settle_steps": 20,
        },
        {
            "stage_index": 4,
            "name": "press_test_start_button",
            "kind": "articulation_joint",
            "object_id": "ingun_fixture",
            "joint_name": "TestStartButtonJoint",
            "target_value": -0.0024,
            "interp_steps": 18,
            "settle_steps": 20,
        },
    ],
    "modern_office_brother_calibrate": [
        {
            "stage_index": 0,
            "name": "load_a5_media_into_open_cassette",
            "kind": "rigid_relative_teleport",
            "object_id": "a5_media_pack",
            "relative_to": "brother_printer",
            "offset_xyz_m": [0.0, -0.261, 0.015],
            "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
            "settle_steps": 35,
            "max_settle_drift_m": 0.014,
        },
        {
            "stage_index": 1,
            "name": "push_cassette_closed_into_hollow_tunnel",
            "kind": "articulation_joint",
            "object_id": "brother_printer",
            "joint_name": "PaperCassetteJoint",
            "target_value": 0.0,
            "drive_effort": 32.0,
            "interp_steps": 90,
            "settle_steps": 25,
            "watch_cavity_object": "a5_media_pack",
            "watch_relative_to": "brother_printer",
            "watch_z_bounds_m": [0.008, 0.030],
        },
        {
            "stage_index": 2,
            "name": "place_calibration_sheet_on_platen",
            "kind": "rigid_relative_teleport",
            "object_id": "calibration_sheet",
            "relative_to": "brother_printer",
            "offset_xyz_m": [0.0, -0.010, 0.283],
            "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
            "settle_steps": 35,
            "max_settle_drift_m": 0.012,
        },
        {
            "stage_index": 3,
            "name": "close_scanner_lid_over_sheet",
            "kind": "articulation_joint",
            "object_id": "brother_printer",
            "joint_name": "ScannerLidJoint",
            "target_value": 0.0,
            "interp_steps": 30,
            "settle_steps": 20,
            "watch_cavity_object": "calibration_sheet",
            "watch_relative_to": "brother_printer",
            "watch_z_bounds_m": [0.276, 0.292],
        },
        {
            "stage_index": 4,
            "name": "press_copy_start_button",
            "kind": "articulation_joint",
            "object_id": "brother_printer",
            "joint_name": "ButtonStartJoint",
            "target_value": -0.0017,
            "interp_steps": 18,
            "settle_steps": 20,
        },
    ],
}


STAGE_CANARY_PLANS_REAL2SIM: dict[str, list[dict[str, Any]]] = {
    "real2sim_office_desk_riser_organize": [
        {
            "stage_index": 0,
            "name": "pull_open_right_drawer",
            "kind": "articulation_joint",
            "object_id": "desktop_riser_rig",
            "joint_name": "drawer_right",
            "target_value": 0.158,
            "interp_steps": 30,
            "settle_steps": 20,
        },
        {
            "stage_index": 1,
            "name": "store_chocopie_in_right_drawer",
            "kind": "rigid_relative_teleport",
            "object_id": "chocopie_pack",
            "relative_to": "desktop_riser_rig",
            "offset_xyz_m": [0.080, -0.205, 0.0175],
            "orientation_wxyz": [0.70710678, 0.0, 0.0, 0.70710678],
            "settle_steps": 35,
            "max_settle_drift_m": 0.016,
        },
        {
            "stage_index": 2,
            "name": "store_pen_in_right_drawer",
            "kind": "rigid_relative_teleport",
            "object_id": "blue_ballpoint_pen",
            "relative_to": "desktop_riser_rig",
            "offset_xyz_m": [0.172, -0.198, 0.0175],
            "orientation_wxyz": [0.8660254, 0.0, 0.0, 0.5],
            "settle_steps": 35,
            "max_settle_drift_m": 0.016,
        },
        {
            "stage_index": 3,
            "name": "push_right_drawer_closed",
            "kind": "articulation_joint",
            "object_id": "desktop_riser_rig",
            "joint_name": "drawer_right",
            "target_value": 0.0,
            "drive_effort": -36.0,
            "interp_steps": 80,
            "settle_steps": 25,
            "cyclic_return_after_stage": 0,
            "watch_cavity_object": "chocopie_pack",
            "watch_relative_to": "desktop_riser_rig",
            "watch_z_bounds_m": [0.010, 0.048],
        },
        {
            "stage_index": 4,
            "name": "place_water_mug_beside_sprite",
            "kind": "rigid_relative_teleport",
            "object_id": "glass_water_mug",
            "relative_to": "sprite_bottle_500ml",
            "offset_xyz_m": [-0.115, 0.0, 0.002],
            "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
            "settle_steps": 35,
            "max_settle_drift_m": 0.016,
        },
    ],
}


def _plans_for_profile(
    profile: str,
    *,
    plan_file: Path | None = None,
) -> dict[str, list[dict[str, Any]]]:
    if profile in {"r2", "r3", "r4"}:
        selected = STAGE_CANARY_PLANS_R2
    elif profile == "real2sim":
        selected = STAGE_CANARY_PLANS_REAL2SIM
    else:
        selected = STAGE_CANARY_PLANS
    if plan_file is None:
        return selected
    base = copy.deepcopy(selected)
    loaded = yaml.safe_load(plan_file.read_text(encoding="utf-8"))
    if not isinstance(loaded, Mapping):
        raise ValueError(f"Expected mapping in plan file {plan_file}")
    for k, v in loaded.items():
        base[str(k)] = list(v)
    return base


def _normalize_joint_token(name: str) -> str:
    cleaned = name.strip().lower().replace("_", "").replace("-", "")
    if cleaned.endswith("joint"):
        cleaned = cleaned[:-5]
    return cleaned


def _resolve_dof_index(art: Any, step_plan: Mapping[str, Any], art_id: str) -> int:
    if "joint_name" not in step_plan:
        return int(step_plan["dof_index"])
    dof_names = [str(x) for x in art.dof_names]
    jname = str(step_plan["joint_name"])
    if jname in dof_names:
        return dof_names.index(jname)
    norm_target = _normalize_joint_token(jname)
    for idx, cand in enumerate(dof_names):
        if _normalize_joint_token(cand) == norm_target:
            return idx
    raise ValueError(f"joint_name {jname!r} not in {art_id}.dof_names={dof_names}")


def _lookup_reference_world_pose(scene: Any, rel_id: str) -> tuple[Any, Any]:
    if rel_id in scene.articulation_list:
        return scene.articulation_list[rel_id].get_world_pose()
    if rel_id in scene.object_list:
        return scene.object_list[rel_id].get_world_pose()
    raise KeyError(
        f"reference object {rel_id!r} not found in articulation_list or object_list"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Critic-1 cold-reset settling + Multi-Stage Predicate Canary."
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=DEFAULT_OUT_ROOT,
        help="Factory output root containing packages/<scenario_id>/collected_package.",
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=None,
        help="Optional extra path to write predicate_canary_summary.json.",
    )
    parser.add_argument(
        "--plan-file",
        type=Path,
        default=None,
        help="Optional YAML/JSON stage canary plan override file.",
    )
    parser.add_argument(
        "--single-collected-root",
        type=Path,
        help="Internal worker mode: run canary on one collected_package inside SimulationApp.",
    )
    parser.add_argument(
        "--isaac-python",
        type=Path,
        default=DEFAULT_ISAAC_PYTHON,
        help="Isaac Sim 4.1 + GenManip Python executable.",
    )
    parser.add_argument(
        "--genmanip-root",
        type=Path,
        default=DEFAULT_GENMANIP_ROOT,
        help="GenManip checkout directory.",
    )
    parser.add_argument(
        "--profile",
        choices=("r1", "r2", "r3", "r4", "real2sim"),
        default="r1",
        help="Stage canary profile (r1: 5/4/4; r2/r3/r4: 6/5/5 CAD UI; real2sim: 5-stage workstation).",
    )
    parser.add_argument(
        "--curobo-src",
        type=Path,
        default=DEFAULT_CUROBO_SRC,
        help="Optional CuRobo Python source directory added to worker PYTHONPATH.",
    )
    return parser


def _isaac_environment(
    isaac_python: Path,
    *,
    curobo_src: Path | None = None,
) -> dict[str, str]:
    environment = dict(os.environ)
    if curobo_src is not None and curobo_src.is_dir():
        inherited = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = os.pathsep.join(
            [str(curobo_src.resolve()), *([inherited] if inherited else [])]
        )
    environment["PATH"] = os.pathsep.join(
        [str(isaac_python.parent), environment.get("PATH", "")]
    )
    prefix = isaac_python.parent.parent
    libraries = (
        prefix / "lib/python3.10/site-packages/torch/lib",
        prefix / "lib/python3.10/site-packages/nvidia/cuda_runtime/lib",
        prefix / "lib/python3.10/site-packages/isaacsim/extscache/omni.cuda.libs/bin",
    )
    inherited_ld = environment.get("LD_LIBRARY_PATH", "")
    environment["LD_LIBRARY_PATH"] = os.pathsep.join(
        [
            *[str(path) for path in libraries if path.is_dir()],
            *([inherited_ld] if inherited_ld else []),
        ]
    )
    return environment


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _quat_angle_deg(q1_wxyz: Sequence[float], q2_wxyz: Sequence[float]) -> float:
    n1 = math.sqrt(sum(float(v) * float(v) for v in q1_wxyz))
    n2 = math.sqrt(sum(float(v) * float(v) for v in q2_wxyz))
    if n1 == 0.0 or n2 == 0.0:
        return 180.0
    dot = abs(sum((float(a) / n1) * (float(b) / n2) for a, b in zip(q1_wxyz, q2_wxyz)))
    dot = min(1.0, max(-1.0, dot))
    return math.degrees(2.0 * math.acos(dot))


def _resolve_collected_asset_paths(
    task_data: dict[str, Any],
    collected_root: Path,
    package_id: str,
) -> None:
    initial_layout = task_data["initial_layout"]
    prefix = f"collected_packages/{package_id}/"
    resolved_root = collected_root.resolve()
    for raw_item in initial_layout.values():
        if not isinstance(raw_item, dict):
            continue
        raw_path = raw_item.get("path")
        if isinstance(raw_path, str) and raw_path.startswith(prefix):
            relative = Path(raw_path.removeprefix(prefix))
            raw_item["path"] = str((resolved_root / relative).resolve())


def _run_single_collected_worker(
    collected_root: Path,
    genmanip_root: Path,
    *,
    profile: str = "r1",
    plan_file: Path | None = None,
) -> int:
    collected_root = collected_root.resolve()
    genmanip_root = genmanip_root.resolve()
    if str(genmanip_root) not in sys.path:
        sys.path.insert(0, str(genmanip_root))

    plans = _plans_for_profile(profile, plan_file=plan_file)
    manifest_path = collected_root / "package_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    package_id = str(manifest["package_id"])
    if package_id not in plans:
        raise ValueError(f"no stage canary plan declared for {package_id!r} in profile {profile!r}")

    entrypoints = manifest["entrypoints"]
    task_config_path = collected_root / entrypoints["task_config"]
    episode_path = collected_root / entrypoints["episode_metadata"]
    scene_path = collected_root / entrypoints["scene_usd"]
    camera_path = collected_root / entrypoints["camera_config"]

    task_config = yaml.safe_load(task_config_path.read_text(encoding="utf-8"))
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    task_name = str(episode["task_name"])
    task_data = copy.deepcopy(episode["task_data"])
    _resolve_collected_asset_paths(task_data, collected_root, package_id)

    matches = [
        copy.deepcopy(cfg)
        for cfg in task_config["evaluation_configs"]
        if cfg.get("task_name") == task_name
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one evaluation config for {task_name!r}")
    evaluation = matches[0]
    evaluation["usd_name"] = str(scene_path.with_suffix(""))
    evaluation["domain_randomization"]["cameras"]["config_path"] = str(camera_path)

    from isaacsim import SimulationApp

    simulation_app = SimulationApp({"headless": True, "multi_gpu": False})
    try:
        import numpy as np
        from omni.isaac.core.utils.types import ArticulationAction

        from genmanip.core.metrics.utils import MetricFactory
        from genmanip.core.scene.scene import Scene
        from genmanip.core.scene.scene_config import SceneConfig
        from genmanip.utils.loader.domain_randomization import reset_scene
        from genmanip.utils.loader.scene import recovery_scene
        from genmanip.utils.standalone.file_utils import load_default_config
        from genmanip.utils.usd_utils.prim_utils import clean_prim_velocity
        import genmanip.extensions.metrics  # noqa: F401

        default_config = load_default_config(
            str(genmanip_root), "__scenario_forge_canary__.json", "local"
        )
        scene_config = SceneConfig(**evaluation)
        scene = Scene(scene_config)
        scene.initialize(
            default_config,
            physics_dt=float(evaluation.get("physics_dt", 1.0 / 60.0)),
            rendering_dt=float(evaluation.get("rendering_dt", 1.0 / 60.0)),
            is_render=False,
            only_color_rep_for_camera=True,
        )
        scene.post_initialize()
        reset_scene(scene)

        preserved_parts = tuple(scene.articulation_part_list)
        recovered_task_data = copy.deepcopy(task_data)
        for part_id in preserved_parts:
            recovered_task_data["initial_layout"].setdefault(
                part_id, {"type": "articulation_part"}
            )
        recovery_scene(scene, recovered_task_data, task_name, default_config)

        for _ in range(50):
            scene.world.step(render=False)

        # ------------------------------------------------------------------
        # 1. Critic 1: 120-frame zero-action cold-reset settling audit
        # ------------------------------------------------------------------
        dynamic_obj_ids = [
            uid
            for uid, info in task_data["initial_layout"].items()
            if isinstance(info, Mapping)
            and info.get("type") == "object"
            and not info.get("is_articulation_part", False)
            and uid != TABLE_RUNTIME_ID
            and uid in scene.object_list
        ]
        articulation_ids = [
            uid
            for uid, info in task_data["initial_layout"].items()
            if isinstance(info, Mapping)
            and info.get("type") == "articulation"
            and uid in scene.articulation_list
        ]

        baseline_poses: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for uid in dynamic_obj_ids:
            pos, ori = scene.object_list[uid].get_world_pose()
            baseline_poses[uid] = (np.asarray(pos, dtype=float), np.asarray(ori, dtype=float))
        baseline_joints: dict[str, np.ndarray] = {}
        for uid in articulation_ids:
            baseline_joints[uid] = np.asarray(
                scene.articulation_list[uid].get_joint_positions(), dtype=float
            )
            # Lock joint PD targets at reset values so drives hold their initial reset pose
            scene.articulation_list[uid].apply_action(
                ArticulationAction(joint_positions=baseline_joints[uid].tolist())
            )

        for _ in range(120):
            scene.world.step(render=False)

        settling_objects: dict[str, Any] = {}
        max_pos_drift_m = 0.0
        max_rot_drift_deg = 0.0
        min_object_z_m = 999.0
        for uid in dynamic_obj_ids:
            pos1, ori1 = scene.object_list[uid].get_world_pose()
            pos1_arr = np.asarray(pos1, dtype=float)
            ori1_arr = np.asarray(ori1, dtype=float)
            pos0_arr, ori0_arr = baseline_poses[uid]
            drift_m = float(np.linalg.norm(pos1_arr - pos0_arr))
            rot_deg = _quat_angle_deg(ori0_arr, ori1_arr)
            max_pos_drift_m = max(max_pos_drift_m, drift_m)
            max_rot_drift_deg = max(max_rot_drift_deg, rot_deg)
            min_object_z_m = min(min_object_z_m, float(pos1_arr[2]))
            settling_objects[uid] = {
                "position_after_120_steps_m": [round(float(x), 6) for x in pos1_arr],
                "translation_drift_m": round(drift_m, 6),
                "orientation_drift_deg": round(rot_deg, 4),
            }

        max_joint_drift = 0.0
        settling_articulations: dict[str, Any] = {}
        for uid in articulation_ids:
            joints1 = np.asarray(
                scene.articulation_list[uid].get_joint_positions(), dtype=float
            )
            j_drift = float(np.max(np.abs(joints1 - baseline_joints[uid])))
            max_joint_drift = max(max_joint_drift, j_drift)
            settling_articulations[uid] = {
                "joints_after_120_steps": [round(float(x), 6) for x in joints1],
                "max_abs_joint_drift": round(j_drift, 6),
            }

        settling_pass = (
            max_pos_drift_m <= 0.005
            and max_rot_drift_deg <= 3.0
            and min_object_z_m >= 0.70
            and max_joint_drift <= 0.03
        )
        if not settling_pass:
            raise RuntimeError(
                f"Critic-1 cold-reset settling failed for {package_id}: "
                f"max_pos_drift_m={max_pos_drift_m:.5f}, max_rot_drift_deg={max_rot_drift_deg:.3f}, "
                f"min_z={min_object_z_m:.4f}, max_joint_drift={max_joint_drift:.5f}"
            )

        # ------------------------------------------------------------------
        # 2. t=0 False-Positive Audit (MetricsManager + all stages & primary leaves)
        # ------------------------------------------------------------------
        goal = copy.deepcopy(task_data["goal"])
        scene.build_metrics_manager(goal)
        metrics_manager = scene.metric_manager
        t0_score = float(metrics_manager.step(scene))

        plan = plans[package_id]
        cyclic_gate_by_stage = {
            int(sp["stage_index"]): int(sp["cyclic_return_after_stage"])
            for sp in plan
            if "cyclic_return_after_stage" in sp
        }

        t0_stage_results: list[dict[str, Any]] = []
        t0_leaf_results: list[dict[str, Any]] = []
        any_t0_false_positive = False
        for stage_idx, stage_disjunctions in enumerate(goal):
            is_cyclic_return = stage_idx in cyclic_gate_by_stage
            conjunction_statuses: list[bool] = []
            for conj_idx, conj_leaves in enumerate(stage_disjunctions):
                leaf_bools: list[bool] = []
                for leaf_cfg in conj_leaves:
                    m_type = str(
                        leaf_cfg.get(
                            "type", "manip/default/sr_based_genmanip_relationship"
                        )
                    )
                    metric = MetricFactory.build(
                        m_type,
                        skip_steps=leaf_cfg.get("skip_steps", 1),
                        succ_cnts=leaf_cfg.get("succ_cnts", 0),
                        never_reset=leaf_cfg.get("never_reset", False),
                        sub_goal_setting=leaf_cfg,
                    )
                    status = bool(metric.check_status(scene))
                    leaf_bools.append(status)
                    is_primary_state_predicate = m_type in {
                        "manip/default/sr_based_genmanip_range",
                        "manip/default/sr_based_genmanip_relationship",
                    }
                    if is_primary_state_predicate and status and not is_cyclic_return:
                        any_t0_false_positive = True
                    t0_leaf_results.append(
                        {
                            "stage_index": stage_idx,
                            "conjunction_index": conj_idx,
                            "metric_type": m_type,
                            "role": (
                                "cyclic_state_return_gated"
                                if is_cyclic_return
                                else (
                                    "primary_state_transition"
                                    if is_primary_state_predicate
                                    else "auxiliary_orientation_guard"
                                )
                            ),
                            "obj1_uid": leaf_cfg.get("obj1_uid"),
                            "t0_status": status,
                        }
                    )
                conjunction_statuses.append(bool(leaf_bools) and all(leaf_bools))
            stage_satisfied = any(conjunction_statuses)
            if stage_satisfied and not is_cyclic_return:
                any_t0_false_positive = True
            t0_stage_results.append(
                {
                    "stage_index": stage_idx,
                    "t0_stage_satisfied": stage_satisfied,
                    **(
                        {"cyclic_return_after_stage": cyclic_gate_by_stage[stage_idx]}
                        if is_cyclic_return
                        else {}
                    ),
                }
            )
        for stage_idx, gate_idx in cyclic_gate_by_stage.items():
            if gate_idx >= stage_idx or t0_stage_results[gate_idx]["t0_stage_satisfied"]:
                any_t0_false_positive = True

        if t0_score != 0.0 or any_t0_false_positive:
            raise RuntimeError(
                f"t=0 false-positive audit failed for {package_id}: "
                f"t0_score={t0_score}, stages={t0_stage_results}, leaves={t0_leaf_results}"
            )

        # ------------------------------------------------------------------
        # 3. Sequential Multi-Stage State-Teleport + Physics Settling Canary
        # ------------------------------------------------------------------
        total_stages = len(plan)
        stage_traces: list[dict[str, Any]] = []
        previous_score = t0_score

        for step_plan in plan:
            kind = step_plan["kind"]
            if kind == "articulation_joint":
                art_id = step_plan["object_id"]
                art = scene.articulation_list[art_id]
                dof_index = _resolve_dof_index(art, step_plan, art_id)
                target_val = float(step_plan["target_value"])
                interp_steps = int(step_plan["interp_steps"])
                settle_steps = int(step_plan["settle_steps"])

                current = np.asarray(art.get_joint_positions(), dtype=float)
                start_val = float(current[dof_index])
                drive_effort = step_plan.get("drive_effort")
                if drive_effort is not None:
                    efforts = [0.0 for _ in range(len(current))]
                    efforts[dof_index] = float(drive_effort)
                    for _ in range(interp_steps):
                        art.apply_action(ArticulationAction(joint_efforts=efforts))
                        scene.world.step(render=False)
                    zero_efforts = [0.0 for _ in range(len(current))]
                    art.apply_action(ArticulationAction(joint_efforts=zero_efforts))
                    for _ in range(settle_steps):
                        scene.world.step(render=False)
                else:
                    for step_i in range(1, interp_steps + 1):
                        alpha = step_i / float(interp_steps)
                        cmd_joints = current.copy()
                        cmd_joints[dof_index] = start_val + alpha * (target_val - start_val)
                        art.set_joint_positions(cmd_joints.tolist())
                        art.apply_action(
                            ArticulationAction(joint_positions=cmd_joints.tolist())
                        )
                        scene.world.step(render=False)

                    final_cmd = np.asarray(art.get_joint_positions(), dtype=float)
                    final_cmd[dof_index] = target_val
                    art.set_joint_positions(final_cmd.tolist())
                    art.apply_action(ArticulationAction(joint_positions=final_cmd.tolist()))
                    for _ in range(settle_steps):
                        scene.world.step(render=False)

                observed_joints = [
                    round(float(x), 6) for x in art.get_joint_positions()
                ]
                stage_detail: dict[str, Any] = {
                    "articulation_id": art_id,
                    "dof_index": dof_index,
                    "target_value": round(target_val, 6),
                    "observed_joint_positions": observed_joints,
                }
                if "watch_cavity_object" in step_plan:
                    watch_obj = step_plan["watch_cavity_object"]
                    watch_rel = step_plan["watch_relative_to"]
                    obj_pos, _ = scene.object_list[watch_obj].get_world_pose()
                    rel_pos, _ = _lookup_reference_world_pose(scene, watch_rel)
                    delta = np.asarray(obj_pos, dtype=float) - np.asarray(
                        rel_pos, dtype=float
                    )
                    z_lo, z_hi = step_plan["watch_z_bounds_m"]
                    if not (float(z_lo) <= float(delta[2]) <= float(z_hi)):
                        raise RuntimeError(
                            f"cavity pop-out detected for {watch_obj} in {package_id} "
                            f"stage {step_plan['stage_index']}: relative_xyz={delta.tolist()}"
                        )
                    stage_detail["watched_cavity_object"] = {
                        "object_id": watch_obj,
                        "relative_xyz_m": [round(float(x), 6) for x in delta],
                        "cavity_retention_pass": True,
                    }

            elif kind in {"rigid_relative_teleport", "rigid_world_teleport"}:
                obj_id = step_plan["object_id"]
                target_ori = np.asarray(step_plan["orientation_wxyz"], dtype=float)
                settle_steps = int(step_plan["settle_steps"])

                if kind == "rigid_world_teleport":
                    hero_pos_arr = np.zeros(3, dtype=float)
                    target_pos = np.asarray(step_plan["world_xyz_m"], dtype=float)
                else:
                    rel_id = step_plan["relative_to"]
                    offset = np.asarray(step_plan["offset_xyz_m"], dtype=float)
                    hero_pos, _ = _lookup_reference_world_pose(scene, rel_id)
                    hero_pos_arr = np.asarray(hero_pos, dtype=float)
                    target_pos = hero_pos_arr + offset
                scene.object_list[obj_id].set_world_pose(
                    target_pos.tolist(), target_ori.tolist()
                )
                clean_prim_velocity(scene.object_list[obj_id].prim_path)
                for _ in range(settle_steps):
                    scene.world.step(render=False)

                settled_pos, settled_ori = scene.object_list[obj_id].get_world_pose()
                settled_pos_arr = np.asarray(settled_pos, dtype=float)
                settled_ori_arr = np.asarray(settled_ori, dtype=float)
                settle_drift_m = float(np.linalg.norm(settled_pos_arr - target_pos))
                max_allowed = float(step_plan.get("max_settle_drift_m", 0.015))
                if settle_drift_m > max_allowed:
                    raise RuntimeError(
                        f"excessive post-teleport settle drift ({settle_drift_m:.4f} m > "
                        f"{max_allowed:.4f} m) for {obj_id} in {package_id}"
                    )
                rel_offset_after = settled_pos_arr - hero_pos_arr
                stage_detail = {
                    "object_id": obj_id,
                    "teleported_world_xyz_m": [round(float(x), 6) for x in target_pos],
                    "settled_world_xyz_m": [round(float(x), 6) for x in settled_pos_arr],
                    "settled_relative_xyz_m": [
                        round(float(x), 6) for x in rel_offset_after
                    ],
                    "settled_wxyz": [round(float(x), 6) for x in settled_ori_arr],
                    "settle_drift_m": round(settle_drift_m, 6),
                }
            else:
                raise ValueError(f"unknown canary step kind: {kind!r}")

            score_after = float(metrics_manager.step(scene))
            expected_score = (int(step_plan["stage_index"]) + 1) / float(total_stages)
            if not math.isclose(score_after, expected_score, rel_tol=0.0, abs_tol=1e-4):
                raise RuntimeError(
                    f"stage {step_plan['stage_index']} ({step_plan['name']}) failed to advance "
                    f"MetricsManager in {package_id}: expected {expected_score:.4f}, "
                    f"got {score_after:.4f}; detail={stage_detail}"
                )
            if score_after <= previous_score:
                raise RuntimeError(
                    f"non-monotonic score in {package_id}: {previous_score} -> {score_after}"
                )
            previous_score = score_after
            stage_traces.append(
                {
                    "stage_index": int(step_plan["stage_index"]),
                    "name": step_plan["name"],
                    "kind": kind,
                    "expected_score": round(expected_score, 6),
                    "observed_score": round(score_after, 6),
                    "detail": stage_detail,
                }
            )

        if not math.isclose(previous_score, 1.0, rel_tol=0.0, abs_tol=1e-5):
            raise RuntimeError(f"final score for {package_id} did not reach 1.0: {previous_score}")

        report = {
            "schema_version": "scenario-forge-genmanip-predicate-canary/v0.1",
            "package_id": package_id,
            "task_name": task_name,
            "status": "pass",
            "inputs": {
                "package_manifest_sha256": _file_sha256(manifest_path),
                "task_config_sha256": _file_sha256(task_config_path),
                "episode_metadata_sha256": _file_sha256(episode_path),
                "scene_usd_sha256": _file_sha256(scene_path),
            },
            "critic1_cold_reset_settling_120_steps": {
                "status": "pass",
                "max_translation_drift_m": round(max_pos_drift_m, 6),
                "max_orientation_drift_deg": round(max_rot_drift_deg, 4),
                "min_dynamic_object_z_m": round(min_object_z_m, 6),
                "max_articulation_joint_drift": round(max_joint_drift, 6),
                "objects": settling_objects,
                "articulations": settling_articulations,
            },
            "t0_false_positive_audit": {
                "status": "pass",
                "metrics_manager_t0_score": t0_score,
                "stages": t0_stage_results,
                "leaf_predicates": t0_leaf_results,
            },
            "multi_stage_state_teleport_canary": {
                "status": "pass",
                "stage_count": total_stages,
                "final_score": round(previous_score, 6),
                "stages": stage_traces,
            },
            "claim_boundary": (
                "Verifies cold-reset physics stability, zero t=0 predicate false positives, "
                "non-convex cavity retention, and monotonic multi-stage MetricsManager 0.0 -> 1.0 "
                "progression via state teleportation; robotic IK/motion-planning trajectory "
                "synthesis is delegated to downstream privileged-world solver (Astra)."
            ),
        }
        report_path = collected_root / "evidence" / "predicate_canary_report.yaml"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            yaml.safe_dump(report, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        print(
            f"[CanaryWorker] PASS {package_id}: t0={t0_score:.2f} -> final={previous_score:.2f} "
            f"(max_drift={max_pos_drift_m*1000:.2f}mm)"
        )
        scene.world.stop()
        scene.world.clear_instance()
        return 0
    except BaseException:
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(2)
    finally:
        simulation_app.close()


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan_file = (
        (
            args.plan_file
            if args.plan_file.is_absolute()
            else (REPO_ROOT / args.plan_file)
        ).resolve()
        if args.plan_file is not None
        else None
    )
    if args.single_collected_root is not None:
        return _run_single_collected_worker(
            args.single_collected_root,
            args.genmanip_root,
            profile=args.profile,
            plan_file=plan_file,
        )

    plans = _plans_for_profile(args.profile, plan_file=plan_file)
    out_root = (
        args.out_root if args.out_root.is_absolute() else (REPO_ROOT / args.out_root)
    ).resolve()
    isaac_python = args.isaac_python.resolve()
    genmanip_root = args.genmanip_root.resolve()
    worker_env = _isaac_environment(isaac_python, curobo_src=args.curobo_src)
    summaries: list[dict[str, Any]] = []
    for scenario_id in plans:
        collected_dir = out_root / "packages" / scenario_id / "collected_package"
        if not collected_dir.is_dir():
            raise FileNotFoundError(f"missing collected_package for {scenario_id}: {collected_dir}")
        cmd = [
            str(isaac_python),
            str(Path(__file__).resolve()),
            "--profile",
            args.profile,
            "--single-collected-root",
            str(collected_dir),
            "--genmanip-root",
            str(genmanip_root),
        ]
        if plan_file is not None:
            cmd.extend(["--plan-file", str(plan_file)])
        completed = subprocess.run(cmd, cwd=genmanip_root, env=worker_env, check=False)
        if completed.returncode != 0:
            raise RuntimeError(
                f"predicate canary failed for {scenario_id} (exit={completed.returncode})"
            )
        report_path = collected_dir / "evidence" / "predicate_canary_report.yaml"
        report_data = yaml.safe_load(report_path.read_text(encoding="utf-8"))
        summaries.append(
            {
                "scenario_id": scenario_id,
                "status": report_data["status"],
                "report_yaml": str(report_path),
                "report_sha256": _file_sha256(report_path),
                "critic1_max_translation_drift_m": report_data[
                    "critic1_cold_reset_settling_120_steps"
                ]["max_translation_drift_m"],
                "t0_score": report_data["t0_false_positive_audit"][
                    "metrics_manager_t0_score"
                ],
                "stage_scores": [
                    s["observed_score"]
                    for s in report_data["multi_stage_state_teleport_canary"]["stages"]
                ],
                "final_score": report_data["multi_stage_state_teleport_canary"][
                    "final_score"
                ],
            }
        )

    summary_payload = {
        "schema_version": "out-of-domain-predicate-canary-summary/v0.1",
        "overall_status": "pass",
        "scenarios": summaries,
    }
    summary_text = (
        json.dumps(summary_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    summary_path = out_root / "predicate_canary_summary.json"
    summary_path.write_text(summary_text, encoding="utf-8")
    if args.summary_out is not None:
        extra_out = (
            args.summary_out
            if args.summary_out.is_absolute()
            else (REPO_ROOT / args.summary_out)
        ).resolve()
        extra_out.parent.mkdir(parents=True, exist_ok=True)
        extra_out.write_text(summary_text, encoding="utf-8")
        print(f"Wrote predicate canary summary: {extra_out}")
    print(f"Wrote predicate canary summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

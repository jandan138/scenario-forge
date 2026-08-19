#!/usr/bin/env python3
"""Compile the Task 09 r12 VR-first room-floor package."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
from typing import Any, Sequence

import yaml

import scripts.generate_scientific_workbench_r11 as r11
from scenario_forge.adapters.vr_teleop import export_vr_teleop_package
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.package_compiler import compile_scenario_package
from scenario_forge.generation.source_resolver import resolve_scenario_source_bindings
from scenario_forge.package import validate_package


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "outputs/scientific_workbench_task09_r12_20260818"
DEFAULT_BINDINGS = (
    REPO_ROOT / "configs/source_bindings/scientific_workbench_task09_r12_20260818.yaml"
)


def _pose(
    xyz: list[float], *, scale_xyz: list[float] | None = None
) -> dict[str, list[float]]:
    return {
        "xyz": xyz,
        "wxyz": [1.0, 0.0, 0.0, 0.0],
        **({"scale_xyz": scale_xyz} if scale_xyz is not None else {}),
    }


def build_task09_r12_scenario() -> dict[str, Any]:
    scenario = deepcopy(r11.build_task09_scenario())
    scenario["schema_version"] = "scenario-spec/v0.7"
    scenario["scenario_id"] = (
        "scientific_workbench_r12_task09_oven_load_start__"
        "background_analytical_instrumentation_floor"
    )
    scenario["metadata"] = {
        "release": "r12-vr-first",
        "visual_ready": False,
        "asset_interaction_ready": True,
        "task_interaction_ready": False,
        "robot_policy_success": False,
        "claim_boundary": (
            "Portable room-floor layout and qualified asset inputs only; no robot-policy, "
            "complete-task, benchmark-score, or thermal-behavior claim."
        ),
        "collision_strategy": (
            "convexDecomposition on the main door, temperature dial, and power rocker; "
            "source collision is preserved on fixed and non-task links"
        ),
    }
    scenario["objects"] = [
        {
            "id": "table",
            "asset_id": "scientific_workbench_r12_analytical_room_floor_static_support",
            "source_prim_path": "/World/table",
            "role": "table",
            "pose": _pose([0.0, 0.0, 0.0]),
            "metadata": {
                "support_semantics": "room_floor",
                "visible_surface_owner": (
                    "scientific_environment_code_room_analytical_instrumentation_v2"
                ),
                "vr_presentation_visibility": "invisible",
            },
        },
        {
            "id": "obj_oven",
            "asset_id": "scientific_workbench_r12_analog_oven",
            "source_prim_path": "/World/AnalogGravityConvectionOven",
            "role": "articulated_device",
            "pose": _pose([0.35, 0.0, 0.0]),
            "metadata": {
                "articulated_pose_frame": "support_plane",
                "support_surface": "room_floor",
                "vr_randomization_group": "task09_oven",
                "vr_worst_case_xy_offset_m": 0.01,
                "visual_envelope_size_xyz_m": [0.875, 0.77, 0.9332],
                "door_sweep_clearance_required": True,
            },
        },
        {
            "id": "obj_sample_beaker",
            "asset_id": "scientific_workbench_r12_beaker_dynamic_glass_v1",
            "source_prim_path": "/World/Beaker",
            "role": "sample_vessel",
            "pose": _pose([-0.35, -0.16, 0.0], scale_xyz=[0.7, 0.7, 0.7]),
            "metadata": {
                "support_surface": "room_floor",
                "vr_randomization_group": "task09_sample_beaker",
                "task_instance_uniform_scale": 0.7,
                "scale_reason": "Lift2 collection graspability feedback",
            },
        },
    ]
    return scenario


def build_vr_release(
    *, output_dir: Path = DEFAULT_OUT, bindings_path: Path = DEFAULT_BINDINGS
) -> Path:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f"r12 output already exists: {output_dir}")
    scenario = ScenarioSpec.from_mapping(build_task09_r12_scenario())
    sources = resolve_scenario_source_bindings(bindings_path)
    package_root = output_dir / "packages/task09"
    compiled = compile_scenario_package(scenario, sources, package_root)
    closure = validate_package(compiled.package_root)
    if not closure.ok:
        raise ValueError("compiled package failed closure: " + "; ".join(closure.messages))
    closure_path = package_root / "evidence/package_closure.yaml"
    closure_path.parent.mkdir(parents=True, exist_ok=True)
    closure_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "scenario-forge-package-closure/v0.1",
                "status": "pass",
                "messages": list(closure.messages),
                "claim_boundary": "Portable dependency closure only; not runtime task success.",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    vr = export_vr_teleop_package(
        package_root,
        package_root / "adapters/vr_teleop",
        task_id=scenario.scenario_id,
        include_robot_physics_overrides=False,
    )
    manifest = {
        "schema_version": "scenario-forge-scientific-workbench-task09-r12/v0.1",
        "status": "vr_static_complete_open_smoke_pending",
        "release": "r12-vr-first",
        "package_root": str(package_root.resolve()),
        "vr_root": str(vr.output_dir.resolve()),
        "vr_scene": str(vr.scene_usd.resolve()),
        "vr_task_config": str(vr.task_config.resolve()),
        "portable_closure": "pass",
        "vr_open_smoke": "pending",
        "ebench_export": "deferred",
        "claim_boundary": (
            "VR package shape and portable closure only; no robot-policy or task-success claim."
        ),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "manifest.yaml"
    destination.write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return destination


def finalize_vr_release(*, output_dir: Path = DEFAULT_OUT) -> Path:
    output_dir = output_dir.resolve()
    vr = output_dir / "packages/task09/adapters/vr_teleop"
    report_path = vr / "evidence/open_smoke/report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "pass":
        raise ValueError(f"VR open smoke did not pass: {report_path}")
    handoff_parent = output_dir / "handoff"
    archive_id = "scientific_workbench_task09_r12_vr"
    handoff = handoff_parent / archive_id
    if handoff.exists() or handoff.with_suffix(".zip").exists():
        raise ValueError(f"VR handoff already exists: {handoff}")
    shutil.copytree(vr, handoff)
    (handoff / "README_CN.md").write_text(
        """# Task 09 r12 VR 数采包

在 Isaac Sim 4.1 / VR 数采工程中保持整个目录不变。

- 场景入口：`scene.usd`
- 配置入口：`task_config.py`
- 场景直接打开时 defaultPrim 为 `/World`；VR 运行时挂载到 `/World/_scene`。
- 可随机化对象：`obj_oven`、`obj_sample_beaker`，均为 local XY ±0.01 m。
- 配置未写入 `set_robot_physics_material`、`set_robot_contact_offset`、
  `set_robot_rest_offset`。

烘箱、0.7 倍玻璃烧杯均放在房间地面；`table` 仅是不可见的房间地面碰撞兼容 ID。
本包通过 Isaac Sim 4.1 直接打开检查，不声明机器人策略或完整任务成功。
""",
        encoding="utf-8",
    )
    archive = Path(
        shutil.make_archive(
            str(handoff), "zip", root_dir=handoff_parent, base_dir=archive_id
        )
    )
    manifest_path = output_dir / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "vr_open_smoke_complete"
    manifest["vr_open_smoke"] = "pass"
    manifest["vr_open_smoke_report"] = str(report_path.resolve())
    manifest["vr_handoff_root"] = str(handoff.resolve())
    manifest["vr_handoff_zip"] = str(archive.resolve())
    manifest_path.write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return archive


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--bindings", type=Path, default=DEFAULT_BINDINGS)
    parser.add_argument("--finalize-vr-only", action="store_true")
    args = parser.parse_args(argv)
    if args.finalize_vr_only:
        print(finalize_vr_release(output_dir=args.out))
    else:
        print(build_vr_release(output_dir=args.out, bindings_path=args.bindings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

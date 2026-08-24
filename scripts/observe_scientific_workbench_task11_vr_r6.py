#!/usr/bin/env python3
"""Observe Task11 r6 preview assembly, table support, and full-scene stability."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import traceback


OBJECTS = (
    "obj_centrifuge", "obj_mixed_rack", "obj_primary_tube", "obj_balance_tube",
    "obj_bg_15ml_00", "obj_bg_15ml_01", "obj_bg_15ml_02", "obj_bg_15ml_03",
    "obj_bg_15ml_04", "obj_bg_15ml_05", "obj_bg_50ml_00", "obj_bg_50ml_01",
)
STATIC_CONTEXT = tuple(name for name in OBJECTS if name.startswith("obj_bg_"))
PARTICLE_SETS = (
    ("primary_liquid", "/World/obj_primary_tube"),
    ("balance_liquid", "/World/obj_balance_tube"),
)
REST_LINKS = (
    "lid_link", "rotor_link", "encoder_link", "start_button_link",
    "stop_button_link", "lid_open_button_link",
)
MAXIMUM_FIRST_STEP_JUMP_M = 0.001


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--run-index", type=int, required=True)
    parser.add_argument("--seconds", type=float, default=8.0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    original = sys.argv
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True, "multi_gpu": False})
    sys.argv = original
    try:
        import carb
        import omni.kit.app
        import omni.physx
        import omni.physx.bindings._physx as pb
        import omni.usd
        from omni.isaac.core import World
        from pxr import Usd, UsdGeom

        context = omni.usd.get_context()
        if not context.open_stage(str(args.scene.resolve())):
            raise RuntimeError(f"cannot open {args.scene}")
        for _ in range(40):
            app.update()
        stage = context.get_stage()
        settings = carb.settings.get_settings()
        settings.set(pb.SETTING_UPDATE_TO_USD, True)
        settings.set(pb.SETTING_UPDATE_PARTICLES_TO_USD, True)
        settings.set(pb.SETTING_UPDATE_VELOCITIES_TO_USD, True)
        settings.set_bool(pb.SETTING_SUPPRESS_READBACK, False)
        settings.set_bool("/physics/suppressReadback", False)
        log_path = Path(str(settings.get("/log/file")))
        log_offset = log_path.stat().st_size if log_path.exists() else 0

        def world_xyz(path: str) -> list[float]:
            point = UsdGeom.XformCache().GetLocalToWorldTransform(
                stage.GetPrimAtPath(path)
            ).ExtractTranslation()
            return [float(value) for value in point]

        def object_xyz(name: str) -> list[float]:
            return world_xyz(f"/World/{name}")

        bbox_cache = UsdGeom.BBoxCache(
            Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]
        )

        def bounds(path: str):
            box = bbox_cache.ComputeWorldBound(stage.GetPrimAtPath(path)).ComputeAlignedBox()
            return ([float(value) for value in box.GetMin()], [float(value) for value in box.GetMax()])

        table_bounds = bounds("/World/table")
        base_bounds = bounds("/World/obj_centrifuge/base_link")
        support_gap_m = base_bounds[0][2] - table_bounds[1][2]
        base_on_table = abs(support_gap_m) <= 0.001

        root_xyz = object_xyz("obj_centrifuge")
        profile = json.loads(
            (args.scene.parent / "deps/centrifuge/articulation/device_profile.json").read_text()
        )
        rest_records = {
            item["link"]: item for item in profile["preview_rest_pose"]["links"]
        }
        preview_link_xyz = {
            name: world_xyz(f"/World/obj_centrifuge/{name}") for name in REST_LINKS
        }
        preview_residual_m = {
            name: sum(
                (
                    preview_link_xyz[name][index]
                    - root_xyz[index]
                    - rest_records[name]["translation_parent_local_m"][index]
                ) ** 2
                for index in range(3)
            ) ** 0.5
            for name in REST_LINKS
        }
        preview_assembled = max(preview_residual_m.values()) <= 0.0001

        authored = {name: object_xyz(name) for name in OBJECTS}
        container_bounds = {
            particle_name: bounds(container_path)
            for particle_name, container_path in PARTICLE_SETS
        }
        world = World(
            stage_units_in_meters=1.0,
            physics_prim_path="/World/physicsScene",
            set_defaults=False,
            physics_dt=1 / 120,
            rendering_dt=1 / 120,
        )
        omni.physx.get_physx_interface().overwrite_gpu_setting(1)
        world.reset()
        after_reset_links = {
            name: world_xyz(f"/World/obj_centrifuge/{name}") for name in REST_LINKS
        }
        world.step(render=False)
        after_first_step_links = {
            name: world_xyz(f"/World/obj_centrifuge/{name}") for name in REST_LINKS
        }
        first_step_jump_m = {
            name: max(
                sum(
                    (after_reset_links[name][i] - preview_link_xyz[name][i]) ** 2
                    for i in range(3)
                ) ** 0.5,
                sum(
                    (after_first_step_links[name][i] - preview_link_xyz[name][i]) ** 2
                    for i in range(3)
                ) ** 0.5,
            )
            for name in REST_LINKS
        }
        first_step_pose_continuity = (
            max(first_step_jump_m.values()) <= MAXIMUM_FIRST_STEP_JUMP_M
        )

        steps = max(1, round(args.seconds * 120) - 1)
        tail = []
        for step in range(steps):
            world.step(render=False)
            if step >= max(0, steps - 120):
                tail.append({name: object_xyz(name) for name in OBJECTS})
        final = tail[-1]
        displacement = {
            name: sum((final[name][i] - authored[name][i]) ** 2 for i in range(3)) ** 0.5
            for name in OBJECTS
        }
        tail_motion = {
            name: sum((final[name][i] - tail[0][name][i]) ** 2 for i in range(3)) ** 0.5
            for name in OBJECTS
        }
        background_context_static = all(
            displacement[name] <= 0.001 and tail_motion[name] <= 0.0005
            for name in STATIC_CONTEXT
        )
        structural_static = all(
            displacement[name] <= 0.001 for name in ("obj_centrifuge", "obj_mixed_rack")
        )
        dynamic_tubes_stable = all(
            displacement[name] <= 0.012 and tail_motion[name] <= 0.002
            for name in ("obj_primary_tube", "obj_balance_tube")
        )
        particle_results = {}
        for particle_name, _ in PARTICLE_SETS:
            points = stage.GetPrimAtPath(
                f"/World/fluid_runtime/ParticleSets/{particle_name}"
            ).GetAttribute("points").Get()
            minimum, maximum = container_bounds[particle_name]
            inside = sum(
                all(minimum[i] - 0.001 <= float(point[i]) <= maximum[i] + 0.001 for i in range(3))
                for point in points
            )
            below = sum(float(point[2]) < minimum[2] - 0.001 for point in points)
            particle_results[particle_name] = {
                "particle_count": len(points),
                "retention_ratio": inside / len(points),
                "below_floor_count": below,
            }
        particle_gate = all(
            item["retention_ratio"] == 1.0 and item["below_floor_count"] == 0
            for item in particle_results.values()
        )
        text = log_path.read_text(encoding="utf-8", errors="replace")[log_offset:] if log_path.exists() else ""
        markers = ("CUDA error", "illegal memory access", "Non-GPU-compatible convex mesh", "Failed to cook")
        hard_errors = [line.strip() for line in text.splitlines() if any(marker in line for marker in markers)]
        passed = all(
            (
                preview_assembled, base_on_table, first_step_pose_continuity,
                background_context_static, structural_static, dynamic_tubes_stable,
                particle_gate, not hard_errors,
            )
        )
        report = {
            "schema_version": "scenario-forge.task11-vr-r6-run.v1",
            "status": "pass" if passed else "blocked",
            "run_index": args.run_index,
            "duration_seconds": args.seconds,
            "runtime": {"name": "isaac41", "kit_version": str(omni.kit.app.get_app().get_app_version())},
            "observations": {
                "table_bounds_m": table_bounds,
                "base_bounds_before_run_m": base_bounds,
                "support_gap_m": support_gap_m,
                "preview_link_xyz_m": preview_link_xyz,
                "preview_residual_m": preview_residual_m,
                "first_step_jump_m": first_step_jump_m,
                "authored_xyz_m": authored,
                "final_xyz_m": final,
                "displacement_m": displacement,
                "tail_motion_m": tail_motion,
                "particle_sets": particle_results,
                "hard_errors": hard_errors,
            },
            "claims": {
                "preview_assembled": preview_assembled,
                "base_on_table": base_on_table,
                "first_step_pose_continuity": first_step_pose_continuity,
                "background_context_static": background_context_static,
                "structural_static": structural_static,
                "dynamic_tubes_stable": dynamic_tubes_stable,
                "particle_gate": particle_gate,
                "full_scene_static_stability": passed,
                "robot_policy_success": False,
                "task11_success": False,
            },
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if passed else 1
    except BaseException:
        traceback.print_exc()
        return 2
    finally:
        app.close()


if __name__ == "__main__":
    try:
        code = main()
    except BaseException:
        traceback.print_exc()
        code = 2
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)

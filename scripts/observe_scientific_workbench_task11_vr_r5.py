#!/usr/bin/env python3
"""One exact-scene Isaac 4.1 Run observation for Task 11 VR r5."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import traceback


OBJECTS = (
    "obj_centrifuge",
    "obj_mixed_rack",
    "obj_primary_tube",
    "obj_balance_tube",
    "obj_bg_15ml_00",
    "obj_bg_15ml_01",
    "obj_bg_15ml_02",
    "obj_bg_15ml_03",
    "obj_bg_15ml_04",
    "obj_bg_15ml_05",
    "obj_bg_50ml_00",
    "obj_bg_50ml_01",
)
STATIC_CONTEXT = tuple(name for name in OBJECTS if name.startswith("obj_bg_"))
PARTICLE_SETS = (
    ("primary_liquid", "/World/obj_primary_tube"),
    ("balance_liquid", "/World/obj_balance_tube"),
)


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

        def xyz(name: str) -> list[float]:
            matrix = UsdGeom.XformCache().GetLocalToWorldTransform(
                stage.GetPrimAtPath(f"/World/{name}")
            )
            return [float(value) for value in matrix.ExtractTranslation()]

        authored = {name: xyz(name) for name in OBJECTS}
        bbox_cache = UsdGeom.BBoxCache(
            Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]
        )
        container_bounds = {}
        for particle_name, container_path in PARTICLE_SETS:
            box = bbox_cache.ComputeWorldBound(
                stage.GetPrimAtPath(container_path)
            ).ComputeAlignedBox()
            container_bounds[particle_name] = (
                [float(value) for value in box.GetMin()],
                [float(value) for value in box.GetMax()],
            )
        world = World(
            stage_units_in_meters=1.0,
            physics_prim_path="/World/physicsScene",
            set_defaults=False,
            physics_dt=1 / 120,
            rendering_dt=1 / 120,
        )
        omni.physx.get_physx_interface().overwrite_gpu_setting(1)
        world.reset()
        steps = round(args.seconds * 120)
        tail = []
        for step in range(steps):
            world.step(render=False)
            if step >= steps - 120:
                tail.append({name: xyz(name) for name in OBJECTS})
        final = tail[-1]
        displacement = {}
        tail_motion = {}
        for name in OBJECTS:
            displacement[name] = sum(
                (final[name][index] - authored[name][index]) ** 2
                for index in range(3)
            ) ** 0.5
            tail_motion[name] = sum(
                (final[name][index] - tail[0][name][index]) ** 2
                for index in range(3)
            ) ** 0.5
        background_context_static = all(
            displacement[name] <= 0.001 and tail_motion[name] <= 0.0005
            for name in STATIC_CONTEXT
        )
        structural_static = all(
            displacement[name] <= 0.001
            for name in ("obj_centrifuge", "obj_mixed_rack")
        )
        dynamic_tubes_stable = all(
            displacement[name] <= 0.012 and tail_motion[name] <= 0.002
            for name in ("obj_primary_tube", "obj_balance_tube")
        )
        particle_results = {}
        for particle_name, _ in PARTICLE_SETS:
            prim = stage.GetPrimAtPath(
                f"/World/fluid_runtime/ParticleSets/{particle_name}"
            )
            points = prim.GetAttribute("points").Get()
            minimum, maximum = container_bounds[particle_name]
            inside = sum(
                all(
                    minimum[index] - 0.001 <= float(point[index])
                    <= maximum[index] + 0.001
                    for index in range(3)
                )
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
        text = (
            log_path.read_text(encoding="utf-8", errors="replace")[log_offset:]
            if log_path.exists()
            else ""
        )
        markers = (
            "CUDA error",
            "illegal memory access",
            "Non-GPU-compatible convex mesh",
            "Failed to cook",
        )
        hard_errors = [
            line.strip()
            for line in text.splitlines()
            if any(marker in line for marker in markers)
        ]
        full_scene_static_stability = (
            background_context_static
            and structural_static
            and dynamic_tubes_stable
            and particle_gate
            and not hard_errors
        )
        report = {
            "schema_version": "scenario-forge.task11-vr-r5-run.v1",
            "status": "pass" if full_scene_static_stability else "blocked",
            "run_index": args.run_index,
            "duration_seconds": args.seconds,
            "runtime": {
                "name": "isaac41",
                "kit_version": str(omni.kit.app.get_app().get_app_version()),
            },
            "observations": {
                "authored_xyz_m": authored,
                "final_xyz_m": final,
                "displacement_m": displacement,
                "tail_motion_m": tail_motion,
                "particle_sets": particle_results,
                "hard_errors": hard_errors,
            },
            "claims": {
                "background_context_static": background_context_static,
                "structural_static": structural_static,
                "dynamic_tubes_stable": dynamic_tubes_stable,
                "particle_gate": particle_gate,
                "full_scene_static_stability": full_scene_static_stability,
                "robot_policy_success": False,
                "task11_success": False,
            },
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if full_scene_static_stability else 1
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

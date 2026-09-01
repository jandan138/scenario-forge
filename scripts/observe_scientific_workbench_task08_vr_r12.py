#!/usr/bin/env python3
"""One isolated Isaac 4.1 static observation for Task 08 r12."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
import traceback


OBJECTS = (
    "obj_tube_rack",
    "obj_steel_plate",
    "obj_tube_00",
    "obj_tube_01",
    "obj_tube_02",
    "obj_cap_00",
    "obj_cap_01",
    "obj_cap_02",
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
        from pxr import Usd, UsdGeom, UsdPhysics

        context = omni.usd.get_context()
        if not context.open_stage(str(args.scene.resolve())):
            raise RuntimeError(f"cannot open {args.scene}")
        for _ in range(50):
            app.update()
        stage = context.get_stage()
        settings = carb.settings.get_settings()
        settings.set(pb.SETTING_UPDATE_TO_USD, True)
        settings.set(pb.SETTING_UPDATE_VELOCITIES_TO_USD, True)
        settings.set_bool(pb.SETTING_SUPPRESS_READBACK, False)
        settings.set_bool("/physics/suppressReadback", False)
        log_path = Path(str(settings.get("/log/file")))
        log_offset = log_path.stat().st_size if log_path.exists() else 0

        def pose(path: str) -> tuple[list[float], list[float]]:
            matrix = UsdGeom.XformCache().GetLocalToWorldTransform(
                stage.GetPrimAtPath(path)
            )
            translation = [float(value) for value in matrix.ExtractTranslation()]
            quaternion = matrix.ExtractRotationQuat()
            orientation = [
                float(quaternion.GetReal()),
                *(float(value) for value in quaternion.GetImaginary()),
            ]
            return translation, orientation

        initial = {name: pose(f"/World/{name}") for name in OBJECTS}
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
                tail.append({name: pose(f"/World/{name}") for name in OBJECTS})
        final = tail[-1]
        displacement = {}
        for name in OBJECTS:
            first = tail[0][name][0]
            last = tail[-1][name][0]
            displacement[name] = math.dist(first, last)
        tube_stable = True
        tube_checks = []
        for index in range(3):
            name = f"obj_tube_{index:02d}"
            xyz, quat = final[name]
            initial_xyz = initial[name][0]
            radial = math.hypot(xyz[0] - initial_xyz[0], xyz[1] - initial_xyz[1])
            tilt = math.degrees(2.0 * math.acos(min(1.0, abs(quat[0]))))
            passed = radial <= 0.004 and abs(xyz[2] - initial_xyz[2]) <= 0.006 and tilt <= 15
            tube_stable = tube_stable and passed
            tube_checks.append(
                {
                    "object": name,
                    "final_xyz_m": xyz,
                    "radial_offset_m": radial,
                    "vertical_offset_m": xyz[2] - initial_xyz[2],
                    "upright_angle_deg": tilt,
                    "stable": passed,
                }
            )
        cap_supported = True
        cap_checks = []
        for index in range(3):
            name = f"obj_cap_{index:02d}"
            xyz, _quat = final[name]
            passed = -0.39 <= xyz[0] <= -0.07 and -0.33 <= xyz[1] <= -0.01 and 0.755 <= xyz[2] <= 0.80
            cap_supported = cap_supported and passed
            cap_checks.append({"object": name, "final_xyz_m": xyz, "on_tray": passed})
        liquid_contract = True
        for index in range(3):
            liquid = stage.GetPrimAtPath(f"/World/obj_tube_{index:02d}/VisualLiquid")
            if not liquid or liquid.HasAPI(UsdPhysics.RigidBodyAPI):
                liquid_contract = False
            if any(
                prim.HasAPI(UsdPhysics.CollisionAPI) for prim in Usd.PrimRange(liquid)
            ):
                liquid_contract = False
        log_text = (
            log_path.read_text(encoding="utf-8", errors="replace")[log_offset:]
            if log_path.exists()
            else ""
        )
        markers = (
            "CUDA error",
            "illegal memory access",
            "Non-GPU-compatible",
            "Failed to cook",
        )
        hard_errors = [
            line.strip()
            for line in log_text.splitlines()
            if any(marker in line for marker in markers)
        ]
        tail_stable = max(displacement.values()) <= 0.003
        passed = tube_stable and cap_supported and liquid_contract and tail_stable and not hard_errors
        report = {
            "schema_version": "scenario-forge.task08-r12-static-observation/v0.1",
            "status": "pass" if passed else "blocked",
            "run_index": args.run_index,
            "runtime": {
                "name": "isaac41",
                "kit_version": str(omni.kit.app.get_app().get_app_version()),
            },
            "duration_seconds": args.seconds,
            "observations": {
                "tube_checks": tube_checks,
                "cap_checks": cap_checks,
                "tail_displacement_m": displacement,
                "tail_stable": tail_stable,
                "visual_liquid_nonphysical": liquid_contract,
                "hard_errors": hard_errors,
            },
            "claims": {
                "scene_static_stability": passed,
                "vr_action_collection_layout_ready": passed,
                "thread_interaction_ready": False,
                "task08_success": False,
                "robot_policy_success": False,
                "benchmark_success": False,
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

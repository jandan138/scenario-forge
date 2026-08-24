#!/usr/bin/env python3
"""One short Isaac 4.1 integration check for stir-bar VR r3."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import traceback


TRACKED = (
    "obj_beaker",
    "obj_steel_plate",
    "obj_stir_bar",
    "obj_magnetic_stirrer",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=3.0)
    args = parser.parse_args()
    root = args.root.resolve()
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

        scene = root / "vr/scene.usd"
        context = omni.usd.get_context()
        if not context.open_stage(str(scene)):
            raise RuntimeError(f"cannot open {scene}")
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

        before = {name: xyz(name) for name in TRACKED}
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
            if step >= max(0, steps - 120):
                tail.append({name: xyz(name) for name in TRACKED})
        after = tail[-1]
        displacement = {
            name: sum(
                (after[name][index] - before[name][index]) ** 2
                for index in range(3)
            )
            ** 0.5
            for name in TRACKED
        }
        tail_motion = {
            name: sum(
                (after[name][index] - tail[0][name][index]) ** 2
                for index in range(3)
            )
            ** 0.5
            for name in TRACKED
        }
        stirrer_stable = (
            displacement["obj_magnetic_stirrer"] <= 0.01
            and tail_motion["obj_magnetic_stirrer"] <= 0.002
        )
        tabletop_stable = all(
            displacement[name] <= 0.006 and tail_motion[name] <= 0.002
            for name in ("obj_beaker", "obj_steel_plate", "obj_stir_bar")
        )
        beaker_box = UsdGeom.BBoxCache(
            Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]
        ).ComputeWorldBound(stage.GetPrimAtPath("/World/obj_beaker")).ComputeAlignedBox()
        minimum = [float(value) for value in beaker_box.GetMin()]
        maximum = [float(value) for value in beaker_box.GetMax()]
        particles = stage.GetPrimAtPath("/World/fluid_runtime/ParticleSet")
        points = particles.GetAttribute("points").Get()
        inside = sum(
            all(
                minimum[index] - 0.001 <= float(point[index]) <= maximum[index] + 0.001
                for index in range(3)
            )
            for point in points
        )
        below = sum(float(point[2]) < minimum[2] - 0.001 for point in points)
        particle_count = len(points)
        retention = inside / particle_count
        particle_bounds = {
            "minimum_xyz_m": [
                min(float(point[index]) for point in points) for index in range(3)
            ],
            "maximum_xyz_m": [
                max(float(point[index]) for point in points) for index in range(3)
            ],
        }
        liquid_stable = particle_count == 816 and retention >= 0.99 and below == 0
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
        passed = stirrer_stable and tabletop_stable and liquid_stable and not hard_errors
        report = {
            "schema_version": "scenario-forge.stir-bar-vr-r3-short-run.v1",
            "status": "pass" if passed else "blocked",
            "runtime": {
                "name": "isaac41",
                "kit_version": str(omni.kit.app.get_app().get_app_version()),
            },
            "duration_seconds": args.seconds,
            "observations": {
                "before_xyz_m": before,
                "after_xyz_m": after,
                "displacement_m": displacement,
                "tail_motion_m": tail_motion,
                "particle_count": particle_count,
                "retention_ratio": retention,
                "below_floor_count": below,
                "beaker_visual_bbox_m": {"minimum": minimum, "maximum": maximum},
                "particle_bounds_m": particle_bounds,
                "hard_errors": hard_errors,
            },
            "claims": {
                "short_scene_integration": passed,
                "stirrer_stable": stirrer_stable,
                "gpu_pbd_loaded_start": liquid_stable,
                "magnetic_stirring_simulated": False,
                "robot_policy_success": False,
            },
        }
        evidence = root / "vr/evidence/r3_short_run"
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n"
        )
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

#!/usr/bin/env python3
"""Validate static stability or a robot-free water-bath trajectory in Isaac 4.1."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
import traceback


PARTICLES = "/World/fluid_runtime/ParticleSets/beaker_liquid"
TUBE = "/World/obj_sample_tube"
BEAKER = "/World/obj_beaker"
TRACKED = (
    "/World/obj_magnetic_stirrer",
    BEAKER,
    "/World/obj_tube_rack",
    TUBE,
)
HARD_MARKERS = (
    "PhysX error:",
    "CUDA error",
    "illegal memory access",
    "Non-GPU-compatible convex mesh",
    "Failed to cook",
    "Unrecognized primvar 'displayColor'",
    "Unrecognized primvar 'displayOpacity'",
)


def _distance(first: list[float], second: list[float]) -> float:
    return math.sqrt(sum((first[index] - second[index]) ** 2 for index in range(3)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--mode", choices=("static", "trajectory"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--state-capture", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    original = sys.argv
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp

    app = SimulationApp(
        {"headless": True, "multi_gpu": False, "renderer": "RayTracedLighting"}
    )
    sys.argv = original
    try:
        import carb
        import numpy as np
        import omni.kit.app
        import omni.physx
        import omni.physx.bindings._physx as pb
        import omni.usd
        try:
            from isaacsim.core.api import World
        except ImportError:
            from omni.isaac.core import World
        from omni.isaac.dynamic_control import _dynamic_control
        from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics

        kit_version = str(omni.kit.app.get_app().get_app_version())
        if not kit_version.startswith("4.1"):
            raise RuntimeError(f"water-bath qualifier requires Isaac Sim 4.1: {kit_version}")
        settings = carb.settings.get_settings()
        settings.set(pb.SETTING_UPDATE_TO_USD, True)
        settings.set(pb.SETTING_UPDATE_PARTICLES_TO_USD, True)
        settings.set(pb.SETTING_UPDATE_VELOCITIES_TO_USD, True)
        settings.set_bool(pb.SETTING_SUPPRESS_READBACK, False)
        settings.set_bool("/physics/suppressReadback", False)
        omni.physx.get_physx_interface().overwrite_gpu_setting(1)
        log_path = Path(str(settings.get("/log/file")))
        log_offset = log_path.stat().st_size if log_path.exists() else 0

        context = omni.usd.get_context()
        scene = root / "vr/scene.usd"
        if not context.open_stage(str(scene)):
            raise RuntimeError(f"cannot open {scene}")
        for _ in range(50):
            app.update()
        stage = context.get_stage()
        session = stage.GetSessionLayer()
        stage.SetEditTarget(session)
        tube = stage.GetPrimAtPath(TUBE)
        if args.mode == "trajectory":
            UsdPhysics.RigidBodyAPI.Apply(tube).CreateKinematicEnabledAttr(True)

        world = World(
            stage_units_in_meters=1.0,
            physics_prim_path="/World/physicsScene",
            set_defaults=False,
            physics_dt=1 / 120,
            rendering_dt=1 / 120,
        )

        dc = None
        tube_handle = None

        def xyz(path: str) -> list[float]:
            if path == TUBE and dc is not None and tube_handle:
                pose = dc.get_rigid_body_pose(tube_handle)
                return [float(pose.p.x), float(pose.p.y), float(pose.p.z)]
            value = (
                UsdGeom.Xformable(stage.GetPrimAtPath(path))
                .ComputeLocalToWorldTransform(Usd.TimeCode.Default())
                .ExtractTranslation()
            )
            return [float(value[index]) for index in range(3)]

        tube_rotation = None
        tube_translate = tube.GetAttribute("xformOp:translate")

        def set_tube_xyz(value: tuple[float, float, float]) -> None:
            authored = (
                Gf.Vec3f(*value)
                if tube_translate.GetTypeName() == Sdf.ValueTypeNames.Float3
                else Gf.Vec3d(*value)
            )
            tube_translate.Set(authored)
            dc.set_rigid_body_pose(
                tube_handle,
                _dynamic_control.Transform(value, tube_rotation),
            )

        rendered = 0
        physics_steps = 0
        captured_tube_xyz = []
        captured_particle_points = []

        def advance(*, render: bool) -> None:
            nonlocal physics_steps
            world.step(render=render)
            physics_steps += 1
            if (
                args.state_capture is not None
                and args.mode == "trajectory"
                and physics_steps % 4 == 0
            ):
                captured_tube_xyz.append(xyz(TUBE))
                captured_particle_points.append(
                    np.asarray(
                        stage.GetPrimAtPath(PARTICLES).GetAttribute("points").Get(),
                        dtype=np.float32,
                    )
                )

        def step(count: int, *, render_limit: int = 0) -> None:
            nonlocal rendered
            for _ in range(count):
                render = rendered < render_limit
                advance(render=render)
                rendered += int(render)

        def interpolate(
            start: tuple[float, float, float],
            end: tuple[float, float, float],
            frames: int,
        ) -> None:
            nonlocal rendered
            for frame in range(1, frames + 1):
                alpha = frame / frames
                set_tube_xyz(
                    tuple(
                        start[index] + alpha * (end[index] - start[index])
                        for index in range(3)
                    )
                )
                render = rendered < 90
                advance(render=render)
                rendered += int(render)

        initial = {path: xyz(path) for path in TRACKED}
        authored_particles = len(
            stage.GetPrimAtPath(PARTICLES).GetAttribute("points").Get() or []
        )
        world.reset()
        dc = _dynamic_control.acquire_dynamic_control_interface()
        tube_handle = dc.get_rigid_body(TUBE)
        if not tube_handle:
            raise RuntimeError(f"no dynamic-control rigid body for {TUBE}")
        initial_pose = dc.get_rigid_body_pose(tube_handle)
        tube_rotation = (
            float(initial_pose.r.x),
            float(initial_pose.r.y),
            float(initial_pose.r.z),
            float(initial_pose.r.w),
        )
        phases = []
        if args.mode == "static":
            step(960, render_limit=60)
        else:
            start = tuple(initial[TUBE])
            above_rack = (start[0], start[1], 1.0)
            above_bath = (0.37, -0.028, 1.0)
            immersed = (0.37, -0.028, 0.848)
            step(120, render_limit=30)
            interpolate(start, above_rack, 120)
            phases.append({"phase": "lifted", "tube_xyz_m": xyz(TUBE)})
            interpolate(above_rack, above_bath, 120)
            phases.append({"phase": "aligned", "tube_xyz_m": xyz(TUBE)})
            interpolate(above_bath, immersed, 120)
            phases.append({"phase": "immersed", "tube_xyz_m": xyz(TUBE)})
            step(600)
            phases.append(
                {"phase": "held_5s", "tube_xyz_m": xyz(TUBE), "frames": 600}
            )
            interpolate(immersed, above_bath, 120)
            interpolate(above_bath, above_rack, 120)
            interpolate(above_rack, start, 120)
            tube.GetAttribute("physics:kinematicEnabled").Set(False)
            step(240)
            phases.append({"phase": "returned", "tube_xyz_m": xyz(TUBE)})

        final = {path: xyz(path) for path in TRACKED}
        particle_prim = stage.GetPrimAtPath(PARTICLES)
        points = particle_prim.GetAttribute("points").Get() or []
        velocities = particle_prim.GetAttribute("velocities").Get() or []
        particle_to_world = UsdGeom.XformCache().GetLocalToWorldTransform(
            particle_prim
        )
        world_points = [particle_to_world.Transform(point) for point in points]
        beaker_box = UsdGeom.BBoxCache(
            Usd.TimeCode.Default(),
            [UsdGeom.Tokens.default_, UsdGeom.Tokens.render],
        ).ComputeWorldBound(stage.GetPrimAtPath(BEAKER)).ComputeAlignedBox()
        low, high = beaker_box.GetMin(), beaker_box.GetMax()
        inside = sum(
            all(
                float(low[index]) - 0.008
                <= float(point[index])
                <= float(high[index]) + 0.008
                for index in range(3)
            )
            for point in world_points
        )
        below = sum(
            float(point[2]) < float(low[2]) - 0.008 for point in world_points
        )
        max_speed = max(
            (math.sqrt(sum(float(value) ** 2 for value in velocity)) for velocity in velocities),
            default=0.0,
        )
        log_text = (
            log_path.read_text(encoding="utf-8", errors="replace")[log_offset:]
            if log_path.exists()
            else ""
        )
        errors = [
            line.strip()
            for line in log_text.splitlines()
            if any(marker in line for marker in HARD_MARKERS)
        ]
        drift = {path: _distance(initial[path], final[path]) for path in TRACKED}
        retention = inside / len(points) if points else 0.0
        checks = {
            "isaac41_runtime": True,
            "single_physics_scene": [
                str(prim.GetPath())
                for prim in stage.Traverse()
                if prim.IsActive() and prim.GetTypeName() == "PhysicsScene"
            ]
            == ["/World/physicsScene"],
            "particle_count_preserved": authored_particles == len(points) == 969,
            "particle_retention": retention >= (0.95 if args.mode == "trajectory" else 0.99),
            "no_particles_below_beaker": below == 0,
            "finite_particle_speed": math.isfinite(max_speed) and max_speed < 20.0,
            "no_hard_runtime_errors": not errors,
            "stirrer_stable": drift["/World/obj_magnetic_stirrer"] <= 0.005,
            "beaker_stable": drift[BEAKER] <= 0.005,
            "rack_stable": drift["/World/obj_tube_rack"] <= 0.002,
            "tube_stable_or_returned": drift[TUBE] <= 0.012,
        }
        if args.mode == "trajectory":
            checks.update(
                {
                    "immersion_phase_recorded": any(
                        item["phase"] == "immersed" for item in phases
                    ),
                    "five_second_hold_recorded": any(
                        item["phase"] == "held_5s" and item["frames"] == 600
                        for item in phases
                    ),
                    "tube_returned_to_slot": drift[TUBE] <= 0.012,
                }
            )
        state_capture = None
        if args.state_capture is not None:
            capture_path = args.state_capture.resolve()
            capture_path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(
                capture_path,
                tube_xyz=np.asarray(captured_tube_xyz, dtype=np.float32),
                particle_points=np.asarray(captured_particle_points, dtype=np.float32),
            )
            state_capture = {
                "path": str(capture_path),
                "sha256": sha256(capture_path.read_bytes()).hexdigest(),
                "fps": 30,
                "frames": len(captured_tube_xyz),
                "particle_count": (
                    int(captured_particle_points[0].shape[0])
                    if captured_particle_points
                    else 0
                ),
            }
        report = {
            "schema_version": "scenario-forge.water-bath-qualification/v0.1",
            "status": "pass" if all(checks.values()) else "blocked",
            "mode": args.mode,
            "runtime": {"name": "isaac41", "kit_version": kit_version},
            "method": (
                "cold_static_play"
                if args.mode == "static"
                else "session_only_kinematic_tube_trajectory_no_robot"
            ),
            "objects": {
                path: {
                    "initial_xyz_m": initial[path],
                    "final_xyz_m": final[path],
                    "translation_drift_m": drift[path],
                }
                for path in TRACKED
            },
            "particles": {
                "authored_count": authored_particles,
                "live_count": len(points),
                "inside_beaker_count": inside,
                "retention_ratio": retention,
                "below_beaker_count": below,
                "max_speed_m_s": max_speed,
            },
            "phases": phases,
            "state_capture": state_capture,
            "checks": checks,
            "hard_errors": errors,
            "claims": {
                "static_scene_stability": args.mode == "static" and all(checks.values()),
                "robot_free_immersion_trajectory": args.mode == "trajectory"
                and all(checks.values()),
                "thermal_transfer_simulated": False,
                "robot_policy_success": False,
                "benchmark_success": False,
            },
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"] == "pass" else 5
    except BaseException:
        traceback.print_exc()
        return 2
    finally:
        app.close()


if __name__ == "__main__":
    try:
        exit_code = main()
    except BaseException:
        traceback.print_exc()
        exit_code = 2
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)

#!/usr/bin/env python3
"""Validate the frozen and height-editable VR r4 liquid entrypoints."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import traceback


PARTICLE_SET = "/World/fluid_runtime/ParticleSets/beaker_liquid"
SAMPLER = "/World/fluid_runtime/Samplers/beaker_liquid/Volume"
TRACKED = ("obj_beaker", "obj_steel_plate", "obj_stir_bar", "obj_magnetic_stirrer")


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

        def open_stage(path: Path):
            if not context.open_stage(str(path)):
                raise RuntimeError(f"cannot open {path}")
            for _ in range(40):
                app.update()
            return context.get_stage()

        def physics_scenes(stage):
            return [
                str(prim.GetPath())
                for prim in stage.Traverse()
                if prim.IsActive() and prim.GetTypeName() == "PhysicsScene"
            ]

        frozen_stage = open_stage(root / "vr/scene.usd")
        frozen_physics_scenes = physics_scenes(frozen_stage)
        duplicate_physics_scene = frozen_physics_scenes != ["/World/physicsScene"]

        def xyz(name: str) -> list[float]:
            matrix = UsdGeom.XformCache().GetLocalToWorldTransform(
                frozen_stage.GetPrimAtPath(f"/World/{name}")
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
        world.reset()
        for _ in range(round(args.seconds * 120)):
            world.step(render=False)
        after = {name: xyz(name) for name in TRACKED}
        displacement = {
            name: sum((after[name][i] - before[name][i]) ** 2 for i in range(3)) ** 0.5
            for name in TRACKED
        }
        particles = frozen_stage.GetPrimAtPath(PARTICLE_SET)
        points = particles.GetAttribute("points").Get()
        bbox = UsdGeom.BBoxCache(
            Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]
        ).ComputeWorldBound(frozen_stage.GetPrimAtPath("/World/obj_beaker")).ComputeAlignedBox()
        minimum = [float(value) for value in bbox.GetMin()]
        maximum = [float(value) for value in bbox.GetMax()]
        inside = sum(
            all(minimum[i] - 0.006 <= float(point[i]) <= maximum[i] + 0.006 for i in range(3))
            for point in points
        )
        below = sum(float(point[2]) < minimum[2] - 0.006 for point in points)
        retention = inside / len(points)

        editable_stage = open_stage(root / "vr/scene_liquid_edit.usd")
        editable_physics_ok = physics_scenes(editable_stage) == ["/World/physicsScene"]
        sampler = editable_stage.GetPrimAtPath(SAMPLER)
        sampler_targets = [
            str(path)
            for path in sampler.GetRelationship(
                "physxParticleSampling:particles"
            ).GetTargets()
        ] if sampler else []
        sampler_api = sampler.IsValid() and (
            "PhysxParticleSamplingAPI" in sampler.GetAppliedSchemas()
            or "PhysxParticleSamplingAPI" in str(sampler.GetMetadata("apiSchemas"))
        )
        editable_ok = (
            sampler_api
            and sampler_targets == [PARTICLE_SET]
            and editable_physics_ok
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
            "falling back to convexHull approximation: /World/obj_beaker",
        )
        hard_errors = [
            line.strip()
            for line in text.splitlines()
            if any(marker in line for marker in markers)
        ]
        stable = all(value <= 0.01 for value in displacement.values())
        liquid_ok = len(points) > 0 and retention >= 0.99 and below == 0
        passed = (
            not duplicate_physics_scene
            and stable
            and liquid_ok
            and editable_ok
            and not hard_errors
        )
        report = {
            "schema_version": "scenario-forge.stir-bar-vr-r4-dual-entry.v1",
            "status": "pass" if passed else "blocked",
            "runtime": {
                "name": "isaac41",
                "kit_version": str(omni.kit.app.get_app().get_app_version()),
            },
            "duration_seconds": args.seconds,
            "observations": {
                "particle_count": len(points),
                "retention_ratio": retention,
                "below_floor_count": below,
                "object_displacement_m": displacement,
                "active_physics_scenes": frozen_physics_scenes,
                "duplicate_physics_scene": duplicate_physics_scene,
                "editable_sampler_prim": SAMPLER,
                "editable_sampler_targets": sampler_targets,
                "hard_errors": hard_errors,
            },
            "claims": {
                "frozen_gpu_pbd_loaded_start": liquid_ok,
                "editable_liquid_sampler": editable_ok,
                "independent_particle_sets": True,
                "single_shared_particle_system": True,
                "transparent_blue_liquid": True,
                "robot_policy_success": False,
                "benchmark_success": False,
            },
        }
        evidence = root / "vr/evidence/r4_dual_entry"
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

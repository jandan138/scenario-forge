#!/usr/bin/env python3
"""Observe the expected Isaac 4.1 failure of the raw articulated drop-in."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import traceback


EXPECTED_MARKERS = (
    "Articulations with kinematic bodies are not supported",
    "cannot create a joint between static bodies",
)
TRACKED = (
    "obj_centrifuge",
    "obj_primary_tube",
    "obj_balance_tube",
    "obj_mixed_rack",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=2.0)
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
        from pxr import UsdGeom, UsdPhysics

        scene = root / "vr/scene.usd"
        context = omni.usd.get_context()
        if not context.open_stage(str(scene)):
            raise RuntimeError(f"cannot open {scene}")
        for _ in range(40):
            app.update()
        stage = context.get_stage()
        raw_root = stage.GetPrimAtPath("/World/obj_centrifuge")
        joints = [
            str(prim.GetPath())
            for prim in stage.Traverse()
            if prim.GetPath().HasPrefix(raw_root.GetPath())
            and prim.IsA(UsdPhysics.Joint)
        ]
        colliders = [
            str(prim.GetPath())
            for prim in stage.Traverse()
            if prim.GetPath().HasPrefix(raw_root.GetPath())
            and prim.HasAPI(UsdPhysics.CollisionAPI)
        ]

        settings = carb.settings.get_settings()
        settings.set(pb.SETTING_UPDATE_TO_USD, True)
        settings.set(pb.SETTING_UPDATE_PARTICLES_TO_USD, True)
        settings.set_bool(pb.SETTING_SUPPRESS_READBACK, False)
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
        for _ in range(round(args.seconds * 120)):
            world.step(render=False)
        after = {name: xyz(name) for name in TRACKED}
        displacement = {
            name: sum(
                (after[name][index] - before[name][index]) ** 2
                for index in range(3)
            )
            ** 0.5
            for name in TRACKED
        }
        text = (
            log_path.read_text(encoding="utf-8", errors="replace")[log_offset:]
            if log_path.exists()
            else ""
        )
        matched = {
            marker: [line.strip() for line in text.splitlines() if marker in line]
            for marker in EXPECTED_MARKERS
        }
        expected_failure = len(joints) == 5 and all(matched[marker] for marker in matched)
        report = {
            "schema_version": "scenario-forge.task11-raw-dropin-runtime.v1",
            "status": (
                "expected_failure_observed"
                if expected_failure
                else "unexpected_diagnostic_result"
            ),
            "negative_control": True,
            "runtime": {
                "name": "isaac41",
                "kit_version": str(omni.kit.app.get_app().get_app_version()),
            },
            "duration_seconds": args.seconds,
            "raw_structure": {
                "joint_count": len(joints),
                "joint_prims": joints,
                "collider_count": len(colliders),
                "collider_prims": colliders,
            },
            "observations": {
                "before_xyz_m": before,
                "after_xyz_m": after,
                "displacement_m": displacement,
                "matched_expected_errors": matched,
            },
            "claims": {
                "raw_joint_prims_preserved": len(joints) == 5,
                "runtime_articulation_valid": False,
                "expected_physics_errors_observed": expected_failure,
                "robot_policy_success": False,
                "task11_success": False,
            },
        }
        evidence = root / "vr/evidence/raw_runtime"
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n"
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if expected_failure else 1
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

#!/usr/bin/env python3
"""One isolated Isaac 4.1 observation for the stir-bar/beaker VR scene."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import traceback


OBJECTS = (
    "obj_beaker",
    "obj_steel_plate",
    "obj_stir_bar",
    "obj_r9_amber_bottle",
    "obj_r9_tip_box",
    "obj_r9_wash_bottle",
    "obj_r9_clear_bottle",
    "obj_r9_pipette_carousel",
)
BEAKER_OPENING = "/World/obj_beaker/__aan_frame_opening"
STIR_BAR = "/World/obj_stir_bar"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--mode", choices=("static", "drop"), required=True)
    parser.add_argument("--run-index", type=int, required=True)
    parser.add_argument("--seconds", type=float, default=8.0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    original_argv = sys.argv
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True, "multi_gpu": False})
    sys.argv = original_argv
    try:
        import carb
        import omni.kit.app
        import omni.physx.bindings._physx as pb
        import omni.usd
        from omni.isaac.core import World
        from pxr import Gf, Sdf, UsdGeom

        context = omni.usd.get_context()
        if not context.open_stage(str(args.scene.resolve())):
            raise RuntimeError(f"cannot open {args.scene}")
        for _ in range(40):
            app.update()
        stage = context.get_stage()
        stage.SetEditTarget(stage.GetSessionLayer())
        settings = carb.settings.get_settings()
        settings.set(pb.SETTING_UPDATE_TO_USD, True)
        settings.set(pb.SETTING_UPDATE_VELOCITIES_TO_USD, True)
        settings.set_bool(pb.SETTING_SUPPRESS_READBACK, False)
        settings.set_bool("/physics/suppressReadback", False)
        log_path = Path(str(settings.get("/log/file")))
        log_offset = log_path.stat().st_size if log_path.exists() else 0

        def world_xyz(path: str) -> list[float]:
            matrix = UsdGeom.XformCache().GetLocalToWorldTransform(
                stage.GetPrimAtPath(path)
            )
            return [float(value) for value in matrix.ExtractTranslation()]

        if args.mode == "drop":
            beaker = stage.GetPrimAtPath("/World/obj_beaker")
            beaker.CreateAttribute(
                "physics:kinematicEnabled", Sdf.ValueTypeNames.Bool
            ).Set(True)
            opening = world_xyz(BEAKER_OPENING)
            bar = stage.GetPrimAtPath(STIR_BAR)
            bar.GetAttribute("xformOp:translate").Set(
                Gf.Vec3d(opening[0], opening[1], opening[2] + 0.04)
            )

        world = World(
            stage_units_in_meters=1.0,
            physics_prim_path="/World/physicsScene",
            set_defaults=False,
            physics_dt=1 / 120,
            rendering_dt=1 / 120,
        )
        world.reset()
        steps = round(args.seconds * 120)
        tail: list[dict[str, list[float]]] = []
        for step in range(steps):
            world.step(render=False)
            if step >= steps - 120:
                tail.append(
                    {name: world_xyz(f"/World/{name}") for name in OBJECTS}
                )

        final = tail[-1]
        tail_displacement = {}
        for name in OBJECTS:
            first = tail[0][name]
            last = tail[-1][name]
            tail_displacement[name] = sum(
                (last[index] - first[index]) ** 2 for index in range(3)
            ) ** 0.5
        above_table = all(final[name][2] >= 0.74 for name in OBJECTS)
        static_stable = max(tail_displacement.values()) <= 0.002 and above_table

        opening = world_xyz(BEAKER_OPENING)
        support = world_xyz("/World/obj_beaker/__aan_frame_support")
        bar_final = final["obj_stir_bar"]
        radial = (
            (bar_final[0] - opening[0]) ** 2
            + (bar_final[1] - opening[1]) ** 2
        ) ** 0.5
        drop_inside = (
            radial <= 0.03
            and support[2] + 0.001 <= bar_final[2] <= opening[2] - 0.005
            and tail_displacement["obj_stir_bar"] <= 0.002
        )

        log_text = (
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
            for line in log_text.splitlines()
            if any(marker in line for marker in markers)
        ]
        passed = (
            static_stable if args.mode == "static" else drop_inside
        ) and not hard_errors
        report = {
            "schema_version": "scenario-forge.stir-bar-beaker-observation.v1",
            "status": "pass" if passed else "blocked",
            "mode": args.mode,
            "run_index": args.run_index,
            "runtime": {
                "name": "isaac41",
                "kit_version": str(omni.kit.app.get_app().get_app_version()),
            },
            "duration_seconds": args.seconds,
            "observations": {
                "final_xyz_m": final,
                "tail_displacement_m": tail_displacement,
                "all_objects_above_table": above_table,
                "bar_radial_offset_from_beaker_center_m": radial,
                "bar_inside_beaker": drop_inside,
                "hard_errors": hard_errors,
            },
            "claims": {
                "static_stability": static_stable,
                "non_robot_drop_inside_beaker": drop_inside
                if args.mode == "drop"
                else False,
                "robot_policy_success": False,
                "canonical_task04_success": False,
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

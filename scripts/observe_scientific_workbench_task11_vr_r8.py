#!/usr/bin/env python3
"""Observe Task 11 r8 particle-free scene stability in Isaac Sim 4.1."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
import traceback


OBJECTS = (
    "obj_centrifuge",
    "obj_mixed_rack",
    "obj_primary_tube",
    "obj_balance_tube",
    *(f"obj_bg_15ml_{index:02d}" for index in range(6)),
    "obj_bg_50ml_00",
    "obj_bg_50ml_01",
    "obj_r9_amber_bottle",
    "obj_r9_tip_box",
    "obj_r9_wash_bottle",
    "obj_r9_clear_bottle",
    "obj_r9_pipette_carousel",
)
STATIC_CONTEXT = tuple(
    name for name in OBJECTS if name.startswith(("obj_bg_", "obj_r9_"))
)
REST_LINKS = (
    "lid_link",
    "rotor_link",
    "encoder_link",
    "start_button_link",
    "stop_button_link",
    "lid_open_button_link",
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
        from omni.isaac.core.articulations import Articulation
        from pxr import Usd, UsdGeom, UsdPhysics

        context = omni.usd.get_context()
        if not context.open_stage(str(args.scene.resolve())):
            raise RuntimeError(f"cannot open {args.scene}")
        while context.get_stage_loading_status()[2] > 0:
            app.update()
        stage = context.get_stage()
        settings = carb.settings.get_settings()
        settings.set(pb.SETTING_UPDATE_TO_USD, True)
        settings.set(pb.SETTING_UPDATE_VELOCITIES_TO_USD, True)
        settings.set_bool(pb.SETTING_SUPPRESS_READBACK, False)
        log_path = Path(str(settings.get("/log/file")))
        log_offset = log_path.stat().st_size if log_path.exists() else 0

        def world_xyz(path: str) -> list[float]:
            point = UsdGeom.XformCache().GetLocalToWorldTransform(
                stage.GetPrimAtPath(path)
            ).ExtractTranslation()
            return [float(value) for value in point]

        bbox_cache = UsdGeom.BBoxCache(
            Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]
        )

        def bounds(path: str) -> tuple[list[float], list[float]]:
            box = bbox_cache.ComputeWorldBound(
                stage.GetPrimAtPath(path)
            ).ComputeAlignedRange()
            return ([float(v) for v in box.GetMin()], [float(v) for v in box.GetMax()])

        authored = {name: world_xyz(f"/World/{name}") for name in OBJECTS}
        table_bounds = bounds("/World/table")
        base_bounds = bounds("/World/obj_centrifuge/base_link")
        support_gap_m = base_bounds[0][2] - table_bounds[1][2]
        base_on_table = abs(support_gap_m) <= 0.001
        preview = {
            name: world_xyz(f"/World/obj_centrifuge/{name}") for name in REST_LINKS
        }
        visual_liquids = (
            "/World/obj_primary_tube/VisualLiquid",
            "/World/obj_balance_tube/VisualLiquid",
        )
        liquid_forbidden = []
        for path in visual_liquids:
            root = stage.GetPrimAtPath(path)
            if not root or root.GetAttribute("scenarioForge:role").Get() != "visual_static_liquid":
                liquid_forbidden.append(f"{path}:missing_role")
                continue
            for prim in Usd.PrimRange(root):
                if any(
                    (
                        prim.HasAPI(UsdPhysics.CollisionAPI),
                        prim.HasAPI(UsdPhysics.RigidBodyAPI),
                        prim.HasAPI(UsdPhysics.MassAPI),
                    )
                ):
                    liquid_forbidden.append(str(prim.GetPath()))
        particle_like = [
            str(prim.GetPath())
            for prim in stage.Traverse()
            if "Particle" in prim.GetTypeName()
            or any("Particle" in schema for schema in prim.GetAppliedSchemas())
        ]

        world = World(
            stage_units_in_meters=1.0,
            physics_prim_path="/World/physicsScene",
            set_defaults=False,
            physics_dt=1 / 120,
            rendering_dt=1 / 120,
        )
        articulation = world.scene.add(
            Articulation("/World/obj_centrifuge", name="task11_r8_static_device")
        )
        omni.physx.get_physx_interface().overwrite_gpu_setting(1)
        world.reset()
        dof_index = {name: index for index, name in enumerate(articulation.dof_names)}
        rotor_index = dof_index["rotor_spin_joint"]
        maximum_rotor_speed = abs(float(articulation.get_joint_velocities()[rotor_index]))
        after_reset = {
            name: world_xyz(f"/World/obj_centrifuge/{name}") for name in REST_LINKS
        }
        world.step(render=False)
        after_first = {
            name: world_xyz(f"/World/obj_centrifuge/{name}") for name in REST_LINKS
        }
        first_step_jump = {
            name: max(math.dist(preview[name], after_reset[name]), math.dist(preview[name], after_first[name]))
            for name in REST_LINKS
        }
        first_step_pose_continuity = max(first_step_jump.values()) <= 0.001
        steps = max(1, round(args.seconds * 120) - 1)
        tail = []
        for step in range(steps):
            world.step(render=False)
            maximum_rotor_speed = max(
                maximum_rotor_speed,
                abs(float(articulation.get_joint_velocities()[rotor_index])),
            )
            if step >= max(0, steps - 120):
                tail.append(
                    {name: world_xyz(f"/World/{name}") for name in OBJECTS}
                )
        final = tail[-1]
        displacement = {
            name: math.dist(authored[name], final[name]) for name in OBJECTS
        }
        tail_motion = {
            name: math.dist(tail[0][name], final[name]) for name in OBJECTS
        }
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
        log = (
            log_path.read_text(encoding="utf-8", errors="replace")[log_offset:]
            if log_path.exists()
            else ""
        )
        markers = (
            "CUDA error",
            "illegal memory access",
            "Non-GPU-compatible convex mesh",
            "Failed to cook",
            "PhysX error",
        )
        hard_errors = [
            line.strip()
            for line in log.splitlines()
            if any(marker in line for marker in markers)
        ]
        particle_free = not particle_like
        visual_liquid_contract = not liquid_forbidden
        passed = all(
            (
                base_on_table,
                first_step_pose_continuity,
                background_context_static,
                structural_static,
                dynamic_tubes_stable,
                particle_free,
                visual_liquid_contract,
                not hard_errors,
            )
        )
        report = {
            "schema_version": "scenario-forge.task11-vr-r8-static-run.v1",
            "status": "pass" if passed else "blocked",
            "run_index": args.run_index,
            "duration_seconds": args.seconds,
            "runtime": {
                "name": "isaac41",
                "kit_version": str(omni.kit.app.get_app().get_app_version()),
            },
            "scene_usd_sha256": sha256(args.scene.read_bytes()).hexdigest(),
            "observations": {
                "support_gap_m": support_gap_m,
                "first_step_jump_m": first_step_jump,
                "authored_xyz_m": authored,
                "final_xyz_m": final,
                "displacement_m": displacement,
                "tail_motion_m": tail_motion,
                "particle_like_prims": particle_like,
                "visual_liquid_forbidden_physics": liquid_forbidden,
                "hard_errors": hard_errors,
                "maximum_rotor_speed_rad_s": maximum_rotor_speed,
            },
            "claims": {
                "base_on_table": base_on_table,
                "first_step_pose_continuity": first_step_pose_continuity,
                "background_context_static": background_context_static,
                "structural_static": structural_static,
                "dynamic_tubes_stable": dynamic_tubes_stable,
                "particle_free_scene": particle_free,
                "visual_static_liquid_only": visual_liquid_contract,
                "scene_static_stability": passed,
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

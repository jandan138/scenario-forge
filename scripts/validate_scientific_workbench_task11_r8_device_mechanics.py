#!/usr/bin/env python3
"""Validate Task 11 r8 device mechanics in the composed scene without a robot."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import traceback


DEVICE = "/World/obj_centrifuge"
OPEN_LOCAL = (0.194, -0.263, 0.198)
STOP_LOCAL = (0.205, -0.2675, 0.145)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    original = sys.argv
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True, "multi_gpu": False})
    sys.argv = original
    try:
        import carb
        import numpy as np
        import omni.kit.app
        import omni.physx
        import omni.usd
        from omni.isaac.core import World
        from omni.isaac.core.articulations import Articulation
        from omni.isaac.core.prims import XFormPrim
        from omni.isaac.core.utils.types import ArticulationAction
        from pxr import Gf, UsdGeom, UsdPhysics

        context = omni.usd.get_context()
        if not context.open_stage(str(args.scene.resolve())):
            raise RuntimeError(f"cannot open {args.scene}")
        while context.get_stage_loading_status()[2] > 0:
            app.update()
        stage = context.get_stage()
        stage.SetEditTarget(stage.GetSessionLayer())
        device_matrix = UsdGeom.XformCache().GetLocalToWorldTransform(
            stage.GetPrimAtPath(DEVICE)
        )

        def world_center(local):
            point = device_matrix.Transform(Gf.Vec3d(*local))
            return tuple(float(value) for value in point)

        def make_pusher(name: str, center):
            path = f"/World/__task11_r8_device_probe/{name}"
            cube = UsdGeom.Cube.Define(stage, path)
            cube.CreateSizeAttr(1.0)
            cube.AddTranslateOp().Set(Gf.Vec3d(center[0], center[1] - 0.035, center[2]))
            cube.AddScaleOp().Set(Gf.Vec3f(0.045, 0.018, 0.014))
            UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
            UsdPhysics.RigidBodyAPI.Apply(cube.GetPrim()).CreateKinematicEnabledAttr(True)
            return path

        open_center = world_center(OPEN_LOCAL)
        stop_center = world_center(STOP_LOCAL)
        open_path = make_pusher("open_pusher", open_center)
        stop_path = make_pusher("stop_pusher", stop_center)
        settings = carb.settings.get_settings()
        log_path = Path(str(settings.get("/log/file")))
        log_offset = log_path.stat().st_size if log_path.exists() else 0
        world = World(
            stage_units_in_meters=1.0,
            physics_prim_path="/World/physicsScene",
            set_defaults=False,
            physics_dt=1 / 120,
            rendering_dt=1 / 120,
        )
        articulation = world.scene.add(Articulation(DEVICE, name="centrifuge_r8"))
        open_pusher = world.scene.add(XFormPrim(open_path, name="open_pusher"))
        stop_pusher = world.scene.add(XFormPrim(stop_path, name="stop_pusher"))
        omni.physx.get_physx_interface().overwrite_gpu_setting(1)
        world.reset()
        for _ in range(90):
            world.step(render=False)
        index = {name: i for i, name in enumerate(articulation.dof_names)}
        required = {
            "lid_open_button_joint",
            "stop_button_joint",
            "lid_hinge_joint",
            "rotor_spin_joint",
        }
        if not required.issubset(index):
            raise RuntimeError(f"missing dofs: {required - set(index)}")

        def positions():
            return articulation.get_joint_positions().copy()

        def velocities():
            return articulation.get_joint_velocities().copy()

        def move_pusher(pusher, center, joint_name, pressed, steps=90):
            initial, _ = pusher.get_world_pose()
            end_y = center[1] + 0.003 if pressed else center[1] - 0.035
            maximum = -1.0
            for step in range(steps):
                alpha = (step + 1) / steps
                y = float(initial[1]) + (end_y - float(initial[1])) * alpha
                pusher.set_world_pose(position=[center[0], y, center[2]])
                world.step(render=False)
                maximum = max(maximum, float(positions()[index[joint_name]]))
            return maximum

        articulation.apply_action(
            ArticulationAction(
                joint_velocities=np.asarray([8.0]),
                joint_indices=np.asarray([index["rotor_spin_joint"]]),
            )
        )
        for _ in range(180):
            world.step(render=False)
        rotor_during_interlock = abs(float(velocities()[index["rotor_spin_joint"]]))
        interlock_button = move_pusher(
            open_pusher, open_center, "lid_open_button_joint", True
        )
        interlock_lid = float(positions()[index["lid_hinge_joint"]])
        move_pusher(open_pusher, open_center, "lid_open_button_joint", False, 60)
        articulation.apply_action(
            ArticulationAction(
                joint_velocities=np.asarray([0.0]),
                joint_indices=np.asarray([index["rotor_spin_joint"]]),
            )
        )
        for _ in range(360):
            world.step(render=False)
            if abs(float(velocities()[index["rotor_spin_joint"]])) <= 0.05:
                break
        rotor_before_open = abs(float(velocities()[index["rotor_spin_joint"]]))
        open_button = move_pusher(
            open_pusher, open_center, "lid_open_button_joint", True
        )
        for _ in range(420):
            world.step(render=False)
        lid_open = float(positions()[index["lid_hinge_joint"]])
        lid_state = stage.GetPrimAtPath(DEVICE).GetAttribute("device:lidState").Get()
        move_pusher(open_pusher, open_center, "lid_open_button_joint", False, 60)
        for _ in range(180):
            world.step(render=False)
        lid_held = float(positions()[index["lid_hinge_joint"]])
        stop_button = move_pusher(stop_pusher, stop_center, "stop_button_joint", True)
        for _ in range(60):
            world.step(render=False)
        power_state = stage.GetPrimAtPath(DEVICE).GetAttribute("device:powerState").Get()

        lid_proxy = f"{DEVICE}/lid_link/__aan_collision_proxy"
        new_proxies = (
            "top_panel",
            "front_perimeter",
            "rear_perimeter",
            "left_perimeter",
            "right_perimeter",
            "handle_grip",
            "handle_post_left",
            "handle_post_right",
            "latch_tongue",
        )
        collision_layout_ok = all(
            stage.GetPrimAtPath(f"{lid_proxy}/{name}") for name in new_proxies
        ) and not any(
            stage.GetPrimAtPath(f"{lid_proxy}/{name}")
            for name in ("main_shell", "front_shell")
        )
        checks = {
            "visual_fitted_lid_collision_composed": collision_layout_ok,
            "rotor_open_interlock": (
                rotor_during_interlock >= 1.0
                and interlock_button >= 0.0021
                and abs(interlock_lid) <= 0.05
            ),
            "button_causes_lid_open": (
                rotor_before_open <= 0.05
                and open_button >= 0.0021
                and lid_open <= -1.30
            ),
            "lid_remains_open_after_release": lid_held <= -1.30 and lid_state == "open_hold",
            "shutdown_causes_power_off": stop_button >= 0.0021 and power_state == "off",
        }
        log = (
            log_path.read_text(encoding="utf-8", errors="replace")[log_offset:]
            if log_path.exists()
            else ""
        )
        hard_errors = [
            line.strip()
            for line in log.splitlines()
            if any(marker in line for marker in ("CUDA error", "illegal memory access", "PhysX error"))
        ]
        passed = all(checks.values()) and not hard_errors
        report = {
            "schema_version": "scenario-forge.task11-r8-device-mechanics.v1",
            "status": "pass" if passed else "blocked",
            "runtime": {
                "name": "isaac41",
                "kit_version": str(omni.kit.app.get_app().get_app_version()),
            },
            "scene_usd_sha256": sha256(args.scene.read_bytes()).hexdigest(),
            "method": "kinematic_contact_pushers_no_direct_button_or_lid_joint_write",
            "checks": checks,
            "observations": {
                "interlock_button_max_m": interlock_button,
                "rotor_during_interlock_rad_s": rotor_during_interlock,
                "lid_during_interlock_rad": interlock_lid,
                "rotor_before_open_rad_s": rotor_before_open,
                "open_button_max_m": open_button,
                "lid_open_rad": lid_open,
                "lid_held_rad": lid_held,
                "lid_state": lid_state,
                "stop_button_max_m": stop_button,
                "power_state": power_state,
                "hard_errors": hard_errors,
            },
            "claims": {
                "robot_free_device_mechanics": passed,
                "mechanical_oracle_success": False,
                "robot_policy_success": False,
                "task11_success": False,
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

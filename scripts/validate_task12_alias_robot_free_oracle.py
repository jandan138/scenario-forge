#!/usr/bin/env python3
"""Validate OPEN, rack-to-rotor transfer and STOP without a robot policy."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
import traceback


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import generate_task12_alias_centrifuge_rack_to_rotor as alias  # noqa: E402
from scripts import generate_scientific_workbench_task11_vr_static as base  # noqa: E402


DEVICE = "/World/obj_centrifuge"
TARGET = "/World/obj_primary_tube"
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
        from pxr import Gf, Sdf, UsdGeom, UsdPhysics

        context = omni.usd.get_context()
        if not context.open_stage(str(args.scene.resolve())):
            raise RuntimeError(f"cannot open {args.scene}")
        while context.get_stage_loading_status()[2] > 0:
            app.update()
        stage = context.get_stage()
        stage.SetEditTarget(stage.GetSessionLayer())
        cache = UsdGeom.XformCache()
        device_matrix = cache.GetLocalToWorldTransform(stage.GetPrimAtPath(DEVICE))
        target_matrix = cache.GetLocalToWorldTransform(stage.GetPrimAtPath(TARGET))
        target_start = target_matrix.ExtractTranslation()
        target_start_quat = target_matrix.ExtractRotationQuat()

        profile_path = args.scene.parent / "deps/centrifuge/articulation/device_profile.json"
        profile = json.loads(profile_path.read_text())
        socket = profile["tube_sockets"][alias.TARGET_ROTOR_SOCKET]
        target_local = Gf.Vec3d(
            *(
                float(base.ROTOR_ORIGIN[index])
                + float(socket["inserted_bottom_rotor_local_m"][index])
                for index in range(3)
            )
        )
        desired_position = device_matrix.Transform(target_local)
        desired_axis = device_matrix.TransformDir(
            Gf.Vec3d(*map(float, socket["axis_out_rotor_local"]))
        ).GetNormalized()
        desired_quat = base._orientation_z_to(tuple(float(value) for value in desired_axis))

        def world_center(local):
            point = device_matrix.Transform(Gf.Vec3d(*local))
            return tuple(float(value) for value in point)

        def make_pusher(name: str, center):
            path = f"/World/__task12_alias_oracle/{name}"
            cube = UsdGeom.Cube.Define(stage, path)
            cube.CreateSizeAttr(1.0)
            cube.AddTranslateOp().Set(Gf.Vec3d(center[0], center[1] - 0.035, center[2]))
            cube.AddScaleOp().Set(Gf.Vec3f(0.045, 0.018, 0.014))
            UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
            rigid = UsdPhysics.RigidBodyAPI.Apply(cube.GetPrim())
            rigid.CreateRigidBodyEnabledAttr(True)
            rigid.CreateKinematicEnabledAttr(True)
            return path

        open_center = world_center(OPEN_LOCAL)
        stop_center = world_center(STOP_LOCAL)
        open_path = make_pusher("open_pusher", open_center)
        stop_path = make_pusher("stop_pusher", stop_center)
        carrier = UsdGeom.Xform.Define(stage, "/World/__task12_alias_oracle/tube_carrier")
        carrier.AddTranslateOp().Set(Gf.Vec3d(*target_start))
        carrier.AddOrientOp().Set(
            Gf.Quatf(
                float(target_start_quat.GetReal()),
                Gf.Vec3f(*map(float, target_start_quat.GetImaginary())),
            )
        )
        carrier_rigid = UsdPhysics.RigidBodyAPI.Apply(carrier.GetPrim())
        carrier_rigid.CreateRigidBodyEnabledAttr(True)
        carrier_rigid.CreateKinematicEnabledAttr(True)
        joint = UsdPhysics.FixedJoint.Define(
            stage, "/World/__task12_alias_oracle/tube_carrier/FixedJoint"
        )
        joint.CreateBody0Rel().SetTargets([carrier.GetPath()])
        joint.CreateBody1Rel().SetTargets([Sdf.Path(TARGET)])
        joint.CreateLocalPos0Attr(Gf.Vec3f(0.0))
        joint.CreateLocalPos1Attr(Gf.Vec3f(0.0))
        joint.CreateLocalRot0Attr(Gf.Quatf(1.0))
        joint.CreateLocalRot1Attr(Gf.Quatf(1.0))

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
        articulation = world.scene.add(Articulation(DEVICE, name="task12_alias_device"))
        open_pusher = world.scene.add(XFormPrim(open_path, name="open_pusher"))
        stop_pusher = world.scene.add(XFormPrim(stop_path, name="stop_pusher"))
        tube_carrier = world.scene.add(
            XFormPrim(str(carrier.GetPath()), name="tube_carrier")
        )
        omni.physx.get_physx_interface().overwrite_gpu_setting(1)
        world.reset()
        for _ in range(90):
            world.step(render=False)
        index = {name: i for i, name in enumerate(articulation.dof_names)}

        def move_pusher(pusher, center, joint_name, pressed, steps=90):
            initial, _ = pusher.get_world_pose()
            end_y = center[1] + 0.003 if pressed else center[1] - 0.035
            maximum = -1.0
            for step in range(steps):
                alpha = (step + 1) / steps
                y = float(initial[1]) + (end_y - float(initial[1])) * alpha
                pusher.set_world_pose(position=[center[0], y, center[2]])
                world.step(render=False)
                maximum = max(
                    maximum,
                    float(articulation.get_joint_positions()[index[joint_name]]),
                )
            return maximum

        open_button = move_pusher(
            open_pusher, open_center, "lid_open_button_joint", True
        )
        for _ in range(420):
            world.step(render=False)
        lid_open = float(articulation.get_joint_positions()[index["lid_hinge_joint"]])
        lid_state = stage.GetPrimAtPath(DEVICE).GetAttribute("device:lidState").Get()
        move_pusher(open_pusher, open_center, "lid_open_button_joint", False, 60)

        start_np = np.asarray(target_start, dtype=float)
        desired_np = np.asarray(desired_position, dtype=float)
        lifted = start_np.copy()
        lifted[2] += 0.15
        above = desired_np.copy()
        above[2] += 0.15
        q0 = Gf.Quatf(
            float(target_start_quat.GetReal()),
            Gf.Vec3f(*map(float, target_start_quat.GetImaginary())),
        )

        def move_carrier(start, end, start_q, end_q, steps):
            for step in range(steps):
                alpha = (step + 1) / steps
                smooth = alpha * alpha * (3.0 - 2.0 * alpha)
                position = (1.0 - smooth) * start + smooth * end
                quat = Gf.Slerp(smooth, start_q, end_q)
                imag = quat.GetImaginary()
                tube_carrier.set_world_pose(
                    position=position,
                    orientation=np.asarray(
                        [quat.GetReal(), imag[0], imag[1], imag[2]], dtype=float
                    ),
                )
                world.step(render=False)

        move_carrier(start_np, lifted, q0, q0, 180)
        move_carrier(lifted, above, q0, desired_quat, 360)
        move_carrier(above, desired_np, desired_quat, desired_quat, 300)
        joint.CreateJointEnabledAttr(False)
        tail_positions = []
        for step in range(360):
            world.step(render=False)
            if step >= 240:
                cache.Clear()
                point = cache.GetLocalToWorldTransform(
                    stage.GetPrimAtPath(TARGET)
                ).ExtractTranslation()
                tail_positions.append([float(value) for value in point])
        cache.Clear()
        final_matrix = cache.GetLocalToWorldTransform(stage.GetPrimAtPath(TARGET))
        final_position = final_matrix.ExtractTranslation()
        final_axis = final_matrix.TransformDir(Gf.Vec3d(0.0, 0.0, 1.0)).GetNormalized()
        dot = max(-1.0, min(1.0, float(final_axis * desired_axis)))
        axis_error = math.degrees(math.acos(dot))
        position_error = math.dist(
            [float(value) for value in final_position],
            [float(value) for value in desired_position],
        )
        tail_span = max(
            math.dist(tail_positions[0], point) for point in tail_positions
        )

        stop_button = move_pusher(stop_pusher, stop_center, "stop_button_joint", True)
        for _ in range(60):
            world.step(render=False)
        power_state = stage.GetPrimAtPath(DEVICE).GetAttribute("device:powerState").Get()
        cap_local = UsdGeom.Xformable(
            stage.GetPrimAtPath(TARGET + "/Cap")
        ).GetLocalTransformation()
        cap_fixed = abs(float(cap_local.ExtractTranslation()[2]) - 0.1074) <= 1e-6
        log = (
            log_path.read_text(encoding="utf-8", errors="replace")[log_offset:]
            if log_path.exists()
            else ""
        )
        hard_errors = [
            line.strip()
            for line in log.splitlines()
            if any(
                marker in line
                for marker in ("CUDA error", "illegal memory access", "PhysX error")
            )
        ]
        checks = {
            "open_contact_and_hold": open_button >= 0.0021
            and lid_open <= -1.30
            and lid_state == "open_hold",
            "target_tube_reaches_socket_18": position_error <= 0.015,
            "target_tube_axis_aligned": axis_error <= 15.0,
            "target_tube_released_stable": tail_span <= 0.002,
            "fixed_red_cap_remains_attached": cap_fixed,
            "stop_contact_causes_power_off": stop_button >= 0.0021
            and power_state == "off",
            "no_hard_errors": not hard_errors,
        }
        passed = all(checks.values())
        report = {
            "schema_version": "scenario-forge.task12-alias-robot-free-oracle/v1",
            "status": "pass" if passed else "blocked",
            "runtime": {
                "name": "isaac41",
                "kit_version": str(omni.kit.app.get_app().get_app_version()),
            },
            "scene_usd_sha256": sha256(args.scene.read_bytes()).hexdigest(),
            "method": "contact_buttons_and_kinematic_carrier_fixed_joint_no_robot_policy",
            "checks": checks,
            "observations": {
                "open_button_max_m": open_button,
                "lid_open_rad": lid_open,
                "lid_state": lid_state,
                "target_socket": alias.TARGET_ROTOR_SOCKET,
                "target_position_error_m": position_error,
                "target_axis_error_deg": axis_error,
                "target_tail_span_m": tail_span,
                "stop_button_max_m": stop_button,
                "power_state": power_state,
                "hard_errors": hard_errors,
            },
            "claims": {
                "robot_free_transfer_oracle_success": passed,
                "manual_close_and_latch": False,
                "robot_policy_success": False,
                "task_success": False,
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

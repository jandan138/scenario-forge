#!/usr/bin/env python3
"""Validate Task11 mechanics in one episode without a robot or object teleports."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
import traceback


DEVICE = "/World/obj_centrifuge"
TUBE = "/World/obj_primary_tube"
TARGET_FRAME = "/World/obj_mixed_rack/__frames/slot_15ml_r00_c02_inserted_bottom"
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
        import omni.kit.app
        import omni.physx
        import omni.physx.bindings._physx as pb
        import omni.usd
        from omni.isaac.core import World
        from omni.isaac.core.articulations import Articulation
        from omni.isaac.core.prims import RigidPrim, XFormPrim
        from pxr import Gf, Usd, UsdGeom, UsdPhysics

        context = omni.usd.get_context()
        if not context.open_stage(str(args.scene.resolve())):
            raise RuntimeError(f"cannot open {args.scene}")
        while context.get_stage_loading_status()[2] > 0:
            app.update()
        stage = context.get_stage()
        stage.SetEditTarget(stage.GetSessionLayer())
        cache = UsdGeom.XformCache()
        device_xyz = cache.GetLocalToWorldTransform(
            stage.GetPrimAtPath(DEVICE)
        ).ExtractTranslation()
        tube_matrix = cache.GetLocalToWorldTransform(stage.GetPrimAtPath(TUBE))
        tube_xyz = tube_matrix.ExtractTranslation()
        tube_q = tube_matrix.ExtractRotationQuat()
        target_xyz = cache.GetLocalToWorldTransform(
            stage.GetPrimAtPath(TARGET_FRAME)
        ).ExtractTranslation()

        def world_center(local):
            return tuple(float(device_xyz[i] + local[i]) for i in range(3))

        def make_pusher(name: str, center):
            path = f"/World/__task11_mechanical_oracle/{name}"
            cube = UsdGeom.Cube.Define(stage, path)
            cube.CreateSizeAttr(1.0)
            translate = cube.AddTranslateOp()
            translate.Set(Gf.Vec3d(center[0], center[1] - 0.035, center[2]))
            cube.AddScaleOp().Set(Gf.Vec3f(0.045, 0.018, 0.014))
            UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
            body = UsdPhysics.RigidBodyAPI.Apply(cube.GetPrim())
            body.CreateKinematicEnabledAttr(True)
            return path

        open_center = world_center(OPEN_LOCAL)
        stop_center = world_center(STOP_LOCAL)
        open_path = make_pusher("open_pusher", open_center)
        stop_path = make_pusher("stop_pusher", stop_center)

        jaw_paths = []
        for name, sign in (("left_jaw", -1.0), ("right_jaw", 1.0)):
            path = f"/World/__task11_mechanical_oracle/{name}"
            jaw = UsdGeom.Cube.Define(stage, path)
            jaw.CreateSizeAttr(1.0)
            jaw.AddTranslateOp().Set(Gf.Vec3d(sign * 0.1, 0.0, 2.0))
            jaw.AddOrientOp().Set(Gf.Quatf(tube_q))
            jaw.AddScaleOp().Set(Gf.Vec3f(0.035, 0.012, 0.024))
            UsdPhysics.CollisionAPI.Apply(jaw.GetPrim())
            body = UsdPhysics.RigidBodyAPI.Apply(jaw.GetPrim())
            body.CreateKinematicEnabledAttr(True)
            jaw_paths.append(path)

        settings = carb.settings.get_settings()
        settings.set(pb.SETTING_UPDATE_TO_USD, True)
        settings.set(pb.SETTING_UPDATE_PARTICLES_TO_USD, True)
        settings.set(pb.SETTING_UPDATE_VELOCITIES_TO_USD, True)
        settings.set_bool(pb.SETTING_SUPPRESS_READBACK, False)
        log_path = Path(str(settings.get("/log/file")))
        log_offset = log_path.stat().st_size if log_path.exists() else 0
        world = World(
            stage_units_in_meters=1.0,
            physics_prim_path="/World/physicsScene",
            set_defaults=False,
            physics_dt=1 / 120,
            rendering_dt=1 / 120,
        )
        articulation = world.scene.add(Articulation(DEVICE, name="centrifuge"))
        primary = world.scene.add(RigidPrim(TUBE, name="primary_tube"))
        open_pusher = world.scene.add(XFormPrim(open_path, name="open_pusher"))
        stop_pusher = world.scene.add(XFormPrim(stop_path, name="stop_pusher"))
        left_jaw = world.scene.add(XFormPrim(jaw_paths[0], name="left_jaw"))
        right_jaw = world.scene.add(XFormPrim(jaw_paths[1], name="right_jaw"))
        omni.physx.get_physx_interface().overwrite_gpu_setting(1)
        world.reset()
        for _ in range(120):
            world.step(render=False)

        dof_index = {name: i for i, name in enumerate(articulation.dof_names)}
        required = {"lid_open_button_joint", "stop_button_joint", "lid_hinge_joint"}
        if not required.issubset(dof_index):
            raise RuntimeError(f"missing device dofs: {required - set(dof_index)}")

        def joint_positions():
            return articulation.get_joint_positions().copy()

        def move_pusher(pusher, center, button_joint, *, press, steps=90):
            start_y = center[1] - 0.035
            end_y = center[1] + 0.003 if press else start_y
            current, _ = pusher.get_world_pose()
            start = float(current[1])
            maximum = -1.0
            for step in range(steps):
                y = start + (end_y - start) * (step + 1) / steps
                pusher.set_world_pose(position=[center[0], y, center[2]])
                world.step(render=False)
                maximum = max(maximum, float(joint_positions()[dof_index[button_joint]]))
            return maximum

        open_button_max = move_pusher(
            open_pusher, open_center, "lid_open_button_joint", press=True
        )
        for _ in range(420):
            world.step(render=False)
        lid_open_rad = float(joint_positions()[dof_index["lid_hinge_joint"]])
        lid_state = stage.GetPrimAtPath(DEVICE).GetAttribute("device:lidState").Get()
        move_pusher(
            open_pusher, open_center, "lid_open_button_joint", press=False, steps=60
        )

        tube_start_pos, tube_start_ori = primary.get_world_pose()
        start_pos = [float(v) for v in tube_start_pos]
        start_ori = [float(v) for v in tube_start_ori]
        start_quat = Gf.Quatd(
            float(start_ori[0]), Gf.Vec3d(*[float(v) for v in start_ori[1:]])
        )
        axis = Gf.Rotation(start_quat).TransformDir(
            Gf.Vec3d(0.0, 0.0, 1.0)
        ).GetNormalized()

        gripper_root = list(start_pos)
        gripper_q = list(start_ori)

        def jaw_world(root_pos, root_q, sign, gap):
            q = Gf.Quatd(float(root_q[0]), Gf.Vec3d(*[float(v) for v in root_q[1:]]))
            offset = Gf.Rotation(q).TransformDir(
                Gf.Vec3d(0.0, sign * gap, 0.11033)
            )
            return [float(root_pos[i] + offset[i]) for i in range(3)]

        def set_jaws(root_pos, root_q, gap):
            left_jaw.set_world_pose(
                position=jaw_world(root_pos, root_q, -1.0, gap),
                orientation=root_q,
            )
            right_jaw.set_world_pose(
                position=jaw_world(root_pos, root_q, 1.0, gap),
                orientation=root_q,
            )

        set_jaws(gripper_root, gripper_q, 0.031)
        for _ in range(5):
            world.step(render=False)
        for step in range(180):
            gap = 0.031 + (0.0150 - 0.031) * (step + 1) / 180
            set_jaws(gripper_root, gripper_q, gap)
            world.step(render=False)

        def move_gripper(destination, orientation, steps, *, grip_gap=0.0150):
            nonlocal gripper_root, gripper_q
            current_pos = list(gripper_root)
            current_ori = list(gripper_q)
            q0 = Gf.Quatd(float(current_ori[0]), Gf.Vec3d(*[float(v) for v in current_ori[1:]]))
            q1 = Gf.Quatd(float(orientation[0]), Gf.Vec3d(*[float(v) for v in orientation[1:]]))
            for step in range(steps):
                alpha = (step + 1) / steps
                pos = [
                    float(current_pos[i]) + (float(destination[i]) - float(current_pos[i])) * alpha
                    for i in range(3)
                ]
                q = Gf.Slerp(alpha, q0, q1)
                qi = q.GetImaginary()
                interpolated_q = [q.GetReal(), qi[0], qi[1], qi[2]]
                set_jaws(pos, interpolated_q, grip_gap)
                world.step(render=False)
            gripper_root = [float(v) for v in destination]
            gripper_q = [float(v) for v in orientation]

        initial_carrier_q = list(start_ori)
        lifted_goal = [float(start_pos[i] + axis[i] * 0.12) for i in range(3)]
        move_gripper(lifted_goal, initial_carrier_q, 180, grip_gap=0.0150)
        lifted_tube, _ = primary.get_world_pose()
        for step in range(120):
            gap = 0.0150
            set_jaws(gripper_root, gripper_q, gap)
            world.step(render=False)
        socket_clearance = math.dist(
            [float(v) for v in lifted_tube], [float(v) for v in tube_xyz]
        )
        above_target = [float(target_xyz[0]), float(target_xyz[1]), float(target_xyz[2] + 0.14)]
        upright_q = [1.0, 0.0, 0.0, 0.0]
        move_gripper(lifted_goal, upright_q, 1200)
        rotated_tube, rotated_q = primary.get_world_pose()
        for _ in range(3):
            actual, _ = primary.get_world_pose()
            correction = [float(actual[i]) - gripper_root[i] for i in range(3)]
            if math.sqrt(sum(value * value for value in correction)) <= 0.002:
                break
            move_gripper(
                [gripper_root[i] + correction[i] for i in range(3)],
                upright_q,
                360,
            )
        centered_tube, centered_q = primary.get_world_pose()
        transfer_q = upright_q
        move_gripper(above_target, transfer_q, 1200)
        transferred_tube, transferred_q = primary.get_world_pose()
        release_goal = [float(target_xyz[0]), float(target_xyz[1]), float(target_xyz[2] + 0.005)]
        move_gripper(release_goal, transfer_q, 360)
        release_xyz, release_q = primary.get_world_pose()
        for step in range(120):
            gap = 0.0150 + (0.031 - 0.0150) * (step + 1) / 120
            set_jaws(gripper_root, gripper_q, gap)
            world.step(render=False)
        tail = []
        for _ in range(240):
            world.step(render=False)
            tail.append([float(v) for v in primary.get_world_pose()[0]])
        final_xyz = tail[-1]
        final_q = [float(v) for v in primary.get_world_pose()[1]]
        radial_error = math.hypot(
            final_xyz[0] - float(target_xyz[0]), final_xyz[1] - float(target_xyz[1])
        )
        vertical_error = abs(final_xyz[2] - float(target_xyz[2]))
        final_quat = Gf.Quatd(
            float(final_q[0]), Gf.Vec3d(*[float(v) for v in final_q[1:]])
        )
        final_axis = Gf.Rotation(final_quat).TransformDir(Gf.Vec3d(0.0, 0.0, 1.0))
        upright_angle = math.degrees(
            math.acos(max(-1.0, min(1.0, float(final_axis[2]))))
        )
        tail_motion = math.dist(tail[0], tail[-1])

        stop_button_max = move_pusher(
            stop_pusher, stop_center, "stop_button_joint", press=True
        )
        for _ in range(60):
            world.step(render=False)
        power_state = stage.GetPrimAtPath(DEVICE).GetAttribute("device:powerState").Get()

        points = stage.GetPrimAtPath(
            "/World/fluid_runtime/ParticleSets/primary_liquid"
        ).GetAttribute("points").Get()
        particle_count = len(points)
        below_floor = sum(float(point[2]) < 0.755 for point in points)
        tube_box = UsdGeom.BBoxCache(
            Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]
        ).ComputeWorldBound(stage.GetPrimAtPath(TUBE)).ComputeAlignedBox()
        low, high = tube_box.GetMin(), tube_box.GetMax()
        retained = sum(
            all(float(low[i]) - 0.003 <= float(point[i]) <= float(high[i]) + 0.003 for i in range(3))
            for point in points
        )
        retention_ratio = retained / particle_count if particle_count else 0.0

        text = log_path.read_text(encoding="utf-8", errors="replace")[log_offset:] if log_path.exists() else ""
        markers = ("CUDA error", "illegal memory access", "Non-GPU-compatible convex mesh", "Failed to cook")
        hard_errors = [line.strip() for line in text.splitlines() if any(marker in line for marker in markers)]
        predicates = {
            "open_button_trigger": open_button_max >= 0.0021,
            "lid_open_for_sampling": lid_open_rad <= -1.30 and lid_state == "open_hold",
            "tube_clears_rotor_socket": socket_clearance >= 0.10,
            "tube_enters_target_rack_slot": radial_error <= 0.006 and vertical_error <= 0.006 and upright_angle <= 10.0,
            "tube_released_and_stably_supported": tail_motion <= 0.002,
            "shutdown_button_trigger": stop_button_max >= 0.0021,
            "final_tube_stable": tail_motion <= 0.002,
            "final_power_off": power_state == "off",
        }
        particle_gate = particle_count == 2640 and retention_ratio >= 0.99 and below_floor == 0
        passed = all(predicates.values()) and particle_gate and not hard_errors
        weights = {
            "open_button_trigger": 0.10,
            "lid_open_for_sampling": 0.15,
            "tube_clears_rotor_socket": 0.20,
            "tube_enters_target_rack_slot": 0.15,
            "tube_released_and_stably_supported": 0.15,
            "shutdown_button_trigger": 0.10,
            "final_tube_stable": 0.10,
            "final_power_off": 0.05,
        }
        report = {
            "schema_version": "scenario-forge.task11-mechanical-oracle.v1",
            "status": "pass" if passed else "blocked",
            "runtime": {"name": "isaac41", "kit_version": str(omni.kit.app.get_app().get_app_version())},
            "method": ["kinematic_rigid_contact_pushers", "kinematic_parallel_jaws"],
            "predicates": {name: {"passed": value, "weight": weights[name]} for name, value in predicates.items()},
            "progress_score": sum(weights[name] for name, value in predicates.items() if value),
            "observations": {
                "open_button_max_m": open_button_max,
                "lid_open_rad": lid_open_rad,
                "lid_state": lid_state,
                "socket_clearance_m": socket_clearance,
                "after_rotate_xyz_m": [float(v) for v in rotated_tube],
                "after_rotate_wxyz": [float(v) for v in rotated_q],
                "after_recenter_xyz_m": [float(v) for v in centered_tube],
                "after_recenter_wxyz": [float(v) for v in centered_q],
                "after_transfer_xyz_m": [float(v) for v in transferred_tube],
                "after_transfer_wxyz": [float(v) for v in transferred_q],
                "target_frame_xyz_m": [float(v) for v in target_xyz],
                "release_xyz_m": [float(v) for v in release_xyz],
                "release_wxyz": [float(v) for v in release_q],
                "final_xyz_m": final_xyz,
                "radial_error_m": radial_error,
                "vertical_error_m": vertical_error,
                "upright_angle_deg": upright_angle,
                "settle_tail_motion_m": tail_motion,
                "stop_button_max_m": stop_button_max,
                "power_state": power_state,
                "primary_liquid": {"particle_count": particle_count, "retention_ratio": retention_ratio, "below_floor_count": below_floor},
                "hard_errors": hard_errors,
                "post_initialization_object_transform_write_count": 0,
                "direct_device_joint_target_write_count": 0,
            },
            "claims": {
                "mechanical_oracle_success": passed,
                "task11_success": False,
                "true_lift2_robot": False,
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
        result = main()
    except BaseException:
        traceback.print_exc()
        result = 2
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(result)

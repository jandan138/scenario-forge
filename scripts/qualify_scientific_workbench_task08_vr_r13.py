#!/usr/bin/env python3
"""Run one Isaac 4.1 cold-start qualification for Task08 r13."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
import traceback


TUBE = "/World/obj_tube_01"
CAP = "/World/obj_cap_01"
CONTRACT = "/World/TaskRuntime/AssistedThreadContract"
START_RELATIVE_Z_M = 0.115
DRIVE_DEGREES = 360
HOLD_UPDATES = 1200
LIFT_M = 0.05


def _q_multiply(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def _q_rotate_xyzw(q, vector):
    rotated = _q_multiply(
        _q_multiply(q, (vector[0], vector[1], vector[2], 0.0)),
        (-q[0], -q[1], -q[2], q[3]),
    )
    return rotated[:3]


def _relative_z(tube_pose, cap_pose):
    delta = (
        float(cap_pose.p.x - tube_pose.p.x),
        float(cap_pose.p.y - tube_pose.p.y),
        float(cap_pose.p.z - tube_pose.p.z),
    )
    inverse = (
        -float(tube_pose.r.x),
        -float(tube_pose.r.y),
        -float(tube_pose.r.z),
        float(tube_pose.r.w),
    )
    return float(_q_rotate_xyzw(inverse, delta)[2])


def _contract(stage):
    prim = stage.GetPrimAtPath(CONTRACT)
    return {
        "state": str(prim.GetAttribute("assistedThread:state").Get()),
        "progress": float(prim.GetAttribute("assistedThread:progress").Get()),
        "rotation_deg": float(
            prim.GetAttribute("assistedThread:accumulatedClockwiseDegrees").Get()
        ),
        "target_relative_z_m": float(
            prim.GetAttribute("assistedThread:targetRelativeZM").Get()
        ),
        "closed": bool(prim.GetAttribute("assistedThread:closed").Get()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    saved = sys.argv
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True, "multi_gpu": False})
    sys.argv = saved
    exit_code = 3
    try:
        import carb
        import omni.physx
        import omni.usd
        from omni.isaac.core import World
        from omni.isaac.dynamic_control import _dynamic_control
        from pxr import UsdPhysics

        settings = carb.settings.get_settings()
        log_path = Path(str(settings.get("/log/file")))
        log_offset = log_path.stat().st_size if log_path.exists() else 0
        context = omni.usd.get_context()
        if not context.open_stage(str(args.scene.resolve())):
            raise RuntimeError("could not open Task08 r13 stage")
        while context.get_stage_loading_status()[2] > 0:
            app.update()
        for _ in range(60):
            app.update()
        stage = context.get_stage()
        stage.SetEditTarget(stage.GetSessionLayer())
        UsdPhysics.RigidBodyAPI(stage.GetPrimAtPath(TUBE)).CreateKinematicEnabledAttr().Set(
            True
        )
        world = World(
            stage_units_in_meters=1.0,
            physics_prim_path="/World/physicsScene",
            set_defaults=False,
            backend="numpy",
            device="cpu",
            physics_dt=1.0 / 120.0,
            rendering_dt=1.0 / 120.0,
        )
        omni.physx.get_physx_interface().overwrite_gpu_setting(1)
        world.reset()
        for _ in range(30):
            world.step(render=False)
        dc = _dynamic_control.acquire_dynamic_control_interface()
        tube = dc.get_rigid_body(TUBE)
        cap = dc.get_rigid_body(CAP)
        if min(tube, cap) == _dynamic_control.INVALID_HANDLE:
            raise RuntimeError("target tube/cap rigid body handles unavailable")
        tube_pose = dc.get_rigid_body_pose(tube)
        tube_q = (
            float(tube_pose.r.x),
            float(tube_pose.r.y),
            float(tube_pose.r.z),
            float(tube_pose.r.w),
        )
        offset = _q_rotate_xyzw(tube_q, (0.0, 0.0, START_RELATIVE_Z_M))
        start_position = (
            float(tube_pose.p.x) + offset[0],
            float(tube_pose.p.y) + offset[1],
            float(tube_pose.p.z) + offset[2],
        )
        dc.set_rigid_body_pose(cap, _dynamic_control.Transform(start_position, tube_q))
        dc.set_rigid_body_linear_velocity(cap, (0.0, 0.0, 0.0))
        dc.set_rigid_body_angular_velocity(cap, (0.0, 0.0, 0.0))
        for _ in range(8):
            dc.set_rigid_body_pose(
                cap, _dynamic_control.Transform(start_position, tube_q)
            )
            dc.set_rigid_body_linear_velocity(cap, (0.0, 0.0, 0.0))
            dc.set_rigid_body_angular_velocity(cap, (0.0, 0.0, 0.0))
            world.step(render=False)
        initial = _contract(stage)
        start_relative_z = _relative_z(
            dc.get_rigid_body_pose(tube), dc.get_rigid_body_pose(cap)
        )
        trace = []
        for degree in range(1, DRIVE_DEGREES + 1):
            tube_pose = dc.get_rigid_body_pose(tube)
            cap_pose = dc.get_rigid_body_pose(cap)
            half = math.radians(-float(degree)) * 0.5
            relative_yaw = (0.0, 0.0, math.sin(half), math.cos(half))
            target_q = _q_multiply(
                (
                    float(tube_pose.r.x),
                    float(tube_pose.r.y),
                    float(tube_pose.r.z),
                    float(tube_pose.r.w),
                ),
                relative_yaw,
            )
            dc.set_rigid_body_pose(
                cap,
                _dynamic_control.Transform(
                    (float(cap_pose.p.x), float(cap_pose.p.y), float(cap_pose.p.z)),
                    target_q,
                ),
            )
            world.step(render=False)
            if degree % 30 == 0 or degree == DRIVE_DEGREES:
                state = _contract(stage)
                state["commanded_clockwise_deg"] = degree
                state["measured_relative_z_m"] = _relative_z(
                    dc.get_rigid_body_pose(tube), dc.get_rigid_body_pose(cap)
                )
                trace.append(state)
        terminal = _contract(stage)
        closed_relative_z = _relative_z(
            dc.get_rigid_body_pose(tube), dc.get_rigid_body_pose(cap)
        )
        for _ in range(HOLD_UPDATES):
            world.step(render=False)
        hold_relative_z = _relative_z(
            dc.get_rigid_body_pose(tube), dc.get_rigid_body_pose(cap)
        )
        before_lift = dc.get_rigid_body_pose(tube)
        dc.set_rigid_body_pose(
            tube,
            _dynamic_control.Transform(
                (
                    float(before_lift.p.x),
                    float(before_lift.p.y),
                    float(before_lift.p.z) + LIFT_M,
                ),
                (
                    float(before_lift.r.x),
                    float(before_lift.r.y),
                    float(before_lift.r.z),
                    float(before_lift.r.w),
                ),
            ),
        )
        for _ in range(120):
            world.step(render=False)
        lift_relative_z = _relative_z(
            dc.get_rigid_body_pose(tube), dc.get_rigid_body_pose(cap)
        )
        log = log_path.read_text(errors="replace")[log_offset:] if log_path.exists() else ""
        markers = ("CUDA error", "illegal memory access", "PhysX error", "Traceback")
        hard_errors = list(
            dict.fromkeys(
                line for line in log.splitlines() if any(marker in line for marker in markers)
            )
        )
        passed = (
            initial["state"] in {"capture", "engaged"}
            and terminal["state"] == "closed"
            and terminal["progress"] >= 0.999
            and terminal["rotation_deg"] >= 350.0
            and abs(closed_relative_z - 0.1074) <= 0.001
            and abs(hold_relative_z - closed_relative_z) <= 0.001
            and abs(lift_relative_z - closed_relative_z) <= 0.0015
            and not hard_errors
        )
        result = {
            "schema_version": "scenario-forge.task08-r13-runtime-observation/v0.1",
            "status": "pass" if passed else "fail",
            "runtime": "isaac41",
            "scene": str(args.scene.resolve()),
            "protocol": "aligned_capture_clockwise_360deg_release_hold_and_tube_lift",
            "initial": initial,
            "terminal": terminal,
            "start_relative_z_m": start_relative_z,
            "closed_relative_z_m": closed_relative_z,
            "hold_relative_z_m": hold_relative_z,
            "lift_relative_z_m": lift_relative_z,
            "hold_updates": HOLD_UPDATES,
            "tube_lift_m": LIFT_M,
            "trace": trace,
            "hard_errors": hard_errors,
            "claims": {
                "one_turn_assisted_thread": passed,
                "release_retention": passed,
                "physical_thread_contact": False,
                "robot_policy_success": False,
                "benchmark_success": False,
            },
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(json.dumps(result, indent=2, sort_keys=True), flush=True)
        exit_code = 0 if passed else 2
    except BaseException:
        traceback.print_exc()
        exit_code = 3
    finally:
        app.close()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())

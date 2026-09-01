#!/usr/bin/env python3
"""Render Isaac 4.1 evidence for Task08 r13's one-turn closure."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.qualify_scientific_workbench_task08_vr_r13 import (  # noqa: E402
    CAP,
    START_RELATIVE_Z_M,
    TUBE,
    _contract,
    _q_multiply,
    _q_rotate_xyzw,
)


FPS = 30
ROTATION_FRAMES = 120
HOLD_START_FRAMES = 20
HOLD_CLOSED_FRAMES = 30
LIFT_FRAMES = 30
HOLD_LIFTED_FRAMES = 20


def _camera_quaternion(position, target):
    import numpy as np
    from scipy.spatial.transform import Rotation

    offset = np.asarray(position) - np.asarray(target)
    elevation = math.degrees(math.asin(float(offset[2]) / np.linalg.norm(offset)))
    azimuth = math.degrees(math.atan2(float(offset[1]), float(offset[0])))
    quat = Rotation.from_euler(
        "xyz", [0.0, elevation, azimuth - 180.0], degrees=True
    ).as_quat()
    return (quat[3], quat[0], quat[1], quat[2])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    evidence = root / "vr/evidence/runtime"
    frames = evidence / "one_turn_video_frames"
    if frames.exists():
        raise FileExistsError(frames)
    frames.mkdir(parents=True)
    saved = sys.argv
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp

    app = SimulationApp(
        {
            "headless": True,
            "renderer": "RayTracedLighting",
            "anti_aliasing": 4,
            "multi_gpu": False,
            "width": 960,
            "height": 540,
        }
    )
    sys.argv = saved
    try:
        import carb.settings
        import numpy as np
        import omni.physx
        import omni.usd
        from omni.isaac.core import World
        from omni.isaac.dynamic_control import _dynamic_control
        from omni.isaac.sensor import Camera
        from PIL import Image
        from pxr import UsdPhysics

        settings = carb.settings.get_settings()
        settings.set("/rtx/post/aa/autoExposureMode", 0)
        settings.set("/rtx/post/aa/exposureMultiplier", 0.9)
        context = omni.usd.get_context()
        scene = root / "vr/scene.usd"
        if not context.open_stage(str(scene)):
            raise RuntimeError(f"cannot open {scene}")
        while context.get_stage_loading_status()[2] > 0:
            app.update()
        for _ in range(40):
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
        tube_pose = dc.get_rigid_body_pose(tube)
        tube_q = (
            float(tube_pose.r.x),
            float(tube_pose.r.y),
            float(tube_pose.r.z),
            float(tube_pose.r.w),
        )
        start_offset = _q_rotate_xyzw(tube_q, (0.0, 0.0, START_RELATIVE_Z_M))
        start_position = tuple(
            float(getattr(tube_pose.p, axis)) + start_offset[index]
            for index, axis in enumerate(("x", "y", "z"))
        )
        target = (
            float(tube_pose.p.x),
            float(tube_pose.p.y),
            float(tube_pose.p.z) + 0.105,
        )
        position = (target[0] + 0.34, target[1] - 0.42, target[2] + 0.22)
        camera = Camera(
            prim_path="/World/__task08_r13_video_camera",
            name="task08_r13_video_camera",
            resolution=(960, 540),
        )
        camera.initialize()
        camera.set_focal_length(58.0)
        camera.set_horizontal_aperture(20.955)
        camera.set_vertical_aperture(11.784)
        camera.set_clipping_range(0.005, 100.0)
        camera.set_world_pose(
            position=np.asarray(position, dtype=float),
            orientation=np.asarray(_camera_quaternion(position, target), dtype=float),
        )
        # Camera initialization rebuilds the render product and can invalidate
        # the active physics scene and dynamic-control handles acquired before it.
        world.reset()
        for _ in range(8):
            world.step(render=False)
        dc = _dynamic_control.acquire_dynamic_control_interface()
        tube = dc.get_rigid_body(TUBE)
        cap = dc.get_rigid_body(CAP)
        print("TASK08_R13_VIDEO camera_ready", flush=True)
        frame_index = 0

        def write_frame() -> None:
            nonlocal frame_index
            for _ in range(4):
                world.step(render=(_ == 3))
            rgba = np.asarray(camera.get_rgba())
            if not rgba.size:
                raise RuntimeError("camera returned no frame")
            if rgba.dtype != np.uint8:
                rgba = np.clip(
                    rgba * 255.0 if rgba.max() <= 1.0 else rgba, 0, 255
                ).astype(np.uint8)
            Image.fromarray(rgba[..., :3]).save(frames / f"frame_{frame_index:04d}.png")
            frame_index += 1

        for _ in range(HOLD_START_FRAMES):
            dc.set_rigid_body_pose(
                cap, _dynamic_control.Transform(start_position, tube_q)
            )
            dc.set_rigid_body_linear_velocity(cap, (0.0, 0.0, 0.0))
            dc.set_rigid_body_angular_velocity(cap, (0.0, 0.0, 0.0))
            write_frame()
        print("TASK08_R13_VIDEO start_hold_complete", flush=True)
        for index in range(ROTATION_FRAMES):
            degree = 360.0 * (index + 1) / ROTATION_FRAMES
            cap_pose = dc.get_rigid_body_pose(cap)
            half = math.radians(-degree) * 0.5
            relative = (0.0, 0.0, math.sin(half), math.cos(half))
            target_q = _q_multiply(tube_q, relative)
            dc.set_rigid_body_pose(
                cap,
                _dynamic_control.Transform(
                    (float(cap_pose.p.x), float(cap_pose.p.y), float(cap_pose.p.z)),
                    target_q,
                ),
            )
            write_frame()
        for _ in range(HOLD_CLOSED_FRAMES):
            write_frame()
        lift_start = dc.get_rigid_body_pose(tube)
        for index in range(LIFT_FRAMES):
            fraction = float(index + 1) / LIFT_FRAMES
            dc.set_rigid_body_pose(
                tube,
                _dynamic_control.Transform(
                    (
                        float(lift_start.p.x),
                        float(lift_start.p.y),
                        float(lift_start.p.z) + 0.05 * fraction,
                    ),
                    (
                        float(lift_start.r.x),
                        float(lift_start.r.y),
                        float(lift_start.r.z),
                        float(lift_start.r.w),
                    ),
                ),
            )
            write_frame()
        for _ in range(HOLD_LIFTED_FRAMES):
            write_frame()
        state = _contract(stage)
        video = evidence / "task08_r13_one_turn_assisted_thread.mp4"
        completed = subprocess.run(
            [
                "/usr/bin/ffmpeg",
                "-y",
                "-framerate",
                str(FPS),
                "-i",
                str(frames / "frame_%04d.png"),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-crf",
                "18",
                str(video),
            ],
            text=True,
            capture_output=True,
        )
        if completed.returncode:
            raise RuntimeError(completed.stderr)
        shutil.rmtree(frames)
        manifest = {
            "schema_version": "scenario-forge.task08-r13-video-evidence/v0.1",
            "status": "pass" if state["state"] == "closed" else "fail",
            "runtime": "isaac41",
            "renderer": "RayTracedLighting",
            "resolution": [960, 540],
            "fps": FPS,
            "frames": frame_index,
            "terminal": state,
            "video": video.relative_to(root).as_posix(),
            "sha256": sha256(video.read_bytes()).hexdigest(),
        }
        (evidence / "task08_r13_one_turn_video_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        )
        print(video, flush=True)
        return 0 if manifest["status"] == "pass" else 2
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())

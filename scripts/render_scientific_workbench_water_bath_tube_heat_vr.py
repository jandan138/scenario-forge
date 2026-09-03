#!/usr/bin/env python3
"""Render Isaac 4.1 evidence from a captured physical water-bath trajectory."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback


FPS = 30
RESOLUTION = (960, 540)
TUBE = "/World/obj_sample_tube"
PARTICLES = "/World/fluid_runtime/ParticleSets/beaker_liquid"
BEAKER = "/World/obj_beaker"


def _camera_quaternion(position, target):
    import numpy as np
    from scipy.spatial.transform import Rotation

    offset = np.asarray(position) - np.asarray(target)
    elevation = math.degrees(math.asin(float(offset[2]) / np.linalg.norm(offset)))
    azimuth = math.degrees(math.atan2(float(offset[1]), float(offset[0])))
    quaternion = Rotation.from_euler(
        "xyz", [0.0, elevation, azimuth - 180.0], degrees=True
    ).as_quat()
    return (quaternion[3], quaternion[0], quaternion[1], quaternion[2])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--state-capture", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    capture_path = args.state_capture.resolve()
    initial_evidence = root / "vr/evidence/initial_scene"
    runtime_evidence = root / "vr/evidence/runtime"
    frames = runtime_evidence / "water_bath_video_frames"
    if frames.exists():
        raise FileExistsError(frames)
    initial_evidence.mkdir(parents=True, exist_ok=True)
    frames.mkdir(parents=True)

    original = sys.argv
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp

    app = SimulationApp(
        {
            "headless": True,
            "renderer": "RayTracedLighting",
            "anti_aliasing": 4,
            "multi_gpu": False,
            "width": RESOLUTION[0],
            "height": RESOLUTION[1],
        }
    )
    sys.argv = original
    try:
        import carb.settings
        import numpy as np
        import omni.kit.app
        import omni.replicator.core as rep
        import omni.usd
        from omni.isaac.sensor import Camera
        from PIL import Image
        from pxr import Gf, Usd, UsdGeom

        kit_version = str(omni.kit.app.get_app().get_app_version())
        if not kit_version.startswith("4.1"):
            raise RuntimeError(f"water-bath renderer requires Isaac Sim 4.1: {kit_version}")
        captured = np.load(capture_path)
        tube_xyz = np.asarray(captured["tube_xyz"], dtype=np.float32)
        particle_points = np.asarray(captured["particle_points"], dtype=np.float32)
        if (
            tube_xyz.ndim != 2
            or tube_xyz.shape[1] != 3
            or particle_points.shape != (len(tube_xyz), 969, 3)
        ):
            raise ValueError(
                f"unexpected state capture shapes: {tube_xyz.shape}, {particle_points.shape}"
            )

        settings = carb.settings.get_settings()
        settings.set("/rtx/post/aa/autoExposureMode", 0)
        settings.set("/rtx/post/aa/exposureMultiplier", 0.82)
        settings.set("/rtx/post/histogram/enabled", False)
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
        tube_translate = stage.GetPrimAtPath(TUBE).GetAttribute("xformOp:translate")
        particle_prim = stage.GetPrimAtPath(PARTICLES)
        points_attr = particle_prim.GetAttribute("points")
        simulation_points_attr = particle_prim.GetAttribute(
            "physxParticle:simulationPoints"
        )
        extent_attr = particle_prim.GetAttribute("extent")

        camera = Camera(
            prim_path="/World/__water_bath_replay_camera",
            name="water_bath_replay_camera",
            resolution=RESOLUTION,
        )
        camera.initialize()
        camera.set_horizontal_aperture(20.955)
        camera.set_vertical_aperture(11.784)
        camera.set_clipping_range(0.005, 100.0)
        for _ in range(20):
            app.update()
        for _ in range(4):
            rep.orchestrator.step(
                rt_subframes=4, pause_timeline=True, delta_time=0.0
            )

        def set_camera(position, target, focal) -> None:
            camera.set_focal_length(focal)
            camera.set_world_pose(
                position=np.asarray(position, dtype=float),
                orientation=np.asarray(
                    _camera_quaternion(position, target), dtype=float
                ),
            )

        def render_rgb(rt_subframes: int = 2):
            rep.orchestrator.step(
                rt_subframes=rt_subframes, pause_timeline=True, delta_time=0.0
            )
            value = np.asarray(camera.get_rgba())
            if not value.size:
                raise RuntimeError("water-bath replay camera returned no frame")
            if value.dtype != np.uint8:
                value = np.clip(
                    value * 255.0 if value.max() <= 1.0 else value, 0, 255
                ).astype(np.uint8)
            return value[..., :3]

        views = {
            "scene_overview": ((1.35, -2.05, 1.75), (0.12, -0.03, 0.84), 31.0),
            "water_bath_closeup": ((0.90, -1.02, 1.18), (0.34, -0.03, 0.86), 49.0),
            "single_tube_rack": ((0.38, -0.82, 1.13), (0.08, -0.14, 0.84), 55.0),
        }
        image_records = {}
        for name, (position, target, focal) in views.items():
            set_camera(position, target, focal)
            for _ in range(4):
                app.update()
            render_rgb(2)
            path = initial_evidence / f"{name}.png"
            Image.fromarray(render_rgb(4)).save(path)
            image_records[name] = {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256(path.read_bytes()).hexdigest(),
            }

        video_position = (1.02, -1.52, 1.28)
        video_target = (0.18, -0.06, 0.90)
        set_camera(video_position, video_target, 36.0)
        for _ in range(4):
            app.update()
        render_rgb(2)
        immersed_indices = np.flatnonzero(
            (np.abs(tube_xyz[:, 0] - 0.37) < 0.002)
            & (np.abs(tube_xyz[:, 1] + 0.028) < 0.002)
            & (np.abs(tube_xyz[:, 2] - 0.848) < 0.002)
        )
        if not len(immersed_indices):
            raise ValueError("captured trajectory has no immersed state")
        immersed_index = int(immersed_indices[len(immersed_indices) // 2])

        for frame_index in range(len(tube_xyz)):
            tube_translate.Set(Gf.Vec3d(*[float(value) for value in tube_xyz[frame_index]]))
            frame_points = particle_points[frame_index]
            authored_points = [
                Gf.Vec3f(*[float(value) for value in point]) for point in frame_points
            ]
            points_attr.Set(authored_points)
            simulation_points_attr.Set(authored_points)
            minimum = frame_points.min(axis=0)
            maximum = frame_points.max(axis=0)
            extent_attr.Set(
                [
                    Gf.Vec3f(*[float(value) for value in minimum]),
                    Gf.Vec3f(*[float(value) for value in maximum]),
                ]
            )
            image = render_rgb(1)
            Image.fromarray(image).save(frames / f"frame_{frame_index:04d}.png")
            if frame_index == immersed_index:
                immersed_path = initial_evidence / "tube_immersed_in_pbd_water.png"
                Image.fromarray(image).save(immersed_path)
                image_records["tube_immersed_in_pbd_water"] = {
                    "path": immersed_path.relative_to(root).as_posix(),
                    "sha256": sha256(immersed_path.read_bytes()).hexdigest(),
                }

        video = runtime_evidence / "water_bath_tube_immersion_isaac41.mp4"
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

        final_points = particle_points[-1]
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
            for point in final_points
        )
        retention = inside / len(final_points)
        status = "pass" if retention >= 0.95 else "blocked"
        manifest = {
            "schema_version": "scenario-forge.water-bath-render/v0.2",
            "status": status,
            "runtime": {"name": "isaac41", "kit_version": kit_version},
            "method": "captured_isaac41_physics_state_replay",
            "state_capture": {
                "path": capture_path.relative_to(root).as_posix(),
                "sha256": sha256(capture_path.read_bytes()).hexdigest(),
            },
            "renderer": "RayTracedLighting",
            "resolution": list(RESOLUTION),
            "images": image_records,
            "video": {
                "path": video.relative_to(root).as_posix(),
                "sha256": sha256(video.read_bytes()).hexdigest(),
                "fps": FPS,
                "frames": len(tube_xyz),
            },
            "terminal_particle_count": len(final_points),
            "terminal_particle_retention": retention,
            "claims": {
                "robot_free_physics_state_replay": status == "pass",
                "live_camera_physics_capture": False,
                "robot_policy_success": False,
                "benchmark_success": False,
            },
        }
        destination = runtime_evidence / "render_manifest.json"
        destination.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        print(video, flush=True)
        return 0 if status == "pass" else 5
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

#!/usr/bin/env python3
"""Render fixed review views for Task 08 r12 before or after physics settling."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys


VIEWS = (
    ("scene_overview", (-1.55, -2.35, 2.05), (0.0, 0.0, 0.86), 20.0),
    ("tabletop_wide", (0.85, -1.60, 1.34), (0.0, -0.08, 0.82), 34.0),
    ("rack_closeup", (0.52, -0.92, 1.02), (0.15, -0.14, 0.82), 52.0),
    ("tray_closeup", (-0.58, -0.90, 1.00), (-0.23, -0.17, 0.79), 52.0),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--evidence-subdir", default="initial_scene")
    parser.add_argument("--run-seconds", type=float, default=0.0)
    args = parser.parse_args()
    root = args.root.resolve()
    original = sys.argv
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp

    app = SimulationApp(
        {
            "headless": True,
            "renderer": "RayTracedLighting",
            "anti_aliasing": 4,
            "multi_gpu": False,
            "width": 1280,
            "height": 720,
        }
    )
    sys.argv = original
    try:
        import carb.settings
        import numpy as np
        import omni.physx
        import omni.replicator.core as rep
        import omni.usd
        from omni.isaac.core import World
        from omni.isaac.sensor import Camera
        from PIL import Image
        from scipy.spatial.transform import Rotation

        settings = carb.settings.get_settings()
        settings.set("/rtx/post/aa/autoExposureMode", 0)
        settings.set("/rtx/post/aa/exposureMultiplier", 0.8)
        settings.set("/rtx/post/histogram/enabled", False)
        scene = root / "vr/scene.usd"
        context = omni.usd.get_context()
        if not context.open_stage(str(scene)):
            raise RuntimeError(f"cannot open {scene}")
        for _ in range(50):
            app.update()
        if args.run_seconds > 0:
            world = World(
                stage_units_in_meters=1.0,
                physics_prim_path="/World/physicsScene",
                set_defaults=False,
                physics_dt=1 / 120,
                rendering_dt=1 / 120,
            )
            omni.physx.get_physx_interface().overwrite_gpu_setting(1)
            world.reset()
            for _ in range(round(args.run_seconds * 120)):
                world.step(render=False)
        evidence = root / "vr/evidence" / args.evidence_subdir
        evidence.mkdir(parents=True, exist_ok=True)
        cameras = []
        for index, (name, position, target, focal) in enumerate(VIEWS):
            camera = Camera(
                prim_path=f"/World/__evidence_camera_{index}",
                name=name,
                resolution=(1280, 720),
            )
            camera.initialize()
            camera.set_focal_length(focal)
            camera.set_horizontal_aperture(20.955)
            camera.set_vertical_aperture(11.784)
            distance = math.dist(position, target)
            camera.set_clipping_range(0.005, max(100.0, distance * 20.0))
            offset = np.asarray(position) - np.asarray(target)
            elevation = math.degrees(math.asin(float(offset[2]) / np.linalg.norm(offset)))
            azimuth = math.degrees(math.atan2(float(offset[1]), float(offset[0])))
            quat = Rotation.from_euler(
                "xyz", [0.0, elevation, azimuth - 180.0], degrees=True
            ).as_quat()
            camera.set_world_pose(
                position=np.asarray(position, dtype=float),
                orientation=np.asarray([quat[3], quat[0], quat[1], quat[2]]),
            )
            cameras.append((name, camera, position, target, focal))
        for _ in range(20):
            app.update()
        for _ in range(4):
            rep.orchestrator.step(rt_subframes=4, pause_timeline=True, delta_time=0.0)
        records = {}
        for name, camera, position, target, focal in cameras:
            rep.orchestrator.step(rt_subframes=4, pause_timeline=True, delta_time=0.0)
            rgba = camera.get_rgba()
            if not isinstance(rgba, np.ndarray) or not rgba.size:
                raise RuntimeError(f"camera returned no frame: {name}")
            array = np.asarray(rgba)
            if array.dtype != np.uint8:
                array = np.clip(
                    array * 255.0 if array.max() <= 1.0 else array, 0, 255
                ).astype(np.uint8)
            path = evidence / f"{name}.png"
            Image.fromarray(array[..., :3]).save(path)
            records[name] = {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256(path.read_bytes()).hexdigest(),
                "position_xyz": position,
                "target_xyz": target,
                "focal_length_mm": focal,
            }
        (evidence / "render_manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": "scenario-forge.fixed-scene-render.v1",
                    "status": "pass",
                    "runtime": "isaac41",
                    "renderer": "RayTracedLighting",
                    "resolution": [1280, 720],
                    "physics_settle_seconds": args.run_seconds,
                    "views": records,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        print(evidence)
        return 0
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())

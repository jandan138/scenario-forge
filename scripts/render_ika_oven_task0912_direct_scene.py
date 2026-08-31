#!/usr/bin/env python3
"""Render the closed overview and open interior of the direct-stage oven scene."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys


VIEWS = (
    (
        "closed_overview",
        "scene.usd",
        (2.6, -3.5, 2.25),
        (0.0, 0.0, 0.70),
        26.0,
    ),
    (
        "open_interior",
        "scene_open_preview.usd",
        (-0.72, -1.30, 1.34),
        (0.0, -0.02, 1.14),
        38.0,
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
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
        import omni.replicator.core as rep
        import omni.usd
        from omni.isaac.sensor import Camera
        from PIL import Image
        from scipy.spatial.transform import Rotation

        settings = carb.settings.get_settings()
        settings.set("/app/omni.graph.scriptnode/opt_in", False)
        settings.set("/rtx/post/aa/autoExposureMode", 0)
        settings.set("/rtx/post/aa/exposureMultiplier", 0.88)
        context = omni.usd.get_context()
        evidence = root / "evidence/initial_scene"
        evidence.mkdir(parents=True, exist_ok=True)
        records = {}
        for index, (name, scene_name, position, target, focal) in enumerate(VIEWS):
            scene = root / scene_name
            if not context.open_stage(str(scene)):
                raise RuntimeError(f"cannot open {scene}")
            while context.get_stage_loading_status()[2] > 0:
                app.update()
            for _ in range(30):
                app.update()
            camera = Camera(
                prim_path=f"/World/__ika_oven_camera_{index}",
                name=name,
                resolution=(1280, 720),
            )
            camera.initialize()
            camera.set_focal_length(focal)
            camera.set_horizontal_aperture(20.955)
            camera.set_vertical_aperture(11.784)
            camera.set_clipping_range(0.005, 100.0)
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
            for _ in range(4):
                rep.orchestrator.step(
                    rt_subframes=4, pause_timeline=True, delta_time=0.0
                )
            array = np.asarray(camera.get_rgba())
            if array.dtype != np.uint8:
                array = np.clip(
                    array * 255.0 if array.max() <= 1.0 else array, 0, 255
                ).astype(np.uint8)
            path = evidence / f"{name}.png"
            Image.fromarray(array[..., :3]).save(path)
            records[name] = {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256(path.read_bytes()).hexdigest(),
                "scene": scene_name,
                "position_xyz": list(position),
                "target_xyz": list(target),
                "focal_length_mm": focal,
            }
        destination = evidence / "render_manifest.json"
        destination.write_text(
            json.dumps(
                {
                    "schema_version": "scenario-forge-ika-oven-direct-render/v0.1",
                    "status": "pass",
                    "runtime": "isaac41",
                    "renderer": "RayTracedLighting",
                    "resolution": [1280, 720],
                    "views": records,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print(destination)
        return 0
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())

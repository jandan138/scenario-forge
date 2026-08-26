#!/usr/bin/env python3
"""Render matched pre-Run and post-Run Task 11 r8 review views."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys


VIEWS = (
    ("scene_overview", (1.35, -1.85, 1.55), (0.0, 0.0, 0.90), 28.0),
    ("tabletop_wide", (0.0, -2.20, 1.65), (0.0, 0.0, 0.88), 30.0),
    ("device_closeup", (0.85, -1.15, 1.22), (0.0, -0.10, 0.96), 48.0),
    ("rotor_liquid_closeup", (0.55, -0.82, 1.38), (0.0, -0.10, 1.02), 52.0),
    ("tube_liquid_closeup", (0.62, -0.82, 1.02), (0.35, -0.35, 0.82), 70.0),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--state",
        choices=("before", "after", "open_review", "liquid_review"),
        required=True,
    )
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
        from pxr import Gf
        from scipy.spatial.transform import Rotation

        settings = carb.settings.get_settings()
        settings.set("/rtx/post/aa/autoExposureMode", 0)
        settings.set("/rtx/post/aa/exposureMultiplier", 0.8)
        scene = root / "vr/scene.usd"
        context = omni.usd.get_context()
        if not context.open_stage(str(scene)):
            raise RuntimeError(f"cannot open {scene}")
        while context.get_stage_loading_status()[2] > 0:
            app.update()
        for _ in range(40):
            app.update()
        if args.state == "open_review":
            stage = context.get_stage()
            stage.SetEditTarget(stage.GetSessionLayer())
            angle = -1.361356817
            stage.GetPrimAtPath(
                "/World/obj_centrifuge/lid_link"
            ).GetAttribute("xformOp:orient").Set(
                Gf.Quatf(
                    math.cos(angle * 0.5),
                    Gf.Vec3f(math.sin(angle * 0.5), 0.0, 0.0),
                )
            )
            for _ in range(20):
                app.update()
        if args.state == "liquid_review":
            stage = context.get_stage()
            stage.SetEditTarget(stage.GetSessionLayer())
            tube = stage.GetPrimAtPath("/World/obj_primary_tube")
            tube.GetAttribute("xformOp:translate").Set(Gf.Vec3d(0.35, -0.35, 0.755))
            tube.GetAttribute("xformOp:orient").Set(Gf.Quatf(1.0, Gf.Vec3f(0.0)))
            for _ in range(20):
                app.update()
        if args.state == "after":
            world = World(
                stage_units_in_meters=1.0,
                physics_prim_path="/World/physicsScene",
                set_defaults=False,
                physics_dt=1 / 120,
                rendering_dt=1 / 120,
            )
            omni.physx.get_physx_interface().overwrite_gpu_setting(1)
            world.reset()
            for _ in range(360):
                world.step(render=True)

        evidence = root / "vr/evidence/initial_scene"
        evidence.mkdir(parents=True, exist_ok=True)
        cameras = []
        for index, (name, position, target, focal) in enumerate(VIEWS):
            camera = Camera(
                prim_path=f"/World/__task11_r8_evidence_camera_{index}",
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
            cameras.append((name, camera, position, target, focal))

        manifest_path = evidence / "render_manifest.json"
        records = (
            json.loads(manifest_path.read_text()).get("views", {})
            if manifest_path.exists()
            else {}
        )
        prefix = {
            "before": "",
            "after": "after_run_",
            "open_review": "open_review_",
            "liquid_review": "liquid_review_",
        }[args.state]
        for _ in range(4):
            rep.orchestrator.step(rt_subframes=4, pause_timeline=True, delta_time=0.0)
        for name, camera, position, target, focal in cameras:
            array = np.asarray(camera.get_rgba())
            if array.dtype != np.uint8:
                array = np.clip(
                    array * 255.0 if array.max() <= 1.0 else array, 0, 255
                ).astype(np.uint8)
            filename = f"{prefix}{name}.png"
            path = evidence / filename
            Image.fromarray(array[..., :3]).save(path)
            records[filename] = {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256(path.read_bytes()).hexdigest(),
                "position_xyz": position,
                "target_xyz": target,
                "focal_length_mm": focal,
            }
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": "scenario-forge.task11-r8-render.v1",
                    "status": "pass",
                    "runtime": "isaac41",
                    "renderer": "RayTracedLighting",
                    "scene_usd_sha256": sha256(scene.read_bytes()).hexdigest(),
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

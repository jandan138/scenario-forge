#!/usr/bin/env python3
"""Camera-only paper retake of the admitted Task 12 OVEN 125 scene.

Opens the current-delivery scene unchanged, drives the door with the same
hinge command as the evidence renderer, and captures paper views that match
the manufacturer's front three-quarter open-door photograph.  It never edits
scene state, geometry, materials, or physics, and it writes outside the
delivery tree so formal evidence is untouched.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys


OVEN_BOUND = ((1.16, -0.44, 0.53), (1.86, 0.36, 1.35))
DOOR_HINGE = "/World/obj_oven/Instance/Joints/DoorHinge"
EXPOSURE_MULTIPLIER = 1.08


def oven_center() -> tuple[float, float, float]:
    low, high = OVEN_BOUND
    return tuple((a + b) / 2.0 for a, b in zip(low, high))


def three_quarter_view(
    name: str, *, azimuth_deg: float, elevation_deg: float, distance: float, focal: float
):
    """Front-left three-quarter view aimed at the open oven plus its swung door."""
    cx, cy, cz = oven_center()
    # The open door swings toward -y, so aim slightly in front of the body.
    target = (cx + 0.04, cy - 0.30, cz)
    azimuth = math.radians(azimuth_deg)
    elevation = math.radians(elevation_deg)
    position = (
        target[0] - distance * math.cos(elevation) * math.sin(azimuth),
        target[1] - distance * math.cos(elevation) * math.cos(azimuth),
        target[2] + distance * math.sin(elevation),
    )
    return (name, position, target, focal)


def paper_open_views():
    """Candidate hero views; each keeps the whole body and open door in frame."""
    return (
        three_quarter_view(
            "hero_open_threequarter", azimuth_deg=35.0, elevation_deg=18.0, distance=2.6, focal=28.0
        ),
        three_quarter_view(
            "hero_open_wide", azimuth_deg=42.0, elevation_deg=21.0, distance=2.9, focal=28.0
        ),
        three_quarter_view(
            "hero_open_tight", azimuth_deg=30.0, elevation_deg=15.0, distance=2.35, focal=26.0
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="handoff root with scene.usd")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    out = args.out.resolve()
    scene = root / "scene.usd"
    scene_sha256 = sha256(scene.read_bytes()).hexdigest()

    original = sys.argv
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp

    app = SimulationApp(
        {
            "headless": True,
            "renderer": "RayTracedLighting",
            "anti_aliasing": 4,
            "multi_gpu": False,
            "width": 1920,
            "height": 1080,
        }
    )
    sys.argv = original
    try:
        import carb.settings
        import numpy as np
        import omni.kit.app
        import omni.replicator.core as rep
        import omni.timeline
        import omni.usd
        from omni.isaac.sensor import Camera
        from PIL import Image
        from scipy.spatial.transform import Rotation

        settings = carb.settings.get_settings()
        settings.set_bool("/app/omni.graph.scriptnode/enable_opt_in", False)
        settings.set_bool("/app/omni.graph.scriptnode/opt_in", True)
        settings.set_bool("/app/scripting/ignoreWarningDialog", True)
        settings.set("/rtx/post/aa/autoExposureMode", 0)
        settings.set("/rtx/post/aa/exposureMultiplier", EXPOSURE_MULTIPLIER)
        kit_version = str(omni.kit.app.get_app().get_app_version())
        manager = omni.kit.app.get_app().get_extension_manager()
        for extension in ("omni.graph.action_nodes", "omni.graph.scriptnode"):
            manager.set_extension_enabled_immediate(extension, True)
        context = omni.usd.get_context()
        if not context.open_stage(str(scene)):
            raise RuntimeError(f"cannot open {scene}")
        while context.get_stage_loading_status()[2] > 0:
            app.update()
        for _ in range(30):
            app.update()
        stage = context.get_stage()
        out.mkdir(parents=True, exist_ok=True)

        timeline = omni.timeline.get_timeline_interface()
        timeline.play()
        for _ in range(30):
            app.update()
        timeline.pause()
        velocity = stage.GetPrimAtPath(DOOR_HINGE).GetAttribute(
            "drive:angular:physics:targetVelocity"
        )
        velocity.Set(45.0)
        timeline.play()
        for _ in range(180):
            app.update()
        velocity.Set(0.0)
        timeline.pause()

        records = {}
        for index, (name, position, target, focal) in enumerate(paper_open_views()):
            camera = Camera(
                prim_path=f"/World/__lab2sim_paper_camera_{index}",
                name=name,
                resolution=(1920, 1080),
            )
            camera.initialize()
            camera.set_focal_length(focal)
            camera.set_horizontal_aperture(20.955)
            camera.set_vertical_aperture(11.784)
            camera.set_clipping_range(0.005, 100.0)
            delta = np.asarray(position) - np.asarray(target)
            elevation = math.degrees(math.asin(float(delta[2]) / np.linalg.norm(delta)))
            azimuth = math.degrees(math.atan2(float(delta[1]), float(delta[0])))
            quat = Rotation.from_euler(
                "xyz", [0.0, elevation, azimuth - 180.0], degrees=True
            ).as_quat()
            camera.set_world_pose(
                position=np.asarray(position, dtype=float),
                orientation=np.asarray([quat[3], quat[0], quat[1], quat[2]]),
            )
            for _ in range(6):
                rep.orchestrator.step(rt_subframes=6, pause_timeline=True, delta_time=0.0)
            array = np.asarray(camera.get_rgba())
            if array.dtype != np.uint8:
                array = np.clip(
                    array * 255.0 if array.max() <= 1.0 else array, 0, 255
                ).astype(np.uint8)
            path = out / f"{name}.png"
            Image.fromarray(array[..., :3]).save(path)
            records[name] = {
                "path": path.name,
                "sha256": sha256(path.read_bytes()).hexdigest(),
                "position_xyz": [round(v, 4) for v in position],
                "target_xyz": [round(v, 4) for v in target],
                "focal_length_mm": focal,
            }
        timeline.stop()
        manifest = out / "render_manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": "lab2sim-fig3-camera-retake/v1",
                    "status": "pass",
                    "camera_only": True,
                    "scene": str(scene),
                    "scene_sha256": scene_sha256,
                    "door_command": {"prim": DOOR_HINGE, "target_velocity": 45.0, "frames": 180},
                    "runtime": {"name": "isaac45", "kit_version": kit_version},
                    "renderer": "RayTracedLighting",
                    "exposure_multiplier": EXPOSURE_MULTIPLIER,
                    "resolution": [1920, 1080],
                    "robot_policy_success": False,
                    "views": records,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print(manifest)
        return 0
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())

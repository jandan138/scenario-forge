#!/usr/bin/env python3
"""Render fixed closed, open-interior, and control views for Task 12."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import traceback


CLOSED_VIEWS = (
    ("scene_overview", (2.15, -2.35, 2.45), (0.75, 0.0, 0.70), 24.0),
    ("completed_control_panel", (2.15, -1.30, 1.40), (1.51, -0.31, 1.20), 50.0),
)
OPEN_VIEWS = (
    ("lower_shelf_dual_glassware", (0.92, -1.42, 1.18), (1.51, -0.02, 0.91), 43.0),
    ("open_oven_station", (0.72, -2.05, 1.55), (1.45, -0.02, 0.86), 34.0),
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
        settings.set("/rtx/post/aa/exposureMultiplier", 0.92)
        manager = omni.kit.app.get_app().get_extension_manager()
        kit_version = str(omni.kit.app.get_app().get_app_version())
        if not kit_version.startswith("4.1"):
            raise RuntimeError(
                f"Task12 evidence renderer requires Isaac Sim 4.1, found {kit_version}"
            )
        for extension in ("omni.graph.action_nodes", "omni.graph.scriptnode"):
            manager.set_extension_enabled_immediate(extension, True)
        context = omni.usd.get_context()
        scene = root / "scene.usd"
        if not context.open_stage(str(scene)):
            raise RuntimeError(f"cannot open {scene}")
        while context.get_stage_loading_status()[2] > 0:
            app.update()
        for _ in range(30):
            app.update()
        stage = context.get_stage()
        evidence = root / "evidence/initial_scene"
        evidence.mkdir(parents=True, exist_ok=True)
        records = {}

        timeline = omni.timeline.get_timeline_interface()
        timeline.play()
        for _ in range(30):
            app.update()
        timeline.pause()

        def capture(views, offset_index: int) -> None:
            for index, (name, position, target, focal) in enumerate(views, offset_index):
                camera = Camera(
                    prim_path=f"/World/__task12_oven_camera_{index}",
                    name=name,
                    resolution=(1280, 720),
                )
                camera.initialize()
                camera.set_focal_length(focal)
                camera.set_horizontal_aperture(20.955)
                camera.set_vertical_aperture(11.784)
                camera.set_clipping_range(0.005, 100.0)
                delta = np.asarray(position) - np.asarray(target)
                elevation = math.degrees(
                    math.asin(float(delta[2]) / np.linalg.norm(delta))
                )
                azimuth = math.degrees(math.atan2(float(delta[1]), float(delta[0])))
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
                    "position_xyz": list(position),
                    "target_xyz": list(target),
                    "focal_length_mm": focal,
                }

        capture(CLOSED_VIEWS, 0)
        velocity = stage.GetPrimAtPath(
            "/World/obj_oven/Instance/Joints/DoorHinge"
        ).GetAttribute("drive:angular:physics:targetVelocity")
        velocity.Set(45.0)
        timeline.play()
        for _ in range(180):
            app.update()
        velocity.Set(0.0)
        timeline.pause()
        capture(OPEN_VIEWS, len(CLOSED_VIEWS))
        timeline.stop()

        manifest = evidence / "render_manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": "scenario-forge-task12-oven-render/v0.1",
                    "status": "pass",
                    "runtime": {"name": "isaac41", "kit_version": kit_version},
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
        print(manifest)
        return 0
    except BaseException:
        traceback.print_exc()
        raise
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())

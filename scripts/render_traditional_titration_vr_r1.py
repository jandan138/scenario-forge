#!/usr/bin/env python3
"""Render fixed overview, interaction, and endpoint evidence for titration r1."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys


VIEWS = (
    ("scene_overview", (1.55, -2.05, 1.80), (0.0, 0.02, 0.90), 30.0),
    ("titration_workspace", (0.82, -1.15, 1.28), (-0.04, 0.03, 0.96), 48.0),
    ("stopcock_closeup", (0.48, -0.72, 1.28), (-0.03, 0.03, 1.04), 64.0),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    render_scene = root / ".titration_render_scene.usda"
    source_text = (root / "scene.usd").read_text(encoding="utf-8")
    graph_header = 'def OmniGraph "TitrationFlowGraph"\n'
    if source_text.count(graph_header) != 1:
        raise ValueError("expected one materialized TitrationFlowGraph")
    render_scene.write_text(
        source_text.replace(
            graph_header,
            'def OmniGraph "TitrationFlowGraph" (\n    active = false\n)\n',
            1,
        ),
        encoding="utf-8",
    )
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

        try:
            from isaacsim.sensors.camera import Camera
        except ImportError:
            from omni.isaac.sensor import Camera
        from PIL import Image
        from pxr import Gf, Usd, UsdGeom
        from scipy.spatial.transform import Rotation

        settings = carb.settings.get_settings()
        settings.set_bool("/app/omni.graph.scriptnode/enable_opt_in", False)
        settings.set_bool("/app/omni.graph.scriptnode/opt_in", True)
        settings.set("/rtx/post/aa/autoExposureMode", 0)
        settings.set("/rtx/post/aa/exposureMultiplier", 0.92)
        context = omni.usd.get_context()
        if not context.open_stage(str(render_scene)):
            raise RuntimeError("cannot open titration scene")
        stage = context.get_stage()
        stage.SetEditTarget(Usd.EditTarget(stage.GetSessionLayer()))
        while context.get_stage_loading_status()[2] > 0:
            app.update()
        for _ in range(30):
            app.update()
        evidence = root / "evidence/initial_scene"
        evidence.mkdir(parents=True, exist_ok=True)
        camera = Camera(
            prim_path="/World/__titration_evidence_camera",
            name="titration_evidence_camera",
            resolution=(1280, 720),
        )
        camera.initialize()
        camera.set_horizontal_aperture(20.955)
        camera.set_vertical_aperture(11.784)
        camera.set_clipping_range(0.005, 100.0)

        def set_camera(position, target, focal):
            camera.set_focal_length(focal)
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

        def capture(path: Path) -> None:
            for _ in range(4):
                rep.orchestrator.step(rt_subframes=4, pause_timeline=True, delta_time=0.0)
            array = np.asarray(camera.get_rgba())
            if array.dtype != np.uint8:
                array = np.clip(array * 255.0 if array.max() <= 1.0 else array, 0, 255).astype(
                    np.uint8
                )
            Image.fromarray(array[..., :3]).save(path)

        records = {}
        for name, position, target, focal in VIEWS:
            set_camera(position, target, focal)
            capture(evidence / f"{name}.png")
            path = evidence / f"{name}.png"
            records[name] = {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256(path.read_bytes()).hexdigest(),
                "position_xyz": list(position),
                "target_xyz": list(target),
                "focal_length_mm": focal,
                "state": "initial_colorless_closed",
            }

        for suffix in ("Colorless", "Transition", "EndpointPalePink", "Overshoot"):
            visual = stage.GetPrimAtPath(f"/World/obj_receiver_flask/VisualLiquid/Solution{suffix}")
            UsdGeom.Imageable(visual).GetVisibilityAttr().Set(
                "inherited" if suffix == "EndpointPalePink" else "invisible"
            )
        column = stage.GetPrimAtPath(
            "/World/obj_titration_station/Instance/Burette/body_link/Visual/liquid_column"
        )
        UsdGeom.Cylinder(column).GetHeightAttr().Set(0.128)
        column.GetAttribute("xformOp:translate").Set(Gf.Vec3d(0.0, 0.0, -0.026))
        for _ in range(30):
            app.update()
        set_camera((0.82, -1.15, 1.28), (-0.04, 0.03, 0.96), 48.0)
        endpoint = evidence / "endpoint_pale_pink.png"
        capture(endpoint)
        records["endpoint_pale_pink"] = {
            "path": endpoint.relative_to(root).as_posix(),
            "sha256": sha256(endpoint.read_bytes()).hexdigest(),
            "state": "15.0_ml_closed_pale_pink_visual_snapshot",
        }

        manifest = evidence / "render_manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": "scenario-forge-titration-render/v0.1",
                    "status": "pass",
                    "runtime": app.app.get_app_version(),
                    "renderer": "RayTracedLighting",
                    "resolution": [1280, 720],
                    "views": records,
                    "claims": {
                        "isaac_rendered": True,
                        "endpoint_frame_is_visual_state_snapshot": True,
                        "robot_policy_success": False,
                    },
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
        render_scene.unlink(missing_ok=True)
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())

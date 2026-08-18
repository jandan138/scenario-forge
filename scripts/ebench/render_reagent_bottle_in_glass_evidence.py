#!/usr/bin/env python3
"""Render the incoming reagent bottle in the glass-guide evidence setup."""

from __future__ import annotations

from hashlib import sha256
import importlib.metadata
import json
import math
from pathlib import Path
import shutil
import sys
import tarfile
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scenario_forge.generation.glass_material_evidence import (  # noqa: E402
    build_evidence_scene,
)


CONVERT_ROOT = Path("/cpfs/user/zhuzihou/dev/ConvertAsset")
ROOM = CONVERT_ROOT / "outputs/generated_scientific_labs_v2_20260804/modern_wet_chemistry/package/asset.usd"
TABLE = CONVERT_ROOT / "outputs/scientific_workbench_standard_table_20260811/package/asset.usd"
TARBALL = REPO_ROOT / "external_artifacts/incoming/manual_glassware_v1.tar.gz"
OUTPUT = (
    REPO_ROOT
    / "outputs/scientific_workbench_glass_material_bottle_recipe_20260818/evidence/comparisons"
)


def _extract_bottle(staging: Path) -> Path:
    incoming = staging / "incoming"
    if incoming.exists():
        shutil.rmtree(incoming)
    incoming.mkdir(parents=True)
    with tarfile.open(TARBALL, "r:gz") as archive:
        archive.extractall(incoming)
    bottle = incoming / "manual_glassware_v1/simready/reagent_bottle_90x55.usdc"
    if not bottle.is_file():
        raise FileNotFoundError(bottle)
    wrapper = staging / "reagent_bottle_world.usda"
    wrapper.write_text(
        "#usda 1.0\n"
        "(\n"
        '    defaultPrim = "World"\n'
        "    metersPerUnit = 1\n"
        '    upAxis = "Z"\n'
        ")\n"
        "\n"
        'def Xform "World"\n'
        "{\n"
        '    def Xform "ReagentBottle" (\n'
        f"        prepend references = @{bottle.resolve()}@</ObjectRoot>\n"
        "    )\n"
        "    {\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    return wrapper


def _look_at_orientation(*, position: Any, target: Any, Rotation: Any, np: Any) -> Any:
    offset = np.asarray(position, dtype=float) - np.asarray(target, dtype=float)
    distance = float(np.linalg.norm(offset))
    elevation = math.degrees(math.asin(float(offset[2]) / distance))
    azimuth = math.degrees(math.atan2(float(offset[1]), float(offset[0])))
    quat_xyzw = Rotation.from_euler(
        "xyz", [0.0, elevation, azimuth - 180.0], degrees=True
    ).as_quat()
    return np.array([quat_xyzw[3], quat_xyzw[0], quat_xyzw[1], quat_xyzw[2]])


def main() -> int:
    isaac_version = importlib.metadata.version("isaacsim")
    if not (isaac_version == "4.1" or isaac_version.startswith("4.1.")):
        raise RuntimeError(f"requires Isaac Sim 4.1.x, found {isaac_version}")
    staging = OUTPUT.parent / ".reagent_bottle.staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    wrapper = _extract_bottle(staging)
    scene = staging / "reagent_bottle_90x55.usda"
    build_evidence_scene(
        output_path=scene,
        room_usd=ROOM,
        table_usd=TABLE,
        asset_usd=wrapper,
        asset_prim_path="/World/ReagentBottle",
        object_height_m=0.755,
    )

    from isaacsim import SimulationApp

    app = SimulationApp(
        {
            "headless": True,
            "renderer": "RayTracedLighting",
            "anti_aliasing": 4,
            "multi_gpu": False,
            "sync_loads": True,
            "width": 1600,
            "height": 1000,
        }
    )
    try:
        import carb.settings
        import numpy as np
        import omni.replicator.core as rep
        import omni.timeline
        import omni.usd
        from omni.isaac.sensor import Camera
        from PIL import Image
        from scipy.spatial.transform import Rotation

        settings = carb.settings.get_settings()
        settings.set("/rtx/post/aa/autoExposureMode", 0)
        settings.set("/rtx/post/aa/exposureMultiplier", 0.82)
        settings.set("/rtx/post/histogram/enabled", False)
        omni.timeline.get_timeline_interface().stop()
        print("phase=open asset=reagent_bottle_90x55", flush=True)
        omni.usd.get_context().open_stage(str(scene))
        for _ in range(20):
            app.update()
        print("phase=camera asset=reagent_bottle_90x55", flush=True)
        camera = Camera(
            prim_path="/World/GlassEvidenceCamera",
            name="glass_evidence",
            position=np.array([0.84, -1.38, 1.18]),
            resolution=(1600, 1000),
        )
        camera.initialize()
        camera.set_focal_length(54.0)
        camera.set_horizontal_aperture(20.955)
        camera.set_vertical_aperture(13.097)
        camera.set_clipping_range(0.005, 100.0)
        camera.set_world_pose(
            position=np.array([0.84, -1.38, 1.18]),
            orientation=_look_at_orientation(
                position=[0.84, -1.38, 1.18],
                target=[0.0, -0.16, 0.87],
                Rotation=Rotation,
                np=np,
            ),
        )
        for _ in range(34):
            app.update()
            rep.orchestrator.step(rt_subframes=2, pause_timeline=False)
        print("phase=readback asset=reagent_bottle_90x55", flush=True)
        rgb = camera.get_rgb()
        if rgb is None:
            raise RuntimeError("camera readback failed for reagent_bottle_90x55")
        pixels = np.asarray(rgb)
        if pixels.shape[-1] == 4:
            pixels = pixels[..., :3]
        pixels = pixels.astype(np.uint8)
        OUTPUT.mkdir(parents=True, exist_ok=True)
        path = OUTPUT / "reagent_bottle_90x55.png"
        Image.fromarray(pixels).save(path)
        record = {
            "asset_id": "reagent_bottle_90x55",
            "image": path.name,
            "sha256": sha256(path.read_bytes()).hexdigest(),
            "source_asset_usd": str(wrapper),
            "mean_rgb": [round(float(v), 3) for v in pixels.mean(axis=(0, 1))],
            "runtime": isaac_version,
        }
        (OUTPUT / "reagent_bottle_90x55.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(path, flush=True)
    except BaseException as error:
        (staging / "failure.json").write_text(
            json.dumps({"error_type": type(error).__name__, "error": str(error)}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        print(f"GLASS_RENDER_FAILED {type(error).__name__}: {error}", flush=True)
        app.close()
        return 1
    app.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Render webpage-reference versus admitted-package glass evidence in Isaac 4.1."""

from __future__ import annotations

from hashlib import sha256
import importlib.metadata
import json
import math
from pathlib import Path
import shutil
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scenario_forge.generation.glass_material_evidence import (  # noqa: E402
    REAGENT_BOTTLE_CLEAR_OMNIGLASS_INPUTS,
    build_evidence_scene,
)


CONVERT_ROOT = Path("/cpfs/user/zhuzihou/dev/ConvertAsset")
ROOM = (
    CONVERT_ROOT
    / "outputs/generated_scientific_labs_v2_20260804/modern_wet_chemistry/package/asset.usd"
)
TABLE = (
    CONVERT_ROOT
    / "outputs/scientific_workbench_standard_table_20260819/package/asset.usd"
)
REFERENCE_ROOT = (
    CONVERT_ROOT / "outputs/scientific_workbench_glass_material_v1_20260818/packages"
)
INPUT_ROOT = (
    CONVERT_ROOT / "outputs/scientific_workbench_glass_web_standard_20260819/input"
)
PACKAGE_ROOT = (
    CONVERT_ROOT / "outputs/scientific_workbench_glass_web_standard_20260819/packages"
)
OUTPUT = (
    REPO_ROOT
    / "outputs/scientific_workbench_glass_web_standard_20260819/evidence/comparisons"
)
MANIFEST_SCHEMA = "scenario-forge-glass-web-standard-comparison/v1"
STANDARD = "glass-material-guide webpage fixed setup"
CLAIM_BOUNDARY = (
    "The first four references reproduce the public webpage recipe on the prior "
    "glass_v1 meshes. The two manual-vessel references are the producer SimReady "
    "sources used as material authorities. Candidate images are admitted packages. "
    "This evidence does not claim robot, liquid-transfer, or benchmark success."
)


ASSETS = (
    {
        "id": "graduated_cylinder_250ml",
        "package_name": "graduated_cylinder_250ml_glass_web_standard_v1",
        "label": "250 mL 量筒（透明六边形底座）",
        "prim": "/World/GraduatedCylinder250ml",
        "reference": REFERENCE_ROOT / "graduated_cylinder_250ml_glass_v1/asset.usd",
        "candidate": PACKAGE_ROOT
        / "graduated_cylinder_250ml_glass_web_standard_v1/asset.usd",
        "reference_overlay": True,
    },
    {
        "id": "beaker_325ml",
        "package_name": "beaker_325ml_glass_web_standard_v1",
        "label": "325 mL 烧杯",
        "prim": "/World/Beaker325ml",
        "reference": REFERENCE_ROOT / "beaker_325ml_glass_v1/asset.usd",
        "candidate": PACKAGE_ROOT / "beaker_325ml_glass_web_standard_v1/asset.usd",
        "reference_overlay": True,
    },
    {
        "id": "flat_bottom_flask_250ml_29_42",
        "package_name": "flat_bottom_flask_250ml_29_42_glass_web_standard_v1",
        "label": "250 mL 平底烧瓶（29/42）",
        "prim": "/World/FlatBottomFlask2942",
        "reference": REFERENCE_ROOT / "flat_bottom_flask_250ml_29_42_glass_v1/asset.usd",
        "candidate": PACKAGE_ROOT
        / "flat_bottom_flask_250ml_29_42_glass_web_standard_v1/asset.usd",
        "reference_overlay": True,
    },
    {
        "id": "beaker_dynamic",
        "package_name": "beaker_dynamic_glass_web_standard_v1",
        "label": "动态烧杯",
        "prim": "/World/Beaker",
        "reference": REFERENCE_ROOT / "beaker_dynamic_glass_v1/asset.usd",
        "candidate": PACKAGE_ROOT / "beaker_dynamic_glass_web_standard_v1/asset.usd",
        "reference_overlay": True,
    },
    {
        "id": "reagent_bottle_90x55",
        "package_name": "reagent_bottle_90x55_original_simready",
        "label": "90×55 试剂瓶（生产者原材质）",
        "prim": "/ObjectRoot",
        "reference": INPUT_ROOT
        / "source/manual_glassware_v1/simready/reagent_bottle_90x55.usdc",
        "candidate": PACKAGE_ROOT / "reagent_bottle_90x55_original_simready/asset.usd",
        "reference_overlay": False,
    },
    {
        "id": "erlenmeyer_flask_250ml_90x35",
        "package_name": "erlenmeyer_flask_250ml_90x35_original_simready",
        "label": "250 mL 锥形瓶（生产者原材质）",
        "prim": "/ObjectRoot",
        "reference": INPUT_ROOT
        / "source/manual_glassware_v1/simready/erlenmeyer_flask_250ml_90x35.usdc",
        "candidate": PACKAGE_ROOT
        / "erlenmeyer_flask_250ml_90x35_original_simready/asset.usd",
        "reference_overlay": False,
    },
)


def main() -> int:
    isaac_version = importlib.metadata.version("isaacsim")
    if not (isaac_version == "4.1" or isaac_version.startswith("4.1.")):
        raise RuntimeError(f"requires Isaac Sim 4.1.x, found {isaac_version}")
    staging = OUTPUT.parent / ".comparisons.staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    scenes = staging / "scenes"
    for asset in ASSETS:
        for variant in ("reference", "candidate"):
            build_evidence_scene(
                output_path=scenes / f"{asset['id']}_{variant}.usda",
                room_usd=ROOM,
                table_usd=TABLE,
                asset_usd=asset[variant],
                asset_prim_path=str(asset["prim"]),
                object_height_m=0.755,
                mdl_inputs=(
                    REAGENT_BOTTLE_CLEAR_OMNIGLASS_INPUTS
                    if variant == "reference" and asset["reference_overlay"]
                    else None
                ),
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
        records = _render_all(app, staging, scenes)
    except BaseException as error:
        (staging / "failure.json").write_text(
            json.dumps({"error_type": type(error).__name__, "error": str(error)}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        print(f"GLASS_WEB_STANDARD_RENDER_FAILED {type(error).__name__}: {error}", flush=True)
        app.close()
        return 1

    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "standard": STANDARD,
        "status": "rendered_pending_human_visual_review",
        "runtime": {
            "engine": "Isaac Sim",
            "version": isaac_version,
            "renderer": "RayTracedLighting",
            "resolution": [1600, 1000],
        },
        "fixed_review_setup": {
            "room": str(ROOM),
            "table": str(TABLE),
            "camera_position_xyz_m": [0.84, -1.38, 1.18],
            "camera_target_xyz_m": [0.0, -0.16, 0.87],
            "focal_length_mm": 54.0,
            "object_support_z_m": 0.755,
        },
        "comparisons": records,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    (staging / "comparison_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    staging.rename(OUTPUT)
    print(OUTPUT, flush=True)
    app.close()
    return 0


def _render_all(app: Any, output: Path, scenes: Path) -> list[dict[str, Any]]:
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
    records: list[dict[str, Any]] = []
    for asset in ASSETS:
        record: dict[str, Any] = {
            "asset_id": asset["id"],
            "package_name": asset["package_name"],
            "label": asset["label"],
        }
        for variant in ("reference", "candidate"):
            print(f"phase=open asset={asset['id']} variant={variant}", flush=True)
            omni.usd.get_context().open_stage(
                str(scenes / f"{asset['id']}_{variant}.usda")
            )
            for _ in range(20):
                app.update()
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
            pixels = np.asarray(camera.get_rgb())
            if pixels.size == 0:
                raise RuntimeError(f"camera readback failed for {asset['id']} {variant}")
            if pixels.shape[-1] == 4:
                pixels = pixels[..., :3]
            pixels = pixels.astype(np.uint8)
            path = output / f"{asset['id']}_{variant}.png"
            Image.fromarray(pixels).save(path)
            record[variant] = {
                "image": path.name,
                "sha256": sha256(path.read_bytes()).hexdigest(),
                "source_asset_usd": str(asset[variant]),
                "mean_rgb": [round(float(v), 3) for v in pixels.mean(axis=(0, 1))],
            }
        records.append(record)
    return records


def _look_at_orientation(*, position: Any, target: Any, Rotation: Any, np: Any) -> Any:
    offset = np.asarray(position, dtype=float) - np.asarray(target, dtype=float)
    distance = float(np.linalg.norm(offset))
    elevation = math.degrees(math.asin(float(offset[2]) / distance))
    azimuth = math.degrees(math.atan2(float(offset[1]), float(offset[0])))
    quat_xyzw = Rotation.from_euler(
        "xyz", [0.0, elevation, azimuth - 180.0], degrees=True
    ).as_quat()
    return np.array([quat_xyzw[3], quat_xyzw[0], quat_xyzw[1], quat_xyzw[2]])


if __name__ == "__main__":
    raise SystemExit(main())

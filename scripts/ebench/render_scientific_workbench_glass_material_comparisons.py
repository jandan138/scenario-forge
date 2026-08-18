#!/usr/bin/env python3
"""Render fixed-room A/B evidence for the four glass_v1 packages in Isaac Sim 4.1."""

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

from scenario_forge.generation.glass_material_evidence import build_evidence_scene  # noqa: E402


CONVERT_ROOT = Path("/cpfs/user/zhuzihou/dev/ConvertAsset")
ROOM = CONVERT_ROOT / "outputs/generated_scientific_labs_v2_20260804/modern_wet_chemistry/package/asset.usd"
TABLE = CONVERT_ROOT / "outputs/scientific_workbench_standard_table_20260811/package/asset.usd"
NEW_ROOT = CONVERT_ROOT / "outputs/scientific_workbench_glass_material_v1_20260818/packages"
OUTPUT = REPO_ROOT / "outputs/scientific_workbench_glass_material_v1_20260818/evidence/comparisons"


ASSETS = (
    {
        "id": "graduated_cylinder_250ml",
        "label": "250 mL 量筒",
        "prim": "/World/GraduatedCylinder250ml",
        "before": CONVERT_ROOT / "outputs/scientific_workbench_r7_task_assets_20260813/packages/graduated_cylinder_250ml/asset.usd",
        "after": NEW_ROOT / "graduated_cylinder_250ml_glass_v1/asset.usd",
    },
    {
        "id": "beaker_325ml",
        "label": "325 mL 烧杯",
        "prim": "/World/Beaker325ml",
        "before": CONVERT_ROOT / "outputs/scientific_workbench_r7_task_assets_20260813/packages/beaker_325ml/asset.usd",
        "after": NEW_ROOT / "beaker_325ml_glass_v1/asset.usd",
    },
    {
        "id": "flat_bottom_flask_250ml_29_42",
        "label": "250 mL 平底烧瓶（29/42）",
        "prim": "/World/FlatBottomFlask2942",
        "before": CONVERT_ROOT / "outputs/scientific_workbench_task05_task09_assets_r11_20260817/packages/flat_bottom_flask_250ml_29_42/asset.usd",
        "after": NEW_ROOT / "flat_bottom_flask_250ml_29_42_glass_v1/asset.usd",
    },
    {
        "id": "beaker_dynamic",
        "label": "动态烧杯",
        "prim": "/World/Beaker",
        "before": CONVERT_ROOT / "outputs/scientific_workbench_asset_library_20260810/packages/beaker_transparent_r3/asset.usd",
        "after": NEW_ROOT / "beaker_dynamic_glass_v1/asset.usd",
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
        for variant in ("before", "after"):
            build_evidence_scene(
                output_path=scenes / f"{asset['id']}_{variant}.usda",
                room_usd=ROOM,
                table_usd=TABLE,
                asset_usd=asset[variant],
                asset_prim_path=str(asset["prim"]),
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
        records = _render_all(app, staging, scenes)
    except BaseException as error:
        (staging / "failure.json").write_text(
            json.dumps({"error_type": type(error).__name__, "error": str(error)}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        print(f"GLASS_RENDER_FAILED {type(error).__name__}: {error}", flush=True)
        app.close()
        return 1
    finally:
        pass
    manifest = {
        "schema_version": "scenario-forge-glass-material-comparison/v0.1",
        "status": "pass",
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
        "claim_boundary": (
            "Fixed-pose visual material comparison only; no physics step, robot policy, "
            "liquid transfer, or benchmark claim."
        ),
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
        record: dict[str, Any] = {"asset_id": asset["id"], "label": asset["label"]}
        for variant in ("before", "after"):
            print(f"phase=open asset={asset['id']} variant={variant}", flush=True)
            scene = scenes / f"{asset['id']}_{variant}.usda"
            context = omni.usd.get_context()
            context.open_stage(str(scene))
            for _ in range(20):
                app.update()
            print(f"phase=camera asset={asset['id']} variant={variant}", flush=True)
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
            print(f"phase=readback asset={asset['id']} variant={variant}", flush=True)
            rgb = camera.get_rgb()
            if rgb is None:
                raise RuntimeError(f"camera readback failed for {asset['id']} {variant}")
            pixels = np.asarray(rgb)
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

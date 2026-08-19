#!/usr/bin/env python3
"""Same-camera PathTracing stills for the glass-guide evidence setup."""

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
    REAGENT_BOTTLE_CLEAR_OMNIGLASS_INPUTS,
    build_evidence_scene,
)


CONVERT_ROOT = Path("/cpfs/user/zhuzihou/dev/ConvertAsset")
ROOM = CONVERT_ROOT / "outputs/generated_scientific_labs_v2_20260804/modern_wet_chemistry/package/asset.usd"
TABLE = CONVERT_ROOT / "outputs/scientific_workbench_standard_table_20260819/package/asset.usd"
NEW_ROOT = CONVERT_ROOT / "outputs/scientific_workbench_glass_material_v1_20260818/packages"
TARBALL = REPO_ROOT / "external_artifacts/incoming/manual_glassware_v1.tar.gz"
OUTPUT = (
    REPO_ROOT
    / "outputs/scientific_workbench_glass_material_bottle_recipe_20260818/evidence/pathtracing"
)

CAMERA_POS = [0.84, -1.38, 1.18]
CAMERA_TARGET = [0.0, -0.16, 0.87]
RESOLUTION = (1600, 1000)
PT_SPP = 8
PT_TOTAL_SPP = 256
PT_BOUNCES = 16
LOAD_FRAMES = 24
WARMUP_FRAMES = 16
ACCUMULATE_STEPS = 32
RT_SUBFRAMES = 1


ASSETS = (
    {
        "id": "reagent_bottle_90x55",
        "label": "试剂瓶 90x55",
        "prim": "/World/ReagentBottle",
        "overlay": False,
        "from_tarball": True,
    },
    {
        "id": "graduated_cylinder_250ml",
        "label": "250 mL 量筒",
        "prim": "/World/GraduatedCylinder250ml",
        "usd": NEW_ROOT / "graduated_cylinder_250ml_glass_v1/asset.usd",
        "overlay": True,
    },
    {
        "id": "beaker_325ml",
        "label": "325 mL 烧杯",
        "prim": "/World/Beaker325ml",
        "usd": NEW_ROOT / "beaker_325ml_glass_v1/asset.usd",
        "overlay": True,
    },
    {
        "id": "flat_bottom_flask_250ml_29_42",
        "label": "250 mL 平底烧瓶（29/42）",
        "prim": "/World/FlatBottomFlask2942",
        "usd": NEW_ROOT / "flat_bottom_flask_250ml_29_42_glass_v1/asset.usd",
        "overlay": True,
    },
    {
        "id": "beaker_dynamic",
        "label": "动态烧杯",
        "prim": "/World/Beaker",
        "usd": NEW_ROOT / "beaker_dynamic_glass_v1/asset.usd",
        "overlay": True,
    },
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


def _configure_path_tracing(settings: Any) -> None:
    settings.set("/rtx/rendermode", "PathTracing")
    settings.set("/rtx/pathtracing/spp", PT_SPP)
    settings.set("/rtx/pathtracing/totalSpp", PT_TOTAL_SPP)
    settings.set("/rtx/pathtracing/clampSpp", PT_TOTAL_SPP)
    settings.set("/rtx/pathtracing/maxBounces", PT_BOUNCES)
    settings.set("/rtx/pathtracing/maxSpecularAndTransmissionBounces", PT_BOUNCES)
    settings.set("/rtx/pathtracing/optixDenoiser/enabled", True)
    settings.set("/rtx/post/aa/autoExposureMode", 0)
    settings.set("/rtx/post/aa/exposureMultiplier", 0.82)
    settings.set("/rtx/post/histogram/enabled", False)


def main() -> int:
    isaac_version = importlib.metadata.version("isaacsim")
    if not (isaac_version == "4.1" or isaac_version.startswith("4.1.")):
        raise RuntimeError(f"requires Isaac Sim 4.1.x, found {isaac_version}")
    staging = OUTPUT.parent / ".pathtracing.staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    scenes = staging / "scenes"
    bottle_usd = _extract_bottle(staging)
    for asset in ASSETS:
        usd = bottle_usd if asset.get("from_tarball") else Path(asset["usd"])
        build_evidence_scene(
            output_path=scenes / f"{asset['id']}.usda",
            room_usd=ROOM,
            table_usd=TABLE,
            asset_usd=usd,
            asset_prim_path=str(asset["prim"]),
            object_height_m=0.755,
            mdl_inputs=(
                REAGENT_BOTTLE_CLEAR_OMNIGLASS_INPUTS if asset.get("overlay") else None
            ),
        )

    from isaacsim import SimulationApp

    app = SimulationApp(
        {
            "headless": True,
            "renderer": "PathTracing",
            "anti_aliasing": 4,
            "multi_gpu": False,
            "sync_loads": True,
            "width": RESOLUTION[0],
            "height": RESOLUTION[1],
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
        print(f"GLASS_PT_RENDER_FAILED {type(error).__name__}: {error}", flush=True)
        app.close()
        return 1
    manifest = {
        "schema_version": "scenario-forge-glass-material-pathtracing/v0.1",
        "after_recipe": "reagent_bottle_clear_omniglass",
        "status": "pass",
        "runtime": {
            "engine": "Isaac Sim",
            "version": isaac_version,
            "renderer": "PathTracing",
            "resolution": list(RESOLUTION),
            "spp": PT_SPP,
            "total_spp": PT_TOTAL_SPP,
            "max_specular_transmission_bounces": PT_BOUNCES,
            "accumulate_steps": ACCUMULATE_STEPS,
            "rt_subframes": RT_SUBFRAMES,
        },
        "fixed_review_setup": {
            "room": str(ROOM),
            "table": str(TABLE),
            "camera_position_xyz_m": CAMERA_POS,
            "camera_target_xyz_m": CAMERA_TARGET,
            "focal_length_mm": 54.0,
            "object_support_z_m": 0.755,
        },
        "stills": records,
        "claim_boundary": (
            "Same-camera PathTracing stills of the glass evidence setup. "
            "RTL comparisons are unchanged. ConvertAsset packages were not rebuilt."
        ),
    }
    (staging / "pathtracing_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for path in staging.glob("*.png"):
        shutil.copy2(path, OUTPUT / path.name)
    shutil.copy2(staging / "pathtracing_manifest.json", OUTPUT / "pathtracing_manifest.json")
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
    _configure_path_tracing(settings)
    omni.timeline.get_timeline_interface().stop()
    records: list[dict[str, Any]] = []
    for asset in ASSETS:
        print(f"phase=open asset={asset['id']}", flush=True)
        scene = scenes / f"{asset['id']}.usda"
        omni.usd.get_context().open_stage(str(scene))
        _configure_path_tracing(settings)
        for _ in range(LOAD_FRAMES):
            app.update()
        print(f"phase=camera asset={asset['id']}", flush=True)
        camera = Camera(
            prim_path="/World/GlassEvidenceCamera",
            name="glass_evidence",
            position=np.array(CAMERA_POS),
            resolution=RESOLUTION,
        )
        camera.initialize()
        camera.set_focal_length(54.0)
        camera.set_horizontal_aperture(20.955)
        camera.set_vertical_aperture(13.097)
        camera.set_clipping_range(0.005, 100.0)
        camera.set_world_pose(
            position=np.array(CAMERA_POS),
            orientation=_look_at_orientation(
                position=CAMERA_POS,
                target=CAMERA_TARGET,
                Rotation=Rotation,
                np=np,
            ),
        )
        for _ in range(WARMUP_FRAMES):
            app.update()
        print(f"phase=accumulate asset={asset['id']}", flush=True)
        for step in range(ACCUMULATE_STEPS):
            app.update()
            rep.orchestrator.step(rt_subframes=RT_SUBFRAMES, pause_timeline=True)
            if step == 0 or (step + 1) % 8 == 0:
                print(
                    f"phase=accumulate asset={asset['id']} step={step + 1}/{ACCUMULATE_STEPS}",
                    flush=True,
                )
        print(f"phase=readback asset={asset['id']}", flush=True)
        rgb = camera.get_rgb()
        if rgb is None:
            raise RuntimeError(f"camera readback failed for {asset['id']}")
        pixels = np.asarray(rgb)
        if pixels.shape[-1] == 4:
            pixels = pixels[..., :3]
        pixels = pixels.astype(np.uint8)
        path = output / f"{asset['id']}_pathtracing.png"
        Image.fromarray(pixels).save(path)
        records.append(
            {
                "asset_id": asset["id"],
                "label": asset["label"],
                "image": path.name,
                "sha256": sha256(path.read_bytes()).hexdigest(),
                "mean_rgb": [round(float(v), 3) for v in pixels.mean(axis=(0, 1))],
                "overlay": bool(asset.get("overlay")),
            }
        )
    return records


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Render stills and a rigid-follow tilt video for the visual-liquid prototype."""

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.metadata
import json
import math
from pathlib import Path
import shutil
import subprocess
from typing import Any, Mapping, Sequence

import yaml


SCHEMA_VERSION = "scenario-forge-visual-static-liquid-render-evidence/v0.1"
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
DEFAULT_FPS = 30
DEFAULT_DURATION_SECONDS = 8.0
DEFAULT_TILT_DEGREES = 55.0


def tilt_degrees_at_time(
    time_seconds: float, *, instance_index: int, tilt_degrees: float
) -> float:
    """Return the sequential one-second rise/hold/fall tilt schedule."""

    if instance_index < 0:
        raise ValueError("instance_index must be non-negative")
    start = 1.0 + 3.0 * instance_index
    local = float(time_seconds) - start
    if local <= 0.0 or local >= 3.0:
        return 0.0
    if local < 1.0:
        return float(tilt_degrees) * _smootherstep(local)
    if local <= 2.0:
        return float(tilt_degrees)
    return float(tilt_degrees) * (1.0 - _smootherstep(local - 2.0))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prototype-dir", type=Path, required=True)
    parser.add_argument("--ffmpeg", type=Path, default=Path("/usr/bin/ffmpeg"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    prototype_dir = args.prototype_dir.resolve()
    if not prototype_dir.is_dir():
        raise ValueError(f"prototype directory does not exist: {prototype_dir}")
    config = _load_yaml(prototype_dir / "prototype.yaml")
    render = _mapping(config.get("render", {}), "prototype render config")
    resolution = render.get("resolution", [DEFAULT_WIDTH, DEFAULT_HEIGHT])
    if not isinstance(resolution, Sequence) or len(resolution) != 2:
        raise ValueError("render.resolution must contain width and height")
    width, height = int(resolution[0]), int(resolution[1])
    fps = int(render.get("fps", DEFAULT_FPS))
    duration = float(render.get("duration_seconds", DEFAULT_DURATION_SECONDS))
    tilt = float(render.get("tilt_degrees", DEFAULT_TILT_DEGREES))
    representatives = list(render.get("representative_instances", []))
    if width < 1 or height < 1 or fps < 1 or duration <= 0.0:
        raise ValueError("render dimensions, fps, and duration must be positive")
    if len(representatives) != 2:
        raise ValueError("render requires exactly two representative_instances")
    if not args.ffmpeg.is_file():
        raise FileNotFoundError(args.ffmpeg)

    evidence_dir = prototype_dir / "evidence/static_liquid"
    staging = evidence_dir.parent / ".static_liquid.staging"
    _remove_path(staging)
    staging.mkdir(parents=True)
    simulation_app = None
    try:
        from isaacsim import SimulationApp

        isaac_version = _package_version("isaacsim")
        if not (isaac_version == "4.1" or isaac_version.startswith("4.1.")):
            raise RuntimeError(f"renderer requires Isaac Sim 4.1.x, found {isaac_version}")
        simulation_app = SimulationApp(
            {
                "headless": True,
                "renderer": "RayTracedLighting",
                "anti_aliasing": 4,
                "multi_gpu": False,
                "sync_loads": True,
                "width": width,
                "height": height,
            }
        )
        runtime = _render_all(
            simulation_app=simulation_app,
            prototype_dir=prototype_dir,
            output_dir=staging,
            width=width,
            height=height,
            fps=fps,
            duration_seconds=duration,
            tilt_degrees=tilt,
            representative_instances=representatives,
            ffmpeg=args.ffmpeg.resolve(),
        )
        files = [
            "neutral_front.png",
            "neutral_top.png",
            "neutral_three_quarter.png",
            "lab_review.png",
            "contact_sheet.png",
            "visual_static_liquid_rigid_follow_boundary.mp4",
            "ffmpeg.log",
        ]
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "status": "pass",
            "runtime": {
                "engine": "Isaac Sim",
                "isaac_sim_version": isaac_version,
                "renderer": "RayTracedLighting",
                "resolution": [width, height],
                "fps": fps,
            },
            "artifacts": {
                name: {"sha256": _sha256(staging / name)} for name in files
            },
            "video": {
                "path": "visual_static_liquid_rigid_follow_boundary.mp4",
                "duration_seconds": duration,
                "frame_count": round(duration * fps),
                "tilt_degrees": tilt,
                "representative_instances": representatives,
                "behavior": "visual_liquid_rigidly_follows_container",
            },
            "runtime_checks": runtime,
            "claim_boundary": (
                "Visual-only background-liquid presentation and rigid-follow boundary; "
                "not fluid physics, liquid transfer, task integration, or benchmark evidence."
            ),
        }
        (staging / "render_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _remove_path(evidence_dir)
        staging.rename(evidence_dir)
        _update_prototype_manifest(prototype_dir, evidence_dir / "render_manifest.json")
        print(f"Rendered visual-static-liquid evidence: {evidence_dir}", flush=True)
        if simulation_app is not None:
            simulation_app.close()
        return 0
    except BaseException as error:
        (staging / "render_manifest.json").write_text(
            json.dumps(
                {"schema_version": SCHEMA_VERSION, "status": "failed", "error": str(error)},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        if simulation_app is not None:
            simulation_app.close()
        raise


def _render_all(
    *,
    simulation_app: Any,
    prototype_dir: Path,
    output_dir: Path,
    width: int,
    height: int,
    fps: int,
    duration_seconds: float,
    tilt_degrees: float,
    representative_instances: Sequence[str],
    ffmpeg: Path,
) -> dict[str, Any]:
    import carb.settings
    import numpy as np
    import omni.replicator.core as rep
    import omni.timeline
    import omni.usd
    from omni.isaac.sensor import Camera
    from PIL import Image, ImageDraw, ImageFont
    from pxr import Gf, Usd, UsdPhysics, UsdUtils
    from scipy.spatial.transform import Rotation

    settings = carb.settings.get_settings()
    settings.set("/rtx/post/aa/autoExposureMode", 0)
    settings.set("/rtx/post/aa/exposureMultiplier", 0.82)
    settings.set("/rtx/post/histogram/enabled", False)
    omni.timeline.get_timeline_interface().stop()

    neutral_views = [
        ("neutral_front", (0.0, -1.30, 1.02), (0.0, 0.0, 0.84), 42.0),
        ("neutral_top", (0.0, -0.035, 1.72), (0.0, 0.0, 0.79), 43.0),
        ("neutral_three_quarter", (0.82, -1.12, 1.14), (0.0, 0.0, 0.84), 42.0),
    ]
    neutral_scene = prototype_dir / "scene_neutral.usda"
    stage, liquid_check = _open_static_stage(
        simulation_app=simulation_app,
        context=omni.usd.get_context(),
        scene_path=neutral_scene,
        Usd=Usd,
        UsdPhysics=UsdPhysics,
    )
    cameras: list[Any] = []
    for index, (name, position, target, focal_length) in enumerate(neutral_views):
        camera = _create_camera(
            Camera=Camera,
            Rotation=Rotation,
            np=np,
            prim_path=f"/World/PrototypeCamera_{index}",
            name=name,
            position=position,
            target=target,
            focal_length=focal_length,
            resolution=(width, height),
        )
        cameras.append(camera)
    _warmup(simulation_app, rep, frames=36)
    still_records: dict[str, Any] = {}
    for (name, position, target, focal_length), camera in zip(neutral_views, cameras):
        path = output_dir / f"{name}.png"
        rgb = _capture_rgb(camera, simulation_app, rep, np=np)
        Image.fromarray(rgb).save(path)
        still_records[name] = _image_record(path, position, target, focal_length, rgb, np=np)

    lab_scene = prototype_dir / "scene_lab.usda"
    stage, lab_liquid_check = _open_static_stage(
        simulation_app=simulation_app,
        context=omni.usd.get_context(),
        scene_path=lab_scene,
        Usd=Usd,
        UsdPhysics=UsdPhysics,
    )
    lab_position = (-1.5353276, -2.7066600, 2.7726877)
    lab_target = (0.0, -0.20, 0.86)
    lab_camera = _create_camera(
        Camera=Camera,
        Rotation=Rotation,
        np=np,
        prim_path="/World/PrototypeLabCamera",
        name="lab_review",
        position=lab_position,
        target=lab_target,
        focal_length=10.0,
        resolution=(width, height),
    )
    _warmup(simulation_app, rep, frames=36)
    lab_rgb = _capture_rgb(lab_camera, simulation_app, rep, np=np)
    lab_path = output_dir / "lab_review.png"
    Image.fromarray(lab_rgb).save(lab_path)
    still_records["lab_review"] = _image_record(
        lab_path, lab_position, lab_target, 10.0, lab_rgb, np=np
    )

    stage, video_liquid_check = _open_static_stage(
        simulation_app=simulation_app,
        context=omni.usd.get_context(),
        scene_path=neutral_scene,
        Usd=Usd,
        UsdPhysics=UsdPhysics,
    )
    video_position = (0.82, -1.12, 1.14)
    video_target = (0.0, 0.0, 0.84)
    video_camera = _create_camera(
        Camera=Camera,
        Rotation=Rotation,
        np=np,
        prim_path="/World/PrototypeVideoCamera",
        name="rigid_follow_boundary",
        position=video_position,
        target=video_target,
        focal_length=42.0,
        resolution=(width, height),
    )
    _warmup(simulation_app, rep, frames=24)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir()
    base_translations: dict[str, tuple[float, float, float]] = {}
    prims: dict[str, Any] = {}
    for instance_id in representative_instances:
        prim = stage.GetPrimAtPath(f"/World/Showcase/{instance_id}")
        if not prim.IsValid():
            raise RuntimeError(f"representative instance is missing: {instance_id}")
        prims[instance_id] = prim
        value = prim.GetAttribute("xformOp:translate").Get()
        base_translations[instance_id] = tuple(float(item) for item in value)
    frame_count = round(duration_seconds * fps)
    with Usd.EditContext(stage, stage.GetSessionLayer()):
        for frame in range(frame_count):
            time_seconds = frame / fps
            for index, instance_id in enumerate(representative_instances):
                angle = tilt_degrees_at_time(
                    time_seconds, instance_index=index, tilt_degrees=tilt_degrees
                )
                signed_angle = angle if index == 0 else -angle
                radians = math.radians(signed_angle)
                prim = prims[instance_id]
                prim.GetAttribute("xformOp:orient").Set(
                    Gf.Quatd(math.cos(radians / 2.0), math.sin(radians / 2.0), 0.0, 0.0)
                )
                base = base_translations[instance_id]
                lift = 0.08 * min(abs(angle) / max(tilt_degrees, 1.0), 1.0)
                prim.GetAttribute("xformOp:translate").Set(
                    Gf.Vec3d(base[0], base[1], base[2] + lift)
                )
            rep.orchestrator.step(rt_subframes=1, pause_timeline=True, delta_time=0.0)
            rgb = _capture_rgb(video_camera, simulation_app, rep, np=np, advance=False)
            Image.fromarray(rgb).save(frames_dir / f"frame_{frame:06d}.png")
            if frame % fps == 0:
                print(f"video frame {frame}/{frame_count}", flush=True)

    video_path = output_dir / "visual_static_liquid_rigid_follow_boundary.mp4"
    completed = subprocess.run(
        [
            str(ffmpeg),
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(frames_dir / "frame_%06d.png"),
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(video_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    (output_dir / "ffmpeg.log").write_text(
        completed.stdout + completed.stderr, encoding="utf-8"
    )
    if completed.returncode != 0 or not video_path.is_file():
        raise RuntimeError(f"ffmpeg failed with exit code {completed.returncode}")
    shutil.rmtree(frames_dir)
    _write_contact_sheet(
        output_dir=output_dir,
        image_names=[name for name, *_ in neutral_views] + ["lab_review"],
        Image=Image,
        ImageDraw=ImageDraw,
        ImageFont=ImageFont,
    )

    closure = _closure_record(
        prototype_dir=prototype_dir,
        scene_paths=[neutral_scene, lab_scene],
        UsdUtils=UsdUtils,
    )
    return {
        "liquid_visual_only": liquid_check,
        "lab_liquid_visual_only": lab_liquid_check,
        "video_liquid_visual_only": video_liquid_check,
        "dependency_closure": closure,
        "stills": still_records,
    }


def _open_static_stage(*, simulation_app, context, scene_path, Usd, UsdPhysics):
    if not context.open_stage(str(scene_path.resolve())):
        raise RuntimeError(f"failed to open prototype scene: {scene_path}")
    for _ in range(10000):
        loading = bool(context.is_stage_loading()) if hasattr(context, "is_stage_loading") else False
        standby = getattr(context, "is_standby", None)
        if callable(standby):
            loading = loading or bool(standby())
        if not loading:
            break
        simulation_app.update()
    else:
        raise RuntimeError(f"stage loading did not finish: {scene_path}")
    stage = context.get_stage()
    if stage is None:
        raise RuntimeError(f"opened stage is unavailable: {scene_path}")
    liquid_prims = 0
    forbidden: list[str] = []
    with Usd.EditContext(stage, stage.GetSessionLayer()):
        for prim in stage.TraverseAll():
            path = str(prim.GetPath())
            if "/VisualLiquid" in path:
                liquid_prims += 1
                if prim.HasAPI(UsdPhysics.RigidBodyAPI) or prim.HasAPI(UsdPhysics.CollisionAPI):
                    forbidden.append(path)
                if "Particle" in prim.GetTypeName():
                    forbidden.append(path)
                if any("physxParticle" in attr.GetName() for attr in prim.GetAuthoredAttributes()):
                    forbidden.append(path)
            if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                UsdPhysics.RigidBodyAPI(prim).GetRigidBodyEnabledAttr().Set(False)
            if prim.HasAPI(UsdPhysics.CollisionAPI):
                UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Set(False)
    if forbidden:
        raise RuntimeError(f"visual liquid contains forbidden physics: {sorted(set(forbidden))}")
    return stage, {
        "visual_liquid_prim_count": liquid_prims,
        "forbidden_physics_prim_count": 0,
        "container_physics_disabled_for_evidence": True,
    }


def _create_camera(
    *, Camera, Rotation, np, prim_path, name, position, target, focal_length, resolution
):
    camera = Camera(prim_path=prim_path, name=name, resolution=resolution)
    camera.initialize()
    camera.set_focal_length(float(focal_length))
    camera.set_horizontal_aperture(20.955)
    camera.set_vertical_aperture(11.784)
    distance = math.dist(position, target)
    camera.set_clipping_range(max(0.005, distance * 1.0e-5), max(100.0, distance * 20.0))
    camera.set_world_pose(
        position=np.asarray(position, dtype=float),
        orientation=_look_at_orientation(
            position=position, target=target, rotation_type=Rotation, np=np
        ),
    )
    return camera


def _warmup(simulation_app, rep, *, frames: int) -> None:
    for _ in range(min(frames, 20)):
        simulation_app.update()
    for _ in range(max(1, math.ceil(frames / 12))):
        rep.orchestrator.step(rt_subframes=4, pause_timeline=True, delta_time=0.0)


def _capture_rgb(camera, simulation_app, rep, *, np, advance: bool = True):
    if advance:
        rep.orchestrator.step(rt_subframes=4, pause_timeline=True, delta_time=0.0)
    rgba = camera.get_rgba()
    attempts = 0
    while (not isinstance(rgba, np.ndarray) or rgba.size == 0) and attempts < 60:
        simulation_app.update()
        rgba = camera.get_rgba()
        attempts += 1
    if not isinstance(rgba, np.ndarray) or rgba.size == 0:
        raise RuntimeError("camera returned no frame")
    return _rgba_to_rgb(rgba, np=np)


def _look_at_orientation(*, position, target, rotation_type, np):
    offset = np.asarray(position, dtype=float) - np.asarray(target, dtype=float)
    distance = float(np.linalg.norm(offset))
    elevation = math.degrees(math.asin(float(offset[2]) / distance))
    azimuth = math.degrees(math.atan2(float(offset[1]), float(offset[0])))
    quaternion = rotation_type.from_euler(
        "xyz", [0.0, elevation, azimuth - 180.0], degrees=True
    ).as_quat()
    return np.asarray(
        [quaternion[3], quaternion[0], quaternion[1], quaternion[2]], dtype=float
    )


def _rgba_to_rgb(rgba, *, np):
    array = np.asarray(rgba)
    if array.dtype != np.uint8:
        array = np.nan_to_num(array.astype(np.float32), nan=0.0, posinf=255.0, neginf=0.0)
        if array.size and float(np.max(array)) <= 1.0:
            array *= 255.0
        array = np.clip(array, 0, 255).astype(np.uint8)
    if array.ndim != 3 or array.shape[2] < 3:
        raise RuntimeError(f"unexpected camera frame shape: {array.shape}")
    if array.shape[2] == 3:
        return array
    alpha = array[:, :, 3:4].astype(np.float32) / 255.0
    background = np.full(array[:, :, :3].shape, 24.0, dtype=np.float32)
    return (
        array[:, :, :3].astype(np.float32) * alpha + background * (1.0 - alpha)
    ).astype(np.uint8)


def _image_record(path, position, target, focal_length, rgb, *, np) -> dict[str, Any]:
    luminance = (
        rgb[:, :, 0].astype(np.float32) * 0.2126
        + rgb[:, :, 1].astype(np.float32) * 0.7152
        + rgb[:, :, 2].astype(np.float32) * 0.0722
    )
    return {
        "path": path.name,
        "sha256": _sha256(path),
        "camera_position": list(position),
        "camera_target": list(target),
        "focal_length_mm": focal_length,
        "mean_luminance": round(float(np.mean(luminance)), 3),
        "p99_luminance": round(float(np.percentile(luminance, 99.0)), 3),
    }


def _write_contact_sheet(*, output_dir, image_names, Image, ImageDraw, ImageFont) -> None:
    images = [Image.open(output_dir / f"{name}.png").convert("RGB") for name in image_names]
    thumb_width, thumb_height = 720, 405
    label_height = 32
    sheet = Image.new("RGB", (thumb_width * 2, (thumb_height + label_height) * 2), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (name, image) in enumerate(zip(image_names, images)):
        image.thumbnail((thumb_width, thumb_height))
        x = (index % 2) * thumb_width
        y = (index // 2) * (thumb_height + label_height)
        sheet.paste(image, (x, y))
        draw.text((x + 8, y + thumb_height + 8), name, fill=(245, 245, 245), font=font)
        image.close()
    sheet.save(output_dir / "contact_sheet.png")


def _closure_record(*, prototype_dir, scene_paths, UsdUtils) -> dict[str, Any]:
    dependencies: set[Path] = set()
    unresolved: set[str] = set()
    external: set[str] = set()
    for scene in scene_paths:
        layers, assets, raw_unresolved = UsdUtils.ComputeAllDependencies(str(scene))
        for layer in layers:
            identifier = getattr(layer, "realPath", "") or getattr(layer, "identifier", "")
            if identifier:
                dependencies.add(Path(str(identifier)).resolve())
        for asset in assets:
            dependencies.add(Path(str(asset)).resolve())
        unresolved.update(str(item) for item in raw_unresolved)
    for dependency in dependencies:
        try:
            dependency.relative_to(prototype_dir)
        except ValueError:
            external.add(str(dependency))
    if unresolved or external:
        raise RuntimeError(
            f"prototype dependency closure failed: unresolved={sorted(unresolved)}, external={sorted(external)}"
        )
    return {
        "dependency_count": len(dependencies),
        "unresolved_count": 0,
        "external_count": 0,
        "package_local": True,
    }


def _update_prototype_manifest(prototype_dir: Path, render_manifest: Path) -> None:
    path = prototype_dir / "prototype_manifest.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["status"] = "runtime_preview_complete"
    value["render_evidence"] = {
        "path": render_manifest.relative_to(prototype_dir).as_posix(),
        "sha256": _sha256(render_manifest),
    }
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _smootherstep(value: float) -> float:
    clipped = max(0.0, min(1.0, float(value)))
    return clipped**3 * (clipped * (clipped * 6.0 - 15.0) + 10.0)


def _load_yaml(path: Path) -> Mapping[str, Any]:
    return _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), str(path))


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(16 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _remove_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


if __name__ == "__main__":
    raise SystemExit(main())

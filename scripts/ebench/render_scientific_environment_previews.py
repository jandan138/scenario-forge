#!/usr/bin/env python3
"""Render standardized retake views for shortlisted scientific environments.

The batch side is a pure subprocess orchestrator.  Simulator imports are
deferred to the worker command so Scenario Forge package layers remain free of
Isaac Sim dependencies.  The worker opens each upstream root USD without
modifying it and authors temporary evidence cameras in the in-memory stage.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.metadata
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import traceback
from typing import Any, Mapping, Sequence

import yaml


RENDER_SCHEMA = "scenario-forge-scientific-environment-preview/v0.1"
BATCH_SCHEMA = "scenario-forge-scientific-environment-preview-batch/v0.1"
VIEW_NAMES = ("authored", "eye_left", "eye_right")


def plan_camera_views(
    *,
    position: Sequence[float],
    target: Sequence[float],
    orbit_position: Sequence[float] | None = None,
    orbit_target: Sequence[float] | None = None,
) -> list[dict[str, Any]]:
    """Preserve the author view and add two comparable eye-level orbit views."""

    authored_position = _finite_vector(position, "position")
    authored_target = _finite_vector(target, "target")
    orbit_position_vector = (
        authored_position
        if orbit_position is None
        else _finite_vector(orbit_position, "orbit_position")
    )
    orbit_target_vector = (
        authored_target
        if orbit_target is None
        else _finite_vector(orbit_target, "orbit_target")
    )
    offset = [
        orbit_position_vector[index] - orbit_target_vector[index]
        for index in range(3)
    ]
    distance = math.sqrt(sum(value * value for value in offset))
    if distance <= 0.0:
        raise ValueError("authored camera position and target must differ")
    azimuth = math.degrees(math.atan2(offset[1], offset[0]))
    eye_distance = distance * 1.1

    views: list[dict[str, Any]] = [
        {
            "name": "authored",
            "position": authored_position,
            "target": authored_target,
        }
    ]
    for name, azimuth_delta in (("eye_left", -30.0), ("eye_right", 30.0)):
        views.append(
            {
                "name": name,
                "position": _orbit_position(
                    target=orbit_target_vector,
                    distance=eye_distance,
                    elevation_deg=18.0,
                    azimuth_deg=azimuth + azimuth_delta,
                ),
                "target": orbit_target_vector,
            }
        )
    return views


def load_retake_selection(
    *,
    catalog_path: Path,
    review_path: Path,
    max_scenes: int,
) -> list[dict[str, Any]]:
    """Load hash-bound PASS/WARN candidates in explicit visual-review order."""

    if max_scenes < 1:
        raise ValueError("max_scenes must be positive")
    catalog = _load_json_mapping(catalog_path, "catalog")
    review_document = _load_yaml_mapping(review_path, "visual review")
    if review_document.get("catalog_digest") != catalog.get("catalog_digest"):
        raise ValueError("visual-review catalog digest does not match catalog")
    reviews = review_document.get("reviews")
    if not isinstance(reviews, Mapping):
        raise ValueError("visual review must contain a reviews mapping")
    raw_entries = catalog.get("entries")
    if not isinstance(raw_entries, list):
        raise ValueError("catalog.entries must be a list")
    entries = {
        str(entry["candidate_id"]): entry
        for entry in raw_entries
        if isinstance(entry, Mapping) and isinstance(entry.get("candidate_id"), str)
    }

    selected: list[dict[str, Any]] = []
    for candidate_id, raw_review in reviews.items():
        if not isinstance(raw_review, Mapping):
            raise ValueError(f"review must be a mapping: {candidate_id}")
        if candidate_id not in entries:
            raise ValueError(f"visual review references unknown candidate: {candidate_id}")
        entry = entries[candidate_id]
        if raw_review.get("thumbnail_sha256") != entry.get("thumbnail_sha256"):
            raise ValueError(f"visual-review thumbnail hash is stale: {candidate_id}")
        status = str(raw_review.get("status", "")).upper()
        if status not in {"PASS", "WARN", "FAIL"}:
            raise ValueError(f"invalid visual-review status: {candidate_id}={status}")
        if status == "FAIL":
            continue
        selected.append(
            {
                "candidate_id": candidate_id,
                "selection_rank": int(raw_review.get("selection_rank", 10**9)),
                "review_status": status,
                "source_usd": str(entry["source_usd"]),
                "source_sha256": str(entry["source_sha256"]),
                "thumbnail_sha256": str(entry["thumbnail_sha256"]),
            }
        )
    selected.sort(key=lambda item: (item["selection_rank"], item["candidate_id"]))
    return selected[:max_scenes]


def run_batch(
    *,
    catalog_path: Path,
    review_path: Path,
    isaac_python: Path,
    output_root: Path,
    max_scenes: int,
    timeout_seconds: float,
    width: int,
    height: int,
) -> int:
    if not isaac_python.is_file():
        raise ValueError(f"Isaac Python does not exist: {isaac_python}")
    selected = load_retake_selection(
        catalog_path=catalog_path,
        review_path=review_path,
        max_scenes=max_scenes,
    )
    out = output_root.resolve()
    out.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).resolve()
    results: list[dict[str, Any]] = []
    for item in selected:
        candidate_id = str(item["candidate_id"])
        candidate_dir = out / candidate_id
        candidate_dir.mkdir(parents=True, exist_ok=True)
        command = [
            str(isaac_python.resolve()),
            str(script),
            "worker",
            "--candidate-id",
            candidate_id,
            "--source-usd",
            str(item["source_usd"]),
            "--source-sha256",
            str(item["source_sha256"]),
            "--out",
            str(candidate_dir),
            "--width",
            str(width),
            "--height",
            str(height),
        ]
        environment = _isolated_isaac_environment(isaac_python)
        try:
            completed = subprocess.run(
                command,
                cwd=str(script.parents[2]),
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout_seconds,
                check=False,
                shell=False,
            )
            returncode = completed.returncode
            output = completed.stdout
        except subprocess.TimeoutExpired as exc:
            returncode = 124
            output = _format_timeout_output(exc, timeout_seconds)
        (candidate_dir / "runtime.log").write_text(output, encoding="utf-8")
        manifest_path = candidate_dir / "render_manifest.json"
        manifest_status = None
        if manifest_path.is_file():
            try:
                manifest_status = json.loads(
                    manifest_path.read_text(encoding="utf-8")
                ).get("render_status")
            except (OSError, json.JSONDecodeError):
                manifest_status = "invalid"
        status = "pass" if returncode == 0 and manifest_status == "pass" else "failed"
        results.append(
            {
                **item,
                "status": status,
                "returncode": returncode,
                "manifest_path": str(manifest_path.relative_to(out)),
                "runtime_log_path": str(
                    (candidate_dir / "runtime.log").relative_to(out)
                ),
            }
        )
        print(f"{candidate_id}: {status}", flush=True)

    catalog = _load_json_mapping(catalog_path, "catalog")
    batch = {
        "schema_version": BATCH_SCHEMA,
        "catalog_digest": catalog["catalog_digest"],
        "selected_count": len(selected),
        "pass_count": sum(result["status"] == "pass" for result in results),
        "failed_count": sum(result["status"] != "pass" for result in results),
        "runtime": {
            "isaac_python": str(isaac_python.resolve()),
            "expected_isaac_sim_version": "4.1",
            "width": width,
            "height": height,
        },
        "results": results,
        "claim_boundary": (
            "Preview retakes only; not ConvertAsset admission, dependency closure, "
            "physics qualification, or benchmark success."
        ),
    }
    _write_json(out / "batch_manifest.json", batch)
    return 0 if batch["failed_count"] == 0 else 1


def render_worker(
    *,
    candidate_id: str,
    source_usd: Path,
    source_sha256: str,
    output_root: Path,
    width: int,
    height: int,
    warmup_frames: int,
    fast_static_preview: bool = False,
    exposure_mode: str = "auto",
    exposure_multiplier: float = 0.8,
) -> int:
    if _file_sha256(source_usd) != source_sha256:
        raise ValueError(f"source SHA-256 mismatch: {source_usd}")
    if width < 1 or height < 1:
        raise ValueError("render resolution must be positive")
    if exposure_mode not in {"auto", "fixed"}:
        raise ValueError("exposure_mode must be auto or fixed")
    if not math.isfinite(exposure_multiplier) or exposure_multiplier <= 0.0:
        raise ValueError("exposure_multiplier must be positive and finite")

    output_root.mkdir(parents=True, exist_ok=True)
    simulation_app = None
    cameras: list[Any] = []
    try:
        from isaacsim import SimulationApp

        isaac_sim_version = _package_version("isaacsim")
        if not _is_supported_isaac_sim_version(isaac_sim_version):
            raise RuntimeError(
                "preview worker requires Isaac Sim 4.1.x, "
                f"found {isaac_sim_version}"
            )
        simulation_app = SimulationApp(
            {
                "headless": True,
                "renderer": "RayTracedLighting",
                "anti_aliasing": 0 if fast_static_preview else 4,
                "multi_gpu": False,
                "sync_loads": True,
                "width": width,
                "height": height,
            }
        )

        import carb.settings
        import numpy as np
        import omni.replicator.core as rep
        import omni.timeline
        import omni.usd
        from omni.isaac.sensor import Camera
        from PIL import Image
        from scipy.spatial.transform import Rotation
        from pxr import Usd, UsdGeom, UsdPhysics

        settings = carb.settings.get_settings()
        fixed_exposure = exposure_mode == "fixed"
        settings.set("/rtx/post/aa/autoExposureMode", 0 if fixed_exposure else 1)
        settings.set("/rtx/post/aa/exposureMultiplier", exposure_multiplier)
        settings.set("/rtx/post/histogram/enabled", not fixed_exposure)

        timeline = omni.timeline.get_timeline_interface()
        timeline.stop()
        context = omni.usd.get_context()
        opened = bool(context.open_stage(str(source_usd.resolve())))
        if not opened:
            raise RuntimeError(f"Isaac Sim failed to open stage: {source_usd}")
        for _ in range(10000):
            loading = False
            if hasattr(context, "is_stage_loading"):
                loading = bool(context.is_stage_loading())
            standby = getattr(context, "is_standby", None)
            if callable(standby):
                loading = loading or bool(standby())
            if not loading:
                break
            simulation_app.update()
        else:
            raise RuntimeError(f"stage loading did not finish: {source_usd}")

        stage = context.get_stage()
        if stage is None:
            raise RuntimeError(f"opened stage is unavailable: {source_usd}")
        root_custom_data = stage.GetRootLayer().customLayerData
        authored_static_preview = bool(
            root_custom_data.get("scenarioForgeAuthoredStaticPreview", False)
        )
        if authored_static_preview:
            with Usd.EditContext(stage, stage.GetSessionLayer()):
                for prim in stage.TraverseAll():
                    if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                        UsdPhysics.RigidBodyAPI(prim).GetRigidBodyEnabledAttr().Set(False)
                    if prim.HasAPI(UsdPhysics.CollisionAPI):
                        UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Set(False)
        camera_settings = root_custom_data.get(
            "cameraSettings", {}
        )
        perspective = (
            camera_settings.get("Perspective", {})
            if isinstance(camera_settings, Mapping)
            else {}
        )
        if not isinstance(perspective, Mapping):
            raise RuntimeError("Perspective camera settings are missing")
        position = perspective.get("position")
        target = perspective.get("target")
        if position is None or target is None:
            raise RuntimeError("Perspective camera position/target are missing")
        views = plan_camera_views(
            position=tuple(position),
            target=tuple(target),
            orbit_position=perspective.get("orbitPosition"),
            orbit_target=perspective.get("orbitTarget"),
        )

        for index, view in enumerate(views):
            camera = Camera(
                prim_path=f"/World/ScenarioForgePreviewCamera_{index}",
                name=f"scenario_forge_preview_{index}",
                resolution=(width, height),
            )
            camera.initialize()
            camera.set_focal_length(12.0)
            camera.set_horizontal_aperture(20.955)
            camera.set_vertical_aperture(11.784)
            distance = _distance(view["position"], view["target"])
            camera.set_clipping_range(
                max(0.01, distance * 1.0e-5),
                max(1000.0, distance * 10.0),
            )
            orientation = _look_at_orientation(
                position=view["position"],
                target=view["target"],
                rotation_type=Rotation,
                np=np,
            )
            camera.set_world_pose(
                position=np.asarray(view["position"], dtype=float),
                orientation=orientation,
            )
            cameras.append(camera)

        for _ in range(max(1, min(warmup_frames, 20))):
            simulation_app.update()
        for _ in range(max(1, math.ceil(warmup_frames / 20))):
            rep.orchestrator.step(
                rt_subframes=1 if fast_static_preview else 4,
                pause_timeline=True,
                delta_time=0.0,
            )

        view_records: dict[str, Any] = {}
        for view, camera in zip(views, cameras):
            rgba = camera.get_rgba()
            attempts = 0
            while (not isinstance(rgba, np.ndarray) or rgba.size == 0) and attempts < 60:
                simulation_app.update()
                rgba = camera.get_rgba()
                attempts += 1
            if not isinstance(rgba, np.ndarray) or rgba.size == 0:
                raise RuntimeError(f"camera returned no frame: {view['name']}")
            rgb = _rgba_to_rgb(rgba, np=np)
            visibility = _frame_visibility_stats(rgb, np=np)
            if (
                visibility["mean_luminance"] < 2.0
                or visibility["p99_luminance"] < 10.0
            ):
                raise RuntimeError(
                    "camera frame is effectively black: "
                    f"{view['name']} {visibility}"
                )
            image_path = output_root / f"{view['name']}.png"
            Image.fromarray(rgb).save(image_path)
            view_records[str(view["name"])] = {
                "image_path": image_path.name,
                "sha256": _file_sha256(image_path),
                "position": [float(value) for value in view["position"]],
                "target": [float(value) for value in view["target"]],
                "resolution": [width, height],
                "visibility": visibility,
            }

        _write_retake_contact_sheet(
            output_root=output_root,
            candidate_id=candidate_id,
            view_names=VIEW_NAMES,
        )
        stage_units = float(UsdGeom.GetStageMetersPerUnit(stage))
        manifest = {
            "schema_version": RENDER_SCHEMA,
            "candidate_id": candidate_id,
            "source_usd": str(source_usd.resolve()),
            "source_sha256": source_sha256,
            "render_status": "pass",
            "runtime": {
                "engine": "Isaac Sim",
                "isaac_sim_version": isaac_sim_version,
                "renderer": "RayTracedLighting",
                "stage_meters_per_unit": stage_units,
                "exposure_mode": exposure_mode,
                "exposure_multiplier": exposure_multiplier,
                "authored_static_physics_disabled": authored_static_preview,
            },
            "views": view_records,
            "contact_sheet": {
                "path": "contact_sheet.png",
                "sha256": _file_sha256(output_root / "contact_sheet.png"),
            },
            "claim_boundary": (
                "Source-root preview retake only; not dependency closure, material "
                "admission, physical correctness, or benchmark success."
            ),
        }
        _write_json(output_root / "render_manifest.json", manifest)
        return 0
    except Exception as exc:
        failure = {
            "schema_version": RENDER_SCHEMA,
            "candidate_id": candidate_id,
            "source_usd": str(source_usd.resolve()),
            "source_sha256": source_sha256,
            "render_status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        _write_json(output_root / "render_manifest.json", failure)
        traceback.print_exc()
        return 1
    finally:
        for camera in cameras:
            try:
                if hasattr(camera, "_custom_annotators"):
                    camera._custom_annotators.clear()
                if hasattr(camera, "_render_product"):
                    camera._render_product = None
            except Exception:
                pass
        if simulation_app is not None:
            simulation_app.close()


def _isolated_isaac_environment(isaac_python: Path) -> dict[str, str]:
    environment = dict(os.environ)
    for name in (
        "ISAAC_SIM_ROOT",
        "ISAAC_PATH",
        "ISAACSIM_PATH",
        "CARB_APP_PATH",
        "EXP_PATH",
        "KIT_APP_NAME",
        "OMNI_KIT_ROOT",
        "OMNI_EXTENSIONS_PATH",
        "PYTHONPATH",
        "PYTHONHOME",
    ):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["ACCEPT_EULA"] = "Y"
    environment["OMNI_KIT_ACCEPT_EULA"] = "YES"
    environment["PYTHONUNBUFFERED"] = "1"

    prefix = isaac_python.resolve().parents[1]
    library_paths = [
        prefix
        / "lib/python3.10/site-packages/torch/lib",
        prefix
        / "lib/python3.10/site-packages/nvidia/cuda_runtime/lib",
    ]
    existing = environment.get("LD_LIBRARY_PATH", "")
    environment["LD_LIBRARY_PATH"] = ":".join(
        [str(path) for path in library_paths if path.is_dir()]
        + ([existing] if existing else [])
    )
    return environment


def _format_timeout_output(
    error: subprocess.TimeoutExpired,
    timeout_seconds: float,
) -> str:
    output = error.stdout or ""
    if isinstance(output, bytes):
        output = output.decode("utf-8", errors="replace")
    if output and not output.endswith("\n"):
        output += "\n"
    return output + f"preview worker timed out after {timeout_seconds:.1f}s\n"


def _write_retake_contact_sheet(
    *,
    output_root: Path,
    candidate_id: str,
    view_names: Sequence[str],
) -> None:
    from PIL import Image, ImageDraw, ImageFont

    images = [
        Image.open(output_root / f"{view_name}.png").convert("RGB")
        for view_name in view_names
    ]
    width = max(image.width for image in images)
    height = max(image.height for image in images)
    label_height = 34
    sheet = Image.new(
        "RGB",
        (width * len(images), height + label_height),
        (20, 20, 20),
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (view_name, image) in enumerate(zip(view_names, images)):
        x = index * width
        sheet.paste(image, (x, 0))
        draw.text(
            (x + 8, height + 8),
            f"{candidate_id} / {view_name}",
            fill=(245, 245, 245),
            font=font,
        )
        image.close()
    sheet.save(output_root / "contact_sheet.png")


def _look_at_orientation(*, position, target, rotation_type, np):
    offset = np.asarray(position, dtype=float) - np.asarray(target, dtype=float)
    distance = float(np.linalg.norm(offset))
    if distance <= 0.0:
        raise ValueError("camera position and target must differ")
    elevation = math.degrees(math.asin(float(offset[2]) / distance))
    azimuth = math.degrees(math.atan2(float(offset[1]), float(offset[0])))
    quaternion = rotation_type.from_euler(
        "xyz",
        [0.0, elevation, azimuth - 180.0],
        degrees=True,
    ).as_quat()
    return np.asarray(
        [quaternion[3], quaternion[0], quaternion[1], quaternion[2]],
        dtype=float,
    )


def _rgba_to_rgb(rgba, *, np):
    array = np.asarray(rgba)
    if array.dtype != np.uint8:
        array = np.nan_to_num(
            array.astype(np.float32),
            nan=0.0,
            posinf=255.0,
            neginf=0.0,
        )
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
        array[:, :, :3].astype(np.float32) * alpha
        + background * (1.0 - alpha)
    ).astype(np.uint8)


def _frame_visibility_stats(rgb, *, np) -> dict[str, float]:
    array = np.asarray(rgb, dtype=np.float32)
    if array.ndim != 3 or array.shape[2] != 3:
        raise RuntimeError(f"unexpected RGB frame shape: {array.shape}")
    luminance = (
        array[:, :, 0] * 0.2126
        + array[:, :, 1] * 0.7152
        + array[:, :, 2] * 0.0722
    )
    return {
        "mean_luminance": round(float(np.mean(luminance)), 3),
        "p99_luminance": round(float(np.percentile(luminance, 99.0)), 3),
    }


def _orbit_position(
    *,
    target: Sequence[float],
    distance: float,
    elevation_deg: float,
    azimuth_deg: float,
) -> list[float]:
    elevation = math.radians(elevation_deg)
    azimuth = math.radians(azimuth_deg)
    horizontal = distance * math.cos(elevation)
    return [
        float(target[0]) + horizontal * math.cos(azimuth),
        float(target[1]) + horizontal * math.sin(azimuth),
        float(target[2]) + distance * math.sin(elevation),
    ]


def _finite_vector(value: Sequence[float], label: str) -> list[float]:
    if len(value) != 3:
        raise ValueError(f"{label} must contain three values")
    vector = [float(item) for item in value]
    if not all(math.isfinite(item) for item in vector):
        raise ValueError(f"{label} must contain finite values")
    return vector


def _distance(first: Sequence[float], second: Sequence[float]) -> float:
    return math.sqrt(
        sum((float(first[index]) - float(second[index])) ** 2 for index in range(3))
    )


def _load_json_mapping(path: Path, label: str) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _load_yaml_mapping(path: Path, label: str) -> Mapping[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(16 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _package_version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _is_supported_isaac_sim_version(version: str) -> bool:
    return version == "4.1" or version.startswith("4.1.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render standardized scientific-environment preview retakes."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    batch = subparsers.add_parser("batch")
    batch.add_argument("--catalog", type=Path, required=True)
    batch.add_argument("--reviews", type=Path, required=True)
    batch.add_argument("--isaac-python", type=Path, required=True)
    batch.add_argument("--out", type=Path, required=True)
    batch.add_argument("--max-scenes", type=int, default=10)
    batch.add_argument("--timeout-seconds", type=float, default=600.0)
    batch.add_argument("--width", type=int, default=960)
    batch.add_argument("--height", type=int, default=540)

    worker = subparsers.add_parser("worker")
    worker.add_argument("--candidate-id", required=True)
    worker.add_argument("--source-usd", type=Path, required=True)
    worker.add_argument("--source-sha256", required=True)
    worker.add_argument("--out", type=Path, required=True)
    worker.add_argument("--width", type=int, default=960)
    worker.add_argument("--height", type=int, default=540)
    worker.add_argument("--warmup-frames", type=int, default=20)
    worker.add_argument("--fast-static-preview", action="store_true")
    worker.add_argument("--exposure-mode", choices=("auto", "fixed"), default="auto")
    worker.add_argument("--exposure-multiplier", type=float, default=0.8)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "batch":
        return run_batch(
            catalog_path=args.catalog,
            review_path=args.reviews,
            isaac_python=args.isaac_python,
            output_root=args.out,
            max_scenes=args.max_scenes,
            timeout_seconds=args.timeout_seconds,
            width=args.width,
            height=args.height,
        )
    return render_worker(
        candidate_id=args.candidate_id,
        source_usd=args.source_usd.resolve(),
        source_sha256=args.source_sha256,
        output_root=args.out.resolve(),
        width=args.width,
        height=args.height,
        warmup_frames=args.warmup_frames,
        fast_static_preview=args.fast_static_preview,
        exposure_mode=args.exposure_mode,
        exposure_multiplier=args.exposure_multiplier,
    )


if __name__ == "__main__":
    sys.exit(main())

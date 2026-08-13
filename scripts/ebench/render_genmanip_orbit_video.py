#!/usr/bin/env python3
"""Render a static cinematic room orbit from collected GenManip package state.

The adapter restores one package at its post-reset, pre-action moment, freezes
physics, moves only a temporary evidence camera, and encodes the resulting PNG
sequence as a silent H.264 MP4.  It does not alter the package or claim task
success.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping, NamedTuple, Sequence

import yaml


DEFAULT_FPS = 30
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
DEFAULT_HOLD_START_SECONDS = 0.6
DEFAULT_TRANSITION_SECONDS = 1.2
DEFAULT_ORBIT_SECONDS = 9.6
DEFAULT_HOLD_END_SECONDS = 0.6
DEFAULT_ORBIT_DEGREES = 220.0
DEFAULT_SAFE_RADIUS_M = 2.0
DEFAULT_SAFE_HEIGHT_M = 2.5
DEFAULT_RENDER_STEPS_PER_FRAME = 2
DEFAULT_LIGHT_INTENSITY = 750.0
PREVIEW_RENDERER = Path(__file__).with_name("render_genmanip_initial_preview.py")


class CameraPose(NamedTuple):
    position: tuple[float, float, float]
    target: tuple[float, float, float]
    phase: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a post-reset, camera-only GenManip room orbit video."
    )
    parser.add_argument("--collected-root", type=Path, required=True)
    parser.add_argument("--genmanip-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ffmpeg", type=Path, default=Path("/usr/bin/ffmpeg"))
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    parser.add_argument("--render-steps-per-frame", type=int, default=DEFAULT_RENDER_STEPS_PER_FRAME)
    parser.add_argument("--keep-frames", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    collected_root = args.collected_root.resolve()
    genmanip_root = args.genmanip_root.resolve()
    output_dir = args.output_dir.resolve()
    ffmpeg = args.ffmpeg.resolve()
    if not collected_root.is_dir():
        raise ValueError(f"collected package does not exist: {collected_root}")
    if not genmanip_root.is_dir():
        raise ValueError(f"GenManip root does not exist: {genmanip_root}")
    if not ffmpeg.is_file():
        raise ValueError(f"ffmpeg does not exist: {ffmpeg}")
    if args.fps <= 0 or args.render_steps_per_frame <= 0:
        raise ValueError("fps and render-steps-per-frame must be positive")

    preview_manifest_path = collected_root / "evidence/initial_scene/render_manifest.json"
    preview_request_path = collected_root / "evidence/render_request.yaml"
    preview_manifest = _load_json_mapping(preview_manifest_path, "preview manifest")
    preview_request = _load_yaml_mapping(preview_request_path, "preview request")
    if preview_manifest.get("render_status") != "pass":
        raise ValueError("initial-scene preview must pass before video rendering")
    if preview_manifest.get("package_id") != preview_request.get("package_id"):
        raise ValueError("preview manifest and request package ids differ")
    overview = _mapping(
        _mapping(preview_manifest.get("views"), "preview manifest views").get(
            "scene_overview"
        ),
        "scene overview",
    )
    camera = _mapping(overview.get("camera"), "scene overview camera")
    start_position = _finite_vector(camera.get("position"), "camera position")
    target = _finite_vector(camera.get("look_at"), "camera look_at")
    focal_length = float(camera.get("focal_length_mm", 6.0))
    room_bounds = _mapping(preview_manifest.get("room_world_bound_m"), "room bounds")

    poses = _cinematic_orbit_camera_path(
        start_position=start_position,
        target=target,
        fps=args.fps,
        hold_start_seconds=DEFAULT_HOLD_START_SECONDS,
        transition_seconds=DEFAULT_TRANSITION_SECONDS,
        orbit_seconds=DEFAULT_ORBIT_SECONDS,
        hold_end_seconds=DEFAULT_HOLD_END_SECONDS,
        orbit_degrees=DEFAULT_ORBIT_DEGREES,
        safe_radius_m=DEFAULT_SAFE_RADIUS_M,
        safe_height_m=DEFAULT_SAFE_HEIGHT_M,
    )
    _validate_path_inside_bounds(poses, room_bounds)

    staging_dir = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.staging-", dir=output_dir.parent)
    )
    frames_dir = staging_dir / "frames"
    frames_dir.mkdir()
    movie_name = "scientific_workbench_pour_flask_to_cylinder_v6_lab_orbit_1080p.mp4"
    movie_path = staging_dir / movie_name
    try:
        simulation_app = None
        runtime, simulation_app = _render_frames(
            collected_root=collected_root,
            genmanip_root=genmanip_root,
            preview_request=preview_request,
            poses=poses,
            frames_dir=frames_dir,
            fps=args.fps,
            focal_length=focal_length,
            render_steps_per_frame=args.render_steps_per_frame,
        )
        completed = subprocess.run(
            _ffmpeg_command(
                ffmpeg=ffmpeg,
                frames_dir=frames_dir,
                output_path=movie_path,
                fps=args.fps,
            ),
            capture_output=True,
            text=True,
            check=False,
        )
        (staging_dir / "ffmpeg.log").write_text(
            completed.stdout + completed.stderr, encoding="utf-8"
        )
        if completed.returncode != 0 or not movie_path.is_file():
            raise RuntimeError(f"ffmpeg failed with exit code {completed.returncode}")
        if not args.keep_frames:
            shutil.rmtree(frames_dir)

        manifest = {
            "schema_version": "scenario-forge-genmanip-orbit-video/v0.1",
            "status": "pass",
            "package_id": preview_manifest["package_id"],
            "source": {
                "collected_root": str(collected_root),
                "preview_manifest": str(preview_manifest_path),
                "preview_manifest_sha256": _file_sha256(preview_manifest_path),
                "preview_request_sha256": _file_sha256(preview_request_path),
                "moment": "post_reset_pre_action",
            },
            "camera_path": {
                "style": "indoor_cinematic_orbit",
                "start_position_m": list(start_position),
                "look_at_m": list(target),
                "focal_length_mm": focal_length,
                "orbit_degrees": DEFAULT_ORBIT_DEGREES,
                "safe_radius_m": DEFAULT_SAFE_RADIUS_M,
                "safe_height_m": DEFAULT_SAFE_HEIGHT_M,
                "phase_seconds": {
                    "opening_hold": DEFAULT_HOLD_START_SECONDS,
                    "safe_transition": DEFAULT_TRANSITION_SECONDS,
                    "room_orbit": DEFAULT_ORBIT_SECONDS,
                    "closing_hold": DEFAULT_HOLD_END_SECONDS,
                },
                "camera_only": True,
                "walls_hidden": False,
            },
            "video": {
                "path": movie_name,
                "sha256": _file_sha256(movie_path),
                "codec": "h264",
                "pixel_format": "yuv420p",
                "resolution": [DEFAULT_WIDTH, DEFAULT_HEIGHT],
                "fps": args.fps,
                "frame_count": len(poses),
                "duration_seconds": len(poses) / args.fps,
                "audio": False,
            },
            "runtime": runtime,
            "claim_boundary": (
                "Static post-reset scene presentation only; not task success, policy "
                "success, physics fidelity, or liquid-transfer evidence."
            ),
        }
        (staging_dir / "video_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if output_dir.exists() or output_dir.is_symlink():
            _remove_path(output_dir)
        staging_dir.rename(output_dir)
        print(f"Rendered orbit video: {output_dir / movie_name}", flush=True)
        if simulation_app is not None:
            # Isaac Sim 4.1 may terminate the interpreter from close(); all
            # deliverables have already been atomically promoted at this point.
            simulation_app.close()
    except BaseException:
        if staging_dir.exists() or staging_dir.is_symlink():
            _remove_path(staging_dir)
        raise
    return 0


def _cinematic_orbit_camera_path(
    *,
    start_position: Sequence[float],
    target: Sequence[float],
    fps: int,
    hold_start_seconds: float,
    transition_seconds: float,
    orbit_seconds: float,
    hold_end_seconds: float,
    orbit_degrees: float,
    safe_radius_m: float,
    safe_height_m: float,
) -> list[CameraPose]:
    start = _finite_vector(start_position, "start_position")
    look_at = _finite_vector(target, "target")
    if fps <= 0 or safe_radius_m <= 0.0:
        raise ValueError("fps and safe_radius_m must be positive")
    counts = [
        _frame_count(hold_start_seconds, fps, "hold_start_seconds"),
        _frame_count(transition_seconds, fps, "transition_seconds"),
        _frame_count(orbit_seconds, fps, "orbit_seconds"),
        _frame_count(hold_end_seconds, fps, "hold_end_seconds"),
    ]
    start_angle = math.atan2(start[1] - look_at[1], start[0] - look_at[0])
    safe_start = (
        look_at[0] + safe_radius_m * math.cos(start_angle),
        look_at[1] + safe_radius_m * math.sin(start_angle),
        safe_height_m,
    )
    target_tuple = tuple(look_at)
    poses = [CameraPose(tuple(start), target_tuple, "opening_hold") for _ in range(counts[0])]
    for index in range(counts[1]):
        fraction = (index + 1) / counts[1]
        eased = _smootherstep(fraction)
        position = tuple(
            start[axis] + eased * (safe_start[axis] - start[axis]) for axis in range(3)
        )
        poses.append(CameraPose(position, target_tuple, "safe_transition"))
    orbit_radians = math.radians(float(orbit_degrees))
    for index in range(counts[2]):
        fraction = (index + 1) / counts[2]
        angle = start_angle + orbit_radians * _smootherstep(fraction)
        position = (
            look_at[0] + safe_radius_m * math.cos(angle),
            look_at[1] + safe_radius_m * math.sin(angle),
            safe_height_m,
        )
        poses.append(CameraPose(position, target_tuple, "room_orbit"))
    final_position = poses[-1].position
    poses.extend(
        CameraPose(final_position, target_tuple, "closing_hold") for _ in range(counts[3])
    )
    return poses


def _frame_count(seconds: float, fps: int, label: str) -> int:
    frames = int(round(float(seconds) * fps))
    if frames <= 0 or not math.isclose(frames / fps, float(seconds), abs_tol=1e-9):
        raise ValueError(f"{label} must be a positive whole number of frames")
    return frames


def _smootherstep(value: float) -> float:
    bounded = min(1.0, max(0.0, float(value)))
    return bounded**3 * (bounded * (bounded * 6.0 - 15.0) + 10.0)


def _validate_path_inside_bounds(
    poses: Sequence[CameraPose], room_bounds: Mapping[str, Any]
) -> None:
    lower = _finite_vector(room_bounds.get("min"), "room bounds min")
    upper = _finite_vector(room_bounds.get("max"), "room bounds max")
    for index, pose in enumerate(poses):
        if not all(lower[axis] < pose.position[axis] < upper[axis] for axis in range(3)):
            raise ValueError(f"camera frame {index} lies outside reviewed room bounds")


def _ffmpeg_command(
    *, ffmpeg: Path, frames_dir: Path, output_path: Path, fps: int
) -> list[str]:
    return [
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
        str(output_path),
    ]


def _render_frames(
    *,
    collected_root: Path,
    genmanip_root: Path,
    preview_request: Mapping[str, Any],
    poses: Sequence[CameraPose],
    frames_dir: Path,
    fps: int,
    focal_length: float,
    render_steps_per_frame: int,
) -> tuple[dict[str, Any], Any]:
    preview = _load_preview_renderer()
    preview._validate_request(
        collected_root, preview_request
    )  # Reuse the collected-package integrity contract.
    if str(genmanip_root) not in sys.path:
        sys.path.insert(0, str(genmanip_root))

    # Simulator imports remain inside this adapter runtime boundary.
    from isaacsim import SimulationApp

    simulation_app = SimulationApp(
        {
            "headless": True,
            "renderer": "RayTracedLighting",
            "anti_aliasing": 4,
            "multi_gpu": False,
            "width": DEFAULT_WIDTH,
            "height": DEFAULT_HEIGHT,
        }
    )
    scene = None
    runtime_record: dict[str, Any] | None = None
    try:
        import carb.settings
        import numpy as np
        from PIL import Image
        from pxr import Gf, UsdGeom, UsdLux

        settings = carb.settings.get_settings()
        settings.set("/rtx/post/aa/autoExposureMode", 0)
        settings.set("/rtx/post/aa/exposureMultiplier", 0.8)
        settings.set("/rtx/post/histogram/enabled", False)

        from genmanip.core.scene.scene import Scene
        from genmanip.core.scene.scene_config import SceneConfig
        from genmanip.utils.loader.domain_randomization import reset_scene
        from genmanip.utils.loader.scene import create_camera_list, recovery_scene
        from genmanip.utils.loader.scene import cleanup_camera
        from genmanip.utils.standalone.file_utils import load_default_config
        from genmanip.utils.usd_utils.camera_utils import get_src, set_camera_look_at

        inputs = preview._required_mapping(preview_request, "inputs", "render request")
        task_config_path = preview._input_path(collected_root, inputs, "task_config")
        episode_path = preview._input_path(collected_root, inputs, "episode_metadata")
        scene_path = preview._input_path(collected_root, inputs, "scene_usd")
        evaluation_camera_path = preview._input_path(
            collected_root, inputs, "evaluation_camera"
        )
        task_config = preview._load_mapping(task_config_path, "task config")
        episode = preview._load_json_mapping(episode_path, "episode metadata")
        task_name = preview._required_string(preview_request, "task_name", "render request")
        package_id = preview._required_string(
            preview_request, "package_id", "render request"
        )
        task_data = preview._required_mapping(episode, "task_data", "episode metadata")
        preview._resolve_collected_asset_paths_for_preview(
            task_data, collected_root, package_id
        )
        evaluation = preview._select_evaluation(task_config, task_name)
        evaluation["usd_name"] = str(scene_path.with_suffix(""))
        domain = preview._required_mapping(
            evaluation, "domain_randomization", "evaluation"
        )
        cameras = preview._required_mapping(
            domain, "cameras", "evaluation domain_randomization"
        )
        cameras["config_path"] = str(evaluation_camera_path)
        domain["cameras"] = cameras
        evaluation["domain_randomization"] = domain

        default_config = load_default_config(
            str(genmanip_root), "__scenario_forge_orbit_video__.json", "local"
        )
        scene = Scene(SceneConfig(**evaluation))
        scene.initialize(
            default_config,
            physics_dt=float(evaluation.get("physics_dt", 1.0 / 60.0)),
            rendering_dt=float(evaluation.get("rendering_dt", 1.0 / 60.0)),
            is_render=True,
            only_color_rep_for_camera=True,
        )
        scene.post_initialize()
        reset_scene(scene)
        preserved_parts = tuple(scene.articulation_part_list)
        recovery_scene(
            scene,
            preview._task_data_with_preserved_articulation_parts(
                task_data, preserved_parts
            ),
            task_name,
            default_config,
        )
        warmup_steps, _ = preview._preview_timing(preview_request)
        for _ in range(warmup_steps):
            scene.world.step(render=False)

        room_prim = scene.world.stage.GetPrimAtPath(f"/World/{scene.uuid}/room")
        if room_prim is None or not room_prim.IsValid():
            raise RuntimeError("scene room is unavailable for orbit video")
        UsdGeom.Imageable(room_prim).GetVisibilityAttr().Set(
            UsdGeom.Tokens.inherited
        )

        preview_light = UsdLux.DomeLight.Define(
            scene.world.stage, "/World/ScenarioForgeOrbitVideoLight"
        )
        preview_light.CreateIntensityAttr(DEFAULT_LIGHT_INTENSITY)
        preview_light.CreateColorAttr(Gf.Vec3f(1.0, 1.0, 1.0))
        request_views = preview._required_mapping(
            preview_request, "views", "render request"
        )
        # Match the proven initial-preview allocation order.  Isaac Sim 4.1
        # initializes this scene's RTX render products/materials on the first
        # workspace camera before the contextual overview camera is created.
        workspace_config = preview._camera_config("workspace_closeup", request_views)
        workspace_manifest_path = collected_root / "evidence/initial_scene/render_manifest.json"
        workspace_manifest = preview._load_json_mapping(
            workspace_manifest_path, "preview manifest"
        )
        workspace_record = preview._required_mapping(
            preview._required_mapping(workspace_manifest, "views", "preview manifest"),
            "workspace_closeup",
            "preview manifest views",
        )
        workspace_camera_record = preview._required_mapping(
            workspace_record, "camera", "workspace preview"
        )
        workspace_cameras = create_camera_list(
            {"workspace_closeup": workspace_config},
            scene.uuid,
            float(evaluation.get("rendering_dt", 1.0 / 60.0)),
            only_color_rep_for_camera=True,
        )
        workspace_camera = workspace_cameras["workspace_closeup"]
        workspace_target = np.asarray(workspace_camera_record["look_at"], dtype=float)
        workspace_position = np.asarray(workspace_camera_record["position"], dtype=float)
        workspace_offset = workspace_position - workspace_target
        workspace_distance = float(np.linalg.norm(workspace_offset))
        UsdGeom.Imageable(room_prim).GetVisibilityAttr().Set(UsdGeom.Tokens.invisible)
        set_camera_look_at(
            workspace_camera,
            workspace_target,
            distance=workspace_distance,
            elevation=math.degrees(
                math.asin(float(workspace_offset[2]) / workspace_distance)
            ),
            azimuth=math.degrees(
                math.atan2(float(workspace_offset[1]), float(workspace_offset[0]))
            ),
        )
        for _ in range(preview.RENDER_STEPS):
            scene.world.render()
        get_src(workspace_camera, "rgb")
        cleanup_camera(workspace_config, workspace_camera)
        UsdGeom.Imageable(room_prim).GetVisibilityAttr().Set(UsdGeom.Tokens.inherited)

        camera_config = preview._camera_config("scene_overview", request_views)
        camera_config["focal_length"] = focal_length
        camera_list = create_camera_list(
            {"scene_overview": camera_config},
            scene.uuid,
            float(evaluation.get("rendering_dt", 1.0 / 60.0)),
            only_color_rep_for_camera=True,
        )
        orbit_camera = camera_list["scene_overview"]
        first_pose = poses[0]
        first_position = np.asarray(first_pose.position, dtype=float)
        first_target = np.asarray(first_pose.target, dtype=float)
        first_offset = first_position - first_target
        first_distance = float(np.linalg.norm(first_offset))
        set_camera_look_at(
            orbit_camera,
            first_target,
            distance=first_distance,
            elevation=math.degrees(
                math.asin(float(first_offset[2]) / first_distance)
            ),
            azimuth=math.degrees(
                math.atan2(float(first_offset[1]), float(first_offset[0]))
            ),
        )
        # Match the initial-scene preview's RTX/material warmup before frame 0
        # so the opening shot is comparable to scene_overview.png.
        for _ in range(preview.RENDER_STEPS):
            scene.world.render()
        for index, pose in enumerate(poses):
            position = np.asarray(pose.position, dtype=float)
            target_array = np.asarray(pose.target, dtype=float)
            offset = position - target_array
            distance = float(np.linalg.norm(offset))
            elevation = math.degrees(math.asin(float(offset[2]) / distance))
            azimuth = math.degrees(math.atan2(float(offset[1]), float(offset[0])))
            if index != 0:
                set_camera_look_at(
                    orbit_camera,
                    target_array,
                    distance=distance,
                    elevation=elevation,
                    azimuth=azimuth,
                )
                for _ in range(render_steps_per_frame):
                    scene.world.render()
            rgb = get_src(orbit_camera, "rgb")
            if rgb is None:
                scene.world.render()
                rgb = get_src(orbit_camera, "rgb")
            if rgb is None:
                raise RuntimeError(f"camera returned no RGB frame: {index}")
            preview._save_rgb_png(
                frames_dir / f"frame_{index:06d}.png",
                _video_rgb_uint8(rgb, np),
                np,
                Image,
            )
            if index % fps == 0:
                print(f"rendered frame {index + 1}/{len(poses)}", flush=True)
        runtime_record = {
            "engine": "Isaac Sim",
            "isaac_sim_version": preview._package_version("isaacsim"),
            "genmanip_revision": preview._git_revision(genmanip_root),
            "renderer": "RayTracedLighting",
            "robot_injected": "lift2",
            "action_count": 0,
            "physics_frozen_during_capture": True,
            "render_steps_per_frame": render_steps_per_frame,
            "exposure_mode": "fixed",
            "exposure_multiplier": 0.8,
            "dome_light_intensity": DEFAULT_LIGHT_INTENSITY,
        }
    finally:
        if scene is not None:
            scene.world.stop()
            scene.world.clear_instance()
    if runtime_record is None:
        raise RuntimeError("orbit video runtime did not produce a result")
    return runtime_record, simulation_app


def _video_rgb_uint8(value: Any, np: Any) -> Any:
    """Convert Isaac's linear floating RGB output to portable 8-bit LDR.

    Camera.get_rgba() can return linear values mostly in [0, 1] with a small
    number of highlights above 1.  A global max heuristic therefore leaves
    ordinary pixels near zero when cast to uint8.  Video capture has an
    explicit linear-to-byte contract and clips only the highlights.
    """

    array = np.asarray(value)
    if array.ndim != 3 or array.shape[2] < 3:
        raise RuntimeError(f"unexpected RGB frame shape: {array.shape}")
    if array.dtype == np.uint8:
        return array[:, :, :3]
    linear = np.nan_to_num(
        array[:, :, :3].astype(np.float32), nan=0.0, posinf=1.0, neginf=0.0
    )
    return np.clip(linear, 0.0, 1.0).__mul__(255.0).astype(np.uint8)


def _load_preview_renderer() -> Any:
    spec = importlib.util.spec_from_file_location(
        "scenario_forge_genmanip_initial_preview_for_orbit", PREVIEW_RENDERER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load preview renderer: {PREVIEW_RENDERER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _finite_vector(value: object, label: str) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{label} must contain three numbers")
    result = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in result):
        raise ValueError(f"{label} must be finite")
    return result


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return dict(value)


def _load_json_mapping(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing {label}: {path}")
    return _mapping(json.loads(path.read_text(encoding="utf-8")), label)


def _load_yaml_mapping(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing {label}: {path}")
    return _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), label)


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)


if __name__ == "__main__":
    raise SystemExit(main())

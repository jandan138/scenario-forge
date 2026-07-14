#!/usr/bin/env python3
"""Render two initial-scene QA views through the native GenManip scene path.

This is a one-shot evidence producer.  It resets and restores a collected
episode, takes no actions, and never evaluates a policy or task result.
"""

from __future__ import annotations

import argparse
import copy
import gc
from hashlib import sha256
import importlib.metadata
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import traceback
from typing import Any, Mapping, Sequence

import yaml


REQUEST_SCHEMA = "scenario-forge-genmanip-preview-request/v0.1"
EVIDENCE_SCHEMA = "scenario-forge-genmanip-preview-evidence/v0.1"
VIEW_NAMES = ("workspace_closeup", "scene_overview")
EVIDENCE_DIRECTORY = Path("evidence/initial_scene")
INPUT_ROLES = {
    "package_manifest",
    "task_config",
    "episode_metadata",
    "scene_usd",
    "evaluation_camera",
    "source_bundle",
}
TABLE_RUNTIME_ID = "00000000000000000000000000000000"
WARMUP_STEPS = 50
RENDER_STEPS = 50


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render post-reset, pre-action GenManip initial-scene evidence."
    )
    parser.add_argument("--collected-root", type=Path, required=True)
    parser.add_argument("--genmanip-root", type=Path, required=True)
    parser.add_argument(
        "--request",
        type=Path,
        default=Path("evidence/render_request.yaml"),
        help="Package-relative preview request path.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    collected_root = args.collected_root.resolve()
    genmanip_root = args.genmanip_root.resolve()
    if not collected_root.is_dir():
        raise ValueError(f"collected package does not exist: {collected_root}")
    if not genmanip_root.is_dir():
        raise ValueError(f"GenManip root does not exist: {genmanip_root}")

    request_path = _safe_package_path(collected_root, args.request, "request")
    request = _load_mapping(request_path, "render request")
    _validate_request(collected_root, request)
    evidence_dir = _safe_package_path(
        collected_root,
        Path(_required_mapping(request, "output", "render request")["directory"]),
        "output.directory",
    )
    if evidence_dir.relative_to(collected_root) != EVIDENCE_DIRECTORY:
        raise ValueError(f"output.directory must be {EVIDENCE_DIRECTORY.as_posix()}")
    staging_dir = Path(
        tempfile.mkdtemp(
            prefix=f".{evidence_dir.name}.staging-",
            dir=evidence_dir.parent,
        )
    )

    try:
        _render_initial_scene(
            collected_root=collected_root,
            genmanip_root=genmanip_root,
            request=request,
            request_sha256=_file_sha256(request_path),
            staging_dir=staging_dir,
            evidence_dir=evidence_dir,
        )
    except Exception:
        if staging_dir.exists() or staging_dir.is_symlink():
            _remove_path(staging_dir)
        raise

    print(f"Rendered initial-scene evidence: {evidence_dir}")
    return 0


def _render_initial_scene(
    *,
    collected_root: Path,
    genmanip_root: Path,
    request: Mapping[str, Any],
    request_sha256: str,
    staging_dir: Path,
    evidence_dir: Path,
) -> None:
    if str(genmanip_root) not in sys.path:
        sys.path.insert(0, str(genmanip_root))

    # Simulator imports stay behind the process boundary and after SimulationApp
    # starts.  Pure Scenario Forge package modules never import these SDKs.
    from isaacsim import SimulationApp

    simulation_app = SimulationApp(
        {
            "headless": True,
            "fast_shutdown": False,
            "renderer": "RayTracedLighting",
            "anti_aliasing": 4,
            "multi_gpu": False,
            "width": 1280,
            "height": 720,
        }
    )
    log_lines = [
        "Scenario Forge GenManip initial preview",
        "moment=post_reset_pre_action",
        "action_count=0",
        "phase=simulation_app_ready",
    ]
    _flush_runtime_log(staging_dir, log_lines)
    try:
        import numpy as np
        from PIL import Image
        from pxr import Gf, Usd, UsdGeom, UsdLux

        from genmanip.core.scene.scene import Scene
        from genmanip.core.scene.scene_config import SceneConfig
        from genmanip.utils.loader.domain_randomization import reset_scene
        from genmanip.utils.loader.scene import create_camera_list, recovery_scene
        from genmanip.utils.standalone.file_utils import load_default_config
        from genmanip.utils.usd_utils.camera_utils import get_src, set_camera_look_at

        log_lines.append("phase=runtime_imports_ready")
        _flush_runtime_log(staging_dir, log_lines)

        inputs = _required_mapping(request, "inputs", "render request")
        task_config_path = _input_path(collected_root, inputs, "task_config")
        episode_path = _input_path(collected_root, inputs, "episode_metadata")
        scene_path = _input_path(collected_root, inputs, "scene_usd")
        evaluation_camera_path = _input_path(
            collected_root, inputs, "evaluation_camera"
        )

        task_config = _load_mapping(task_config_path, "task config")
        episode = _load_json_mapping(episode_path, "episode metadata")
        task_name = _required_string(request, "task_name", "render request")
        evaluation = _select_evaluation(task_config, task_name)
        evaluation["usd_name"] = str(scene_path.with_suffix(""))
        domain = _required_mapping(evaluation, "domain_randomization", "evaluation")
        cameras = _required_mapping(domain, "cameras", "evaluation domain_randomization")
        cameras["config_path"] = str(evaluation_camera_path)
        domain["cameras"] = cameras
        evaluation["domain_randomization"] = domain

        default_config = load_default_config(
            str(genmanip_root), "__scenario_forge_preview__.json", "local"
        )
        scene_config = SceneConfig(**evaluation)
        log_lines.append("phase=scene_config_ready")
        _flush_runtime_log(staging_dir, log_lines)
        scene = Scene(scene_config)
        log_lines.append("phase=scene_constructed")
        _flush_runtime_log(staging_dir, log_lines)
        scene.initialize(
            default_config,
            physics_dt=float(evaluation.get("physics_dt", 1.0 / 60.0)),
            rendering_dt=float(evaluation.get("rendering_dt", 1.0 / 60.0)),
            is_render=True,
            only_color_rep_for_camera=True,
        )
        log_lines.append("phase=scene_initialized")
        _flush_runtime_log(staging_dir, log_lines)
        scene.post_initialize()
        reset_scene(scene)
        task_data = _required_mapping(episode, "task_data", "episode metadata")
        recovery_scene(scene, copy.deepcopy(task_data), task_name, default_config)
        for _ in range(WARMUP_STEPS):
            scene.world.step(render=False)
        log_lines.extend(
            [
                f"scene_usd={scene_path}",
                f"scene_uid={scene.uuid}",
                "genmanip_scene_initialized=true",
                "genmanip_reset_scene=true",
                "genmanip_recovery_scene=true",
                f"zero_action_warmup_steps={WARMUP_STEPS}",
            ]
        )

        stage = scene.world.stage
        preview_light = UsdLux.DomeLight.Define(
            stage, "/World/ScenarioForgeInitialPreviewLight"
        )
        preview_light.CreateIntensityAttr(750.0)
        preview_light.CreateColorAttr(Gf.Vec3f(1.0, 1.0, 1.0))

        request_views = _required_mapping(request, "views", "render request")
        camera_data = {
            view_name: _camera_config(view_name, request_views)
            for view_name in VIEW_NAMES
        }
        preview_cameras = create_camera_list(
            camera_data,
            scene.uuid,
            float(evaluation.get("rendering_dt", 1.0 / 60.0)),
            only_color_rep_for_camera=True,
        )
        bbox_cache = UsdGeom.BBoxCache(
            Usd.TimeCode.Default(),
            [UsdGeom.Tokens.default_, UsdGeom.Tokens.render],
            useExtentsHint=True,
        )

        camera_records: dict[str, dict[str, Any]] = {}
        for view_name in VIEW_NAMES:
            view_request = _as_mapping(
                request_views.get(view_name), f"render request view {view_name}"
            )
            anchor_ids = _string_list(
                view_request.get("anchor_runtime_ids"),
                f"{view_name}.anchor_runtime_ids",
            )
            bounds = _runtime_bounds(
                stage=stage,
                scene=scene,
                runtime_ids=anchor_ids,
                bbox_cache=bbox_cache,
                np=np,
            )
            focal_length = float(camera_data[view_name]["focal_length"])
            target, distance = _fit_camera(bounds, view_request, focal_length, np)
            camera = preview_cameras[view_name]
            set_camera_look_at(
                camera,
                target,
                distance=distance,
                elevation=float(view_request["elevation_deg"]),
                azimuth=float(view_request["azimuth_deg"]),
            )
            position, _ = camera.get_world_pose()
            camera_records[view_name] = {
                "target": target,
                "position": position,
                "distance": distance,
                "focal_length": focal_length,
            }

        for _ in range(RENDER_STEPS):
            scene.world.step(render=True)

        manifest_views: dict[str, Any] = {}
        for view_name in VIEW_NAMES:
            camera = preview_cameras[view_name]
            rgb = get_src(camera, "rgb")
            attempts = 0
            while rgb is None and attempts < 20:
                scene.world.step(render=True)
                rgb = get_src(camera, "rgb")
                attempts += 1
            if rgb is None:
                raise RuntimeError(f"camera returned no RGB frame: {view_name}")
            image_path = staging_dir / f"{view_name}.png"
            _save_rgb_png(image_path, rgb, np, Image)

            view_request = _as_mapping(
                request_views.get(view_name), f"render request view {view_name}"
            )
            required_ids = _string_list(
                view_request.get("required_runtime_ids"),
                f"{view_name}.required_runtime_ids",
            )
            present_ids = _present_runtime_ids(stage, scene, required_ids)
            if present_ids != required_ids:
                missing = [item for item in required_ids if item not in present_ids]
                raise RuntimeError(
                    f"required runtime prims missing for {view_name}: {', '.join(missing)}"
                )
            record = camera_records[view_name]
            resolution = _resolution(view_request.get("resolution"), view_name)
            manifest_views[view_name] = {
                "status": "pass",
                "image_path": image_path.name,
                "sha256": _file_sha256(image_path),
                "resolution": list(resolution),
                "present_runtime_ids": present_ids,
                "camera": {
                    "position": _float_list(record["position"]),
                    "look_at": _float_list(record["target"]),
                    "distance_m": float(record["distance"]),
                    "focal_length_mm": float(record["focal_length"]),
                    "engine_native": True,
                    "temporary_evidence_camera": True,
                },
            }

        log_lines.extend(
            [
                "temporary_evidence_cameras=workspace_closeup,scene_overview",
                f"render_steps={RENDER_STEPS}",
                "runtime_log_scan=pending_parent_capture",
                "render_status=pass",
            ]
        )
        (staging_dir / "runtime.log").write_text(
            "\n".join(log_lines) + "\n", encoding="utf-8"
        )
        manifest = {
            "schema_version": EVIDENCE_SCHEMA,
            "package_id": _required_string(request, "package_id", "render request"),
            "input_digest": _required_string(
                request, "input_digest", "render request"
            ),
            "request_sha256": request_sha256,
            "purpose": "evidence_only",
            "moment": "post_reset_pre_action",
            "render_status": "pass",
            "runtime": {
                "engine": "Isaac Sim",
                "isaac_sim_version": _package_version("isaacsim"),
                "genmanip_revision": _git_revision(genmanip_root),
                "renderer": "RayTracedLighting",
                "genmanip_scene_uid": scene.uuid,
                "robot_injected": "lift2",
                "action_count": 0,
                "warmup_steps": WARMUP_STEPS,
            },
            "runtime_log_path": "runtime.log",
            "runtime_log_sha256": _file_sha256(staging_dir / "runtime.log"),
            "runtime_log_scan": {
                "status": "pending_parent_capture",
                "scope": "known_blocking_material_signals",
                "scanned_streams": ["renderer_runtime_log"],
                "blocking_signal_count": 0,
                "blocking_signals": [],
            },
            "views": manifest_views,
            "claim_boundary": (
                "Initial-scene visual evidence only; not task success, policy success, "
                "physics fidelity, or liquid-transfer evidence."
            ),
        }
        _write_json(staging_dir / "render_manifest.json", manifest)
        if evidence_dir.exists() or evidence_dir.is_symlink():
            _remove_path(evidence_dir)
        staging_dir.rename(evidence_dir)
        print(f"Committed initial-scene evidence: {evidence_dir}", flush=True)

        scene.world.stop()
        scene.world.clear_instance()
        del camera
        del preview_cameras
        del bbox_cache
        del stage
        del scene
        gc.collect()
    except BaseException as exc:
        log_lines.extend(
            [
                "render_status=failed",
                f"exception_type={type(exc).__name__}",
                f"exception={exc}",
            ]
        )
        _flush_runtime_log(staging_dir, log_lines)
        traceback.print_exc()
        raise
    finally:
        simulation_app.close()


def _camera_config(
    view_name: str, request_views: Mapping[str, Any]
) -> dict[str, Any]:
    view = _as_mapping(request_views.get(view_name), f"render request view {view_name}")
    width, height = _resolution(view.get("resolution"), view_name)
    return {
        "exists": False,
        "frequency": 60,
        "name": f"scenario_forge_{view_name}",
        "position": [0.0, 0.0, 1.0],
        "orientation": [1.0, 0.0, 0.0, 0.0],
        "prim_path": f"_{view_name}",
        "resolution": [width, height],
        "focal_length": 7.0 if view_name == "workspace_closeup" else 6.0,
        "horizontal_aperture": 10.0,
        "vertical_aperture": 5.625,
        "with_distance": False,
        "with_semantic": False,
        "with_bbox2d": False,
        "with_bbox3d": False,
        "with_motion_vector": False,
    }


def _runtime_bounds(
    *, stage: Any, scene: Any, runtime_ids: list[str], bbox_cache: Any, np: Any
) -> tuple[Any, Any]:
    lower_points: list[Any] = []
    upper_points: list[Any] = []
    for runtime_id in runtime_ids:
        prims = _runtime_prims(stage, scene, runtime_id)
        if not prims:
            raise RuntimeError(f"anchor runtime prim is unavailable: {runtime_id}")
        for prim in prims:
            if prim is None or not prim.IsValid() or not prim.IsActive():
                raise RuntimeError(f"anchor runtime prim is unavailable: {runtime_id}")
            aligned_range = bbox_cache.ComputeWorldBound(prim).ComputeAlignedRange()
            lower = np.asarray(aligned_range.GetMin(), dtype=float)
            upper = np.asarray(aligned_range.GetMax(), dtype=float)
            if lower.shape != (3,) or upper.shape != (3,):
                raise RuntimeError(f"invalid runtime bounds for {runtime_id}")
            if not np.all(np.isfinite(lower)) or not np.all(np.isfinite(upper)):
                raise RuntimeError(f"non-finite runtime bounds for {runtime_id}")
            if np.any(upper <= lower):
                raise RuntimeError(f"empty runtime bounds for {runtime_id}")
            lower_points.append(lower)
            upper_points.append(upper)
    if not lower_points:
        raise RuntimeError("camera anchor set is empty")
    return np.min(np.stack(lower_points), axis=0), np.max(
        np.stack(upper_points), axis=0
    )


def _fit_camera(
    bounds: tuple[Any, Any], view: Mapping[str, Any], focal_length: float, np: Any
) -> tuple[Any, float]:
    lower, upper = bounds
    target = (lower + upper) / 2.0
    extent = upper - lower
    radius = max(float(np.linalg.norm(extent) / 2.0), 0.05)
    vertical_fov = 2.0 * math.atan(5.625 / (2.0 * focal_length))
    margin = float(view.get("framing_margin", 1.25))
    distance = radius / math.tan(vertical_fov / 2.0) * margin
    minimum = float(view.get("minimum_distance", 0.85))
    return target, max(distance, minimum)


def _runtime_prims(stage: Any, scene: Any, runtime_id: str) -> list[Any]:
    if runtime_id == "lift2_end_effectors":
        root = f"/World/{scene.uuid}/lift2/lift2/lift2"
        return [
            stage.GetPrimAtPath(f"{root}/fl/link6"),
            stage.GetPrimAtPath(f"{root}/fr/link6"),
        ]
    prim = _runtime_prim(stage, scene, runtime_id)
    return [] if prim is None else [prim]


def _runtime_prim(stage: Any, scene: Any, runtime_id: str) -> Any | None:
    if runtime_id == "lift2":
        return stage.GetPrimAtPath(f"/World/{scene.uuid}/lift2")
    scene_object = scene.object_list.get(runtime_id)
    return None if scene_object is None else scene_object.prim


def _present_runtime_ids(
    stage: Any, scene: Any, runtime_ids: list[str]
) -> list[str]:
    present: list[str] = []
    for runtime_id in runtime_ids:
        prim = _runtime_prim(stage, scene, runtime_id)
        if prim is not None and prim.IsValid() and prim.IsActive():
            present.append(runtime_id)
    return present


def _save_rgb_png(path: Path, value: Any, np: Any, image_type: Any) -> None:
    array = np.asarray(value)
    if array.ndim != 3 or array.shape[2] < 3:
        raise RuntimeError(f"unexpected RGB frame shape: {array.shape}")
    if array.dtype != np.uint8:
        array = np.nan_to_num(
            array.astype(np.float32), nan=0.0, posinf=255.0, neginf=0.0
        )
        if array.size and float(np.max(array)) <= 1.0:
            array *= 255.0
        array = np.clip(array, 0.0, 255.0).astype(np.uint8)
    image_type.fromarray(array[:, :, :3], mode="RGB").save(path)


def _select_evaluation(
    task_config: Mapping[str, Any], task_name: str
) -> dict[str, Any]:
    raw_configs = task_config.get("evaluation_configs")
    if not isinstance(raw_configs, list):
        raise ValueError("task config evaluation_configs must be a list")
    matches = [
        item
        for item in raw_configs
        if isinstance(item, Mapping) and item.get("task_name") == task_name
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one evaluation config for {task_name!r}")
    return copy.deepcopy(dict(matches[0]))


def _validate_request(root: Path, request: Mapping[str, Any]) -> None:
    if request.get("schema_version") != REQUEST_SCHEMA:
        raise ValueError("unsupported render request schema_version")
    if request.get("purpose") != "evidence_only":
        raise ValueError("render request purpose must be evidence_only")
    if request.get("affects_policy_observation") is not False:
        raise ValueError("render request must not affect policy observations")
    if request.get("moment") != "post_reset_pre_action":
        raise ValueError("render request moment must be post_reset_pre_action")
    inputs = _required_mapping(request, "inputs", "render request")
    if set(inputs) != INPUT_ROLES:
        raise ValueError("render request inputs are incomplete")
    for role, raw_item in inputs.items():
        item = _as_mapping(raw_item, f"render request input {role}")
        path = _safe_package_path(
            root, Path(_required_string(item, "path", f"input {role}")), str(role)
        )
        if role == "source_bundle":
            if not path.is_dir():
                raise ValueError(f"missing render input {role}: {path}")
            current_sha256 = _tree_sha256(path)
        else:
            if not path.is_file():
                raise ValueError(f"missing render input {role}: {path}")
            current_sha256 = _file_sha256(path)
        if item.get("sha256") != current_sha256:
            raise ValueError(f"render input sha256 mismatch: {role}")
    package_id = _required_string(request, "package_id", "render request")
    digest_payload = json.dumps(
        {"package_id": package_id, "inputs": inputs},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    expected_digest = "sha256:" + sha256(digest_payload).hexdigest()
    if request.get("input_digest") != expected_digest:
        raise ValueError("render request input_digest does not match inputs")
    views = _required_mapping(request, "views", "render request")
    if set(views) != set(VIEW_NAMES):
        raise ValueError("render request must contain both preview views")


def _input_path(root: Path, inputs: Mapping[str, Any], role: str) -> Path:
    item = _as_mapping(inputs.get(role), f"render request input {role}")
    return _safe_package_path(
        root, Path(_required_string(item, "path", f"input {role}")), role
    )


def _safe_package_path(root: Path, relative: Path, label: str) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{label} must be a package-relative path")
    candidate = (root / relative).resolve()
    if root != candidate and root not in candidate.parents:
        raise ValueError(f"{label} escapes collected package root")
    return candidate


def _load_mapping(path: Path, label: str) -> Mapping[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing {label}: {path}")
    return _as_mapping(yaml.safe_load(path.read_text(encoding="utf-8")), label)


def _load_json_mapping(path: Path, label: str) -> Mapping[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing {label}: {path}")
    return _as_mapping(json.loads(path.read_text(encoding="utf-8")), label)


def _as_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _required_mapping(
    value: Mapping[str, Any], key: str, label: str
) -> dict[str, Any]:
    result = value.get(key)
    if not isinstance(result, Mapping):
        raise ValueError(f"{label}.{key} must be a mapping")
    return dict(result)


def _required_string(value: Mapping[str, Any], key: str, label: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"{label}.{key} must be a non-empty string")
    return result


def _string_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{label} must be a list of non-empty strings")
    return list(value)


def _resolution(value: object, label: str) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(
            isinstance(item, int) and not isinstance(item, bool) and item > 0
            for item in value
        )
    ):
        raise ValueError(f"{label} resolution must contain two positive integers")
    return value[0], value[1]


def _float_list(value: Any) -> list[float]:
    return [float(item) for item in value]


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _tree_sha256(root: Path) -> str:
    digest = sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"render source bundle must not contain symlinks: {path}")
        if not path.is_file():
            continue
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(_file_sha256(path).removeprefix("sha256:")))
    return "sha256:" + digest.hexdigest()


def _package_version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _git_revision(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _flush_runtime_log(staging_dir: Path, lines: list[str]) -> None:
    (staging_dir / "runtime.log").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)


if __name__ == "__main__":
    raise SystemExit(main())

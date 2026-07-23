from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import struct
import subprocess
from typing import Any, Mapping

import yaml

from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.assets.checksum import compute_sha256


PREVIEW_REQUEST_SCHEMA_VERSION = "scenario-forge-genmanip-preview-request/v0.1"
PREVIEW_EVIDENCE_SCHEMA_VERSION = "scenario-forge-genmanip-preview-evidence/v0.1"
PREVIEW_GATE_SCHEMA_VERSION = "scenario-forge-genmanip-preview-gate/v0.1"
PREVIEW_REQUEST_PATH = Path("evidence/render_request.yaml")
PREVIEW_EVIDENCE_DIR = Path("evidence/initial_scene")
PREVIEW_VIEW_NAMES = ("workspace_closeup", "scene_overview")

_INPUT_ENTRYPOINTS = {
    "package_manifest": None,
    "task_config": "task_config",
    "episode_metadata": "episode_metadata",
    "scene_usd": "scene_usd",
    "evaluation_camera": "camera_config",
}
_SOURCE_BUNDLE_INPUT = "source_bundle"
_BLOCKING_LOG_SIGNALS = (
    "Failed to create MDL shade node",
    "missing texture",
    "could not find texture",
    "could not find module",
    "MDL compiler error",
    "References an asset that can not be found",
    "wasn't resolved properly",
)


class GenManipPreviewError(ValueError):
    """Raised when GenManip initial-scene preview evidence is invalid."""


@dataclass(frozen=True)
class GenManipPreviewValidationResult:
    collected_root: Path
    evidence_dir: Path
    gate_path: Path
    status: str


def run_genmanip_initial_preview(
    collected_root: str | Path,
    isaac_python: str | Path,
    renderer_script: str | Path,
    genmanip_root: str | Path,
    *,
    timeout_seconds: float = 900.0,
) -> GenManipPreviewValidationResult:
    root = Path(collected_root).resolve()
    python_path = Path(isaac_python).resolve()
    script_path = Path(renderer_script).resolve()
    runtime_root = Path(genmanip_root).resolve()
    gate_path = _safe_package_path(
        root,
        PREVIEW_EVIDENCE_DIR / "visual_ready_gate.yaml",
        "preview visual-ready gate",
    )
    if gate_path.exists() or gate_path.is_symlink():
        gate_path.unlink()

    if not root.is_dir():
        raise GenManipPreviewError(f"collected package does not exist: {root}")
    if not python_path.is_file():
        raise GenManipPreviewError(f"Isaac Python does not exist: {python_path}")
    if not script_path.is_file():
        raise GenManipPreviewError(f"preview renderer does not exist: {script_path}")
    if not runtime_root.is_dir():
        raise GenManipPreviewError(f"GenManip root does not exist: {runtime_root}")
    if timeout_seconds <= 0:
        raise GenManipPreviewError("preview timeout_seconds must be positive")

    command = [
        str(python_path),
        str(script_path),
        "--collected-root",
        str(root),
        "--genmanip-root",
        str(runtime_root),
        "--request",
        PREVIEW_REQUEST_PATH.as_posix(),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=runtime_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise GenManipPreviewError(
            f"GenManip initial preview timed out after {timeout_seconds:g} seconds"
        ) from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        suffix = f": {detail[-2000:]}" if detail else ""
        raise GenManipPreviewError(
            f"GenManip initial preview failed with exit status {completed.returncode}{suffix}"
        )
    manifest_path = _safe_package_path(
        root,
        PREVIEW_EVIDENCE_DIR / "render_manifest.json",
        "preview render manifest",
    )
    if not manifest_path.is_file():
        detail = _latest_staging_failure(root)
        if detail is None:
            detail = (completed.stderr or completed.stdout).strip() or None
        suffix = f": {detail[-4000:]}" if detail else ""
        raise GenManipPreviewError(
            "GenManip initial preview exited with status 0 without committing "
            f"render manifest{suffix}"
        )
    _finalize_runtime_log_scan(root, completed.stdout, completed.stderr)
    return validate_genmanip_preview_evidence(root)


def write_genmanip_preview_request(collected_root: str | Path) -> Path:
    root = Path(collected_root).resolve()
    package_manifest = _load_json(root / "package_manifest.json", "package manifest")
    package_id = _required_string(package_manifest, "package_id", "package manifest")
    entrypoints = _required_mapping(package_manifest, "entrypoints", "package manifest")
    episode_path = _entrypoint_path(root, entrypoints, "episode_metadata")
    episode = _load_json(episode_path, "episode metadata")
    task_name = _required_string(episode, "task_name", "episode metadata")
    episode_name = _required_string(episode, "episode_name", "episode metadata")
    task_data = _required_mapping(episode, "task_data", "episode metadata")
    initial_layout = _required_mapping(task_data, "initial_layout", "episode task_data")

    robot_ids = [
        str(runtime_id)
        for runtime_id, item in initial_layout.items()
        if isinstance(item, Mapping) and item.get("type") == "robot"
    ]
    table_ids = [
        str(runtime_id)
        for runtime_id, item in initial_layout.items()
        if isinstance(item, Mapping)
        and item.get("type") == "object"
        and str(runtime_id) == "00000000000000000000000000000000"
    ]
    task_object_ids = [
        str(runtime_id)
        for runtime_id, item in initial_layout.items()
        if isinstance(item, Mapping)
        and item.get("type") == "object"
        and str(runtime_id) not in table_ids
    ]
    if robot_ids != ["lift2"] or len(table_ids) != 1 or not task_object_ids:
        raise GenManipPreviewError(
            "preview request requires Lift2, one table, and at least one task object"
        )

    inputs = _current_preview_inputs(root, package_manifest)
    request = {
        "schema_version": PREVIEW_REQUEST_SCHEMA_VERSION,
        "package_id": package_id,
        "task_name": task_name,
        "episode_name": episode_name,
        "purpose": "evidence_only",
        "affects_policy_observation": False,
        "moment": "post_reset_pre_action",
        "camera_policy_version": "scenario-forge/task-anchor-fit-v6",
        "input_digest": _digest_inputs(package_id, inputs),
        "inputs": inputs,
        "expected_runtime_ids": {
            "robot": "lift2",
            "table": table_ids[0],
            "task_objects": task_object_ids,
        },
        "views": {
            "workspace_closeup": {
                "resolution": [1280, 720],
                "required_runtime_ids": [table_ids[0], *task_object_ids],
                "anchor_runtime_ids": ["lift2_end_effectors", *task_object_ids],
                "azimuth_deg": -35.0,
                "elevation_deg": 34.0,
                "framing_margin": 1.15,
                "minimum_distance": 1.0,
            },
            "scene_overview": {
                "resolution": [1280, 720],
                "required_runtime_ids": ["lift2", table_ids[0], *task_object_ids],
                "anchor_runtime_ids": [
                    "scene_room",
                    "lift2",
                    table_ids[0],
                    *task_object_ids,
                ],
                "azimuth_deg": -125.0,
                "elevation_deg": 38.0,
                "framing_margin": 1.05,
                "minimum_distance": 1.6,
            },
        },
        "output": {
            "directory": PREVIEW_EVIDENCE_DIR.as_posix(),
            "manifest": (PREVIEW_EVIDENCE_DIR / "render_manifest.json").as_posix(),
        },
        "claim_boundary": (
            "Initial-scene visual evidence only; not task success, policy success, "
            "physics fidelity, or liquid-transfer evidence."
        ),
    }
    request_path = _safe_package_path(
        root, PREVIEW_REQUEST_PATH, "preview render request"
    )
    return write_yaml_artifact(request_path, request)


def compute_preview_input_digest(collected_root: str | Path) -> str:
    root = Path(collected_root).resolve()
    package_manifest = _load_json(root / "package_manifest.json", "package manifest")
    package_id = _required_string(package_manifest, "package_id", "package manifest")
    return _digest_inputs(package_id, _current_preview_inputs(root, package_manifest))


def validate_genmanip_preview_evidence(
    collected_root: str | Path,
) -> GenManipPreviewValidationResult:
    root = Path(collected_root).resolve()
    evidence_dir = _safe_package_path(
        root, PREVIEW_EVIDENCE_DIR, "preview evidence directory"
    )
    gate_path = _safe_package_path(
        root,
        PREVIEW_EVIDENCE_DIR / "visual_ready_gate.yaml",
        "preview visual-ready gate",
    )
    if gate_path.exists() or gate_path.is_symlink():
        gate_path.unlink()

    request = _load_yaml(root / PREVIEW_REQUEST_PATH, "preview render request")
    if request.get("schema_version") != PREVIEW_REQUEST_SCHEMA_VERSION:
        raise GenManipPreviewError("unsupported preview request schema_version")
    package_id = _required_string(request, "package_id", "preview request")
    package_manifest = _load_json(root / "package_manifest.json", "package manifest")
    manifest_package_id = _required_string(
        package_manifest, "package_id", "package manifest"
    )
    if package_id != manifest_package_id:
        raise GenManipPreviewError(
            "preview request package_id does not match package manifest"
        )
    current_inputs = _current_preview_inputs(root, package_manifest)
    expected_digest = _digest_inputs(package_id, current_inputs)
    request_digest = _required_string(request, "input_digest", "preview request")
    if request_digest != expected_digest:
        raise GenManipPreviewError("preview request input digest is stale")
    request_inputs = _required_mapping(request, "inputs", "preview request")
    if request_inputs != current_inputs:
        raise GenManipPreviewError("preview request inputs do not match current package inputs")
    if _digest_inputs(package_id, request_inputs) != request_digest:
        raise GenManipPreviewError("preview request input digest does not match request inputs")
    _validate_request_inputs(root, request)

    manifest = _load_json(evidence_dir / "render_manifest.json", "preview render manifest")
    if manifest.get("schema_version") != PREVIEW_EVIDENCE_SCHEMA_VERSION:
        raise GenManipPreviewError("unsupported preview evidence schema_version")
    if manifest.get("package_id") != package_id:
        raise GenManipPreviewError("preview evidence package_id does not match request")
    if manifest.get("input_digest") != expected_digest:
        raise GenManipPreviewError("preview evidence input digest does not match current inputs")
    if manifest.get("request_sha256") != compute_sha256(root / PREVIEW_REQUEST_PATH):
        raise GenManipPreviewError("preview evidence request sha256 does not match")
    if manifest.get("purpose") != "evidence_only":
        raise GenManipPreviewError("preview evidence purpose must be evidence_only")
    if manifest.get("moment") != "post_reset_pre_action":
        raise GenManipPreviewError("preview evidence moment must be post_reset_pre_action")
    if manifest.get("render_status") != "pass":
        raise GenManipPreviewError("preview evidence render_status must be pass")

    runtime_scan = _required_mapping(
        manifest, "runtime_log_scan", "preview render manifest"
    )
    blocking_signals = _string_list(
        runtime_scan.get("blocking_signals", []),
        "preview render manifest.runtime_log_scan.blocking_signals",
    )
    if runtime_scan.get("status") != "pass":
        suffix = f": {blocking_signals[0]}" if blocking_signals else ""
        raise GenManipPreviewError(
            f"preview runtime log contains blocking material signal{suffix}"
        )
    if runtime_scan.get("scope") != "known_blocking_material_signals":
        raise GenManipPreviewError("preview runtime log scan scope is unsupported")
    runtime_log_path = _safe_relative_path(
        evidence_dir,
        _required_string(manifest, "runtime_log_path", "preview render manifest"),
        "runtime_log_path",
    )
    runtime_log_sha256 = compute_sha256(runtime_log_path)
    if manifest.get("runtime_log_sha256") != runtime_log_sha256:
        raise GenManipPreviewError("preview runtime log sha256 mismatch")
    runtime_log = runtime_log_path.read_text(encoding="utf-8", errors="replace")
    for signal in _BLOCKING_LOG_SIGNALS:
        if signal.lower() in runtime_log.lower():
            raise GenManipPreviewError(
                f"preview runtime log contains blocking material signal: {signal}"
            )

    request_views = _required_mapping(request, "views", "preview request")
    manifest_views = _required_mapping(manifest, "views", "preview render manifest")
    if set(manifest_views) != set(PREVIEW_VIEW_NAMES):
        raise GenManipPreviewError("preview evidence must contain both required views")

    gate_views: dict[str, Any] = {}
    for view_name in PREVIEW_VIEW_NAMES:
        view_request = _as_mapping(request_views.get(view_name), f"request view {view_name}")
        view = _as_mapping(manifest_views.get(view_name), f"evidence view {view_name}")
        if view.get("status") != "pass":
            raise GenManipPreviewError(f"preview view {view_name} status must be pass")
        image_path = _safe_relative_path(
            evidence_dir,
            _required_string(view, "image_path", f"evidence view {view_name}"),
            f"{view_name}.image_path",
        )
        if not image_path.is_file():
            raise GenManipPreviewError(f"missing preview image for {view_name}: {image_path.name}")
        actual_hash = compute_sha256(image_path)
        if view.get("sha256") != actual_hash:
            raise GenManipPreviewError(f"preview image sha256 mismatch for {view_name}")
        requested_resolution = _resolution(view_request.get("resolution"), view_name)
        recorded_resolution = _resolution(view.get("resolution"), view_name)
        image_resolution = _png_dimensions(image_path)
        if recorded_resolution != requested_resolution or image_resolution != requested_resolution:
            raise GenManipPreviewError(f"preview image resolution mismatch for {view_name}")
        required_ids = _string_list(
            view_request.get("required_runtime_ids"), f"{view_name}.required_runtime_ids"
        )
        present_ids = _string_list(
            view.get("present_runtime_ids"), f"{view_name}.present_runtime_ids"
        )
        missing_ids = [runtime_id for runtime_id in required_ids if runtime_id not in present_ids]
        if missing_ids:
            raise GenManipPreviewError(
                f"preview view {view_name} is missing runtime ids: {', '.join(missing_ids)}"
            )
        gate_views[view_name] = {
            "image_path": image_path.relative_to(evidence_dir).as_posix(),
            "sha256": actual_hash,
            "resolution": list(image_resolution),
            "status": "passed",
        }

    gate = {
        "schema_version": PREVIEW_GATE_SCHEMA_VERSION,
        "status": "passed",
        "package_id": package_id,
        "input_digest": expected_digest,
        "request_sha256": manifest["request_sha256"],
        "runtime_log_sha256": runtime_log_sha256,
        "moment": "post_reset_pre_action",
        "views": gate_views,
        "verification_scope": "structural_artifact_and_runtime_prim_presence",
        "next_stage": "clean_room_visual_review",
        "claim_boundary": (
            "Structural initial-scene evidence readiness only; does not verify "
            "on-camera visibility or visual quality, and is not task success, policy "
            "success, physics fidelity, or liquid-transfer evidence."
        ),
    }
    write_yaml_artifact(gate_path, gate)
    return GenManipPreviewValidationResult(
        collected_root=root,
        evidence_dir=evidence_dir,
        gate_path=gate_path,
        status="passed",
    )


def _current_preview_inputs(
    root: Path, package_manifest: Mapping[str, Any]
) -> dict[str, dict[str, str]]:
    entrypoints = _required_mapping(package_manifest, "entrypoints", "package manifest")
    result: dict[str, dict[str, str]] = {}
    for role, entrypoint in _INPUT_ENTRYPOINTS.items():
        relative = Path("package_manifest.json") if entrypoint is None else Path(
            _required_string(entrypoints, entrypoint, "package manifest entrypoints")
        )
        path = _safe_package_path(root, relative, role)
        if not path.is_file():
            raise GenManipPreviewError(f"missing preview input {role}: {relative.as_posix()}")
        result[role] = {
            "path": relative.as_posix(),
            "sha256": compute_sha256(path),
        }
    scene_relative = Path(result["scene_usd"]["path"])
    source_bundle_relative = scene_relative.parent / "source_bundle"
    source_bundle = _safe_package_path(
        root, source_bundle_relative, _SOURCE_BUNDLE_INPUT
    )
    if not source_bundle.is_dir():
        raise GenManipPreviewError(
            f"missing preview input source_bundle: {source_bundle_relative.as_posix()}"
        )
    result[_SOURCE_BUNDLE_INPUT] = {
        "path": source_bundle_relative.as_posix(),
        "sha256": _tree_sha256(source_bundle),
    }
    return result


def _digest_inputs(package_id: str, inputs: Mapping[str, Any]) -> str:
    payload = json.dumps(
        {"package_id": package_id, "inputs": inputs},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + sha256(payload).hexdigest()


def _latest_staging_failure(root: Path) -> str | None:
    evidence_root = _safe_package_path(
        root, PREVIEW_EVIDENCE_DIR.parent, "preview evidence root"
    )
    candidates = [
        path
        for path in evidence_root.glob(
            f".{PREVIEW_EVIDENCE_DIR.name}.staging-*/runtime.log"
        )
        if path.is_file()
    ]
    if not candidates:
        return None
    latest = max(
        candidates,
        key=lambda path: (path.stat().st_mtime_ns, path.as_posix()),
    )
    detail = latest.read_text(encoding="utf-8", errors="replace").strip()
    return detail if "render_status=failed" in detail else None


def _finalize_runtime_log_scan(root: Path, stdout: str, stderr: str) -> None:
    evidence_dir = _safe_package_path(
        root, PREVIEW_EVIDENCE_DIR, "preview evidence directory"
    )
    manifest_path = _safe_package_path(
        root,
        PREVIEW_EVIDENCE_DIR / "render_manifest.json",
        "preview render manifest",
    )
    manifest = dict(_load_json(manifest_path, "preview render manifest"))
    runtime_log_path = _safe_relative_path(
        evidence_dir,
        _required_string(manifest, "runtime_log_path", "preview render manifest"),
        "runtime_log_path",
    )
    renderer_log = runtime_log_path.read_text(encoding="utf-8", errors="replace")
    combined = "\n".join(
        [
            renderer_log.rstrip(),
            "=== subprocess stdout ===",
            stdout.rstrip(),
            "=== subprocess stderr ===",
            stderr.rstrip(),
            "",
        ]
    )
    runtime_log_path.write_text(combined, encoding="utf-8")
    lowered = combined.lower()
    matches = [signal for signal in _BLOCKING_LOG_SIGNALS if signal.lower() in lowered]
    manifest["runtime_log_scan"] = {
        "status": "pass" if not matches else "failed",
        "scope": "known_blocking_material_signals",
        "scanned_streams": [
            "renderer_runtime_log",
            "subprocess_stdout",
            "subprocess_stderr",
        ],
        "blocking_signal_count": len(matches),
        "blocking_signals": matches,
    }
    manifest["runtime_log_sha256"] = compute_sha256(runtime_log_path)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _validate_request_inputs(root: Path, request: Mapping[str, Any]) -> None:
    inputs = _required_mapping(request, "inputs", "preview request")
    expected_roles = {*_INPUT_ENTRYPOINTS, _SOURCE_BUNDLE_INPUT}
    if set(inputs) != expected_roles:
        raise GenManipPreviewError("preview request inputs are incomplete")
    for role, raw_item in inputs.items():
        item = _as_mapping(raw_item, f"preview input {role}")
        relative = Path(_required_string(item, "path", f"preview input {role}"))
        path = _safe_package_path(root, relative, role)
        if role == _SOURCE_BUNDLE_INPUT:
            if not path.is_dir():
                raise GenManipPreviewError(f"missing preview input {role}")
            current_sha256 = _tree_sha256(path)
        else:
            if not path.is_file():
                raise GenManipPreviewError(f"missing preview input {role}")
            current_sha256 = compute_sha256(path)
        if item.get("sha256") != current_sha256:
            raise GenManipPreviewError(f"preview input sha256 mismatch for {role}")


def _tree_sha256(root: Path) -> str:
    digest = sha256()
    paths = sorted(root.rglob("*"))
    for path in paths:
        if path.is_symlink():
            raise GenManipPreviewError(
                f"preview source bundle must not contain symlinks: {path}"
            )
        if not path.is_file():
            continue
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(compute_sha256(path).removeprefix("sha256:")))
    return "sha256:" + digest.hexdigest()


def _entrypoint_path(root: Path, entrypoints: Mapping[str, Any], key: str) -> Path:
    relative = Path(_required_string(entrypoints, key, "package manifest entrypoints"))
    return _safe_package_path(root, relative, key)


def _safe_package_path(root: Path, relative: Path, label: str) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise GenManipPreviewError(f"{label} must be a package-relative path")
    resolved_root = root.resolve()
    resolved = (root / relative).resolve()
    if resolved_root not in resolved.parents:
        raise GenManipPreviewError(f"{label} escapes collected package root")
    return resolved


def _safe_relative_path(root: Path, value: str, label: str) -> Path:
    path = _safe_package_path(root, Path(value), label)
    if root.resolve() not in path.parents:
        raise GenManipPreviewError(f"{label} escapes preview evidence directory")
    return path


def _png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise GenManipPreviewError(f"preview image is not a valid PNG: {path.name}")
    width, height = struct.unpack(">II", header[16:24])
    return width, height


def _resolution(value: object, label: str) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(isinstance(item, int) and not isinstance(item, bool) and item > 0 for item in value)
    ):
        raise GenManipPreviewError(f"{label} resolution must contain two positive integers")
    return value[0], value[1]


def _string_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise GenManipPreviewError(f"{label} must be a list of non-empty strings")
    return list(value)


def _load_json(path: Path, label: str) -> Mapping[str, Any]:
    if not path.is_file():
        raise GenManipPreviewError(f"missing {label}: {path}")
    try:
        return _as_mapping(json.loads(path.read_text(encoding="utf-8")), label)
    except json.JSONDecodeError as exc:
        raise GenManipPreviewError(f"invalid JSON for {label}: {path}") from exc


def _load_yaml(path: Path, label: str) -> Mapping[str, Any]:
    if not path.is_file():
        raise GenManipPreviewError(f"missing {label}: {path}")
    return _as_mapping(yaml.safe_load(path.read_text(encoding="utf-8")), label)


def _as_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GenManipPreviewError(f"{label} must be a mapping")
    return value


def _required_mapping(
    data: Mapping[str, Any], key: str, label: str
) -> Mapping[str, Any]:
    return _as_mapping(data.get(key), f"{label}.{key}")


def _required_string(data: Mapping[str, Any], key: str, label: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise GenManipPreviewError(f"{label}.{key} must be a non-empty string")
    return value

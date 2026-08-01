"""Contracts for external fixed-base provisional IK evidence.

Scenario Forge derives deterministic candidate anchors from the canonical task
specification. GenManip/CuRobo owns solving those candidates and emitting the
result. This module only writes requests and verifies returned evidence.
"""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Mapping

import yaml


REQUEST_SCHEMA_VERSION = "scenario-forge-provisional-ik-request/v0.1"
RESULT_SCHEMA_VERSION = "ebench-provisional-ik-result/v0.1"
EVIDENCE_SCHEMA_VERSION = "scenario-forge-provisional-ik-evidence/v0.1"
_FIXED_BASE_TOLERANCE_M = 1e-9


class ProvisionalIKPreflightError(ValueError):
    """Raised when external provisional IK evidence violates the handoff contract."""


def write_provisional_ik_preflight_request(package_root: str | Path) -> Path:
    """Write deterministic top-down candidate anchors for task-grasped objects.

    The candidates are intentionally provisional. They specify an object anchor,
    top-down approach direction, and fixed-base requirement, while leaving arm
    joint solving and collision interpretation to the external runtime.
    """

    root = Path(package_root)
    scenario = _load_mapping(root / "scenario.yaml", "scenario")
    scenario_id = _required_string(scenario, "scenario_id", "scenario")
    candidates, unresolved_objects = _candidates(scenario, root / "scene/main.usda")
    candidate_status = "ready" if not unresolved_objects else "blocked"
    request = {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "scenario_id": scenario_id,
        "scenario_sha256": _digest_file(root / "scenario.yaml"),
        "robot_base_motion": [0.0, 0.0, 0.0],
        "candidate_generation": {
            "algorithm": "composed_bbox_top_down/v0.1",
            "pregrasp_offset_m": 0.12,
            "candidate_scope": "first declared grasp-or-lift actor per task object",
            "status": candidate_status,
            "blocked_reasons": [item["reason"] for item in unresolved_objects],
        },
        "candidates": candidates,
        "unresolved_objects": unresolved_objects,
        "claim_boundary": (
            "This is a request for external fixed-base IK solving. It does not itself "
            "prove IK feasibility, collision freedom, grasp closure, lifting, or task success."
        ),
    }
    request["request_sha256"] = _digest_mapping(request)
    path = root / "adapters/ebench/genmanip/provisional_ik_preflight/request.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(request, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def validate_provisional_ik_result(
    request_path: str | Path,
    result_path: str | Path,
) -> Path:
    """Verify an external fixed-base result and write package-local evidence."""

    request_file = Path(request_path)
    request = _load_mapping(request_file, "IK request")
    result = _load_mapping(Path(result_path), "IK result")
    if request.get("schema_version") != REQUEST_SCHEMA_VERSION:
        raise ProvisionalIKPreflightError("unsupported provisional IK request schema")
    if result.get("schema_version") != RESULT_SCHEMA_VERSION:
        raise ProvisionalIKPreflightError("unsupported provisional IK result schema")
    request_sha = _required_string(request, "request_sha256", "IK request")
    if result.get("request_sha256") != request_sha:
        raise ProvisionalIKPreflightError("IK result does not bind the exact request sha256")
    scenario_id = _required_string(request, "scenario_id", "IK request")
    if result.get("scenario_id") != scenario_id:
        raise ProvisionalIKPreflightError("IK result scenario_id does not match request")
    generation = request.get("candidate_generation")
    if not isinstance(generation, Mapping):
        raise ProvisionalIKPreflightError("IK request.candidate_generation must be a mapping")
    if generation.get("status") != "ready":
        raise ProvisionalIKPreflightError(
            "IK request has no complete composed-geometry candidate set; resolve: "
            + "; ".join(
                _required_string(item, "reason", "IK request unresolved object")
                for item in _mappings(request.get("unresolved_objects"), "IK request.unresolved_objects")
            )
        )
    _validate_fixed_base(result.get("robot_base_motion"))
    runner = result.get("runner")
    if not isinstance(runner, Mapping):
        raise ProvisionalIKPreflightError("IK result.runner must be a mapping")
    _required_string(runner, "name", "IK result.runner")
    _required_string(runner, "revision", "IK result.runner")

    candidates = _mappings(request.get("candidates"), "IK request.candidates")
    expected = {
        _required_string(candidate, "candidate_id", "IK request candidate"): _required_string(
            candidate, "object_id", "IK request candidate"
        )
        for candidate in candidates
    }
    candidate_results = _mappings(result.get("candidate_results"), "IK result.candidate_results")
    statuses: dict[str, str] = {}
    for item in candidate_results:
        candidate_id = _required_string(item, "candidate_id", "IK result candidate")
        if candidate_id not in expected:
            raise ProvisionalIKPreflightError(
                f"IK result contains unknown candidate '{candidate_id}'"
            )
        if candidate_id in statuses:
            raise ProvisionalIKPreflightError(
                f"IK result contains duplicate candidate '{candidate_id}'"
            )
        status = _required_string(item, "status", "IK result candidate")
        if status not in {"pass", "failed"}:
            raise ProvisionalIKPreflightError(
                "IK result candidate status must be 'pass' or 'failed'"
            )
        statuses[candidate_id] = status
    missing = sorted(set(expected).difference(statuses))
    if missing:
        raise ProvisionalIKPreflightError(
            "IK result is missing candidates: " + ", ".join(missing)
        )
    verified_objects = sorted(
        {expected[candidate_id] for candidate_id, status in statuses.items() if status == "pass"}
    )
    missing_objects = sorted(set(expected.values()).difference(verified_objects))
    overall_status = "pass" if not missing_objects else "blocked"
    evidence = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "scenario_id": scenario_id,
        "request_sha256": request_sha,
        "result_sha256": _digest_file(Path(result_path)),
        "runner": {"name": runner["name"], "revision": runner["revision"]},
        "robot_base_motion": [0.0, 0.0, 0.0],
        "overall_status": overall_status,
        "verified_objects": verified_objects,
        "missing_object_passes": missing_objects,
        "candidate_results": [
            {"candidate_id": candidate_id, "object_id": expected[candidate_id], "status": statuses[candidate_id]}
            for candidate_id in sorted(expected)
        ],
        "claim_boundary": (
            "This verifies only that the external runner reported an IK solution for "
            "each listed provisional top-down candidate with a fixed robot base. It does "
            "not prove collision-free approach, grasp closure, lifting, dual-arm "
            "coordination, interaction success, liquid transfer, policy success, or benchmark success."
        ),
    }
    root = _package_root_from_request(request_file)
    evidence_path = root / "evidence/provisional_ik_preflight.yaml"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(yaml.safe_dump(evidence, allow_unicode=True, sort_keys=False), encoding="utf-8")
    if overall_status != "pass":
        raise ProvisionalIKPreflightError(
            "external runner did not report a passing IK candidate for: "
            + ", ".join(missing_objects)
        )
    return evidence_path


def _candidates(
    scenario: Mapping[str, object], scene_path: Path
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    objects = _mappings(scenario.get("objects"), "scenario.objects")
    by_id = {
        _required_string(item, "id", "scenario object"): item
        for item in objects
        if item.get("role") != "table"
    }
    actors_by_object: dict[str, str] = {}
    for step in _mappings(scenario.get("steps"), "scenario.steps"):
        parameters = step.get("parameters")
        actors = step.get("actors")
        if not isinstance(parameters, Mapping) or not isinstance(actors, list):
            continue
        object_id = parameters.get("object")
        if not isinstance(object_id, str) or object_id not in by_id or object_id in actors_by_object:
            continue
        if not actors or not isinstance(actors[0], str) or not actors[0]:
            raise ProvisionalIKPreflightError(
                f"task step for object '{object_id}' must name a non-empty first actor"
            )
        actors_by_object[object_id] = actors[0]
    stage, cache = _open_stage_with_bbox_cache(scene_path)
    candidates: list[dict[str, object]] = []
    unresolved_objects: list[dict[str, str]] = []
    for object_id in sorted(actors_by_object):
        prim_path = _required_string(
            by_id[object_id], "source_prim_path", f"scenario object '{object_id}'"
        )
        try:
            anchor = _bbox_top_anchor(stage, cache, prim_path)
        except ProvisionalIKPreflightError as exc:
            unresolved_objects.append(
                {
                    "object_id": object_id,
                    "actor": actors_by_object[object_id],
                    "source_prim_path": prim_path,
                    "reason": str(exc),
                }
            )
            continue
        candidates.append(
            {
                "candidate_id": f"{object_id}.top_down",
                "object_id": object_id,
                "actor": actors_by_object[object_id],
                "target_anchor_world_xyz_m": anchor,
                "pregrasp_offset_world_m": [0.0, 0.0, 0.12],
                "pregrasp_world_xyz_m": [anchor[0], anchor[1], round(anchor[2] + 0.12, 6)],
                "approach_direction_world": [0.0, 0.0, -1.0],
                "yaw_candidates_deg": [0, 90, 180, 270],
            }
        )
    if not actors_by_object:
        unresolved_objects.append(
            {
                "object_id": "<none>",
                "actor": "<none>",
                "source_prim_path": "<none>",
                "reason": "scenario has no task object with a declared actor",
            }
        )
    return candidates, unresolved_objects


def _open_stage_with_bbox_cache(scene_path: Path) -> tuple[object, object]:
    try:
        from pxr import Usd, UsdGeom
    except ModuleNotFoundError as exc:
        raise ProvisionalIKPreflightError(
            "OpenUSD is required to derive composed provisional IK candidates"
        ) from exc
    stage = Usd.Stage.Open(str(scene_path))
    if stage is None:
        raise ProvisionalIKPreflightError(
            f"unable to open composed scene for provisional IK request: {scene_path}"
        )
    return (
        stage,
        UsdGeom.BBoxCache(
            Usd.TimeCode.Default(),
            [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy],
            useExtentsHint=True,
        ),
    )


def _bbox_top_anchor(stage: object, cache: object, prim_path: str) -> list[float]:
    prim = stage.GetPrimAtPath(prim_path)
    if not prim or not prim.IsValid():
        raise ProvisionalIKPreflightError(
            f"provisional IK candidate prim is missing from composed scene: {prim_path}"
        )
    bounds = cache.ComputeWorldBound(prim).ComputeAlignedRange()
    lower = bounds.GetMin()
    upper = bounds.GetMax()
    values = (lower[0], lower[1], lower[2], upper[0], upper[1], upper[2])
    if not all(math.isfinite(float(value)) for value in values):
        raise ProvisionalIKPreflightError(
            f"provisional IK candidate prim has non-finite bounds: {prim_path}"
        )
    if any(float(upper[index]) <= float(lower[index]) for index in range(3)):
        raise ProvisionalIKPreflightError(
            f"provisional IK candidate prim has empty bounds: {prim_path}"
        )
    return [
        round((float(lower[0]) + float(upper[0])) / 2.0, 6),
        round((float(lower[1]) + float(upper[1])) / 2.0, 6),
        round(float(upper[2]), 6),
    ]


def _package_root_from_request(request_path: Path) -> Path:
    expected = ("provisional_ik_preflight", "genmanip", "ebench", "adapters")
    parent = request_path.parent
    for component in expected:
        if parent.name != component:
            raise ProvisionalIKPreflightError(
                "IK request must reside under adapters/ebench/genmanip/provisional_ik_preflight"
            )
        parent = parent.parent
    return parent


def _validate_fixed_base(value: object) -> None:
    if not isinstance(value, list) or len(value) != 3:
        raise ProvisionalIKPreflightError("IK result.robot_base_motion must contain three numbers")
    if not all(isinstance(item, int | float) and math.isfinite(item) for item in value):
        raise ProvisionalIKPreflightError("IK result.robot_base_motion must be finite")
    if any(abs(float(item)) > _FIXED_BASE_TOLERANCE_M for item in value):
        raise ProvisionalIKPreflightError("IK result must keep a fixed robot base")


def _load_mapping(path: Path, field: str) -> Mapping[str, object]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ProvisionalIKPreflightError(f"could not read {field}: {path}") from exc
    if not isinstance(value, Mapping):
        raise ProvisionalIKPreflightError(f"{field} must be a mapping")
    return value


def _mappings(value: object, field: str) -> list[Mapping[str, object]]:
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise ProvisionalIKPreflightError(f"{field} must be a list of mappings")
    return list(value)


def _required_string(data: Mapping[str, object], key: str, field: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ProvisionalIKPreflightError(f"{field}.{key} must be a non-empty string")
    return value


def _digest_file(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _digest_mapping(value: Mapping[str, object]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + sha256(payload).hexdigest()

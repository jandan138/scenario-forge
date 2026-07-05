from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.evaluation.phase11_gates import (
    PHASE11_EXECUTED_EPISODE_GATE_SCHEMA_VERSION,
    PHASE11_POST_EXECUTION_VISUAL_REVIEW_GATE_SCHEMA_VERSION,
    PHASE11_SINGLE_TASK_RC_GATE_SCHEMA_VERSION,
    PHASE11_SUCCESS_PREDICATE_GATE_SCHEMA_VERSION,
    PHASE11_TASK_EXECUTION_GATE_SCHEMA_VERSION,
    _visual_review_blockers,
)
from scenario_forge.generation.image_grounded.factory import PHASE13_CURRENT_GATE_INDEX_SCHEMA_VERSION
from scenario_forge.package import load_package_manifest


PHASE13_FACTORY_OVERVIEW_VISUAL_GATE_SCHEMA_VERSION = "factory-overview-visual-gate/v0.1"
PHASE13_EXECUTION_PREDICATE_CANARY_GATE_SCHEMA_VERSION = "execution-predicate-canary-gate/v0.1"
PHASE13_STATIC_PREREQUISITE_GATES = ("13.0", "13.1", "13.2", "13.3", "13.4", "13.5", "13.7")
PHASE13_EXECUTION_REQUIRED_PHASE11_GATES = {
    "phase11_task_execution_gate.yaml": PHASE11_TASK_EXECUTION_GATE_SCHEMA_VERSION,
    "phase11_executed_episode_gate.yaml": PHASE11_EXECUTED_EPISODE_GATE_SCHEMA_VERSION,
    "phase11_success_predicate_gate.yaml": PHASE11_SUCCESS_PREDICATE_GATE_SCHEMA_VERSION,
    "phase11_post_execution_visual_review_gate.yaml": (
        PHASE11_POST_EXECUTION_VISUAL_REVIEW_GATE_SCHEMA_VERSION
    ),
}


@dataclass(frozen=True)
class Phase13FactoryOverviewVisualGateResult:
    package_root: Path
    status: str
    evidence_path: Path
    current_index_path: Path
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class Phase13ExecutionPredicateCanaryGateResult:
    package_root: Path
    status: str
    evidence_path: Path
    current_index_path: Path
    blockers: tuple[str, ...]


def generate_phase13_factory_overview_visual_gate(
    package_dir: str | Path,
    visual_review_path: str | Path,
) -> Phase13FactoryOverviewVisualGateResult:
    package_root = Path(package_dir)
    review_path = Path(visual_review_path)
    manifest = load_package_manifest(package_root)
    current_index_path = package_root / "evidence" / "phase13_current_gate_index.yaml"
    current_index = _load_yaml(current_index_path)
    review = _load_yaml(review_path)

    blockers = [
        *_phase13_static_candidate_blockers(current_index),
        *_phase13_visual_review_blockers(review, review_path),
    ]
    status = "passed" if not blockers else "failed"
    gate = {
        "schema_version": PHASE13_FACTORY_OVERVIEW_VISUAL_GATE_SCHEMA_VERSION,
        "phase": "13.6",
        "status": status,
        "package_id": manifest.package_id,
        "request_id": current_index.get("request_id"),
        "visual_review": {
            "source": str(review_path),
            "schema_version": review.get("schema_version"),
            "reviewer": review.get("reviewer"),
            "review_mode": review.get("review_mode"),
            "verdict": review.get("verdict"),
            "image_path": review.get("image_path"),
            "image_sha256": _review_image_sha256(review_path, review),
            "render_metadata_path": review.get("render_metadata_path"),
            "render_metadata_sha256": _review_artifact_sha256(
                review_path,
                review.get("render_metadata_path"),
            ),
            "visible_evidence": review.get("visible_evidence", []),
            "retake_recommendation": review.get("retake_recommendation"),
        },
        "blockers": blockers,
        "next_stage": "execution_predicate_canary" if status == "passed" else "blocked",
        "claim_boundary": (
            "Phase 13.6 factory overview visual gate only. It proves engine-native "
            "visual readability for the generated package, not task success, asset "
            "identity, policy quality, or leaderboard readiness."
        ),
    }
    evidence_path = write_yaml_artifact(
        package_root / "evidence" / "phase13_6_factory_overview_visual_gate.yaml",
        gate,
    )
    _write_phase13_current_index_after_13_6(
        current_index_path=current_index_path,
        current_index=current_index,
        gate_path=evidence_path,
        status=status,
        blockers=blockers,
    )
    return Phase13FactoryOverviewVisualGateResult(
        package_root=package_root,
        status=status,
        evidence_path=evidence_path,
        current_index_path=current_index_path,
        blockers=tuple(blockers),
    )


def generate_phase13_execution_predicate_canary_gate(
    package_dir: str | Path,
    single_task_rc_gate_path: str | Path,
) -> Phase13ExecutionPredicateCanaryGateResult:
    package_root = Path(package_dir)
    rc_gate_path = Path(single_task_rc_gate_path)
    manifest = load_package_manifest(package_root)
    current_index_path = package_root / "evidence" / "phase13_current_gate_index.yaml"
    current_index = _load_yaml(current_index_path)
    phase11_chain, phase11_blockers = _phase11_execution_chain_summary(
        package_root=package_root,
        rc_gate_path=rc_gate_path,
        package_id=manifest.package_id,
    )
    blockers = [
        *_phase13_visual_candidate_blockers(current_index),
        *phase11_blockers,
    ]
    status = "passed" if not blockers else "failed"
    gate = {
        "schema_version": PHASE13_EXECUTION_PREDICATE_CANARY_GATE_SCHEMA_VERSION,
        "phase": "13.8",
        "status": status,
        "package_id": manifest.package_id,
        "request_id": current_index.get("request_id"),
        "phase11_chain": phase11_chain,
        "blockers": blockers,
        "next_stage": "batch_factory_quality_gate" if status == "passed" else "blocked",
        "claim_boundary": (
            "Phase 13.8 execution/predicate canary gate only. It aggregates retained "
            "EOS/EBench Phase 11 execution, completed episode, predicate, "
            "post-execution visual review, and release-policy gates for this generated "
            "package. It is not a benchmark report, leaderboard result, or batch-quality gate."
        ),
    }
    evidence_path = write_yaml_artifact(
        package_root / "evidence" / "phase13_8_execution_predicate_canary_gate.yaml",
        gate,
    )
    _write_phase13_current_index_after_13_8(
        current_index_path=current_index_path,
        current_index=current_index,
        gate_path=evidence_path,
        status=status,
        blockers=blockers,
    )
    return Phase13ExecutionPredicateCanaryGateResult(
        package_root=package_root,
        status=status,
        evidence_path=evidence_path,
        current_index_path=current_index_path,
        blockers=tuple(blockers),
    )


def _phase13_static_candidate_blockers(current_index: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if current_index.get("schema_version") != PHASE13_CURRENT_GATE_INDEX_SCHEMA_VERSION:
        blockers.append(
            "phase13 current gate index schema_version must be "
            f"{PHASE13_CURRENT_GATE_INDEX_SCHEMA_VERSION}"
        )
    if current_index.get("static_candidate_ready") is not True:
        blockers.append("phase13 package must be static_candidate_ready before 13.6")
    latest_gates = current_index.get("latest_gates")
    if not isinstance(latest_gates, dict):
        return [*blockers, "phase13 current gate index latest_gates must be a mapping"]
    for phase in PHASE13_STATIC_PREREQUISITE_GATES:
        gate = latest_gates.get(phase)
        if not isinstance(gate, dict) or gate.get("status") != "passed":
            blockers.append(f"phase13 prerequisite gate {phase} must be passed before 13.6")
    return blockers


def _phase13_visual_candidate_blockers(current_index: dict[str, Any]) -> list[str]:
    blockers = _phase13_static_candidate_blockers(current_index)
    latest_gates = current_index.get("latest_gates")
    if isinstance(latest_gates, dict):
        gate_13_6 = latest_gates.get("13.6")
        if not isinstance(gate_13_6, dict) or gate_13_6.get("status") != "passed":
            blockers.append("phase13 prerequisite gate 13.6 must be passed before 13.8")
    if current_index.get("overview_visual_ready") is not True:
        blockers.append("phase13 package must be overview_visual_ready before 13.8")
    return blockers


def _phase13_visual_review_blockers(review: dict[str, Any], review_path: Path) -> list[str]:
    blockers = _visual_review_blockers(review, review_path)
    render_metadata_path = review.get("render_metadata_path")
    if not isinstance(render_metadata_path, str) or not render_metadata_path.strip():
        blockers.append("phase13 visual review render_metadata_path is required for 13.6")
    return blockers


def _write_phase13_current_index_after_13_6(
    *,
    current_index_path: Path,
    current_index: dict[str, Any],
    gate_path: Path,
    status: str,
    blockers: list[str],
) -> None:
    latest_gates = dict(current_index.get("latest_gates") or {})
    latest_gates["13.6"] = {
        "path": _artifact_ref(gate_path, current_index_path.parent.parent),
        "schema_version": PHASE13_FACTORY_OVERVIEW_VISUAL_GATE_SCHEMA_VERSION,
        "status": status,
    }
    if status == "passed":
        current_index.update(
            {
                "overall_status": "phase13_visual_candidate_ready",
                "formal_package_ready": False,
                "static_candidate_ready": True,
                "overview_visual_ready": True,
                "next_required_gate": "13.8",
                "latest_gates": latest_gates,
                "blockers": [
                    "13.8 EOS execution/predicate canary gate is required before formal package readiness"
                ],
            }
        )
    else:
        current_index.update(
            {
                "overall_status": "blocked",
                "formal_package_ready": False,
                "overview_visual_ready": False,
                "next_required_gate": "13.6",
                "latest_gates": latest_gates,
                "blockers": blockers,
            }
        )
    write_yaml_artifact(current_index_path, current_index)


def _write_phase13_current_index_after_13_8(
    *,
    current_index_path: Path,
    current_index: dict[str, Any],
    gate_path: Path,
    status: str,
    blockers: list[str],
) -> None:
    latest_gates = dict(current_index.get("latest_gates") or {})
    latest_gates["13.8"] = {
        "path": _artifact_ref(gate_path, current_index_path.parent.parent),
        "schema_version": PHASE13_EXECUTION_PREDICATE_CANARY_GATE_SCHEMA_VERSION,
        "status": status,
    }
    if status == "passed":
        current_index.update(
            {
                "overall_status": "phase13_formal_package_ready",
                "formal_package_ready": True,
                "static_candidate_ready": True,
                "overview_visual_ready": True,
                "execution_predicate_ready": True,
                "next_required_gate": "13.9",
                "latest_gates": latest_gates,
                "blockers": [
                    "13.9 batch factory quality gate is required before batch factory readiness"
                ],
            }
        )
    else:
        current_index.update(
            {
                "overall_status": "blocked",
                "formal_package_ready": False,
                "execution_predicate_ready": False,
                "next_required_gate": "13.8",
                "latest_gates": latest_gates,
                "blockers": blockers,
            }
        )
    write_yaml_artifact(current_index_path, current_index)


def _phase11_execution_chain_summary(
    *,
    package_root: Path,
    rc_gate_path: Path,
    package_id: str,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    blockers: list[str] = []
    chain: dict[str, dict[str, Any]] = {}
    for filename, schema_version in PHASE13_EXECUTION_REQUIRED_PHASE11_GATES.items():
        gate_path = package_root / "evidence" / filename
        gate = _load_yaml_if_exists(gate_path)
        key = gate_path.stem
        chain[key] = _phase11_gate_summary(gate_path, gate)
        blockers.extend(
            _phase11_required_gate_blockers(
                key=key,
                gate=gate,
                schema_version=schema_version,
                package_id=package_id,
            )
        )

    rc_gate = _load_yaml_if_exists(rc_gate_path)
    chain["phase11_single_task_release_candidate_gate"] = _phase11_gate_summary(
        rc_gate_path,
        rc_gate,
    )
    blockers.extend(
        _phase11_required_gate_blockers(
            key="phase11_single_task_release_candidate_gate",
            gate=rc_gate,
            schema_version=PHASE11_SINGLE_TASK_RC_GATE_SCHEMA_VERSION,
            package_id=package_id,
        )
    )
    if rc_gate and rc_gate.get("status") == "passed":
        required_gates = rc_gate.get("required_gates")
        if not isinstance(required_gates, dict):
            blockers.append("phase11 single-task RC gate required_gates must be a mapping")
        else:
            for filename in PHASE13_EXECUTION_REQUIRED_PHASE11_GATES:
                required_gate = required_gates.get(filename)
                if not isinstance(required_gate, dict) or required_gate.get("status") != "passed":
                    blockers.append(f"phase11 single-task RC required gate {filename} must be passed")
    return chain, blockers


def _phase11_gate_summary(path: Path, gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": str(path),
        "schema_version": gate.get("schema_version"),
        "phase": gate.get("phase"),
        "status": gate.get("status", "missing"),
        "package_id": gate.get("package_id"),
        "task_id": gate.get("task_id"),
    }


def _phase11_required_gate_blockers(
    *,
    key: str,
    gate: dict[str, Any],
    schema_version: str,
    package_id: str,
) -> list[str]:
    blockers: list[str] = []
    if not gate:
        return [f"{key} must exist before 13.8"]
    if gate.get("schema_version") != schema_version:
        blockers.append(f"{key} schema_version must be {schema_version}")
    if gate.get("status") != "passed":
        blockers.append(f"{key} status must be passed; got {gate.get('status')}")
    if gate.get("package_id") != package_id:
        blockers.append(f"{key} package_id must be {package_id}; got {gate.get('package_id')}")
    return blockers


def _review_image_sha256(review_path: Path, review: dict[str, Any]) -> str | None:
    return _review_artifact_sha256(review_path, review.get("image_path"))


def _review_artifact_sha256(review_path: Path, artifact_ref: object) -> str | None:
    if not isinstance(artifact_ref, str) or not artifact_ref.strip():
        return None
    artifact_path = _resolve_review_path(review_path, artifact_ref)
    if not artifact_path.exists() or not artifact_path.is_file():
        return None
    return f"sha256:{sha256(artifact_path.read_bytes()).hexdigest()}"


def _resolve_review_path(review_path: Path, artifact_ref: str) -> Path:
    path = Path(artifact_ref)
    if path.is_absolute():
        return path
    return review_path.parent / path


def _artifact_ref(path: Path, package_root: Path) -> str:
    try:
        return path.relative_to(package_root).as_posix()
    except ValueError:
        return str(path)


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML input must be a mapping: {path}")
    return data


def _load_yaml_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _load_yaml(path)

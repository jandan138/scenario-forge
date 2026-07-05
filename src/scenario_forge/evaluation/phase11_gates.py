from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import yaml

from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.package import load_package_manifest, validate_package


PHASE11_VISUAL_REVIEW_SCHEMA_VERSION = "phase11-visual-review/v0.1"
PHASE11_VISUAL_REVIEW_GATE_SCHEMA_VERSION = "phase11-visual-review-gate/v0.1"
PHASE11_TASK_EXECUTION_SCHEMA_VERSION = "phase11-eos-task-execution/v0.1"
PHASE11_TASK_EXECUTION_GATE_SCHEMA_VERSION = "phase11-task-execution-gate/v0.1"
PHASE11_EXECUTED_EPISODE_SCHEMA_VERSION = "phase11-executed-episode-evidence/v0.1"
PHASE11_EXECUTED_EPISODE_GATE_SCHEMA_VERSION = "phase11-executed-episode-gate/v0.1"
PHASE11_SUCCESS_PREDICATE_SCHEMA_VERSION = "phase11-success-predicate-evaluation/v0.1"
PHASE11_SUCCESS_PREDICATE_GATE_SCHEMA_VERSION = "phase11-success-predicate-gate/v0.1"
PHASE11_POST_EXECUTION_VISUAL_REVIEW_SCHEMA_VERSION = (
    "phase11-post-execution-visual-review/v0.1"
)
PHASE11_POST_EXECUTION_VISUAL_REVIEW_GATE_SCHEMA_VERSION = (
    "phase11-post-execution-visual-review-gate/v0.1"
)
PHASE11_RELEASE_POLICY_SCHEMA_VERSION = "phase11-release-policy/v0.1"
PHASE11_SINGLE_TASK_RC_GATE_SCHEMA_VERSION = (
    "phase11-single-task-release-candidate-gate/v0.1"
)
PHASE11_SMALL_MULTI_TASK_CANARY_SCHEMA_VERSION = "phase11-small-multi-task-canary/v0.1"
PHASE11_SMALL_MULTI_TASK_CANARY_GATE_SCHEMA_VERSION = (
    "phase11-small-multi-task-canary-gate/v0.1"
)
PHASE11_AUTOMATED_RELEASE_SCHEMA_VERSION = "phase11-automated-release-evidence/v0.1"
PHASE11_AUTOMATED_RELEASE_GATE_SCHEMA_VERSION = "phase11-automated-release-gate/v0.1"
PHASE11_PHASE12_READINESS_SCHEMA_VERSION = "phase11-phase12-readiness/v0.1"
PHASE11_PHASE12_READINESS_GATE_SCHEMA_VERSION = "phase11-phase12-readiness-gate/v0.1"
VISUAL_REVIEWER_ID = "render-visual-reviewer"
EOS_RUNTIME_OWNER = "embodied-eval-os"
EBENCH_PREDICATE_EVALUATOR_OWNER = "embodied-eval-os-ebench-adapter"
RELEASE_POLICY_OWNER = "scenario-forge-policy-gate"

PHASE11_SINGLE_TASK_REQUIRED_GATES = {
    "phase11_visual_review_gate.yaml": PHASE11_VISUAL_REVIEW_GATE_SCHEMA_VERSION,
    "phase11_task_execution_gate.yaml": PHASE11_TASK_EXECUTION_GATE_SCHEMA_VERSION,
    "phase11_executed_episode_gate.yaml": PHASE11_EXECUTED_EPISODE_GATE_SCHEMA_VERSION,
    "phase11_success_predicate_gate.yaml": PHASE11_SUCCESS_PREDICATE_GATE_SCHEMA_VERSION,
    "phase11_post_execution_visual_review_gate.yaml": (
        PHASE11_POST_EXECUTION_VISUAL_REVIEW_GATE_SCHEMA_VERSION
    ),
}

PHASE11_RELEASE_CRITICAL_GATE_KEYS = (
    "package_check",
    "asset_lock_check",
    "adapter_contract",
    "visual_review",
    "episode_execution",
    "predicate_evaluation",
    "license_policy",
)
PHASE11_READINESS_LATEST_GATES = {
    "apple_to_bowl_single_task_rc": PHASE11_SINGLE_TASK_RC_GATE_SCHEMA_VERSION,
    "soap_to_dish_single_task_rc": PHASE11_SINGLE_TASK_RC_GATE_SCHEMA_VERSION,
    "remote_to_holder_single_task_rc": PHASE11_SINGLE_TASK_RC_GATE_SCHEMA_VERSION,
    "small_multi_task_canary": PHASE11_SMALL_MULTI_TASK_CANARY_GATE_SCHEMA_VERSION,
    "automated_release": PHASE11_AUTOMATED_RELEASE_GATE_SCHEMA_VERSION,
}
PHASE11_READINESS_TECHNICAL_GATES = (
    "package_check",
    "asset_lock_check",
    "adapter_contract",
    "overview_visual_review",
    "eos_execution",
    "completed_episode",
    "success_predicate",
    "post_execution_visual_review",
    "material_runtime_closure",
)
RENDER_RUNTIME_LOG_BLOCKING_SIGNALS = (
    "rtx.mdltranslator",
    "Failed to create MDL shade node",
    "missing texture",
    "could not find texture",
    "could not find module",
    "MDL compiler error",
    "References an asset that can not be found",
    "wasn't resolved properly",
)


@dataclass(frozen=True)
class Phase11VisualReviewGateResult:
    package_root: Path
    status: str
    evidence_path: Path
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class Phase11TaskExecutionGateResult:
    package_root: Path
    status: str
    evidence_path: Path
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class Phase11ExecutedEpisodeGateResult:
    package_root: Path
    status: str
    evidence_path: Path
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class Phase11SuccessPredicateGateResult:
    package_root: Path
    status: str
    evidence_path: Path
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class Phase11PostExecutionVisualReviewGateResult:
    package_root: Path
    status: str
    evidence_path: Path
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class Phase11SingleTaskReleaseCandidateGateResult:
    package_root: Path
    status: str
    evidence_path: Path
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class Phase11SmallMultiTaskCanaryGateResult:
    suite_root: Path
    status: str
    evidence_path: Path
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class Phase11AutomatedReleaseGateResult:
    suite_root: Path
    status: str
    evidence_path: Path
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class Phase11Phase12ReadinessGateResult:
    suite_root: Path
    status: str
    evidence_path: Path
    blockers: tuple[str, ...]


def generate_phase11_visual_review_gate(
    package_dir: str | Path,
    visual_review_path: str | Path,
) -> Phase11VisualReviewGateResult:
    package_root = Path(package_dir)
    review_path = Path(visual_review_path)
    manifest = load_package_manifest(package_root)
    task_data = _load_yaml(package_root / manifest.entrypoints["task"])
    review = _load_yaml(review_path)
    blockers = _visual_review_blockers(review, review_path)
    status = "passed" if not blockers else "failed"
    image_path = str(review.get("image_path", ""))
    gate = {
        "schema_version": PHASE11_VISUAL_REVIEW_GATE_SCHEMA_VERSION,
        "phase": "11.0",
        "status": status,
        "package_id": manifest.package_id,
        "task_id": str(task_data.get("task_id", manifest.package_id)),
        "visual_review": {
            "source": str(review_path),
            "schema_version": review.get("schema_version"),
            "reviewer": review.get("reviewer"),
            "review_mode": review.get("review_mode"),
            "verdict": review.get("verdict"),
            "image_path": image_path,
            "render_metadata_path": review.get("render_metadata_path"),
            "visible_evidence": review.get("visible_evidence", []),
            "retake_recommendation": review.get("retake_recommendation"),
        },
        "blockers": blockers,
        "next_stage": "eos_task_execution_integration" if status == "passed" else "blocked",
        "claim_boundary": (
            "Automated visual review gate only; not task success, not physics fidelity, "
            "not release approval, and not leaderboard evidence."
        ),
    }
    evidence_path = write_yaml_artifact(
        package_root / "evidence" / "phase11_visual_review_gate.yaml",
        gate,
    )
    return Phase11VisualReviewGateResult(
        package_root=package_root,
        status=status,
        evidence_path=evidence_path,
        blockers=tuple(blockers),
    )


def generate_phase11_task_execution_gate(
    package_dir: str | Path,
    execution_evidence_path: str | Path,
) -> Phase11TaskExecutionGateResult:
    package_root = Path(package_dir)
    evidence_source_path = Path(execution_evidence_path)
    manifest = load_package_manifest(package_root)
    task_data = _load_yaml(package_root / manifest.entrypoints["task"])
    task_id = str(task_data.get("task_id", manifest.package_id))
    execution = _load_yaml(evidence_source_path)
    blockers = _task_execution_blockers(
        execution,
        evidence_source_path,
        package_id=manifest.package_id,
        task_id=task_id,
    )
    status = "passed" if not blockers else "failed"
    gate = {
        "schema_version": PHASE11_TASK_EXECUTION_GATE_SCHEMA_VERSION,
        "phase": "11.1",
        "status": status,
        "package_id": manifest.package_id,
        "task_id": task_id,
        "execution": {
            "source": str(evidence_source_path),
            "schema_version": execution.get("schema_version"),
            "runtime_owner": execution.get("runtime_owner"),
            "contract_consumed": execution.get("contract_consumed"),
            "execution_config_status": execution.get("execution_config_status"),
            "episode_status": execution.get("episode_status"),
            "trace_uri": execution.get("trace_uri"),
            "runtime_log": execution.get("runtime_log"),
            "lifecycle": execution.get("lifecycle", {}),
            "keyframes": execution.get("keyframes", {}),
        },
        "blockers": blockers,
        "next_stage": "executed_episode_evidence_gate" if status == "passed" else "blocked",
        "claim_boundary": (
            "EOS task execution integration gate only; not task success, not model quality, "
            "not release approval, and not leaderboard evidence."
        ),
    }
    evidence_path = write_yaml_artifact(
        package_root / "evidence" / "phase11_task_execution_gate.yaml",
        gate,
    )
    return Phase11TaskExecutionGateResult(
        package_root=package_root,
        status=status,
        evidence_path=evidence_path,
        blockers=tuple(blockers),
    )


def generate_phase11_executed_episode_gate(
    package_dir: str | Path,
    episode_evidence_path: str | Path,
) -> Phase11ExecutedEpisodeGateResult:
    package_root = Path(package_dir)
    evidence_source_path = Path(episode_evidence_path)
    manifest = load_package_manifest(package_root)
    task_data = _load_yaml(package_root / manifest.entrypoints["task"])
    task_id = str(task_data.get("task_id", manifest.package_id))
    episode = _load_yaml(evidence_source_path)
    blockers = _executed_episode_blockers(
        episode,
        evidence_source_path,
        package_id=manifest.package_id,
        task_id=task_id,
    )
    status = "passed" if not blockers else "failed"
    gate = {
        "schema_version": PHASE11_EXECUTED_EPISODE_GATE_SCHEMA_VERSION,
        "phase": "11.2",
        "status": status,
        "package_id": manifest.package_id,
        "task_id": task_id,
        "episode": {
            "source": str(evidence_source_path),
            "schema_version": episode.get("schema_version"),
            "runtime_owner": episode.get("runtime_owner"),
            "episode_status": episode.get("episode_status"),
            "trace_uri": episode.get("trace_uri"),
            "runtime_log": episode.get("runtime_log"),
            "keyframes": episode.get("keyframes", {}),
            "final_state": episode.get("final_state", {}),
        },
        "blockers": blockers,
        "next_stage": "success_predicate_evaluation_gate" if status == "passed" else "blocked",
        "claim_boundary": (
            "Executed episode evidence gate only; not task success, not model quality, "
            "not release approval, and not leaderboard evidence."
        ),
    }
    evidence_path = write_yaml_artifact(
        package_root / "evidence" / "phase11_executed_episode_gate.yaml",
        gate,
    )
    return Phase11ExecutedEpisodeGateResult(
        package_root=package_root,
        status=status,
        evidence_path=evidence_path,
        blockers=tuple(blockers),
    )


def generate_phase11_success_predicate_gate(
    package_dir: str | Path,
    predicate_evidence_path: str | Path,
) -> Phase11SuccessPredicateGateResult:
    package_root = Path(package_dir)
    evidence_source_path = Path(predicate_evidence_path)
    manifest = load_package_manifest(package_root)
    task_data = _load_yaml(package_root / manifest.entrypoints["task"])
    task_id = str(task_data.get("task_id", manifest.package_id))
    predicate = _load_yaml(evidence_source_path)
    blockers = _success_predicate_blockers(
        predicate,
        evidence_source_path,
        package_id=manifest.package_id,
        task_id=task_id,
    )
    status = "passed" if not blockers else "failed"
    gate = {
        "schema_version": PHASE11_SUCCESS_PREDICATE_GATE_SCHEMA_VERSION,
        "phase": "11.3",
        "status": status,
        "package_id": manifest.package_id,
        "task_id": task_id,
        "predicate": {
            "source": str(evidence_source_path),
            "schema_version": predicate.get("schema_version"),
            "evaluator_owner": predicate.get("evaluator_owner"),
            "success_metric": predicate.get("success_metric"),
            "predicate": predicate.get("predicate"),
            "object": predicate.get("object"),
            "container": predicate.get("container"),
            "predicate_status": predicate.get("predicate_status"),
            "executed_episode_gate": predicate.get("executed_episode_gate"),
            "measurement": predicate.get("measurement", {}),
        },
        "blockers": blockers,
        "next_stage": "post_execution_visual_review_gate" if status == "passed" else "blocked",
        "claim_boundary": (
            "Success predicate evaluation gate only; episode-level task success is "
            "predicate-based and is not model quality, release approval, or leaderboard evidence."
        ),
    }
    evidence_path = write_yaml_artifact(
        package_root / "evidence" / "phase11_success_predicate_gate.yaml",
        gate,
    )
    return Phase11SuccessPredicateGateResult(
        package_root=package_root,
        status=status,
        evidence_path=evidence_path,
        blockers=tuple(blockers),
    )


def generate_phase11_post_execution_visual_review_gate(
    package_dir: str | Path,
    visual_review_path: str | Path,
) -> Phase11PostExecutionVisualReviewGateResult:
    package_root = Path(package_dir)
    review_path = Path(visual_review_path)
    manifest = load_package_manifest(package_root)
    task_data = _load_yaml(package_root / manifest.entrypoints["task"])
    task_id = str(task_data.get("task_id", manifest.package_id))
    review = _load_yaml(review_path)
    blockers = _post_execution_visual_review_blockers(review, review_path)
    status = "passed" if not blockers else "failed"
    gate = {
        "schema_version": PHASE11_POST_EXECUTION_VISUAL_REVIEW_GATE_SCHEMA_VERSION,
        "phase": "11.4",
        "status": status,
        "package_id": manifest.package_id,
        "task_id": task_id,
        "visual_review": {
            "source": str(review_path),
            "schema_version": review.get("schema_version"),
            "reviewer": review.get("reviewer"),
            "review_mode": review.get("review_mode"),
            "verdict": review.get("verdict"),
            "initial_image_path": review.get("initial_image_path"),
            "final_image_path": review.get("final_image_path"),
            "visible_evidence": review.get("visible_evidence", []),
            "success_predicate_gate": review.get("success_predicate_gate"),
            "retake_recommendation": review.get("retake_recommendation"),
        },
        "blockers": blockers,
        "next_stage": (
            "single_task_automated_release_candidate" if status == "passed" else "blocked"
        ),
        "claim_boundary": (
            "Post-execution visual review gate only; visual coherence supports inspection "
            "but does not replace predicate success, release approval, or leaderboard evidence."
        ),
    }
    evidence_path = write_yaml_artifact(
        package_root / "evidence" / "phase11_post_execution_visual_review_gate.yaml",
        gate,
    )
    return Phase11PostExecutionVisualReviewGateResult(
        package_root=package_root,
        status=status,
        evidence_path=evidence_path,
        blockers=tuple(blockers),
    )


def generate_phase11_single_task_release_candidate_gate(
    package_dir: str | Path,
    release_policy_path: str | Path,
) -> Phase11SingleTaskReleaseCandidateGateResult:
    package_root = Path(package_dir)
    policy_path = Path(release_policy_path)
    manifest = load_package_manifest(package_root)
    task_data = _load_yaml(package_root / manifest.entrypoints["task"])
    task_id = str(task_data.get("task_id", manifest.package_id))
    release_policy = _load_yaml(policy_path)
    required_gates, gate_blockers = _required_phase11_gate_statuses(package_root)
    package_blockers = _single_task_package_blockers(package_root, manifest)
    policy_blockers = _release_policy_blockers(
        release_policy,
        package_id=manifest.package_id,
        task_id=task_id,
    )
    blockers = [*package_blockers, *gate_blockers, *policy_blockers]
    status = "passed" if not blockers else "blocked"
    gate = {
        "schema_version": PHASE11_SINGLE_TASK_RC_GATE_SCHEMA_VERSION,
        "phase": "11.5",
        "status": status,
        "package_id": manifest.package_id,
        "task_id": task_id,
        "required_gates": required_gates,
        "release_policy": {
            "source": str(policy_path),
            "schema_version": release_policy.get("schema_version"),
            "policy_owner": release_policy.get("policy_owner"),
            "release_policy_status": release_policy.get("release_policy_status"),
            "asset_license_status": release_policy.get("asset_license_status"),
            "redistribution_approval": release_policy.get("redistribution_approval"),
        },
        "blockers": blockers,
        "next_stage": "small_multi_task_canary" if status == "passed" else "blocked",
        "claim_boundary": (
            "Single-task automated release candidate gate only; not public dataset release, "
            "official score release, leaderboard comparability, or multi-task coverage evidence."
        ),
    }
    evidence_path = write_yaml_artifact(
        package_root / "evidence" / "phase11_single_task_release_candidate_gate.yaml",
        gate,
    )
    return Phase11SingleTaskReleaseCandidateGateResult(
        package_root=package_root,
        status=status,
        evidence_path=evidence_path,
        blockers=tuple(blockers),
    )


def generate_phase11_small_multi_task_canary_gate(
    suite_dir: str | Path,
    canary_evidence_path: str | Path,
) -> Phase11SmallMultiTaskCanaryGateResult:
    suite_root = Path(suite_dir)
    evidence_source_path = Path(canary_evidence_path)
    suite_manifest = _load_yaml(suite_root / "suite_manifest.yaml")
    canary = _load_yaml(evidence_source_path)
    packages = canary.get("packages")
    package_rows = packages if isinstance(packages, list) else []
    blockers = _small_multi_task_canary_blockers(
        canary,
        evidence_source_path,
        suite_manifest=suite_manifest,
        package_rows=package_rows,
    )
    status = "passed" if not blockers else "blocked"
    gate = {
        "schema_version": PHASE11_SMALL_MULTI_TASK_CANARY_GATE_SCHEMA_VERSION,
        "phase": "11.6",
        "status": status,
        "suite_id": suite_manifest.get("suite_id", suite_root.name),
        "package_count": len(package_rows),
        "packages": package_rows,
        "blockers": blockers,
        "next_stage": "automated_release_gate" if status == "passed" else "blocked",
        "claim_boundary": (
            "Small multi-task canary gate only; not public dataset release, official score "
            "release, leaderboard comparability, or broad benchmark coverage evidence."
        ),
    }
    evidence_path = write_yaml_artifact(
        suite_root / "evidence" / "phase11_small_multi_task_canary_gate.yaml",
        gate,
    )
    return Phase11SmallMultiTaskCanaryGateResult(
        suite_root=suite_root,
        status=status,
        evidence_path=evidence_path,
        blockers=tuple(blockers),
    )


def generate_phase11_automated_release_gate(
    suite_dir: str | Path,
    release_evidence_path: str | Path,
) -> Phase11AutomatedReleaseGateResult:
    suite_root = Path(suite_dir)
    evidence_source_path = Path(release_evidence_path)
    suite_manifest = _load_yaml(suite_root / "suite_manifest.yaml")
    release = _load_yaml(evidence_source_path)
    blockers = _automated_release_blockers(
        release,
        evidence_source_path,
        suite_manifest=suite_manifest,
    )
    status = "passed" if not blockers else "blocked"
    gate = {
        "schema_version": PHASE11_AUTOMATED_RELEASE_GATE_SCHEMA_VERSION,
        "phase": "11.7",
        "status": status,
        "release_status": "passed" if status == "passed" else "blocked",
        "suite_id": suite_manifest.get("suite_id", suite_root.name),
        "release_critical_gates": release.get("release_critical_gates", {}),
        "known_blockers": release.get("known_blockers", []),
        "blockers": blockers,
        "next_stage": "release_candidate_passed" if status == "passed" else "blocked",
        "claim_boundary": (
            "Automated release gate only; release candidate passed is not official "
            "leaderboard comparability or public dataset publication without external approval."
        ),
    }
    evidence_path = write_yaml_artifact(
        suite_root / "evidence" / "phase11_automated_release_gate.yaml",
        gate,
    )
    return Phase11AutomatedReleaseGateResult(
        suite_root=suite_root,
        status=status,
        evidence_path=evidence_path,
        blockers=tuple(blockers),
    )


def generate_phase11_phase12_readiness_gate(
    suite_dir: str | Path,
    readiness_evidence_path: str | Path,
) -> Phase11Phase12ReadinessGateResult:
    suite_root = Path(suite_dir)
    evidence_source_path = Path(readiness_evidence_path)
    suite_manifest = _load_yaml(suite_root / "suite_manifest.yaml")
    readiness = _load_yaml(evidence_source_path)
    latest_gates, blockers = _phase12_readiness_blockers(
        readiness,
        evidence_source_path,
        suite_manifest=suite_manifest,
    )
    status = "passed" if not blockers else "blocked"
    gate = {
        "schema_version": PHASE11_PHASE12_READINESS_GATE_SCHEMA_VERSION,
        "phase": "11.8",
        "status": status,
        "phase12_status": readiness.get("phase12_status"),
        "phase12_allowed": readiness.get("phase12_allowed"),
        "suite_id": suite_manifest.get("suite_id", suite_root.name),
        "latest_gates": latest_gates,
        "technical_gate_summary": readiness.get("technical_gate_summary", {}),
        "policy_gate_summary": readiness.get("policy_gate_summary", {}),
        "manual_blockers": readiness.get("manual_blockers", []),
        "unknown_blockers": readiness.get("unknown_blockers", []),
        "known_policy_blockers": readiness.get("known_policy_blockers", []),
        "known_non_policy_blockers": readiness.get("known_non_policy_blockers", []),
        "blockers": blockers,
        "next_stage": "phase12_registry_readiness" if status == "passed" else "blocked",
        "claim_boundary": (
            "Phase 11.8 readiness gate only; it allows Phase 12 planning scope when "
            "all referenced evidence and release-policy blockers are clear, but it is "
            "not public dataset publication or leaderboard comparability."
        ),
    }
    evidence_path = write_yaml_artifact(
        suite_root / "evidence" / "phase11_phase12_readiness_gate.yaml",
        gate,
    )
    return Phase11Phase12ReadinessGateResult(
        suite_root=suite_root,
        status=status,
        evidence_path=evidence_path,
        blockers=tuple(blockers),
    )


def _visual_review_blockers(review: dict[str, Any], review_path: Path) -> list[str]:
    blockers: list[str] = []
    if review.get("schema_version") != PHASE11_VISUAL_REVIEW_SCHEMA_VERSION:
        blockers.append(
            "visual review schema_version must be "
            f"{PHASE11_VISUAL_REVIEW_SCHEMA_VERSION}"
        )
    if review.get("reviewer") != VISUAL_REVIEWER_ID:
        blockers.append(f"visual review reviewer must be {VISUAL_REVIEWER_ID}")
    if review.get("review_mode") != "clean_room_visual_skill":
        blockers.append("visual review review_mode must be clean_room_visual_skill")

    verdict = review.get("verdict")
    if verdict != "PASS":
        blockers.append(f"visual review verdict must be PASS; got {verdict}")

    image_path = review.get("image_path")
    if not isinstance(image_path, str) or not image_path.strip():
        blockers.append("visual review image_path must be a non-empty string")
    elif not _resolve_review_path(review_path, image_path).exists():
        blockers.append(f"visual review image does not exist: {image_path}")

    visible_evidence = review.get("visible_evidence")
    if not isinstance(visible_evidence, list) or not visible_evidence:
        blockers.append("visual review visible_evidence must be a non-empty list")

    render_metadata_path = review.get("render_metadata_path")
    if render_metadata_path is not None:
        blockers.extend(_render_metadata_blockers(review_path, render_metadata_path))

    return blockers


def _render_metadata_blockers(review_path: Path, render_metadata_path: Any) -> list[str]:
    blockers: list[str] = []
    if not isinstance(render_metadata_path, str) or not render_metadata_path.strip():
        return ["visual review render_metadata_path must be a non-empty string"]

    metadata_path = _resolve_review_path(review_path, render_metadata_path)
    if not metadata_path.exists():
        return [f"visual review render metadata does not exist: {render_metadata_path}"]

    metadata = _load_json(metadata_path)
    render_status = metadata.get("render_status")
    if render_status != "pass":
        blockers.append(f"visual review render metadata render_status must be pass; got {render_status}")

    material_preflight = metadata.get("material_runtime_preflight")
    if not isinstance(material_preflight, dict):
        blockers.append("visual review render metadata material_runtime_preflight must be a mapping")
    else:
        material_status = material_preflight.get("status")
        if material_status != "pass":
            blockers.append(
                "visual review render metadata material_runtime_preflight.status must be "
                f"pass; got {material_status}"
            )

    runtime_log_path = metadata.get("runtime_log_path")
    if runtime_log_path is not None:
        blockers.extend(_render_runtime_log_blockers(metadata_path, runtime_log_path))

    return blockers


def _render_runtime_log_blockers(metadata_path: Path, runtime_log_path: Any) -> list[str]:
    blockers: list[str] = []
    if not isinstance(runtime_log_path, str) or not runtime_log_path.strip():
        return ["visual review render metadata runtime_log_path must be a non-empty string"]

    log_path = _resolve_evidence_path(metadata_path, runtime_log_path)
    if not log_path.exists():
        return [f"visual review render runtime log does not exist: {runtime_log_path}"]

    runtime_log = log_path.read_text(encoding="utf-8", errors="replace")
    for signal in RENDER_RUNTIME_LOG_BLOCKING_SIGNALS:
        if signal in runtime_log:
            blockers.append(
                f"visual review render runtime log contains blocking material signal: {signal}"
            )
    return blockers


def _task_execution_blockers(
    execution: dict[str, Any],
    evidence_path: Path,
    *,
    package_id: str,
    task_id: str,
) -> list[str]:
    blockers: list[str] = []
    if execution.get("schema_version") != PHASE11_TASK_EXECUTION_SCHEMA_VERSION:
        blockers.append(
            "execution evidence schema_version must be "
            f"{PHASE11_TASK_EXECUTION_SCHEMA_VERSION}"
        )
    if execution.get("runtime_owner") != EOS_RUNTIME_OWNER:
        blockers.append(f"execution runtime_owner must be {EOS_RUNTIME_OWNER}")
    if execution.get("package_id") != package_id:
        blockers.append(f"execution evidence package_id mismatch: {execution.get('package_id')}")
    if execution.get("task_id") != task_id:
        blockers.append(f"execution evidence task_id mismatch: {execution.get('task_id')}")
    if execution.get("contract_consumed") is not True:
        blockers.append("execution contract_consumed must be true")
    if execution.get("execution_config_status") != "generated":
        blockers.append(
            "execution execution_config_status must be generated; "
            f"got {execution.get('execution_config_status')}"
        )
    episode_status = execution.get("episode_status")
    if episode_status not in {"started", "completed"}:
        blockers.append(f"execution episode_status must be started or completed; got {episode_status}")
    trace_uri = execution.get("trace_uri")
    if not isinstance(trace_uri, str) or not trace_uri.strip():
        blockers.append("execution trace_uri must be a non-empty string")

    runtime_log = execution.get("runtime_log")
    if not isinstance(runtime_log, str) or not runtime_log.strip():
        blockers.append("execution runtime_log must be a non-empty string")
    elif not _resolve_evidence_path(evidence_path, runtime_log).exists():
        blockers.append(f"execution runtime_log does not exist: {runtime_log}")

    lifecycle = execution.get("lifecycle")
    if not isinstance(lifecycle, dict):
        blockers.append("execution lifecycle must be a mapping")
    else:
        for phase in ("reset", "step", "close"):
            if lifecycle.get(phase) != "passed":
                blockers.append(
                    f"execution lifecycle.{phase} must be passed; got {lifecycle.get(phase)}"
                )

    keyframes = execution.get("keyframes")
    if not isinstance(keyframes, dict):
        blockers.append("execution keyframes must be a mapping")
    else:
        initial_keyframe = keyframes.get("initial")
        if not isinstance(initial_keyframe, str) or not initial_keyframe.strip():
            blockers.append("execution initial keyframe must be a non-empty string")
        elif not _resolve_evidence_path(evidence_path, initial_keyframe).exists():
            blockers.append(f"execution initial keyframe does not exist: {initial_keyframe}")

    evidence_blockers = execution.get("blockers")
    if isinstance(evidence_blockers, list):
        blockers.extend(str(blocker) for blocker in evidence_blockers if blocker)
    elif evidence_blockers is not None:
        blockers.append("execution blockers must be a list")

    return blockers


def _post_execution_visual_review_blockers(
    review: dict[str, Any],
    review_path: Path,
) -> list[str]:
    blockers: list[str] = []
    if review.get("schema_version") != PHASE11_POST_EXECUTION_VISUAL_REVIEW_SCHEMA_VERSION:
        blockers.append(
            "post-execution visual review schema_version must be "
            f"{PHASE11_POST_EXECUTION_VISUAL_REVIEW_SCHEMA_VERSION}"
        )
    if review.get("reviewer") != VISUAL_REVIEWER_ID:
        blockers.append(f"post-execution visual review reviewer must be {VISUAL_REVIEWER_ID}")
    if review.get("review_mode") != "clean_room_visual_skill":
        blockers.append(
            "post-execution visual review review_mode must be clean_room_visual_skill"
        )

    verdict = review.get("verdict")
    if verdict != "PASS":
        blockers.append(f"post-execution visual review verdict must be PASS; got {verdict}")

    for field, label in (
        ("initial_image_path", "initial"),
        ("final_image_path", "final"),
    ):
        image_path = review.get(field)
        if not isinstance(image_path, str) or not image_path.strip():
            blockers.append(f"post-execution {label} image must be a non-empty string")
        elif not _resolve_evidence_path(review_path, image_path).exists():
            blockers.append(f"post-execution {label} image does not exist: {image_path}")

    visible_evidence = review.get("visible_evidence")
    if not isinstance(visible_evidence, list) or not visible_evidence:
        blockers.append("post-execution visual review visible_evidence must be a non-empty list")

    success_predicate_gate = review.get("success_predicate_gate")
    if not isinstance(success_predicate_gate, str) or not success_predicate_gate.strip():
        blockers.append("success predicate gate must be a non-empty string")
    else:
        gate_path = _resolve_evidence_path(review_path, success_predicate_gate)
        if not gate_path.exists():
            blockers.append(f"success predicate gate does not exist: {success_predicate_gate}")
        else:
            gate = _load_yaml(gate_path)
            if gate.get("schema_version") != PHASE11_SUCCESS_PREDICATE_GATE_SCHEMA_VERSION:
                blockers.append(
                    "success predicate gate schema_version must be "
                    f"{PHASE11_SUCCESS_PREDICATE_GATE_SCHEMA_VERSION}"
                )
            if gate.get("status") != "passed":
                blockers.append(f"success predicate gate status must be passed; got {gate.get('status')}")

    return blockers


def _executed_episode_blockers(
    episode: dict[str, Any],
    evidence_path: Path,
    *,
    package_id: str,
    task_id: str,
) -> list[str]:
    blockers: list[str] = []
    if episode.get("schema_version") != PHASE11_EXECUTED_EPISODE_SCHEMA_VERSION:
        blockers.append(
            "executed episode schema_version must be "
            f"{PHASE11_EXECUTED_EPISODE_SCHEMA_VERSION}"
        )
    if episode.get("runtime_owner") != EOS_RUNTIME_OWNER:
        blockers.append(f"executed episode runtime_owner must be {EOS_RUNTIME_OWNER}")
    if episode.get("package_id") != package_id:
        blockers.append(f"executed episode package_id mismatch: {episode.get('package_id')}")
    if episode.get("task_id") != task_id:
        blockers.append(f"executed episode task_id mismatch: {episode.get('task_id')}")
    episode_status = episode.get("episode_status")
    if episode_status != "completed":
        blockers.append(f"executed episode_status must be completed; got {episode_status}")

    trace_uri = episode.get("trace_uri")
    if not isinstance(trace_uri, str) or not trace_uri.strip():
        blockers.append("executed episode trace_uri must be a non-empty string")
    elif _local_artifact_missing(evidence_path, trace_uri):
        blockers.append(f"executed episode trace artifact does not exist: {trace_uri}")

    runtime_log = episode.get("runtime_log")
    if not isinstance(runtime_log, str) or not runtime_log.strip():
        blockers.append("executed episode runtime_log must be a non-empty string")
    elif _local_artifact_missing(evidence_path, runtime_log):
        blockers.append(f"executed episode runtime_log does not exist: {runtime_log}")

    keyframes = episode.get("keyframes")
    if not isinstance(keyframes, dict):
        blockers.append("executed episode keyframes must be a mapping")
    else:
        for name in ("initial", "final"):
            keyframe = keyframes.get(name)
            if not isinstance(keyframe, str) or not keyframe.strip():
                blockers.append(f"executed episode {name} keyframe must be a non-empty string")
            elif _local_artifact_missing(evidence_path, keyframe):
                blockers.append(f"executed episode {name} keyframe does not exist: {keyframe}")

    final_state = episode.get("final_state")
    if not isinstance(final_state, dict) or not final_state:
        blockers.append("executed episode final_state must be a non-empty mapping")

    evidence_blockers = episode.get("blockers")
    if isinstance(evidence_blockers, list):
        blockers.extend(str(blocker) for blocker in evidence_blockers if blocker)
    elif evidence_blockers is not None:
        blockers.append("executed episode blockers must be a list")

    return blockers


def _success_predicate_blockers(
    predicate: dict[str, Any],
    evidence_path: Path,
    *,
    package_id: str,
    task_id: str,
) -> list[str]:
    blockers: list[str] = []
    if predicate.get("schema_version") != PHASE11_SUCCESS_PREDICATE_SCHEMA_VERSION:
        blockers.append(
            "predicate schema_version must be "
            f"{PHASE11_SUCCESS_PREDICATE_SCHEMA_VERSION}"
        )
    if predicate.get("evaluator_owner") != EBENCH_PREDICATE_EVALUATOR_OWNER:
        blockers.append(
            f"predicate evaluator_owner must be {EBENCH_PREDICATE_EVALUATOR_OWNER}"
        )
    if predicate.get("package_id") != package_id:
        blockers.append(f"predicate package_id mismatch: {predicate.get('package_id')}")
    if predicate.get("task_id") != task_id:
        blockers.append(f"predicate task_id mismatch: {predicate.get('task_id')}")

    for field in ("success_metric", "predicate", "object", "container"):
        value = predicate.get(field)
        if not isinstance(value, str) or not value.strip():
            blockers.append(f"predicate {field} must be a non-empty string")

    predicate_status = predicate.get("predicate_status")
    if predicate_status is not True:
        blockers.append(f"predicate_status must be true; got {predicate_status}")

    executed_episode_gate = predicate.get("executed_episode_gate")
    if not isinstance(executed_episode_gate, str) or not executed_episode_gate.strip():
        blockers.append("executed episode gate must be a non-empty string")
    else:
        gate_path = _resolve_evidence_path(evidence_path, executed_episode_gate)
        if not gate_path.exists():
            blockers.append(f"executed episode gate does not exist: {executed_episode_gate}")
        else:
            gate = _load_yaml(gate_path)
            if gate.get("schema_version") != PHASE11_EXECUTED_EPISODE_GATE_SCHEMA_VERSION:
                blockers.append(
                    "executed episode gate schema_version must be "
                    f"{PHASE11_EXECUTED_EPISODE_GATE_SCHEMA_VERSION}"
                )
            if gate.get("status") != "passed":
                blockers.append(f"executed episode gate status must be passed; got {gate.get('status')}")

    measurement = predicate.get("measurement")
    if not isinstance(measurement, dict) or not measurement:
        blockers.append("predicate measurement must be a non-empty mapping")

    evidence_blockers = predicate.get("blockers")
    if isinstance(evidence_blockers, list):
        blockers.extend(str(blocker) for blocker in evidence_blockers if blocker)
    elif evidence_blockers is not None:
        blockers.append("predicate blockers must be a list")

    return blockers


def _automated_release_blockers(
    release: dict[str, Any],
    evidence_path: Path,
    *,
    suite_manifest: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if release.get("schema_version") != PHASE11_AUTOMATED_RELEASE_SCHEMA_VERSION:
        blockers.append(
            f"automated release schema_version must be {PHASE11_AUTOMATED_RELEASE_SCHEMA_VERSION}"
        )
    suite_id = suite_manifest.get("suite_id")
    if release.get("suite_id") != suite_id:
        blockers.append(f"automated release suite_id mismatch: {release.get('suite_id')}")

    small_canary_gate = release.get("small_multi_task_canary_gate")
    if not isinstance(small_canary_gate, str) or not small_canary_gate.strip():
        blockers.append("small multi-task canary gate must be a non-empty string")
    else:
        small_canary_gate_path = _resolve_evidence_path(evidence_path, small_canary_gate)
        if not small_canary_gate_path.exists():
            blockers.append(f"small multi-task canary gate does not exist: {small_canary_gate}")
        else:
            gate = _load_yaml(small_canary_gate_path)
            if gate.get("schema_version") != PHASE11_SMALL_MULTI_TASK_CANARY_GATE_SCHEMA_VERSION:
                blockers.append(
                    "small multi-task canary gate schema_version must be "
                    f"{PHASE11_SMALL_MULTI_TASK_CANARY_GATE_SCHEMA_VERSION}"
                )
            if gate.get("status") != "passed":
                blockers.append(
                    f"small multi-task canary gate status must be passed; got {gate.get('status')}"
                )

    critical_gates = release.get("release_critical_gates")
    if not isinstance(critical_gates, dict):
        blockers.append("release_critical_gates must be a mapping")
        critical_gates = {}
    for key in PHASE11_RELEASE_CRITICAL_GATE_KEYS:
        status = critical_gates.get(key)
        if status != "pass":
            blockers.append(f"release-critical gate {key} must be pass; got {status}")

    known_blockers = release.get("known_blockers")
    if not isinstance(known_blockers, list):
        blockers.append("known_blockers must be a list")
    elif known_blockers:
        blockers.append(f"known_blockers must be empty; got {len(known_blockers)}")
        blockers.extend(str(blocker) for blocker in known_blockers if blocker)

    evidence_blockers = release.get("blockers")
    if isinstance(evidence_blockers, list):
        blockers.extend(str(blocker) for blocker in evidence_blockers if blocker)
    elif evidence_blockers is not None:
        blockers.append("automated release blockers must be a list")

    return blockers


def _phase12_readiness_blockers(
    readiness: dict[str, Any],
    evidence_path: Path,
    *,
    suite_manifest: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    blockers: list[str] = []
    if readiness.get("schema_version") != PHASE11_PHASE12_READINESS_SCHEMA_VERSION:
        blockers.append(
            f"readiness schema_version must be {PHASE11_PHASE12_READINESS_SCHEMA_VERSION}"
        )
    if str(readiness.get("phase")) != "11.8":
        blockers.append(f"readiness phase must be 11.8; got {readiness.get('phase')}")

    suite_id = suite_manifest.get("suite_id")
    if readiness.get("suite_id") != suite_id:
        blockers.append(f"readiness suite_id mismatch: {readiness.get('suite_id')}")

    latest_gates = readiness.get("latest_gates")
    gate_rows: dict[str, dict[str, Any]] = {}
    if not isinstance(latest_gates, dict):
        blockers.append("latest_gates must be a mapping")
        latest_gates = {}
    for key, schema_version in PHASE11_READINESS_LATEST_GATES.items():
        gate_ref = latest_gates.get(key)
        gate_rows[key] = _readiness_gate_row(
            evidence_path,
            key,
            gate_ref,
            schema_version,
            blockers,
            require_pass=readiness.get("phase12_allowed") is True,
        )

    technical_summary = readiness.get("technical_gate_summary")
    if not isinstance(technical_summary, dict):
        blockers.append("technical_gate_summary must be a mapping")
        technical_summary = {}
    for key in PHASE11_READINESS_TECHNICAL_GATES:
        status = technical_summary.get(key)
        if status != "pass":
            blockers.append(f"technical gate {key} must be pass; got {status}")

    policy_summary = readiness.get("policy_gate_summary")
    if not isinstance(policy_summary, dict):
        blockers.append("policy_gate_summary must be a mapping")
        policy_summary = {}
    release_policy = policy_summary.get("release_policy")
    if release_policy != "pass":
        blockers.append(f"release policy must be pass before Phase 12 can start; got {release_policy}")
    if policy_summary.get("redistribution_approval") is not True:
        blockers.append("redistribution_approval must be true before Phase 12 can start")

    manual_blockers = readiness.get("manual_blockers")
    if not isinstance(manual_blockers, list):
        blockers.append("manual_blockers must be a list")
    elif manual_blockers:
        blockers.append(f"manual_blockers must be empty; got {len(manual_blockers)}")
        blockers.extend(str(blocker) for blocker in manual_blockers if blocker)

    unknown_blockers = readiness.get("unknown_blockers")
    if not isinstance(unknown_blockers, list):
        blockers.append("unknown_blockers must be a list")
    elif unknown_blockers:
        blockers.append(f"unknown_blockers must be empty; got {len(unknown_blockers)}")
        blockers.extend(str(blocker) for blocker in unknown_blockers if blocker)

    known_non_policy_blockers = readiness.get("known_non_policy_blockers")
    if not isinstance(known_non_policy_blockers, list):
        blockers.append("known_non_policy_blockers must be a list")
    elif known_non_policy_blockers:
        blockers.append(
            f"known_non_policy_blockers must be empty; got {len(known_non_policy_blockers)}"
        )
        blockers.extend(str(blocker) for blocker in known_non_policy_blockers if blocker)

    known_policy_blockers = readiness.get("known_policy_blockers")
    if not isinstance(known_policy_blockers, list):
        blockers.append("known_policy_blockers must be a list")
    else:
        blockers.extend(str(blocker) for blocker in known_policy_blockers if blocker)

    if readiness.get("phase12_allowed") is not True:
        blockers.append("phase12_allowed must be true before Phase 12 can start")

    evidence_blockers = readiness.get("blockers")
    if isinstance(evidence_blockers, list):
        blockers.extend(str(blocker) for blocker in evidence_blockers if blocker)
    elif evidence_blockers is not None:
        blockers.append("readiness blockers must be a list")

    return gate_rows, blockers


def _readiness_gate_row(
    evidence_path: Path,
    key: str,
    gate_ref: Any,
    schema_version: str,
    blockers: list[str],
    *,
    require_pass: bool,
) -> dict[str, Any]:
    if not isinstance(gate_ref, str) or not gate_ref.strip():
        blockers.append(f"latest gate {key} must be a non-empty string")
        return {"path": gate_ref, "status": "missing"}

    gate_path = _resolve_evidence_path(evidence_path, gate_ref)
    if not gate_path.exists():
        blockers.append(f"latest gate {key} does not exist: {gate_ref}")
        return {"path": str(gate_path), "status": "missing"}

    gate = _load_yaml(gate_path)
    status = gate.get("status")
    row = {
        "path": str(gate_path),
        "schema_version": gate.get("schema_version"),
        "status": status,
    }
    if gate.get("schema_version") != schema_version:
        blockers.append(f"latest gate {key} schema_version must be {schema_version}")
    if status not in {"passed", "blocked"}:
        blockers.append(f"latest gate {key} status must be passed or blocked; got {status}")
    if require_pass and status != "passed":
        blockers.append(f"latest gate {key} status must be passed when phase12_allowed=true; got {status}")
    return row


def _small_multi_task_canary_blockers(
    canary: dict[str, Any],
    evidence_path: Path,
    *,
    suite_manifest: dict[str, Any],
    package_rows: list[Any],
) -> list[str]:
    blockers: list[str] = []
    if canary.get("schema_version") != PHASE11_SMALL_MULTI_TASK_CANARY_SCHEMA_VERSION:
        blockers.append(
            "small multi-task canary schema_version must be "
            f"{PHASE11_SMALL_MULTI_TASK_CANARY_SCHEMA_VERSION}"
        )
    suite_id = suite_manifest.get("suite_id")
    if canary.get("suite_id") != suite_id:
        blockers.append(f"small multi-task canary suite_id mismatch: {canary.get('suite_id')}")
    if not isinstance(canary.get("packages"), list):
        blockers.append("small multi-task canary packages must be a list")
    package_count = len(package_rows)
    if package_count < 3 or package_count > 5:
        blockers.append(
            f"small multi-task canary package_count must be between 3 and 5; got {package_count}"
        )

    suite_package_ids = _suite_package_ids(suite_manifest)
    execution_started = False
    for index, row in enumerate(package_rows):
        if not isinstance(row, dict):
            blockers.append(f"small multi-task canary package row {index} must be a mapping")
            continue
        package_id = str(row.get("package_id", ""))
        if not package_id:
            blockers.append(f"small multi-task canary package row {index} missing package_id")
        elif package_id not in suite_package_ids:
            blockers.append(f"package {package_id} not found in suite_manifest.yaml")
        blockers.extend(_small_canary_package_blockers(row, evidence_path, package_id))
        if row.get("execution_lane_status") in {"started", "completed"}:
            execution_started = True

    if not execution_started:
        blockers.append("at least one package must have execution_lane_status started or completed")

    evidence_blockers = canary.get("blockers")
    if isinstance(evidence_blockers, list):
        blockers.extend(str(blocker) for blocker in evidence_blockers if blocker)
    elif evidence_blockers is not None:
        blockers.append("small multi-task canary blockers must be a list")

    return blockers


def _small_canary_package_blockers(
    row: dict[str, Any],
    evidence_path: Path,
    package_id: str,
) -> list[str]:
    blockers: list[str] = []
    rc_gate = row.get("single_task_rc_gate")
    if not isinstance(rc_gate, str) or not rc_gate.strip():
        blockers.append(f"package {package_id} single_task_rc_gate must be a non-empty string")
    else:
        rc_gate_path = _resolve_evidence_path(evidence_path, rc_gate)
        if not rc_gate_path.exists():
            blockers.append(f"package {package_id} single_task_rc_gate does not exist: {rc_gate}")
        else:
            gate = _load_yaml(rc_gate_path)
            if gate.get("schema_version") != PHASE11_SINGLE_TASK_RC_GATE_SCHEMA_VERSION:
                blockers.append(
                    f"package {package_id} single_task_rc_gate schema_version must be "
                    f"{PHASE11_SINGLE_TASK_RC_GATE_SCHEMA_VERSION}"
                )
            if gate.get("status") not in {"passed", "blocked"}:
                blockers.append(
                    f"package {package_id} single_task_rc_gate status must be passed or blocked; "
                    f"got {gate.get('status')}"
                )

    if row.get("real_asset_package") is not True:
        blockers.append(f"package {package_id} real_asset_package must be true")
    if row.get("task_contract") is not True:
        blockers.append(f"package {package_id} task_contract must be true")
    if row.get("overview_visual_review") != "passed":
        blockers.append(f"package {package_id} overview_visual_review must be passed")

    execution_lane_status = row.get("execution_lane_status")
    if execution_lane_status not in {"started", "completed", "blocked"}:
        blockers.append(
            f"package {package_id} execution_lane_status must be started, completed, or blocked; "
            f"got {execution_lane_status}"
        )

    predicate_status = row.get("predicate_evaluation_status")
    if predicate_status not in {"passed", "blocked"}:
        blockers.append(
            f"package {package_id} predicate_evaluation_status must be passed or blocked; "
            f"got {predicate_status}"
        )

    row_blockers = row.get("blockers")
    if (execution_lane_status == "blocked" or predicate_status == "blocked") and not row_blockers:
        blockers.append(f"package {package_id} blocked status must include blockers")
    if row_blockers is not None and not isinstance(row_blockers, list):
        blockers.append(f"package {package_id} blockers must be a list")
    return blockers


def _suite_package_ids(suite_manifest: dict[str, Any]) -> set[str]:
    packages = suite_manifest.get("packages")
    if not isinstance(packages, list):
        return set()
    return {str(package.get("package_id")) for package in packages if isinstance(package, dict)}


def _single_task_package_blockers(package_root: Path, manifest: Any) -> list[str]:
    blockers: list[str] = []
    package_report = validate_package(package_root, require_asset_lock=True)
    if not package_report.ok:
        blockers.extend(package_report.messages)
    task_contract = manifest.entrypoints.get("task_contract", "task/task_contract.yaml")
    if not (package_root / task_contract).exists():
        blockers.append(f"Missing task contract: {task_contract}")
    return blockers


def _required_phase11_gate_statuses(package_root: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    required_gates: dict[str, dict[str, Any]] = {}
    blockers: list[str] = []
    for filename, schema_version in PHASE11_SINGLE_TASK_REQUIRED_GATES.items():
        gate_path = package_root / "evidence" / filename
        if not gate_path.exists():
            required_gates[filename] = {"status": "missing", "path": str(gate_path)}
            blockers.append(f"missing required Phase 11 gate: {filename}")
            continue
        gate = _load_yaml(gate_path)
        status = gate.get("status")
        required_gates[filename] = {
            "path": str(gate_path),
            "schema_version": gate.get("schema_version"),
            "status": status,
        }
        if gate.get("schema_version") != schema_version:
            blockers.append(f"{filename} schema_version must be {schema_version}")
        if status != "passed":
            blockers.append(f"{filename} status must be passed; got {status}")
    return required_gates, blockers


def _release_policy_blockers(
    release_policy: dict[str, Any],
    *,
    package_id: str,
    task_id: str,
) -> list[str]:
    blockers: list[str] = []
    if release_policy.get("schema_version") != PHASE11_RELEASE_POLICY_SCHEMA_VERSION:
        blockers.append(
            f"release policy schema_version must be {PHASE11_RELEASE_POLICY_SCHEMA_VERSION}"
        )
    if release_policy.get("policy_owner") != RELEASE_POLICY_OWNER:
        blockers.append(f"release policy owner must be {RELEASE_POLICY_OWNER}")
    if release_policy.get("package_id") != package_id:
        blockers.append(f"release policy package_id mismatch: {release_policy.get('package_id')}")
    if release_policy.get("task_id") != task_id:
        blockers.append(f"release policy task_id mismatch: {release_policy.get('task_id')}")
    if release_policy.get("release_policy_status") != "pass":
        blockers.append(
            "release policy status must be pass; "
            f"got {release_policy.get('release_policy_status')}"
        )
    if release_policy.get("redistribution_approval") is not True:
        blockers.append("release policy redistribution_approval must be true")

    policy_blockers = release_policy.get("blockers")
    if isinstance(policy_blockers, list):
        blockers.extend(str(blocker) for blocker in policy_blockers if blocker)
    elif policy_blockers is not None:
        blockers.append("release policy blockers must be a list")

    return blockers


def _resolve_review_path(review_path: Path, relative_or_absolute_path: str) -> Path:
    return _resolve_evidence_path(review_path, relative_or_absolute_path)


def _local_artifact_missing(evidence_path: Path, relative_or_absolute_path: str) -> bool:
    if "://" in relative_or_absolute_path:
        return False
    return not _resolve_evidence_path(evidence_path, relative_or_absolute_path).exists()


def _resolve_evidence_path(evidence_path: Path, relative_or_absolute_path: str) -> Path:
    path = Path(relative_or_absolute_path)
    if path.is_absolute():
        return path
    return evidence_path.parent / path


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}

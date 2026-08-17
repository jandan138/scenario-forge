"""Validation and package binding for EOS scientific-workbench robot oracles."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Any, Mapping

import yaml


SCHEMA_VERSION = "eeos.scientific_workbench_scripted_oracle.v0.1"
BLOCKED_SCHEMA_VERSION = "eeos.scientific_workbench_blocked_diagnostic.v0.1"
EXPECTED_STAGES = {
    5: (
        "hold_flask",
        "grasp_and_twist_stopper",
        "lift_stopper",
        "place_stopper_in_rack",
        "terminal_hold",
    ),
    9: (
        "open_door",
        "lift_sample",
        "place_sample_on_shelf",
        "close_door",
        "set_temperature",
        "press_start",
        "terminal_hold",
    ),
}


class ScriptedOracleEvidenceError(ValueError):
    """Raised when EOS oracle evidence exceeds or violates its claim contract."""


@dataclass(frozen=True)
class ScriptedOracleEvidence:
    root: Path
    task_number: int
    scenario_id: str
    run_count: int
    task_interaction_ready: bool


@dataclass(frozen=True)
class BlockedOracleEvidence:
    root: Path
    task_number: int
    scenario_id: str
    blocker_count: int
    task_interaction_ready: bool


def validate_scientific_workbench_oracle_evidence(
    evidence_dir: str | Path,
) -> ScriptedOracleEvidence:
    root = Path(evidence_dir).resolve()
    manifest = _json_mapping(root / "robot_oracle_evidence.json", "oracle manifest")
    validation = _json_mapping(root / "validation_report.json", "validation report")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ScriptedOracleEvidenceError("unsupported scientific-workbench oracle schema")
    if manifest.get("status") != "pass":
        raise ScriptedOracleEvidenceError("oracle manifest did not pass")
    if manifest.get("producer") != "embodied-eval-os":
        raise ScriptedOracleEvidenceError("oracle producer must be embodied-eval-os")
    if manifest.get("execution_mode") != "scripted_robot_oracle":
        raise ScriptedOracleEvidenceError("oracle execution mode must be scripted_robot_oracle")
    if manifest.get("release") != "r11.1":
        raise ScriptedOracleEvidenceError("oracle evidence must bind release r11.1")
    if any(manifest.get(key) is not False for key in ("policy_claim", "benchmark_claim")):
        raise ScriptedOracleEvidenceError("oracle evidence cannot claim policy or benchmark success")
    if manifest.get("thermal_claim") is not False:
        raise ScriptedOracleEvidenceError("oracle evidence cannot claim thermal behavior")
    task_number = manifest.get("task_number")
    if task_number not in EXPECTED_STAGES:
        raise ScriptedOracleEvidenceError("oracle task_number must be 5 or 9")
    scenario_id = _required_string(manifest, "scenario_id", "oracle manifest")
    runs = manifest.get("runs")
    if not isinstance(runs, list) or len(runs) != 3:
        raise ScriptedOracleEvidenceError("oracle evidence must contain exactly three runs")
    for expected_index, run in enumerate(runs, start=1):
        if not isinstance(run, Mapping):
            raise ScriptedOracleEvidenceError("oracle runs must be mappings")
        if run.get("run_index") != expected_index:
            raise ScriptedOracleEvidenceError("oracle run indices must be 1, 2, 3")
        if run.get("cold_start") is not True or run.get("fresh_process") is not True:
            raise ScriptedOracleEvidenceError("every oracle run must be a fresh cold start")
        if run.get("object_motion_source") != "robot_contact_only":
            raise ScriptedOracleEvidenceError("task object motion must be robot contact only")
        if run.get("direct_object_transform_write_count") != 0:
            raise ScriptedOracleEvidenceError("direct object transform write detected")
        if run.get("direct_articulation_state_write_count") != 0:
            raise ScriptedOracleEvidenceError("direct articulation state write detected")
        if run.get("native_goal_passed") is not True:
            raise ScriptedOracleEvidenceError("native GenManip goal did not pass")
        if float(run.get("weighted_progress_score", -1.0)) != 1.0:
            raise ScriptedOracleEvidenceError("weighted progress score must equal 1.0")
        stages = run.get("stage_reports")
        if not isinstance(stages, list):
            raise ScriptedOracleEvidenceError("stage_reports must be a list")
        stage_ids = tuple(
            str(item.get("id")) for item in stages if isinstance(item, Mapping)
        )
        if stage_ids != EXPECTED_STAGES[int(task_number)]:
            raise ScriptedOracleEvidenceError("oracle stage sequence does not match the task")
        if any(not isinstance(item, Mapping) or item.get("passed") is not True for item in stages):
            raise ScriptedOracleEvidenceError("one or more oracle stages failed")
        trace = root / _required_string(run, "trace", "oracle run")
        if not trace.is_file() or not trace.resolve().is_relative_to(root):
            raise ScriptedOracleEvidenceError("oracle trace is missing or outside evidence root")
    if validation.get("overall_status") != "pass":
        raise ScriptedOracleEvidenceError("oracle validation report did not pass")
    if validation.get("task_interaction_ready") is not True:
        raise ScriptedOracleEvidenceError("validation report did not approve task interaction")
    return ScriptedOracleEvidence(
        root=root,
        task_number=int(task_number),
        scenario_id=scenario_id,
        run_count=len(runs),
        task_interaction_ready=True,
    )


def bind_scientific_workbench_oracle_evidence(
    package_root: str | Path,
    evidence_dir: str | Path,
) -> Path:
    package = Path(package_root).resolve()
    result = validate_scientific_workbench_oracle_evidence(evidence_dir)
    scenario = _yaml_mapping(package / "scenario.yaml", "scenario")
    if scenario.get("scenario_id") != result.scenario_id:
        raise ScriptedOracleEvidenceError("oracle scenario_id does not match package")
    if not result.scenario_id.startswith("scientific_workbench_r11_1_"):
        raise ScriptedOracleEvidenceError("package is not an r11.1 scenario")
    destination = package / "evidence/scripted_robot_oracle"
    if destination.exists():
        raise ScriptedOracleEvidenceError("package already contains scripted oracle evidence")
    shutil.copytree(result.root, destination)
    receipt = {
        "schema_version": "scenario-forge-external-oracle-binding/v0.2",
        "status": "pass",
        "producer": "embodied-eval-os",
        "execution_mode": "scripted_robot_oracle",
        "task_number": result.task_number,
        "cold_runs": result.run_count,
        "task_interaction_ready": True,
        "robot_policy_success": False,
        "benchmark_success": False,
        "thermal_behavior": False,
        "manifest": "evidence/scripted_robot_oracle/robot_oracle_evidence.json",
        "manifest_sha256": _sha(destination / "robot_oracle_evidence.json"),
        "validation": "evidence/scripted_robot_oracle/validation_report.json",
        "validation_sha256": _sha(destination / "validation_report.json"),
        "evidence_tree_sha256": _tree_sha(destination),
        "claim_boundary": (
            "Three fixed-layout cold-start scripted robot-contact runs only; not a learned "
            "policy, benchmark result, thermal simulation, or real-world calibration."
        ),
    }
    path = package / "evidence/task_interaction_ready.yaml"
    path.write_text(
        yaml.safe_dump(receipt, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return path


def validate_scientific_workbench_blocked_evidence(
    evidence_dir: str | Path,
) -> BlockedOracleEvidence:
    root = Path(evidence_dir).resolve()
    manifest = _json_mapping(root / "robot_oracle_diagnostic.json", "blocked manifest")
    validation = _json_mapping(root / "validation_report.json", "validation report")
    if manifest.get("schema_version") != BLOCKED_SCHEMA_VERSION:
        raise ScriptedOracleEvidenceError("unsupported blocked diagnostic schema")
    if manifest.get("status") != "blocked":
        raise ScriptedOracleEvidenceError("blocked diagnostic status must be blocked")
    if manifest.get("producer") != "embodied-eval-os":
        raise ScriptedOracleEvidenceError("blocked diagnostic producer must be embodied-eval-os")
    if manifest.get("release") != "r11.1":
        raise ScriptedOracleEvidenceError("blocked diagnostic must bind release r11.1")
    if manifest.get("task_interaction_ready") is not False:
        raise ScriptedOracleEvidenceError("blocked diagnostic cannot approve task interaction")
    if any(
        manifest.get(key) is not False
        for key in ("policy_claim", "benchmark_claim", "thermal_claim")
    ):
        raise ScriptedOracleEvidenceError("blocked diagnostic cannot make success claims")
    task_number = manifest.get("task_number")
    if task_number not in EXPECTED_STAGES:
        raise ScriptedOracleEvidenceError("blocked task_number must be 5 or 9")
    scenario_id = _required_string(manifest, "scenario_id", "blocked manifest")
    blockers = manifest.get("blockers")
    if not isinstance(blockers, list) or not blockers:
        raise ScriptedOracleEvidenceError("blocked diagnostic requires blockers")
    required = {"id", "category", "owner", "summary", "measured_evidence"}
    if any(
        not isinstance(blocker, Mapping)
        or not required.issubset(blocker)
        or not isinstance(blocker.get("measured_evidence"), Mapping)
        for blocker in blockers
    ):
        raise ScriptedOracleEvidenceError("blocked diagnostic contains an invalid blocker")
    observations = manifest.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ScriptedOracleEvidenceError("blocked diagnostic requires observations")
    for observation in observations:
        if not isinstance(observation, Mapping):
            raise ScriptedOracleEvidenceError("blocked observation must be a mapping")
        relative = Path(_required_string(observation, "path", "blocked observation"))
        retained = (root / relative).resolve()
        if not retained.is_file() or not retained.is_relative_to(root):
            raise ScriptedOracleEvidenceError("blocked observation is missing or outside root")
        if observation.get("sha256") != _sha(retained):
            raise ScriptedOracleEvidenceError("blocked observation hash mismatch")
    if validation.get("overall_status") != "blocked":
        raise ScriptedOracleEvidenceError("blocked validation report must be blocked")
    if validation.get("task_interaction_ready") is not False:
        raise ScriptedOracleEvidenceError("blocked validation approved task interaction")
    return BlockedOracleEvidence(
        root=root,
        task_number=int(task_number),
        scenario_id=scenario_id,
        blocker_count=len(blockers),
        task_interaction_ready=False,
    )


def bind_scientific_workbench_blocked_evidence(
    package_root: str | Path,
    evidence_dir: str | Path,
) -> Path:
    package = Path(package_root).resolve()
    result = validate_scientific_workbench_blocked_evidence(evidence_dir)
    scenario = _yaml_mapping(package / "scenario.yaml", "scenario")
    if scenario.get("scenario_id") != result.scenario_id:
        raise ScriptedOracleEvidenceError("blocked scenario_id does not match package")
    if not result.scenario_id.startswith("scientific_workbench_r11_1_"):
        raise ScriptedOracleEvidenceError("package is not an r11.1 scenario")
    destination = package / "evidence/scripted_robot_oracle_blocked"
    if destination.exists():
        raise ScriptedOracleEvidenceError("package already contains blocked oracle evidence")
    shutil.copytree(result.root, destination)
    receipt = {
        "schema_version": "scenario-forge-external-oracle-binding/v0.2",
        "status": "blocked",
        "producer": "embodied-eval-os",
        "execution_mode": "scripted_robot_oracle_prequalification",
        "task_number": result.task_number,
        "blocker_count": result.blocker_count,
        "task_interaction_ready": False,
        "robot_policy_success": False,
        "benchmark_success": False,
        "thermal_behavior": False,
        "manifest": "evidence/scripted_robot_oracle_blocked/robot_oracle_diagnostic.json",
        "manifest_sha256": _sha(destination / "robot_oracle_diagnostic.json"),
        "validation": "evidence/scripted_robot_oracle_blocked/validation_report.json",
        "validation_sha256": _sha(destination / "validation_report.json"),
        "evidence_tree_sha256": _tree_sha(destination),
        "claim_boundary": (
            "Measured r11.1 pre-promotion blocker; no task, policy, benchmark, "
            "thermal, or real-world success claim."
        ),
    }
    path = package / "evidence/task_interaction_ready.yaml"
    if path.exists():
        raise ScriptedOracleEvidenceError("package already has a task readiness receipt")
    path.write_text(
        yaml.safe_dump(receipt, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return path


def _json_mapping(path: Path, label: str) -> Mapping[str, Any]:
    if not path.is_file():
        raise ScriptedOracleEvidenceError(f"{label} is missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ScriptedOracleEvidenceError(f"{label} must be a mapping")
    return value


def _yaml_mapping(path: Path, label: str) -> Mapping[str, Any]:
    if not path.is_file():
        raise ScriptedOracleEvidenceError(f"{label} is missing: {path}")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ScriptedOracleEvidenceError(f"{label} must be a mapping")
    return value


def _required_string(value: Mapping[str, Any], key: str, label: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ScriptedOracleEvidenceError(f"{label}.{key} must be a non-empty string")
    return result


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _tree_sha(root: Path) -> str:
    digest = sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()

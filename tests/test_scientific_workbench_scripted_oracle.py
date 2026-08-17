from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest
import yaml

from scenario_forge.evaluation.scientific_workbench_oracle import (
    ScriptedOracleEvidenceError,
    bind_scientific_workbench_blocked_evidence,
    bind_scientific_workbench_oracle_evidence,
    validate_scientific_workbench_blocked_evidence,
    validate_scientific_workbench_oracle_evidence,
)


TASK05_STAGES = (
    "hold_flask",
    "grasp_and_twist_stopper",
    "lift_stopper",
    "place_stopper_in_rack",
    "terminal_hold",
)


def _write_evidence(root: Path, *, task_number: int = 5) -> Path:
    root.mkdir(parents=True)
    stages = TASK05_STAGES if task_number == 5 else (
        "open_door",
        "lift_sample",
        "place_sample_on_shelf",
        "close_door",
        "set_temperature",
        "press_start",
        "terminal_hold",
    )
    runs = []
    for index in range(1, 4):
        trace = root / f"run_{index:02d}_trace.json"
        trace.write_text(json.dumps({"samples": [{"action": [0.0] * 16}]}), encoding="utf-8")
        runs.append(
            {
                "run_index": index,
                "cold_start": True,
                "fresh_process": True,
                "object_motion_source": "robot_contact_only",
                "direct_object_transform_write_count": 0,
                "direct_articulation_state_write_count": 0,
                "native_goal_passed": True,
                "weighted_progress_score": 1.0,
                "stage_reports": [{"id": stage, "passed": True} for stage in stages],
                "trace": trace.name,
            }
        )
    manifest = {
        "schema_version": "eeos.scientific_workbench_scripted_oracle.v0.1",
        "status": "pass",
        "producer": "embodied-eval-os",
        "execution_mode": "scripted_robot_oracle",
        "release": "r11.1",
        "task_number": task_number,
        "scenario_id": f"scientific_workbench_r11_1_task{task_number:02d}",
        "policy_claim": False,
        "benchmark_claim": False,
        "thermal_claim": False,
        "runs": runs,
    }
    (root / "robot_oracle_evidence.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    (root / "validation_report.json").write_text(
        json.dumps({"overall_status": "pass", "task_interaction_ready": True}),
        encoding="utf-8",
    )
    return root


def test_oracle_evidence_requires_three_contact_only_perfect_runs(tmp_path: Path) -> None:
    evidence = _write_evidence(tmp_path / "evidence")

    result = validate_scientific_workbench_oracle_evidence(evidence)

    assert result.task_number == 5
    assert result.run_count == 3
    assert result.task_interaction_ready is True


def test_oracle_evidence_rejects_direct_articulation_write(tmp_path: Path) -> None:
    evidence = _write_evidence(tmp_path / "evidence", task_number=9)
    manifest_path = evidence / "robot_oracle_evidence.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["runs"][1]["direct_articulation_state_write_count"] = 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ScriptedOracleEvidenceError, match="direct articulation"):
        validate_scientific_workbench_oracle_evidence(evidence)


def test_binding_is_hash_bound_and_does_not_claim_policy_success(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    (package / "scenario.yaml").write_text(
        yaml.safe_dump(
            {
                "scenario_id": "scientific_workbench_r11_1_task05",
                "metadata": {"release": "r11.1"},
            }
        ),
        encoding="utf-8",
    )
    evidence = _write_evidence(tmp_path / "source")

    receipt_path = bind_scientific_workbench_oracle_evidence(package, evidence)
    receipt = yaml.safe_load(receipt_path.read_text(encoding="utf-8"))

    assert receipt["status"] == "pass"
    assert receipt["task_interaction_ready"] is True
    assert receipt["robot_policy_success"] is False
    assert receipt["benchmark_success"] is False
    assert len(receipt["evidence_tree_sha256"]) == 64
    assert (package / "evidence/scripted_robot_oracle/robot_oracle_evidence.json").is_file()


def test_blocked_evidence_binds_without_promoting_task_readiness(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    (package / "scenario.yaml").write_text(
        yaml.safe_dump(
            {
                "scenario_id": "scientific_workbench_r11_1_task09",
                "metadata": {"release": "r11.1"},
            }
        ),
        encoding="utf-8",
    )
    evidence = tmp_path / "blocked"
    retained = evidence / "observations/door_trial.json"
    retained.parent.mkdir(parents=True)
    retained.write_text(json.dumps({"door_angle_rad": 0.0}), encoding="utf-8")
    manifest = {
        "schema_version": "eeos.scientific_workbench_blocked_diagnostic.v0.1",
        "status": "blocked",
        "producer": "embodied-eval-os",
        "release": "r11.1",
        "task_number": 9,
        "scenario_id": "scientific_workbench_r11_1_task09",
        "task_interaction_ready": False,
        "policy_claim": False,
        "benchmark_claim": False,
        "thermal_claim": False,
        "blockers": [
            {
                "id": "door_contact_geometry",
                "category": "asset_interaction_geometry",
                "owner": "convertasset",
                "summary": "The authored door grasp cannot transfer force.",
                "measured_evidence": {"door_angle_rad": 0.0},
            }
        ],
        "observations": [
            {
                "path": "observations/door_trial.json",
                "sha256": sha256(retained.read_bytes()).hexdigest(),
            }
        ],
    }
    (evidence / "robot_oracle_diagnostic.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (evidence / "validation_report.json").write_text(
        json.dumps({"overall_status": "blocked", "task_interaction_ready": False}),
        encoding="utf-8",
    )

    result = validate_scientific_workbench_blocked_evidence(evidence)
    receipt_path = bind_scientific_workbench_blocked_evidence(package, evidence)
    receipt = yaml.safe_load(receipt_path.read_text(encoding="utf-8"))

    assert result.task_number == 9
    assert result.task_interaction_ready is False
    assert receipt["status"] == "blocked"
    assert receipt["task_interaction_ready"] is False
    assert receipt["robot_policy_success"] is False
    assert (package / "evidence/scripted_robot_oracle_blocked/robot_oracle_diagnostic.json").is_file()

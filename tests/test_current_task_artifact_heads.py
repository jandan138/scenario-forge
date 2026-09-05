from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "configs/artifact_retention/current_task_heads.v1.json"


def test_current_task_head_registry_is_complete_and_points_to_local_handoffs() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "scenario-forge-current-task-heads/v1"
    assert payload["default_local_policy"] == "complete_directory_and_handoff_zip"
    assert payload["unclassified_policy"] == "HOLD"
    entries = payload["entries"]
    keys = [(entry["artifact_family"], entry["variant_key"]) for entry in entries]
    assert len(keys) == len(set(keys))
    assert len(entries) >= 13
    for entry in entries:
        output = ROOT / entry["output_root"]
        handoff = output / entry["handoff_zip"]
        assert output.is_dir(), entry
        assert handoff.is_file(), entry
        assert entry["revision"]
        assert entry["status"] in {
            "current_delivery",
            "current_candidate",
            "current_validation_evidence",
        }


def test_current_task_heads_do_not_claim_success_by_default() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    for entry in payload["entries"]:
        assert "benchmark_success" not in entry
        assert "robot_policy_success" not in entry

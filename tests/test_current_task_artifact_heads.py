from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "configs/artifact_retention/current_task_heads.v1.json"


def test_current_task_head_registry_is_complete() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "scenario-forge-current-task-heads/v1"
    assert payload["default_local_policy"] == "complete_directory_and_handoff_zip"
    assert payload["unclassified_policy"] == "HOLD"
    entries = payload["entries"]
    keys = [(entry["artifact_family"], entry["variant_key"]) for entry in entries]
    assert len(keys) == len(set(keys))
    assert len(entries) >= 13
    for entry in entries:
        assert not Path(entry["output_root"]).is_absolute()
        assert ".." not in Path(entry["output_root"]).parts
        assert not Path(entry["handoff_zip"]).is_absolute()
        assert ".." not in Path(entry["handoff_zip"]).parts
        assert entry["revision"]
        assert entry["status"] in {
            "current_delivery",
            "current_candidate",
            "current_validation_evidence",
        }


@pytest.mark.local_artifacts
def test_current_task_heads_point_to_local_handoffs() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    for entry in payload["entries"]:
        output = ROOT / entry["output_root"]
        assert output.is_dir(), entry
        assert (output / entry["handoff_zip"]).is_file(), entry


def test_current_task_heads_do_not_claim_success_by_default() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    for entry in payload["entries"]:
        assert "benchmark_success" not in entry
        assert "robot_policy_success" not in entry


def test_archive_index_accounts_for_retained_exceptions_and_net_bytes() -> None:
    index = json.loads((ROOT / 'external_artifacts/archive-index-20260905.json').read_text())
    removed = index['archived_and_removed']
    exceptions = index['retained_exceptions']
    removed_paths = {row['local_path'] for row in removed}
    assert len(removed_paths) == len(removed)
    assert removed_paths.isdisjoint(row['local_path'] for row in exceptions)
    assert index['bytes_released'] == sum(row['bytes'] for row in removed)
    assert all(batch['status'] == 'complete' for batch in index['batches'])
    for row in removed + index['archived_and_restored']:
        assert len(row['tree_sha256']) == 64
        assert '/artifact-history-v1/' in row['remote_uri']
        assert '..' not in Path(row['remote_uri'].split(':', 1)[1]).parts

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import yaml

from scenario_forge.generation.source_resolver import resolve_scenario_source_bindings


ROOT = Path(__file__).resolve().parents[1]
BINDINGS = ROOT / "configs/source_bindings/scientific_workbench_task08_r12_assets_20260901.yaml"
READINESS = ROOT / "configs/asset_readiness/scientific_workbench_task08_r12_assets_20260901.yaml"


def test_task08_r12_registry_resolves_three_hash_locked_assets() -> None:
    sources = resolve_scenario_source_bindings(BINDINGS)
    assert len(sources) == 3
    payload = yaml.safe_load(BINDINGS.read_text())
    for item in payload["bindings"].values():
        path = Path(item["source_usd"])
        assert path.is_file()
        assert item["expected_sha256"] == "sha256:" + sha256(path.read_bytes()).hexdigest()


def test_task08_r12_readiness_keeps_thread_claim_blocked() -> None:
    readiness = yaml.safe_load(READINESS.read_text())
    producer = Path(readiness["producer_manifest"])
    assert readiness["producer_manifest_sha256"] == "sha256:" + sha256(producer.read_bytes()).hexdigest()
    manifest = json.loads(producer.read_text())
    assert manifest["status"] == "pass"
    assert readiness["readiness"]["vr_action_collection_layout"] == "ready"
    assert readiness["readiness"]["thread_interaction"] == "blocked"
    assert readiness["consumer_policy"]["allow_thread_task_claim"] is False

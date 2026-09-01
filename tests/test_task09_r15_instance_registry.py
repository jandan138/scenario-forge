from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import yaml

from scenario_forge.generation.source_resolver import resolve_scenario_source_bindings


ROOT = Path(__file__).resolve().parents[1]
BINDINGS = ROOT / "configs/source_bindings/scientific_workbench_task09_r15_instance_oven_20260901.yaml"
READINESS = ROOT / "configs/asset_readiness/scientific_workbench_task09_r15_instance_oven_20260901.yaml"


def test_r15_instance_oven_binding_is_hash_locked() -> None:
    source = next(iter(resolve_scenario_source_bindings(BINDINGS).values()))
    payload = yaml.safe_load(BINDINGS.read_text())
    binding = next(iter(payload["bindings"].values()))
    assert binding["expected_sha256"] == "sha256:" + sha256(
        source.source_usd.read_bytes()
    ).hexdigest()
    assert source.root_prim_path == "/World/obj_oven"


def test_r15_readiness_forbids_legacy_and_consumer_rewrite() -> None:
    readiness = yaml.safe_load(READINESS.read_text())
    manifest = Path(readiness["producer_manifest"])
    assert readiness["producer_manifest_sha256"] == "sha256:" + sha256(
        manifest.read_bytes()
    ).hexdigest()
    producer = json.loads(manifest.read_text())
    assert producer["overall_status"] == "pass"
    assert producer["claims"]["runtime_namespace_qualified"] is True
    assert readiness["consumer_policy"]["allow_legacy_link_paths"] is False
    assert readiness["consumer_policy"]["allow_scenario_side_namespace_rewrite"] is False

#!/usr/bin/env python3
"""Validate Task 12 alias adapter composition, goal and runtime contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]


def validate(bundle: Path) -> Path:
    from pxr import Usd

    bundle = bundle.resolve()
    scenario_path = bundle / "scenario.yaml"
    scenario = yaml.safe_load(scenario_path.read_text())
    scene_path = bundle / scenario["scene_usd"]
    stage = Usd.Stage.Open(str(scene_path))
    episode = json.loads((bundle / scenario["episode"]).read_text())
    contract = episode["task_data"]["scenario_forge_runtime_contract"]
    schema = json.loads(
        (ROOT / "src/scenario_forge/schemas/jsonschema/scenario-forge-genmanip-runtime-contract-v0.6.schema.json").read_text()
    )
    contract_error = None
    try:
        jsonschema.validate(contract, schema)
    except jsonschema.ValidationError as exc:
        contract_error = exc.message
    config = yaml.safe_load((bundle / "config.yaml").read_text())
    evaluation = config["evaluation_configs"][0]
    instruction = episode["task_data"]["instruction"]
    missing = [
        path
        for path in (
            "/World/_scene/obj_centrifuge",
            "/World/_scene/obj_mixed_rack",
            "/World/_scene/obj_primary_tube",
            "/World/_scene/obj_balance_tube",
            "/physicsScene",
        )
        if not stage.GetPrimAtPath(path)
    ]
    forbidden_50 = [
        path
        for path in (
            "/World/_scene/obj_bg_50ml_00",
            "/World/_scene/obj_bg_50ml_01",
        )
        if stage.GetPrimAtPath(path)
    ]
    checks = {
        "stage_composes": bool(stage) and not missing,
        "no_50ml_tubes": not forbidden_50,
        "native_goal_nonempty": bool(evaluation["generation_config"]["goal"]),
        "episode_goal_nonempty": bool(episode["task_data"]["goal"]),
        "runtime_contract_v06_valid": contract_error is None,
        "instruction_is_rack_to_rotor": "管架中拿起" in instruction and "转子目标孔位" in instruction,
        "no_task02_pour_metadata": all(
            token not in json.dumps(episode, ensure_ascii=False)
            for token in ("量筒", "烧杯", "倾倒")
        ),
        "config_routes_alias": "task12_alias/scene" in evaluation["usd_name"],
    }
    passed = all(checks.values())
    report = {
        "schema_version": "scenario-forge.task12-alias-adapter-smoke/v1",
        "status": "pass" if passed else "blocked",
        "checks": checks,
        "missing_prims": missing,
        "forbidden_50ml_prims": forbidden_50,
        "runtime_contract_error": contract_error,
        "claims": {
            "adapter_load_smoke": passed,
            "robot_policy_success": False,
            "task_success": False,
            "benchmark_success": False,
        },
    }
    report_path = bundle / "adapter_smoke.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    scenario["status"] = "adapter_smoke_pass" if passed else "adapter_smoke_blocked"
    scenario["adapter_smoke"] = "adapter_smoke.json"
    scenario_path.write_text(yaml.safe_dump(scenario, sort_keys=False, allow_unicode=True))
    manifest_path = bundle / "package_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["claims"]["adapter_load_smoke"] = passed
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    if not passed:
        raise RuntimeError(f"Task 12 alias adapter smoke blocked: {report_path}")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    print(validate(args.bundle))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

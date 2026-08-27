#!/usr/bin/env python3
"""Validate the Task 11 r9.1 left/right GenManip bundle."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

import yaml


def validate(bundle: Path) -> Path:
    from pxr import Usd

    bundle = bundle.resolve()
    scenario_path = bundle / "scenario.yaml"
    scenario = yaml.safe_load(scenario_path.read_text())
    scene = bundle / scenario["scene_usd"]
    source = bundle / scenario["source_scene_copy"]
    stage = Usd.Stage.Open(str(scene))
    manifest_path = bundle / "package_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    config = yaml.safe_load((bundle / "config.yaml").read_text())
    evaluation = config["evaluation_configs"][0]
    checks = {
        "stage_composes": bool(stage),
        "source_hash_bound": sha256(source.read_bytes()).hexdigest()
        == manifest["adapter_local_scene_sha256"],
        "config_routes_r9_1": "task11_r9_1/scene" in evaluation["usd_name"],
        "socket_pair_3_15": manifest["primary_socket"] == 3
        and manifest["balance_socket"] == 15,
        "wrapper_package_relative": "/cpfs/" not in scene.read_text(),
    }
    passed = all(checks.values())
    report = {
        "schema_version": "scenario-forge.task11-r9-1-adapter-smoke/v1",
        "status": "pass" if passed else "blocked",
        "checks": checks,
        "claims": {
            "adapter_load_smoke": passed,
            "robot_policy_success": False,
            "task11_success": False,
            "benchmark_success": False,
        },
    }
    report_path = bundle / "adapter_smoke.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    manifest["claims"]["adapter_load_smoke"] = passed
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    scenario["status"] = "adapter_smoke_pass" if passed else "adapter_smoke_blocked"
    scenario["adapter_smoke"] = "adapter_smoke.json"
    scenario_path.write_text(yaml.safe_dump(scenario, sort_keys=False, allow_unicode=True))
    if not passed:
        raise RuntimeError(f"r9.1 adapter smoke blocked: {report_path}")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    print(validate(args.bundle))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

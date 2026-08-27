#!/usr/bin/env python3
"""Validate the Task 11 r9.1 left/right GenManip bundle."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

import yaml


def validate(
    bundle: Path,
    *,
    release_id: str = "r9_1",
    primary_socket: int = 3,
    balance_socket: int = 15,
) -> Path:
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
        "config_routes_release": f"task11_{release_id}/scene" in evaluation["usd_name"],
        "socket_pair_matches": manifest["primary_socket"] == primary_socket
        and manifest["balance_socket"] == balance_socket,
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
    parser.add_argument("--release-id", default="r9_1")
    parser.add_argument("--primary-socket", type=int, default=3)
    parser.add_argument("--balance-socket", type=int, default=15)
    args = parser.parse_args()
    print(
        validate(
            args.bundle,
            release_id=args.release_id,
            primary_socket=args.primary_socket,
            balance_socket=args.balance_socket,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

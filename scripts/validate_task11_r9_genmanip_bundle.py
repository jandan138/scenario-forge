#!/usr/bin/env python3
"""Run a package-local composition/config smoke for the Task 11 r9 adapter."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

import yaml


REQUIRED_PRIMS = (
    "/World/_scene/obj_centrifuge",
    "/World/_scene/obj_mixed_rack",
    "/World/_scene/obj_primary_tube",
    "/World/_scene/obj_balance_tube",
    *(f"/World/_scene/obj_bg_15ml_{index:02d}" for index in range(6)),
    "/World/_scene/obj_r9_amber_bottle",
    "/World/_scene/obj_r9_tip_box",
    "/World/_scene/obj_r9_wash_bottle",
    "/World/_scene/obj_r9_clear_bottle",
    "/World/_scene/obj_r9_pipette_carousel",
    "/physicsScene",
)


def validate(bundle: Path) -> Path:
    from pxr import Usd, UsdPhysics

    bundle = bundle.resolve()
    scenario_path = bundle / "scenario.yaml"
    scenario = yaml.safe_load(scenario_path.read_text())
    scene_path = bundle / scenario["scene_usd"]
    source_copy = bundle / scenario["source_scene_copy"]
    package_manifest = json.loads((bundle / "package_manifest.json").read_text())
    stage = Usd.Stage.Open(str(scene_path))
    if not stage:
        raise RuntimeError(f"cannot compose adapter scene: {scene_path}")
    missing = [path for path in REQUIRED_PRIMS if not stage.GetPrimAtPath(path)]
    particle_like = [
        str(prim.GetPath())
        for prim in stage.Traverse()
        if "Particle" in prim.GetTypeName()
        or any("Particle" in schema for schema in prim.GetAppliedSchemas())
    ]
    tube_roots = (
        "/World/_scene/obj_primary_tube",
        "/World/_scene/obj_balance_tube",
        *(f"/World/_scene/obj_bg_15ml_{index:02d}" for index in range(6)),
    )
    single_rigid = all(
        len(
            [
                prim
                for prim in Usd.PrimRange(stage.GetPrimAtPath(path))
                if prim.HasAPI(UsdPhysics.RigidBodyAPI)
            ]
        )
        == 1
        for path in tube_roots
    )
    config = yaml.safe_load((bundle / "config.yaml").read_text())
    evaluation = config["evaluation_configs"][0]
    task_files = sorted((bundle / "tasks/scenario_forge/task11_r9").rglob("*.json"))
    wrapper_text = scene_path.read_text()
    checks = {
        "stage_composes": not missing,
        "default_prim_world": str(stage.GetDefaultPrim().GetPath()) == "/World",
        "source_copy_hash_bound": sha256(source_copy.read_bytes()).hexdigest()
        == package_manifest["adapter_local_scene_sha256"],
        "wrapper_has_no_absolute_cpfs_reference": "/cpfs/" not in wrapper_text,
        "particle_free": not particle_like,
        "config_routes_r9": "task11_r9/scene" in evaluation["usd_name"],
        "episode_metadata_present": len(task_files) == 1,
        "all_15ml_single_rigid_body": single_rigid,
    }
    passed = all(checks.values())
    report = {
        "schema_version": "scenario-forge.task11-r9-genmanip-smoke.v1",
        "status": "pass" if passed else "blocked",
        "checks": checks,
        "missing_prims": missing,
        "particle_like_prims": particle_like,
        "scene_usd": scenario["scene_usd"],
        "source_scene_copy": scenario["source_scene_copy"],
        "claims": {
            "adapter_load_smoke": passed,
            "robot_policy_success": False,
            "task11_success": False,
            "benchmark_success": False,
        },
    }
    report_path = bundle / "adapter_smoke.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    scenario["status"] = "adapter_smoke_pass" if passed else "adapter_smoke_blocked"
    scenario["adapter_smoke"] = "adapter_smoke.json"
    scenario_path.write_text(yaml.safe_dump(scenario, sort_keys=False, allow_unicode=True))
    if not passed:
        raise RuntimeError(f"Task 11 r9 adapter smoke blocked: {report_path}")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    print(validate(args.bundle))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

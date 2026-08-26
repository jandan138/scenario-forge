#!/usr/bin/env python3
"""Wrap the exact Task 11 r8 scene for unchanged GenManip consumption."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts import build_task11_r7_genmanip_validation_bundle as legacy  # noqa: E402


DEFAULT_R8 = ROOT / "outputs/scientific_workbench_task11_vr_r8_20260826"
DEFAULT_OUT = DEFAULT_R8 / "adapters/ebench/genmanip"
TASK_NAME = "scenario_forge/scientific_workbench_task11_r8_scene_candidate"


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def build(r8: Path, base: Path, out: Path) -> Path:
    from pxr import Usd

    r8 = r8.resolve()
    scene = r8 / "vr/scene.usd"
    output = legacy.build(r8, base, out)
    old_scene_dir = output / "assets/scene_usds/scenario_forge/task11_r7"
    new_scene_dir = output / "assets/scene_usds/scenario_forge/task11_r8"
    new_scene_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(old_scene_dir), str(new_scene_dir))
    source_copy = output / "assets/task11_r8_source"
    shutil.copytree(
        r8 / "vr",
        source_copy,
        ignore=shutil.ignore_patterns("evidence"),
    )
    wrapped = new_scene_dir / "scene.usda"
    stage = Usd.Stage.Open(str(wrapped))
    scene_root = stage.GetPrimAtPath("/World/_scene")
    scene_root.GetReferences().ClearReferences()
    scene_root.GetReferences().AddReference(
        "../../../task11_r8_source/scene.usd", "/World"
    )
    table = stage.GetPrimAtPath("/World/_scene/obj_table")
    table.GetReferences().ClearReferences()
    table.GetReferences().AddReference(
        "../../../task11_r8_source/scene.usd", "/World/table"
    )
    stage.GetRootLayer().Save()
    old_task_dir = output / "tasks/scenario_forge/task11_r7"
    new_task_dir = output / "tasks/scenario_forge/task11_r8"
    shutil.move(str(old_task_dir), str(new_task_dir))
    config_path = output / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    evaluation = config["evaluation_configs"][0]
    evaluation["task_name"] = TASK_NAME
    evaluation["usd_name"] = "assets/scene_usds/scenario_forge/task11_r8/scene"
    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    manifest = {
        "schema_version": "scenario-forge-task11-r8-genmanip-validation/v1",
        "scenario_id": "scientific_workbench_centrifuge_unload_shutdown",
        "canonical_task": True,
        "runtime": "isaac_sim_4.1_genmanip_lift2",
        "source_scene": str(scene),
        "source_scene_sha256": _sha(scene),
        "adapter_local_scene_sha256": _sha(source_copy / "scene.usd"),
        "scene_usd": "assets/scene_usds/scenario_forge/task11_r8/scene.usda",
        "post_initialization_object_transform_writes_allowed": False,
        "direct_device_joint_target_writes_allowed": False,
        "liquid_contract": {
            "mode": "visual_static_liquid",
            "interactive": False,
            "particle_system_count": 0,
        },
        "claims": {
            "scene_static_stability": True,
            "robot_free_device_mechanics": True,
            "canonical_task11_scripted_oracle_success": False,
            "robot_policy_success": False,
            "benchmark_success": False,
            "task11_success": False,
        },
    }
    (output / "package_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    (output / "scenario.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "scenario-forge.task11-r8-genmanip-scenario/v1",
                "scenario_id": manifest["scenario_id"],
                "scene_usd": manifest["scene_usd"],
                "source_scene_copy": "assets/task11_r8_source/scene.usd",
                "config": "config.yaml",
                "status": "adapter_smoke_pending",
                "claims": manifest["claims"],
            },
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r8", type=Path, default=DEFAULT_R8)
    parser.add_argument("--base", type=Path, default=legacy.DEFAULT_BASE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(build(args.r8, args.base, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

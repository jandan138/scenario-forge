#!/usr/bin/env python3
"""Build the Task 11 r9.1 left/right GenManip validation bundle."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_task11_r9_genmanip_validation_bundle as r9_adapter  # noqa: E402
from scripts import generate_scientific_workbench_task11_vr_r9_1 as r9_1  # noqa: E402


DEFAULT_PACKAGE = r9_1.DEFAULT_OUT
DEFAULT_OUT = DEFAULT_PACKAGE / "adapters/ebench/genmanip"
TASK_NAME = "scenario_forge/scientific_workbench_task11_r9_1_left_right"
INSTRUCTION = (
    "按下离心机开盖按钮，拿起目标15 mL离心管并放入指定管架孔位，"
    "最后按下STOP关机。"
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def build(package: Path, out: Path) -> Path:
    from pxr import Usd

    package = package.resolve()
    output = r9_adapter.build(package, r9_adapter.legacy.DEFAULT_BASE, out.resolve())
    old_scene = output / "assets/scene_usds/scenario_forge/task11_r9"
    new_scene = output / "assets/scene_usds/scenario_forge/task11_r9_1"
    shutil.move(str(old_scene), str(new_scene))
    old_source = output / "assets/task11_r9_source"
    new_source = output / "assets/task11_r9_1_source"
    shutil.move(str(old_source), str(new_source))
    wrapper = new_scene / "scene.usda"
    stage = Usd.Stage.Open(str(wrapper))
    stage.GetPrimAtPath("/World/_scene").GetReferences().ClearReferences()
    stage.GetPrimAtPath("/World/_scene").GetReferences().AddReference(
        "../../../task11_r9_1_source/scene.usd", "/World"
    )
    stage.GetPrimAtPath("/World/_scene/obj_table").GetReferences().ClearReferences()
    stage.GetPrimAtPath("/World/_scene/obj_table").GetReferences().AddReference(
        "../../../task11_r9_1_source/scene.usd", "/World/table"
    )
    stage.GetRootLayer().Save()
    old_tasks = output / "tasks/scenario_forge/task11_r9"
    new_tasks = output / "tasks/scenario_forge/task11_r9_1"
    shutil.move(str(old_tasks), str(new_tasks))

    config_path = output / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    evaluation = config["evaluation_configs"][0]
    evaluation["task_name"] = TASK_NAME
    evaluation["usd_name"] = "assets/scene_usds/scenario_forge/task11_r9_1/scene"
    evaluation["instruction"] = INSTRUCTION
    config_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True))
    episode_path = new_tasks / "002/episode_metadata.json"
    episode = json.loads(episode_path.read_text())
    episode["task_data"]["instruction"] = INSTRUCTION
    episode["task_data"].pop("scenario_forge_runtime_contract", None)
    episode_path.write_text(json.dumps(episode, indent=2, sort_keys=True) + "\n")

    manifest = {
        "schema_version": "scenario-forge.task11-r9-1-genmanip/v1",
        "scenario_id": "scientific_workbench_centrifuge_unload_shutdown",
        "source_scene_sha256": _sha(package / "vr/scene.usd"),
        "adapter_local_scene_sha256": _sha(new_source / "scene.usd"),
        "scene_usd": "assets/scene_usds/scenario_forge/task11_r9_1/scene.usda",
        "source_scene_copy": "assets/task11_r9_1_source/scene.usd",
        "primary_socket": r9_1.PRIMARY_SOCKET,
        "balance_socket": r9_1.BALANCE_SOCKET,
        "claims": {
            "left_right_camera_pair": True,
            "adapter_load_smoke": False,
            "robot_policy_success": False,
            "task11_success": False,
            "benchmark_success": False,
        },
    }
    (output / "package_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    (output / "scenario.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "scenario-forge.task11-r9-1-scenario/v1",
                "scenario_id": manifest["scenario_id"],
                "scene_usd": manifest["scene_usd"],
                "source_scene_copy": manifest["source_scene_copy"],
                "config": "config.yaml",
                "status": "adapter_smoke_pending",
                "claims": manifest["claims"],
            },
            sort_keys=False,
            allow_unicode=True,
        )
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(build(args.package, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

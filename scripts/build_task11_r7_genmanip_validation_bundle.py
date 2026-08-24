#!/usr/bin/env python3
"""Wrap the exact Task11 r7 VR scene as a GenManip Lift2 validation bundle."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_R7 = ROOT / "outputs/scientific_workbench_task11_vr_r7_20260825"
DEFAULT_BASE = (
    ROOT
    / "outputs/scientific_workbench_task02_r10_2_fill_sweep_20260819/"
    "packages/fill40/ebench"
)
DEFAULT_OUT = DEFAULT_R7 / "adapters/ebench/genmanip"
TASK_NAME = "scenario_forge/scientific_workbench_task11_r7_canonical_robot_oracle"


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def build(r7: Path, base: Path, out: Path) -> Path:
    from pxr import Sdf, Usd, UsdGeom

    r7 = r7.resolve()
    base = base.resolve()
    out = out.resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    scene = r7 / "vr/scene.usd"
    source_scene = Usd.Stage.Open(str(scene))
    pose_cache = UsdGeom.XformCache()

    def source_pose(path: str):
        matrix = pose_cache.GetLocalToWorldTransform(source_scene.GetPrimAtPath(path))
        point = matrix.ExtractTranslation()
        quat = matrix.ExtractRotationQuat()
        imag = quat.GetImaginary()
        return (
            [float(point[i]) for i in range(3)],
            [float(quat.GetReal()), float(imag[0]), float(imag[1]), float(imag[2])],
        )

    device_position, device_orientation = source_pose("/World/obj_centrifuge")
    tube_position, tube_orientation = source_pose("/World/obj_primary_tube")
    rack_position, rack_orientation = source_pose("/World/obj_mixed_rack")
    scene_rel = Path("assets/scene_usds/scenario_forge/task11_r7/scene.usda")
    wrapped = out / scene_rel
    wrapped.parent.mkdir(parents=True)
    stage = Usd.Stage.CreateNew(str(wrapped))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    scene_root = UsdGeom.Xform.Define(stage, "/World/_scene")
    scene_root.GetPrim().GetReferences().AddReference(str(scene), "/World")
    source_stage = Usd.Stage.Open(str(scene))
    source_flat = source_stage.Flatten(False)
    Sdf.CopySpec(source_flat, "/World/physicsScene", stage.GetRootLayer(), "/physicsScene")
    stage.OverridePrim("/World/_scene/physicsScene").SetActive(False)
    table = UsdGeom.Xform.Define(stage, "/World/_scene/obj_table")
    table.GetPrim().GetReferences().AddReference(str(scene), "/World/table")
    stage.OverridePrim("/World/_scene/table").SetActive(False)
    stage.GetRootLayer().Save()

    config = yaml.safe_load((base / "config.yaml").read_text(encoding="utf-8"))
    evaluation = config["evaluation_configs"][0]
    evaluation["task_name"] = TASK_NAME
    evaluation["usd_name"] = scene_rel.with_suffix("").as_posix()
    evaluation["instruction"] = (
        "按下离心机开盖按钮，拿起目标15 mL离心管并放入指定管架孔位，"
        "最后按下STOP关机。"
    )
    camera_rel = Path("cameras/fixed_camera_lift2.yml")
    (out / camera_rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(base / camera_rel, out / camera_rel)
    evaluation["domain_randomization"]["cameras"]["config_path"] = str(camera_rel)
    evaluation["generation_config"]["goal"] = []
    evaluation["generation_config"]["articulation"] = {
        "centrifuge": {"is_articulated": True, "target_positions": [0.0] * 6}
    }
    evaluation["object_config"] = {
        "centrifuge": {
            "type": "existed_object",
            "uid_list": ["centrifuge"],
            "is_articulated": True,
            "target_positions": [0.0] * 6,
            "articulation_info": {"is_articulated": True, "part": {}},
        },
        "primary_tube": {"type": "existed_object", "uid_list": ["primary_tube"]},
        "mixed_rack": {"type": "existed_object", "uid_list": ["mixed_rack"]},
    }
    (out / "config.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )

    source_episode = next(base.glob("tasks/scenario_forge/*/002/episode_metadata.json"))
    episode = json.loads(source_episode.read_text(encoding="utf-8"))
    episode["task_data"]["goal"] = []
    base_layout = episode["task_data"]["initial_layout"]
    episode["task_data"]["initial_layout"] = {
        "00000000000000000000000000000000": base_layout[
            "00000000000000000000000000000000"
        ],
        "lift2": base_layout["lift2"],
        "centrifuge": {
            "type": "articulation",
            "prim_path": "/World/_scene/obj_centrifuge",
            "position": device_position,
            "orientation": device_orientation,
            "scale": [1.0, 1.0, 1.0],
            "joint_positions": [0.0] * 6,
        },
        "primary_tube": {
            "type": "rigid",
            "prim_path": "/World/_scene/obj_primary_tube",
            "path": "",
            "position": tube_position,
            "orientation": tube_orientation,
            "scale": [1.0, 1.0, 1.0],
            "add_colliders": False,
            "add_rigid_body": False,
            "is_articulation_part": False,
        },
        "mixed_rack": {
            "type": "object",
            "prim_path": "/World/_scene/obj_mixed_rack",
            "path": "",
            "position": rack_position,
            "orientation": rack_orientation,
            "scale": [1.0, 1.0, 1.0],
            "add_colliders": False,
            "add_rigid_body": False,
            "is_articulation_part": False,
        },
    }
    episode_path = out / "tasks/scenario_forge/task11_r7/002/episode_metadata.json"
    episode_path.parent.mkdir(parents=True)
    episode_path.write_text(json.dumps(episode, indent=2, sort_keys=True) + "\n")
    manifest = {
        "schema_version": "scenario-forge-task11-r7-genmanip-validation/v1",
        "scenario_id": "scientific_workbench_centrifuge_unload_shutdown",
        "canonical_task": True,
        "runtime": "isaac_sim_4.1_genmanip_lift2",
        "source_scene": str(scene),
        "source_scene_sha256": _sha(scene),
        "scene_usd": str(scene_rel),
        "post_initialization_object_transform_writes_allowed": False,
        "direct_device_joint_target_writes_allowed": False,
        "claims": {
            "canonical_task11_scripted_oracle_success": False,
            "robot_policy_success": False,
            "benchmark_success": False,
        },
    }
    (out / "package_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r7", type=Path, default=DEFAULT_R7)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(build(args.r7, args.base, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

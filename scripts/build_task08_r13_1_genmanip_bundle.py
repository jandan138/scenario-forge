#!/usr/bin/env python3
"""Wrap Task08 r13 as a GenManip Lift2 robot-validation bundle."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Any

import yaml
from scripts.retained_build_inputs import input_path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_R13 = ROOT / "outputs/scientific_workbench_task08_vr_r13_20260901"
DEFAULT_BASE = input_path('robot_adapter_metadata')
DEFAULT_OUT = (
    ROOT
    / "outputs/scientific_workbench_task08_vr_r13_1_robot_20260902/"
    "adapters/ebench/genmanip"
)
TASK_NAME = "scenario_forge/task08_r13_1"
SCENE_REL = Path("assets/scene_usds/scenario_forge/task08_r13_1/scene.usda")
CONTROLLER_SOURCE = ROOT / "scripts/task08_assisted_thread_controller.py"
ASSISTED_R2 = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "scientific_workbench_task08_assisted_thread_r2_20260902"
)
OBJECT_PRIMS = (
    "obj_tube_rack",
    "obj_steel_plate",
    "obj_tube_00",
    "obj_tube_01",
    "obj_tube_02",
    "obj_cap_00",
    "obj_cap_01",
    "obj_cap_02",
    "obj_r9_clear_bottle",
    "obj_r9_tip_box",
    "obj_r9_wash_bottle",
    "obj_r9_pipette_carousel",
)
ROBOT_PATCH_TYPES = {
    "set_robot_physics_material",
    "set_robot_contact_offset",
    "set_robot_rest_offset",
}


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _source_pose(stage: Any, path: str) -> tuple[list[float], list[float]]:
    from pxr import UsdGeom

    matrix = UsdGeom.XformCache().GetLocalToWorldTransform(stage.GetPrimAtPath(path))
    point = matrix.ExtractTranslation()
    quat = matrix.ExtractRotationQuat()
    imag = quat.GetImaginary()
    return (
        [float(point[index]) for index in range(3)],
        [float(quat.GetReal()), float(imag[0]), float(imag[1]), float(imag[2])],
    )


def build(
    r13: Path = DEFAULT_R13,
    base: Path = DEFAULT_BASE,
    out: Path = DEFAULT_OUT,
) -> Path:
    from pxr import Sdf, Usd, UsdGeom, UsdPhysics
    from scripts.retained_build_inputs import verify_registered_input

    verify_registered_input(base)

    r13 = r13.resolve()
    base = base.resolve()
    out = out.resolve()
    if out.exists():
        raise FileExistsError(f"refusing to replace output: {out}")
    source_scene = r13 / "vr/scene.usd"
    stage_source = Usd.Stage.Open(str(source_scene))
    if not stage_source:
        raise RuntimeError(f"cannot open Task08 r13 scene: {source_scene}")
    staging = out.parent / f".{out.name}.staging"
    if staging.exists():
        shutil.rmtree(staging)
    try:
        copied_vr = staging / SCENE_REL.parent / "source_bundle/vr"
        shutil.copytree(
            r13 / "vr",
            copied_vr,
            ignore=shutil.ignore_patterns("evidence"),
        )
        for name, package_id in (
            ("tube", "tube15_long_neck_assisted_thread_body_r2"),
            ("cap", "tube15_long_neck_assisted_thread_cap_r2"),
        ):
            destination = copied_vr / "deps" / name
            shutil.rmtree(destination)
            shutil.copytree(ASSISTED_R2 / "packages" / package_id, destination)
        copied_scene = Usd.Stage.Open(str(copied_vr / "scene.usd"))
        controller = copied_scene.GetPrimAtPath(
            "/World/TaskRuntime/AssistedThreadGraph/Controller"
        )
        script = CONTROLLER_SOURCE.read_text()
        controller.GetAttribute("inputs:script").Set(script)
        controller.GetAttribute("runtime:inlineScriptSha256").Set(
            sha256(script.encode()).hexdigest()
        )
        copied_scene.GetRootLayer().Save()

        wrapper_path = staging / SCENE_REL
        wrapper_path.parent.mkdir(parents=True, exist_ok=True)
        wrapper = Usd.Stage.CreateNew(str(wrapper_path))
        UsdGeom.SetStageMetersPerUnit(wrapper, 1.0)
        UsdGeom.SetStageUpAxis(wrapper, UsdGeom.Tokens.z)
        world = UsdGeom.Xform.Define(wrapper, "/World").GetPrim()
        wrapper.SetDefaultPrim(world)
        nested = UsdGeom.Xform.Define(wrapper, "/World/_scene")
        nested.GetPrim().GetReferences().AddReference(
            "source_bundle/vr/scene.usd", "/World"
        )
        source_flat = copied_scene.Flatten(False)
        Sdf.CopySpec(
            source_flat,
            "/World/physicsScene",
            wrapper.GetRootLayer(),
            "/physicsScene",
        )
        wrapper.OverridePrim("/World/_scene/physicsScene").SetActive(False)
        table = UsdGeom.Xform.Define(wrapper, "/World/_scene/obj_table")
        table.GetPrim().GetReferences().AddReference(
            "source_bundle/vr/scene.usd", "/World/table"
        )
        wrapper.OverridePrim("/World/_scene/table").SetActive(False)
        wrapper.GetRootLayer().Save()

        config = yaml.safe_load((base / "config.yaml").read_text())
        evaluation = config["evaluation_configs"][0]
        evaluation.update(
            {
                "task_name": TASK_NAME,
                "usd_name": SCENE_REL.with_suffix("").as_posix(),
                "instruction": (
                    "左臂拿起红色管盖，右臂拿起中间15 mL离心管；"
                    "完成对准、套合和累计一圈旋紧，最后将离心管放回原孔位。"
                ),
                "num_steps": 7200,
                "physics_dt": 1 / 120,
                "rendering_dt": 1 / 60,
            }
        )
        evaluation["robots"] = [
            {
                "type": "manip/lift2/R5a",
                "position": [0.0, -1.02, 0.31],
                "orientation": [0.7071067812, 0.0, 0.0, 0.7071067812],
            }
        ]
        camera_rel = Path("cameras/fixed_camera_lift2.yml")
        (staging / camera_rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(base / camera_rel, staging / camera_rel)
        evaluation["domain_randomization"]["cameras"]["config_path"] = str(
            camera_rel
        )
        evaluation["generation_config"]["goal"] = []
        evaluation["generation_config"]["articulation"] = {}
        evaluation["preprocess_config"] = [
            item
            for item in evaluation.get("preprocess_config", [])
            if item.get("type") not in ROBOT_PATCH_TYPES
        ]
        evaluation["object_config"] = {
            name.removeprefix("obj_"): {
                "type": "existed_object",
                "uid_list": [name.removeprefix("obj_")],
            }
            for name in OBJECT_PRIMS
        }
        (staging / "config.yaml").write_text(
            yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
        )

        source_episode = next(
            base.glob("tasks/scenario_forge/*/002/episode_metadata.json")
        )
        episode = json.loads(source_episode.read_text())
        episode["task_data"]["goal"] = []
        base_layout = episode["task_data"]["initial_layout"]
        layout = {
            "00000000000000000000000000000000": base_layout[
                "00000000000000000000000000000000"
            ],
            "lift2": base_layout["lift2"],
        }
        for prim_name in OBJECT_PRIMS:
            uid = prim_name.removeprefix("obj_")
            prim_path = f"/World/{prim_name}"
            position, orientation = _source_pose(stage_source, prim_path)
            rigid = stage_source.GetPrimAtPath(prim_path).HasAPI(
                UsdPhysics.RigidBodyAPI
            )
            layout[uid] = {
                "type": "rigid" if rigid else "object",
                "prim_path": f"/World/_scene/{prim_name}",
                "path": "",
                "position": position,
                "orientation": orientation,
                "scale": [1.0, 1.0, 1.0],
                "add_colliders": False,
                "add_rigid_body": False,
                "is_articulation_part": False,
            }
        episode["task_data"]["initial_layout"] = layout
        episode["task_data"]["scenario_forge_runtime_contract"] = {
            "task_id": "scientific_workbench_tighten_centrifuge_tube_cap",
            "target_tube": "tube_01",
            "target_cap": "cap_01",
            "twist_segments_degrees": [118.0, 118.0, "until_closed"],
            "embedded_assistance": True,
            "external_object_transform_writes_allowed": False,
        }
        episode_path = (
            staging
            / "tasks/scenario_forge/task08_r13_1/008/episode_metadata.json"
        )
        _write_json(episode_path, episode)
        manifest = {
            "schema_version": "scenario-forge.task08-r13.1-genmanip-validation/v1",
            "scenario_id": "scientific_workbench_tighten_centrifuge_tube_cap",
            "runtime": "isaac_sim_4.1_genmanip_lift2",
            "source_scene": str(source_scene),
            "source_scene_sha256": _sha(source_scene),
            "scene_usd": SCENE_REL.as_posix(),
            "controller_source_sha256": _sha(CONTROLLER_SOURCE),
            "assisted_asset_set": str(ASSISTED_R2),
            "robot_protocol": {
                "cap_arm": "left",
                "tube_arm": "right",
                "twist_segments_degrees": [118.0, 118.0, "until_closed"],
                "post_initialization_external_object_transform_writes": 0,
            },
            "claims": {
                "core_robot_assisted_thread_success": False,
                "task08_scripted_oracle_success": False,
                "robot_policy_success": False,
                "benchmark_success": False,
            },
        }
        _write_json(staging / "package_manifest.json", manifest)
        staging.rename(out)
        return out
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r13", type=Path, default=DEFAULT_R13)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(build(args.r13, args.base, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

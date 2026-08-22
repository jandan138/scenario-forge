#!/usr/bin/env python3
"""Build non-canonical GenManip bundles for LABSPIN X8 robot-contact QA."""

from __future__ import annotations

import argparse
import copy
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Any

import yaml


CENTRIFUGE_PRIM = "/World/_scene/obj_obj_centrifuge"
TUBE_PRIM = "/World/_scene/obj_obj_centrifuge_tube"
MACHINE_POSITION = [0.0, 0.0, 0.755]
TUBE_PLACEHOLDER_POSITION = [0.30, -0.18, 0.95]


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _mapping(path: Path) -> dict[str, Any]:
    if path.suffix == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
    else:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"mapping required: {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _base_scene(base_package: Path, evaluation: dict[str, Any]) -> Path:
    relative = Path(f"{evaluation['usd_name']}.usda")
    if len(relative.parts) >= 3 and relative.parts[0] == "collected_packages":
        relative = Path(*relative.parts[2:])
    return (base_package / relative).resolve()


def _build_scene(
    *,
    base_scene: Path,
    centrifuge_asset: Path,
    tube_asset: Path,
    tube_entry_prim: str,
    destination: Path,
) -> None:
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics

    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(destination))
    stage.GetRootLayer().subLayerPaths = [str(base_scene)]
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    for old in (
        "/World/_scene/obj_obj_graduated_cylinder",
        "/World/_scene/obj_obj_beaker",
    ):
        stage.OverridePrim(old).SetActive(False)

    centrifuge = UsdGeom.Xform.Define(stage, CENTRIFUGE_PRIM)
    centrifuge.GetPrim().GetReferences().AddReference(
        str(centrifuge_asset), Sdf.Path("/World/Centrifuge")
    )
    centrifuge.AddTranslateOp().Set(Gf.Vec3d(*MACHINE_POSITION))

    tube = UsdGeom.Xform.Define(stage, TUBE_PRIM)
    tube.GetPrim().GetReferences().AddReference(
        str(tube_asset), Sdf.Path(tube_entry_prim)
    )
    tube.AddTranslateOp().Set(Gf.Vec3d(*TUBE_PLACEHOLDER_POSITION))
    UsdPhysics.RigidBodyAPI(tube.GetPrim()).CreateKinematicEnabledAttr(True)
    stage.GetRootLayer().Save()


def build_validation_bundle(
    *,
    base_package: Path,
    centrifuge_package: Path,
    tube_package: Path,
    tube_entry_prim: str,
    tube_label: str,
    out: Path,
) -> dict[str, Path]:
    base_package = base_package.resolve()
    centrifuge_package = centrifuge_package.resolve()
    tube_package = tube_package.resolve()
    out = out.resolve()
    scenario_id = f"labspin_x8_robot_contact_{tube_label}"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    base_config = _mapping(base_package / "config.yaml")
    evaluation = copy.deepcopy(base_config["evaluation_configs"][0])
    source_scene = _base_scene(base_package, evaluation)
    scene_rel = Path(
        f"assets/scene_usds/scenario_forge/{scenario_id}/scene.usda"
    )
    scene_usd = out / scene_rel
    _build_scene(
        base_scene=source_scene,
        centrifuge_asset=centrifuge_package / "asset.usd",
        tube_asset=tube_package / "asset.usd",
        tube_entry_prim=tube_entry_prim,
        destination=scene_usd,
    )

    camera_source = base_package / "cameras/fixed_camera_lift2.yml"
    camera_rel = Path("cameras/fixed_camera_lift2.yml")
    (out / camera_rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(camera_source, out / camera_rel)

    evaluation["task_name"] = f"scenario_forge/{scenario_id}"
    evaluation["usd_name"] = scene_rel.with_suffix("").as_posix()
    evaluation["instruction"] = (
        "Lift2 辅助臂真实接触打开离心机盖，操作臂保持闭合15 mL离心管并沿目标孔位插入。"
    )
    evaluation["domain_randomization"]["cameras"]["config_path"] = (
        camera_rel.as_posix()
    )
    evaluation["object_config"].pop("obj_graduated_cylinder", None)
    evaluation["object_config"].pop("obj_beaker", None)
    evaluation["object_config"].update(
        {
            "obj_centrifuge": {
                "type": "existed_object",
                "uid_list": ["obj_centrifuge"],
                "is_articulated": True,
                "target_positions": [0.0] * 5,
                "articulation_info": {
                    "is_articulated": True,
                    "part": {},
                },
            },
            "obj_centrifuge_tube": {
                "type": "existed_object",
                "uid_list": ["obj_centrifuge_tube"],
            },
        }
    )
    evaluation["generation_config"]["goal"] = []
    evaluation["generation_config"]["articulation"] = {
        "obj_centrifuge": {
            "is_articulated": True,
            "target_positions": [0.0] * 5,
        }
    }
    config = out / "config.yaml"
    config.write_text(
        yaml.safe_dump(
            {"demonstration_configs": [], "evaluation_configs": [evaluation]},
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    episode_source = next(
        base_package.glob("tasks/scenario_forge/*/002/episode_metadata.json")
    )
    episode_payload = _mapping(episode_source)
    layout = episode_payload["task_data"]["initial_layout"]
    for info in layout.values():
        raw_path = info.get("path") if isinstance(info, dict) else None
        if not raw_path or Path(raw_path).is_absolute():
            continue
        relative = Path(raw_path)
        if len(relative.parts) >= 3 and relative.parts[0] == "collected_packages":
            relative = Path(*relative.parts[2:])
        info["path"] = str((base_package / relative).resolve())
    layout.pop("obj_graduated_cylinder", None)
    layout.pop("obj_beaker", None)
    layout.update(
        {
            "obj_centrifuge": {
                "type": "articulation",
                "prim_path": CENTRIFUGE_PRIM,
                "position": MACHINE_POSITION,
                "orientation": [1.0, 0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "joint_positions": [0.0] * 5,
            },
            "obj_centrifuge_tube": {
                "type": "rigid",
                "prim_path": TUBE_PRIM,
                "path": "",
                "position": TUBE_PLACEHOLDER_POSITION,
                "orientation": [1.0, 0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "add_colliders": False,
                "add_rigid_body": False,
                "is_articulation_part": False,
            },
        }
    )
    episode_payload["task_data"]["goal"] = []
    episode = (
        out
        / f"tasks/scenario_forge/{scenario_id}/002/episode_metadata.json"
    )
    _write_json(episode, episode_payload)

    manifest = out / "package_manifest.json"
    _write_json(
        manifest,
        {
            "schema_version": "scenario-forge-labspin-x8-robot-validation/v0.1",
            "scenario_id": scenario_id,
            "status": "robot_validation_candidate",
            "canonical_task": False,
            "runtime": "isaac_sim_4.1_genmanip_lift2",
            "scene_usd": scene_rel.as_posix(),
            "source_assets": {
                "base_scene": str(source_scene),
                "base_scene_sha256": _sha(source_scene),
                "centrifuge_package": str(centrifuge_package),
                "centrifuge_asset_usd_sha256": _sha(
                    centrifuge_package / "asset.usd"
                ),
                "tube_package": str(tube_package),
                "tube_asset_usd_sha256": _sha(tube_package / "asset.usd"),
                "tube_entry_prim": tube_entry_prim,
            },
            "placements": {
                "obj_centrifuge": MACHINE_POSITION,
                "obj_centrifuge_tube": TUBE_PLACEHOLDER_POSITION,
            },
            "claims": {
                "robot_contact_success": False,
                "canonical_task_10_success": False,
                "benchmark_success": False,
            },
        },
    )
    return {
        "root": out,
        "scene_usd": scene_usd,
        "config": config,
        "episode": episode,
        "manifest": manifest,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-package", type=Path, required=True)
    parser.add_argument("--centrifuge-package", type=Path, required=True)
    parser.add_argument("--tube-package", type=Path, required=True)
    parser.add_argument("--tube-entry-prim", required=True)
    parser.add_argument("--tube-label", required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = build_validation_bundle(
        base_package=args.base_package,
        centrifuge_package=args.centrifuge_package,
        tube_package=args.tube_package,
        tube_entry_prim=args.tube_entry_prim,
        tube_label=args.tube_label,
        out=args.out,
    )
    print(json.dumps({key: str(value) for key, value in result.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

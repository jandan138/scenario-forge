#!/usr/bin/env python3
"""Generate the first formal VR package for traditional acid-base titration."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from scenario_forge.adapters.vr_object_materialization import (  # noqa: E402
    materialize_vr_object_subtrees,
)


TASK_ID = "scientific_workbench_traditional_acid_base_titration_vr_r1"
HANDOFF_ID = TASK_ID
DEFAULT_BASE = (
    ROOT / "outputs/scientific_workbench_task09_r16_20260904/handoff/"
    "scientific_workbench_task09_r16_vr"
)
DEFAULT_STATION = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/traditional_titration_assets_r1_20260904"
)
DEFAULT_STIRRER = (
    ROOT / "outputs/scientific_workbench_insert_stir_bar_into_beaker_vr_r3_20260824/"
    "vr/deps/objects/obj_magnetic_stirrer"
)
DEFAULT_FLASK = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "scientific_workbench_conical_flask_90x35_glass_warp_20260821/package"
)
DEFAULT_OUTPUT = (
    ROOT / "outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_20260904/handoff"
)

STATION_XYZ = (-0.25, 0.03, 0.755)
STIRRER_XYZ = (-0.03, 0.03, 0.755)
FLASK_XYZ = (-0.03, 0.03, 0.8267)


@dataclass(frozen=True)
class TitrationVRResult:
    root: Path
    scene: Path
    task: Path
    metrics: Path
    config: Path
    manifest: Path
    archive: Path


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _local_group(names: list[str]) -> dict[str, object]:
    return {
        "objs": names,
        "mode": "local",
        "yaw_range_degrees": [0.0, 0.0],
        "x_offset_range": [-0.01, 0.01],
        "y_offset_range": [-0.01, 0.01],
    }


def _author_visual_receiver(stage: object) -> list[str]:
    from pxr import Gf, Sdf, UsdGeom

    liquid_root = UsdGeom.Xform.Define(stage, "/World/obj_receiver_flask/VisualLiquid").GetPrim()
    liquid_root.SetCustomDataByKey("scenario_forge:visualOnly", True)
    phases = (
        ("colorless", (0.92, 0.97, 1.0), 0.25),
        ("transition", (1.0, 0.75, 0.82), 0.50),
        ("endpoint_pale_pink", (1.0, 0.55, 0.70), 0.62),
        ("overshoot", (0.75, 0.05, 0.20), 0.82),
    )
    visual_paths = []
    for index, (phase, color, opacity) in enumerate(phases):
        suffix = "".join(part.title() for part in phase.split("_"))
        liquid = UsdGeom.Cylinder.Define(
            stage, f"/World/obj_receiver_flask/VisualLiquid/Solution{suffix}"
        )
        liquid.CreateAxisAttr("Z")
        liquid.CreateRadiusAttr(0.031)
        liquid.CreateHeightAttr(0.055)
        liquid.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, 0.061))
        liquid.CreateDisplayColorAttr([Gf.Vec3f(*color)])
        liquid.CreateDisplayOpacityAttr([opacity])
        liquid.GetPrim().CreateAttribute(
            "titration:phase", Sdf.ValueTypeNames.Token, custom=True
        ).Set(phase)
        liquid.CreateVisibilityAttr("inherited" if index == 0 else "invisible")
        meniscus = UsdGeom.Cylinder.Define(stage, str(liquid.GetPath()) + "/Meniscus")
        meniscus.CreateAxisAttr("Z")
        meniscus.CreateRadiusAttr(0.0305)
        meniscus.CreateHeightAttr(0.001)
        meniscus.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, 0.028))
        meniscus.CreateDisplayColorAttr([Gf.Vec3f(*color)])
        meniscus.CreateDisplayOpacityAttr([opacity])
        visual_paths.append(str(liquid.GetPath()))

    stir_bar = UsdGeom.Xform.Define(stage, "/World/obj_receiver_flask/VisualLiquid/StirBar")
    stir_bar.GetPrim().SetCustomDataByKey("scenario_forge:visualOnly", True)
    stir_bar.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, 0.044))
    rotate = stir_bar.AddRotateZOp()
    for frame in range(0, 3601, 15):
        rotate.Set(float(frame) * 2.0, frame)
    capsule = UsdGeom.Capsule.Define(stage, "/World/obj_receiver_flask/VisualLiquid/StirBar/Visual")
    capsule.CreateAxisAttr("Z")
    capsule.CreateRadiusAttr(0.003)
    capsule.CreateHeightAttr(0.026)
    capsule.AddRotateYOp().Set(90.0)
    capsule.CreateDisplayColorAttr([Gf.Vec3f(0.94, 0.94, 0.92)])
    return visual_paths


def _write_task_files(root: Path, station_links: list[str]) -> tuple[Path, Path, Path]:
    task = root / "task.yaml"
    task.write_text(
        """schema_version: scenario-forge-task/v0.1
task_id: scientific_workbench_traditional_acid_base_titration_vr_r1
title: 传统酸碱滴定：无色至淡粉终点
mode: single_arm
operating_arm: left
auxiliary_arm: idle
instruction: >-
  使用左臂转动滴定管旋塞，先粗滴、再细调、最后逐滴；当锥形瓶溶液呈稳定淡粉色时关闭旋塞并保持 3 秒，然后释放旋塞。
chemistry_semantics:
  burette: colorless_sodium_hydroxide_visual_model
  receiver: colorless_acid_with_phenolphthalein_visual_model
  true_chemistry_simulation: false
state_contract:
  required_sequence: [OPEN, FINE, DRIP, CLOSED]
  target_volume_ml: 15.0
  success_window_ml: [14.7, 15.3]
  closed_endpoint_hold_seconds: 3.0
  overshoot_continues_episode: true
  overshoot_can_succeed: false
  flow_bands:
    CLOSED: {angle_deg: [0.0, 5.0], rate_ml_s: 0.0}
    DRIP: {angle_deg: [5.0, 15.0], rate_ml_s: 0.05}
    FINE: {angle_deg: [15.0, 40.0], rate_ml_s: 0.4}
    OPEN: {angle_deg: [40.0, 90.0], rate_ml_s: 2.0}
failure_contract:
  persistent_glass_tube_contact: hard_failure
  one_frame_light_stand_or_clamp_touch: tolerated
  persistent_stand_contact_or_displacement: failure
  glass_interpenetration: failure
""",
        encoding="utf-8",
    )
    metrics = root / "metrics.yaml"
    metrics.write_text(
        """schema_version: scenario-forge-metrics/v0.1
task_id: scientific_workbench_traditional_acid_base_titration_vr_r1
score_ceiling: 1.0
metrics:
  - {id: stopcock_grasp, weight: 0.15}
  - {id: coarse_open_phase, weight: 0.20}
  - {id: fine_phase, weight: 0.20}
  - {id: endpoint_volume, weight: 0.25, range_ml: [14.7, 15.3]}
  - {id: closed_pale_pink_hold, weight: 0.15, hold_seconds: 3.0}
  - {id: stopcock_release, weight: 0.05}
hard_requirements:
  ordered_valve_sequence: [OPEN, FINE, DRIP, CLOSED]
  overshoot_failure_threshold_ml: 15.3
""",
        encoding="utf-8",
    )
    obj_paths = [
        "/World/_scene/obj_titration_station",
        *[f"/World/_scene/obj_titration_station/{path}" for path in station_links],
        "/World/_scene/obj_magnetic_stirrer",
        "/World/_scene/obj_receiver_flask",
        "/World/_scene/obj_sample_beaker",
        "/World/_scene/obj_context_conical_flask",
    ]
    config_payload = {
        "scene_usd_file_path": {"scene1": "__SCENE_PATH__"},
        "obj_prim_list": obj_paths,
        "layout_randomization": {
            "table": "table",
            "objects": [
                _local_group(
                    [
                        "obj_titration_station",
                        "obj_magnetic_stirrer",
                        "obj_receiver_flask",
                    ]
                ),
                _local_group(["obj_sample_beaker"]),
                _local_group(["obj_context_conical_flask"]),
            ],
        },
        "robot_cfg": {
            "position": [0.0, -1.02, 0.31],
            "orientation": [0.7071067812, 0.0, 0.0, 0.7071067812],
        },
        "titration_contract": {
            "station_root": "/World/_scene/obj_titration_station",
            "stopcock_joint": (
                "/World/_scene/obj_titration_station/Instance/Burette/stopcock_joint"
            ),
            "success_window_ml": [14.7, 15.3],
            "hold_seconds": 3.0,
            "required_sequence": ["OPEN", "FINE", "DRIP", "CLOSED"],
            "true_chemistry_simulation": False,
        },
    }
    body = repr(config_payload).replace("'__SCENE_PATH__'", "str(_ASSETS_DIR / 'scene.usd')")
    config = root / "task_config.py"
    config.write_text(
        "from pathlib import Path\n"
        "_ASSETS_DIR = Path(__file__).resolve().parent\n"
        f"TASKS = {{{TASK_ID!r}: {body}}}\n",
        encoding="utf-8",
    )
    return task, metrics, config


def build(
    output: Path = DEFAULT_OUTPUT,
    *,
    base: Path = DEFAULT_BASE,
    station: Path = DEFAULT_STATION,
    stirrer: Path = DEFAULT_STIRRER,
    flask: Path = DEFAULT_FLASK,
) -> TitrationVRResult:
    from pxr import Gf, Usd, UsdGeom, UsdPhysics

    output = output.resolve()
    root = output / HANDOFF_ID
    if output.exists():
        raise FileExistsError(f"refusing to replace output: {output}")
    receipt = json.loads((station / "promotion_receipt.json").read_text())
    if receipt.get("status") != "promoted":
        raise ValueError("traditional titration station package is not promoted")

    shutil.copytree(base, root)
    evidence = root / "evidence"
    if evidence.exists():
        shutil.rmtree(evidence)
    evidence.mkdir()
    shutil.copytree(station, root / "deps/titration_assets")
    shutil.copytree(stirrer, root / "deps/magnetic_stirrer")
    shutil.copytree(flask, root / "deps/receiver_flask")

    scene = root / "scene.usd"
    stage = Usd.Stage.Open(str(scene))
    for path in ("/World/obj_oven", "/World/obj_oven_cart"):
        stage.RemovePrim(path)
    stage.GetRootLayer().Save()
    for name in ("oven", "oven_cart"):
        dependency = root / "deps" / name
        if dependency.exists():
            shutil.rmtree(dependency)
    stage.GetPrimAtPath("/World/obj_sample_beaker").GetAttribute("xformOp:translate").Set(
        Gf.Vec3d(0.64, 0.23, 0.755)
    )
    stage.GetPrimAtPath("/World/obj_context_conical_flask").GetAttribute("xformOp:translate").Set(
        Gf.Vec3d(0.43, 0.22, 0.755)
    )

    references = (
        (
            "/World/obj_titration_station",
            "deps/titration_assets/packages/station/asset.usd",
            "/World/TitrationStation",
            STATION_XYZ,
        ),
        (
            "/World/obj_magnetic_stirrer",
            "deps/magnetic_stirrer/asset.usd",
            "/World/MagneticStirrer",
            STIRRER_XYZ,
        ),
        (
            "/World/obj_receiver_flask",
            "deps/receiver_flask/asset.usd",
            "/World/ConicalFlask90x35Warp",
            FLASK_XYZ,
        ),
    )
    for path, asset, entry, xyz in references:
        xform = UsdGeom.Xform.Define(stage, path)
        xform.GetPrim().GetReferences().AddReference(asset, entry)
        translate = xform.GetPrim().GetAttribute("xformOp:translate")
        if not translate:
            translate = xform.AddTranslateOp().GetAttr()
        translate.Set(Gf.Vec3d(*xyz))
    stage.GetRootLayer().Save()
    stage = None

    object_paths = [item[0] for item in references]
    materialize_vr_object_subtrees(
        scene_path=scene,
        scene_prim_paths=object_paths,
        runtime_prim_paths=[path.replace("/World/", "/World/_scene/") for path in object_paths],
        evidence_path=evidence / "vr_object_materialization.json",
    )

    stage = Usd.Stage.Open(str(scene))
    visual_paths = _author_visual_receiver(stage)
    station_root = stage.GetPrimAtPath("/World/obj_titration_station")
    station_root.GetRelationship("titration:receiverLiquidVisuals").SetTargets(visual_paths)
    station_root.GetAttribute("titration:target_container_inside").Set(True)
    stage.SetStartTimeCode(0.0)
    stage.SetEndTimeCode(3600.0)
    stage.SetTimeCodesPerSecond(60.0)
    stage.SetFramesPerSecond(60.0)
    stage.GetRootLayer().Save()

    station_links = []
    for prim in Usd.PrimRange(station_root):
        if prim == station_root:
            continue
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            station_links.append(str(prim.GetPath())[len(str(station_root.GetPath())) + 1 :])
    task, metrics, config = _write_task_files(root, station_links)

    manifest = {
        "schema_version": "scenario-forge-traditional-titration-vr/v0.1",
        "package_id": HANDOFF_ID,
        "status": "layout_ready_static_validation_pending",
        "runtime": "Isaac Sim 4.5",
        "entrypoints": {
            "scene": "scene.usd",
            "task": "task.yaml",
            "metrics": "metrics.yaml",
            "vr_config": "task_config.py",
        },
        "assets": {
            "titration_station_receipt_sha256": _sha(station / "promotion_receipt.json"),
            "background": "scientific_environment_code_room_wet_chemistry_v2",
            "table": "scientific_workbench_standard_2000x800x755_gray",
            "receiver": "conical_flask_90x35_dynamic_sdf",
            "stirrer": "magnetic_stirrer_admitted",
        },
        "layout": {
            "station_xyz_m": list(STATION_XYZ),
            "stirrer_xyz_m": list(STIRRER_XYZ),
            "receiver_flask_xyz_m": list(FLASK_XYZ),
            "task_group_local_randomization_m": [-0.01, 0.01],
            "tabletop_context": [
                "obj_sample_beaker",
                "obj_context_conical_flask",
            ],
        },
        "claims": {
            "asset_functionality": True,
            "scene_static_validation": False,
            "visual_endpoint_state_machine": True,
            "falling_liquid_rendered": False,
            "pbd_liquid": False,
            "true_chemistry_simulation": False,
            "robot_policy_success": False,
            "benchmark_success": False,
        },
    }
    manifest_path = root / "manifest.json"
    _write_json(manifest_path, manifest)
    (root / "README_CN.md").write_text(
        "# 传统酸碱滴定 VR r1\n\n"
        "用 Isaac Sim 4.5 打开 `scene.usd`。场景不内嵌机器人；VR 运行时按 "
        "`task_config.py` 插入 Lift2。首次运行 ScriptNode 时选择 Yes。\n\n"
        "本包用状态机驱动滴定管液柱和锥形瓶颜色，不渲染下落液滴，也不模拟真实化学反应。"
        "旋塞必须依次经过 OPEN → FINE → DRIP → CLOSED，并在 14.7–15.3 mL 淡粉区间"
        "关闭保持 3 秒。超过 15.3 mL 后仍可继续操作，但最终不可成功。\n",
        encoding="utf-8",
    )
    archive = output / f"{HANDOFF_ID}.zip"
    shutil.make_archive(str(archive.with_suffix("")), "zip", root_dir=output, base_dir=HANDOFF_ID)
    return TitrationVRResult(root, scene, task, metrics, config, manifest_path, archive)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    print(build(args.output).archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

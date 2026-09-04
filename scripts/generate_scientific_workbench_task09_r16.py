#!/usr/bin/env python3
"""Generate Task 09 r16 with the fixed-base articulation oven."""

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
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scenario_forge.validation.articulated_instance_layout import (  # noqa: E402
    validate_fixed_base_articulation_layout,
)


R15_ROOT = (
    ROOT / "outputs/scientific_workbench_task09_r15_20260901/handoff/"
    "scientific_workbench_task09_r15_vr"
)
OVEN_R16 = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "ika_oven_125_task09_r16_fixed_articulation_20260904"
)
DEFAULT_OUTPUT = ROOT / "outputs/scientific_workbench_task09_r16_20260904/handoff"
HANDOFF_ID = "scientific_workbench_task09_r16_vr"


@dataclass(frozen=True)
class Task09R16Result:
    root: Path
    archive: Path
    manifest: Path


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def build_handoff(output: Path = DEFAULT_OUTPUT) -> Task09R16Result:
    from pxr import Gf, Sdf, Usd

    output = output.resolve()
    root = output / HANDOFF_ID
    if output.exists():
        raise FileExistsError(f"refusing to replace output: {output}")
    receipt = OVEN_R16 / "promotion_receipt.json"
    if json.loads(receipt.read_text()).get("status") != "promoted":
        raise ValueError("ConvertAsset r16 fixed-base oven is not promoted")

    shutil.copytree(R15_ROOT, root)
    shutil.rmtree(root / "evidence")
    shutil.rmtree(root / "deps/oven")
    shutil.copytree(OVEN_R16, root / "deps/oven")

    scene = root / "scene.usd"
    stage = Usd.Stage.Open(str(scene))
    target_layer = stage.GetRootLayer()
    stage.RemovePrim("/World/obj_oven")
    target_layer.Save()
    source = Usd.Stage.Open(str(OVEN_R16 / "package/asset.usd"))
    Sdf.CopySpec(
        source.GetRootLayer(),
        "/World/obj_oven",
        target_layer,
        "/World/obj_oven",
    )
    target_layer.Save()

    stage = Usd.Stage.Open(str(scene))
    cart = stage.GetPrimAtPath("/World/obj_oven_cart")
    cart.GetAttribute("xformOp:scale").Set(Gf.Vec3d(1.0, 1.0, 0.7))
    cart.SetCustomDataByKey("scenario_forge:guiTrsEditable", True)
    cart.SetCustomDataByKey("scenario_forge:heightScale", 0.7)
    cart.SetCustomDataByKey("scenario_forge:scalePolicy", "fixed_xy_z_height_only")
    oven = stage.GetPrimAtPath("/World/obj_oven")
    oven.GetAttribute("xformOp:translate").Set(Gf.Vec3d(1.51, 0.0, 0.5285))
    oven.GetAttribute("xformOp:scale").Set(Gf.Vec3d(1.0, 1.0, 1.0))
    oven.SetCustomDataByKey("scenario_forge:guiTrsEditable", True)
    oven.SetCustomDataByKey(
        "scenario_forge:pairedAlignmentRule",
        "same_xy_delta; oven_z=cart_z+0.755*cart_scale_z; oven_scale=1",
    )
    control = stage.GetPrimAtPath("/World/obj_oven/Instance/ControlPanel")
    for name, value in {
        "oven:mainsPower": True,
        "oven:heatingEnabled": False,
        "oven:heaterActive": False,
        "oven:temperatureSetpointC": 60.0,
        "oven:operatingState": "idle",
        "ui:page": "home",
        "ui:selectedField": "home",
    }.items():
        control.GetAttribute(name).Set(value)
    stage.GetPrimAtPath("/World/obj_oven/Instance/Joints/MainsRocker").GetAttribute(
        "drive:angular:physics:targetPosition"
    ).Set(8.0)
    stage.GetRootLayer().Save()

    layout = validate_fixed_base_articulation_layout(scene, ["/World/obj_oven"])
    evidence = root / "evidence"
    evidence.mkdir()
    layout_path = evidence / "articulated_instance_layout_v2.json"
    layout_path.write_text(json.dumps(layout, indent=2, sort_keys=True) + "\n")

    config = root / "task_config.py"
    config.write_text(
        config.read_text()
        .replace("scientific_workbench_task09_r15", "scientific_workbench_task09_r16")
        .replace("scientific_workbench_task09_r15_vr", HANDOFF_ID)
    )
    (root / "task_r15.json").unlink()
    controls = {
        "schema_version": "scenario-forge-task09-r16-controls/v0.1",
        "temperature_control": "obj_oven.Instance.ControlPanel.AuxControlKnob",
        "start_control": "obj_oven.Instance.ControlPanel.AuxControlKnob",
        "alternate_control": "obj_oven.Instance.ControlPanel.ControlKnob",
        "door_joint": "obj_oven.Instance.Joints.DoorHinge",
        "articulation_root": "obj_oven",
        "instance_prim": "obj_oven.Instance",
        "base_link": "obj_oven.Instance.Body",
        "base_fixed_joint": "obj_oven.Instance.Joints.BaseFixed",
        "shared_logical_state": True,
        "mechanically_synchronized": False,
        "uniform_scale_range": [0.85, 1.15],
        "scale_policy": "uniform_xyz_only_on_obj_root",
        "cart_scale_xyz": [1.0, 1.0, 0.7],
        "oven_xyz_m": [1.51, 0.0, 0.5285],
    }
    (root / "task_r16.json").write_text(json.dumps(controls, indent=2, sort_keys=True) + "\n")
    readme = root / "README_CN.md"
    readme.write_text(
        readme.read_text()
        + "\n## r16 fixed-base articulation\n\n"
        + "烘箱根 `/World/obj_oven` 是启用的 Articulation Root；全部 link 保持原路径并位于 "
        + "identity `Xform /World/obj_oven/Instance` 下。机身不再是 kinematic，新增 "
        + "`Instance/Joints/BaseFixed` 将机身固定到设备根。设备架高度缩放为 0.7，烘箱底面 "
        + "同步降至 0.5285 m。只在 `obj_oven` 根调整设备 Transform。\n"
    )

    manifest = json.loads((root / "manifest.json").read_text())
    manifest["schema_version"] = "scenario-forge-task09-r16-vr/v0.1"
    manifest["status"] = "static_built_runtime_pending"
    manifest["source_evidence"]["oven_receipt"] = "deps/oven/promotion_receipt.json"
    manifest["source_evidence"]["oven_receipt_sha256"] = _sha(receipt)
    manifest["claims"].pop("articulated_instance_layout_v1", None)
    manifest["claims"].pop("instance_scope_not_xform", None)
    manifest["claims"].update(
        {
            "articulated_instance_layout_v2": True,
            "fixed_base_articulation": True,
            "instance_identity_xform": True,
            "all_links_nonkinematic": True,
            "cart_height_scale": 0.7,
            "robot_policy_success": False,
            "benchmark_success": False,
        }
    )
    manifest.pop("runtime_evidence", None)
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    archive = output / f"{HANDOFF_ID}.zip"
    shutil.make_archive(str(archive.with_suffix("")), "zip", root_dir=output, base_dir=HANDOFF_ID)
    return Task09R16Result(root, archive, manifest_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    print(build_handoff(args.output).archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

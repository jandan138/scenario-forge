#!/usr/bin/env python3
"""Generate Task 09 r14 from the qualified dual-knob materialized oven."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import sys
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pxr import Gf, Usd, UsdGeom  # noqa: E402

import scripts.generate_scientific_workbench_task09_r13 as r13  # noqa: E402


DEFAULT_OUTPUT = REPO_ROOT / "outputs/scientific_workbench_task09_r14_20260831/handoff"
HANDOFF_ID = "scientific_workbench_task09_r14_vr"
OVEN_OUTPUT = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "ika_oven_125_task09_r14_dual_knob_20260831"
)


@dataclass(frozen=True)
class Task09R14Handoff:
    root: Path
    archive: Path
    manifest: Path


def _configure_r13_base() -> None:
    r13.HANDOFF_ID = HANDOFF_ID
    r13.OVEN_OUTPUT = OVEN_OUTPUT


def _ensure_full_trs(prim) -> None:
    xformable = UsdGeom.Xformable(prim)
    translate = prim.GetAttribute("xformOp:translate").Get()
    xformable.ClearXformOpOrder()
    xformable.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble).Set(
        Gf.Vec3d(translate)
    )
    xformable.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(1.0))
    xformable.AddScaleOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(1.0))


def _upgrade(root: Path) -> None:
    scene = root / "scene.usd"
    stage = Usd.Stage.Open(str(scene))
    if stage is None:
        raise RuntimeError("cannot open Task09 r14 scene")
    for path in ("/World/obj_oven", "/World/obj_oven_cart"):
        prim = stage.GetPrimAtPath(path)
        _ensure_full_trs(prim)
        prim.SetCustomDataByKey("scenario_forge:guiTrsEditable", True)
        prim.SetCustomDataByKey("scenario_forge:uniformScaleMin", 0.85)
        prim.SetCustomDataByKey("scenario_forge:uniformScaleMax", 1.15)
    oven = stage.GetPrimAtPath("/World/obj_oven")
    oven.SetCustomDataByKey(
        "scenario_forge:pairedAlignmentRule",
        "same_uniform_scale; oven_z=cart_z+0.755*scale",
    )
    stage.GetRootLayer().Save()

    config = root / "task_config.py"
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            "scientific_workbench_task09_r13", "scientific_workbench_task09_r14"
        ),
        encoding="utf-8",
    )
    task = {
        "schema_version": "scenario-forge-task09-r14-controls/v0.1",
        "temperature_control": "obj_oven.ControlPanel.AuxControlKnob",
        "start_control": "obj_oven.ControlPanel.AuxControlKnob",
        "alternate_control": "obj_oven.ControlPanel.ControlKnob",
        "shared_logical_state": True,
        "mechanically_synchronized": False,
        "uniform_scale_range": [0.85, 1.15],
        "scale_policy": "uniform_xyz_only",
        "alignment_formula": "oven_z = cart_z + 0.755 * uniform_scale",
    }
    (root / "task_r14.json").write_text(
        json.dumps(task, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    readme = root / "README_CN.md"
    readme.write_text(
        readme.read_text(encoding="utf-8")
        + """

## r14 双旋钮与 GUI 调节

- 默认使用电源拨杆与显示面板之间的左侧 `AuxControlKnob`；原右侧旋钮仍可独立旋转和按压，两者共享温度与加热状态。
- 门阻尼：选择 `/World/obj_oven/Joints/DoorHinge`，Property → Physics → Drive → Angular → Damping，正式值 `Damping = 9.0`。
- 门限位：同一 prim 的 Physics → Revolute Joint → Upper Limit，正式值 `Upper Limit = 60°`。
- 烘箱和架子根节点都提供完整 Transform。Scale 必须 XYZ 相同且位于 0.85–1.15。
- 两者使用相同 scale 和 XY 位移；高度公式为 `oven_z = cart_z + 0.755 × scale`。
""",
        encoding="utf-8",
    )
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = "scenario-forge-task09-r14-vr/v0.1"
    manifest["status"] = "static_built_runtime_pending"
    manifest["claims"].update(
        {
            "dual_physical_knobs": True,
            "door_upper_limit_deg": 60.0,
            "door_drive_damping": 9.0,
            "gui_independent_root_trs": True,
            "uniform_scale_range": [0.85, 1.15],
        }
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def build_handoff(output: Path = DEFAULT_OUTPUT) -> Task09R14Handoff:
    _configure_r13_base()
    base = r13.build_handoff(output)
    _upgrade(base.root)
    archive = output.resolve() / f"{HANDOFF_ID}.zip"
    shutil.make_archive(
        str(archive.with_suffix("")),
        "zip",
        root_dir=output.resolve(),
        base_dir=HANDOFF_ID,
    )
    return Task09R14Handoff(
        root=base.root,
        archive=archive,
        manifest=base.root / "manifest.json",
    )


def finalize_handoff(output: Path = DEFAULT_OUTPUT) -> Task09R14Handoff:
    _configure_r13_base()
    base = r13.finalize_handoff(output)
    return Task09R14Handoff(
        root=base.root,
        archive=base.archive,
        manifest=base.manifest,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--finalize-only", action="store_true")
    args = parser.parse_args(argv)
    result = (
        finalize_handoff(args.output)
        if args.finalize_only
        else build_handoff(args.output)
    )
    print(result.archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Generate Task 09 r15 with the oven's complete subtree under `/Instance`."""

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
for _path in (ROOT, ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scenario_forge.validation.articulated_instance_layout import (  # noqa: E402
    validate_articulated_instance_layout,
)


R14_ROOT = (
    ROOT
    / "outputs/scientific_workbench_task09_r14_20260831/handoff/"
    "scientific_workbench_task09_r14_vr"
)
OVEN_R15 = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "ika_oven_125_task09_r15_instance_layout_20260901"
)
DEFAULT_OUTPUT = ROOT / "outputs/scientific_workbench_task09_r15_20260901/handoff"
HANDOFF_ID = "scientific_workbench_task09_r15_vr"


@dataclass(frozen=True)
class Task09R15Result:
    root: Path
    archive: Path
    manifest: Path


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def build_handoff(output: Path = DEFAULT_OUTPUT) -> Task09R15Result:
    from pxr import Gf, Sdf, Usd

    output = output.resolve()
    root = output / HANDOFF_ID
    if output.exists():
        raise FileExistsError(f"refusing to replace output: {output}")
    receipt = OVEN_R15 / "promotion_receipt.json"
    if json.loads(receipt.read_text()).get("status") != "promoted":
        raise ValueError("ConvertAsset r15 Instance oven is not promoted")
    shutil.copytree(R14_ROOT, root)
    shutil.rmtree(root / "evidence")
    shutil.rmtree(root / "deps/oven")
    shutil.copytree(OVEN_R15, root / "deps/oven")
    scene = root / "scene.usd"
    target = Usd.Stage.Open(str(scene))
    target_layer = target.GetRootLayer()
    target.RemovePrim("/World/obj_oven")
    target_layer.Save()
    source = Usd.Stage.Open(str(OVEN_R15 / "package/asset.usd"))
    Sdf.CopySpec(
        source.GetRootLayer(),
        "/World/obj_oven",
        target_layer,
        "/World/obj_oven",
    )
    target_layer.Save()
    target = Usd.Stage.Open(str(scene))
    oven = target.GetPrimAtPath("/World/obj_oven")
    oven.GetAttribute("xformOp:translate").Set(Gf.Vec3d(1.51, 0.0, 0.755))
    control = target.GetPrimAtPath("/World/obj_oven/Instance/ControlPanel")
    control.GetAttribute("oven:mainsPower").Set(True)
    control.GetAttribute("oven:heatingEnabled").Set(False)
    control.GetAttribute("oven:heaterActive").Set(False)
    control.GetAttribute("oven:temperatureSetpointC").Set(60.0)
    control.GetAttribute("oven:operatingState").Set("idle")
    control.GetAttribute("ui:page").Set("home")
    control.GetAttribute("ui:selectedField").Set("home")
    target.GetPrimAtPath(
        "/World/obj_oven/Instance/Joints/MainsRocker"
    ).GetAttribute("drive:angular:physics:targetPosition").Set(8.0)
    target.GetRootLayer().Save()
    layout = validate_articulated_instance_layout(scene, ["/World/obj_oven"])
    evidence = root / "evidence"
    evidence.mkdir()
    (evidence / "articulated_instance_layout.json").write_text(
        json.dumps(layout, indent=2, sort_keys=True) + "\n"
    )
    config = root / "task_config.py"
    config.write_text(
        config.read_text().replace(
            "scientific_workbench_task09_r14", "scientific_workbench_task09_r15"
        )
    )
    task = {
        "schema_version": "scenario-forge-task09-r15-controls/v0.1",
        "temperature_control": "obj_oven.Instance.ControlPanel.AuxControlKnob",
        "start_control": "obj_oven.Instance.ControlPanel.AuxControlKnob",
        "alternate_control": "obj_oven.Instance.ControlPanel.ControlKnob",
        "door_joint": "obj_oven.Instance.Joints.DoorHinge",
        "instance_prim": "obj_oven.Instance",
        "shared_logical_state": True,
        "mechanically_synchronized": False,
        "uniform_scale_range": [0.85, 1.15],
        "scale_policy": "uniform_xyz_only_on_obj_root",
    }
    (root / "task_r15.json").write_text(
        json.dumps(task, indent=2, sort_keys=True) + "\n"
    )
    (root / "task_r14.json").unlink()
    readme = root / "README_CN.md"
    readme.write_text(
        readme.read_text()
        + "\n## r15 铰接 Instance 路径\n\n"
        + "烘箱放置根保持 `/World/obj_oven`；所有 link、joint、控制面板和运行图均位于 "
        + "`/World/obj_oven/Instance/`。VR 运行时对应 `/World/_scene/obj_oven/Instance/`。"
        + "只在 `obj_oven` 根调节 Transform；`Instance` 是无变换的 Scope。\n"
    )
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["schema_version"] = "scenario-forge-task09-r15-vr/v0.1"
    manifest["status"] = "static_built_runtime_pending"
    manifest["source_evidence"]["oven_receipt"] = "deps/oven/promotion_receipt.json"
    manifest["source_evidence"]["oven_receipt_sha256"] = _sha(receipt)
    manifest["claims"].update(
        {
            "articulated_instance_layout_v1": True,
            "all_links_under_instance": True,
            "instance_scope_not_xform": True,
        }
    )
    manifest.pop("runtime_evidence", None)
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    archive = output / f"{HANDOFF_ID}.zip"
    shutil.make_archive(str(archive.with_suffix("")), "zip", root_dir=output, base_dir=HANDOFF_ID)
    return Task09R15Result(root, archive, manifest_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    print(build_handoff(args.output).archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

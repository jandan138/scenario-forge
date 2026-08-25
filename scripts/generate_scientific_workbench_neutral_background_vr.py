#!/usr/bin/env python3
"""Build a task-free VR workbench scene with rear-row context props only."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
from zipfile import ZIP_DEFLATED, ZipFile

import yaml


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scenario_forge.adapters.vr_presentation import (  # noqa: E402
    STANDARD_WORKBENCH_ASSET_ID,
    apply_standard_workbench_vr_presentation,
)


DEFAULT_BASE = (
    ROOT
    / "outputs/scientific_workbench_insert_stir_bar_into_beaker_vr_r5_20260825"
)
DEFAULT_OUT = ROOT / "outputs/scientific_workbench_neutral_background_vr_20260825"
BACKGROUND_LAYOUT = {
    "obj_r9_amber_bottle": (-0.78, 0.25, 0.755),
    "obj_r9_tip_box": (-0.42, 0.25, 0.755),
    "obj_r9_pipette_carousel": (0.0, 0.25, 0.755),
    "obj_r9_clear_bottle": (0.42, 0.25, 0.755),
    "obj_r9_wash_bottle": (0.78, 0.25, 0.755),
}


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _set_translate(prim, xyz: tuple[float, float, float]) -> None:
    from pxr import Gf, UsdGeom

    xformable = UsdGeom.Xformable(prim)
    translate_ops = [
        op
        for op in xformable.GetOrderedXformOps()
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate
    ]
    op = translate_ops[0] if translate_ops else xformable.AddTranslateOp()
    op.Set(Gf.Vec3d(*xyz))


def _write_archive(output: Path) -> Path:
    archive = output / "handoff/scientific_workbench_neutral_background_vr.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive, "w", compression=ZIP_DEFLATED, compresslevel=6) as bundle:
        for relative in ("README_CN.md", "manifest.json", "scene_config.yaml"):
            bundle.write(output / relative, relative)
        for path in sorted((output / "vr").rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(output).as_posix())
    return archive


def build(base: Path, output: Path) -> Path:
    from pxr import Usd, UsdUtils

    base = base.resolve()
    output = output.resolve()
    if output.exists():
        shutil.rmtree(output)
    vr = output / "vr"
    shutil.copytree(base / "vr", vr)

    scene = vr / "scene.usd"
    stage = Usd.Stage.Open(str(scene), Usd.Stage.LoadAll)
    if stage is None:
        raise RuntimeError(f"cannot open base VR scene: {scene}")
    world = stage.GetPrimAtPath("/World")
    if not world:
        raise RuntimeError("neutral VR scene requires /World")
    for child in list(world.GetChildren()):
        name = child.GetName()
        if (name.startswith("obj_") and name not in BACKGROUND_LAYOUT) or name == (
            "fluid_runtime"
        ):
            stage.RemovePrim(child.GetPath())
    for name, xyz in BACKGROUND_LAYOUT.items():
        prim = stage.GetPrimAtPath(f"/World/{name}")
        if not prim:
            raise RuntimeError(f"missing background object: {name}")
        _set_translate(prim, xyz)
    background = stage.GetPrimAtPath("/World/background")
    table = stage.GetPrimAtPath("/World/table")
    if not background or not table:
        raise RuntimeError("neutral VR scene requires background and table")
    background.GetReferences().ClearReferences()
    background.GetReferences().AddReference(
        "deps/r7_scene/scene.usda", "/World/_scene/room"
    )
    table.GetReferences().ClearReferences()
    table.GetReferences().AddReference(
        "deps/r7_scene/source_bundle/scenario_forge_runtime/table.usd", "/Asset"
    )
    stage.GetRootLayer().Save()

    for path in list(vr.iterdir()):
        if path.name not in {"scene.usd", "deps"}:
            shutil.rmtree(path) if path.is_dir() else path.unlink()
    for path in list((vr / "deps").iterdir()):
        if path.name != "r7_scene":
            shutil.rmtree(path) if path.is_dir() else path.unlink()

    presentation = apply_standard_workbench_vr_presentation(
        scene, table_asset_id=STANDARD_WORKBENCH_ASSET_ID
    )
    dependencies, assets, unresolved = UsdUtils.ComputeAllDependencies(str(scene))
    if unresolved:
        raise RuntimeError(
            "neutral VR scene has unresolved dependencies: "
            + ", ".join(sorted(str(item) for item in unresolved))
        )
    closure = {
        Path(item.realPath).resolve()
        for item in dependencies
        if getattr(item, "realPath", "")
    }
    closure.update(Path(str(item)).resolve() for item in assets)
    escaped = [path for path in closure if output not in path.parents and path != output]
    if escaped:
        raise RuntimeError(
            "neutral VR scene dependency escapes package: "
            + ", ".join(str(path) for path in sorted(escaped))
        )

    config = {
        "schema_version": "scenario-forge.neutral-workbench-vr.v1",
        "task_objective": "none",
        "scene_usd": "vr/scene.usd",
        "obj_prim_list": [f"/World/_scene/{name}" for name in BACKGROUND_LAYOUT],
        "layout_randomization": {
            "mode": "local",
            "x_offset_range": [-0.01, 0.01],
            "y_offset_range": [-0.01, 0.01],
            "yaw_range_degrees": [0.0, 0.0],
        },
    }
    (output / "scene_config.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
    )
    manifest = {
        "schema_version": "scenario-forge.neutral-workbench-vr-package.v1",
        "status": "ready",
        "task_objective": "none",
        "background_objects": list(BACKGROUND_LAYOUT),
        "vr_presentation_policy": presentation,
        "claims": {
            "task_success": False,
            "robot_policy_success": False,
            "benchmark_success": False,
        },
        "entrypoint": {"path": "vr/scene.usd", "sha256": _sha(scene)},
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "README_CN.md").write_text(
        "# 中性实验桌背景场景\n\n"
        "直接打开 `vr/scene.usd`。场景没有机器人任务目标、操作器材、液体或任务配置；"
        "桌面后排仅保留五件背景物。`scene_config.yaml` 记录对象列表与 1 cm 本地随机化范围。\n",
        encoding="utf-8",
    )
    archive = _write_archive(output)
    archive.with_suffix(".zip.sha256").write_text(
        _sha(archive) + "  " + archive.name + "\n", encoding="utf-8"
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(build(args.base, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

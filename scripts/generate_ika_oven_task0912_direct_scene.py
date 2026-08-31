#!/usr/bin/env python3
"""Build the direct-stage Task 09/12 IKA OVEN 125 review handoff."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "outputs/ika_oven_125_task0912_direct_scene_r1_20260831/handoff"
HANDOFF_ID = "ika_oven_125_task0912_direct_scene_r1"
OVEN_OUTPUT = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "ika_oven_125_task0912_fixed_benchtop_r1_20260831"
)
TABLE_PACKAGE = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "scientific_workbench_standard_table_20260819/package"
)
FLASK_PACKAGE = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "scientific_workbench_conical_flask_90x35_glass_warp_20260821/package"
)
BEAKER_PACKAGE = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "scientific_workbench_beaker_325ml_sdf_web_standard_20260824/package"
)


@dataclass(frozen=True)
class DirectSceneHandoff:
    root: Path
    archive: Path
    manifest: Path


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _validate_oven_source() -> None:
    manifest = json.loads(
        (OVEN_OUTPUT / "package/evidence/manifest.json").read_text(encoding="utf-8")
    )
    receipt = json.loads(
        (OVEN_OUTPUT / "promotion_receipt.json").read_text(encoding="utf-8")
    )
    if manifest.get("overall_status") != "pass" or receipt.get("status") != "promoted":
        raise ValueError("ConvertAsset IKA oven package is not promoted")
    claims = manifest.get("claims", {})
    if claims.get("task09_task12_subset") is not True:
        raise ValueError("ConvertAsset package lacks the Task 09/12 claim")
    mounting = manifest.get("mounting", {})
    if (
        mounting.get("consumer_mode") != "direct_stage_only"
        or mounting.get("required_runtime_prim_path") != "/World/Oven125"
        or mounting.get("consumer_entry_transform_required") != "identity"
    ):
        raise ValueError("ConvertAsset package has an incompatible consumer contract")


def _write_runtime_scene(root: Path) -> Path:
    from pxr import Gf, Usd, UsdGeom, UsdLux

    destination = root / "scene.usd"
    shutil.copy2(root / "deps/oven/package/asset.usd", destination)
    stage = Usd.Stage.Open(str(destination))
    if stage is None or stage.GetDefaultPrim().GetPath() != "/World":
        raise RuntimeError("cannot open copied direct-stage oven root")

    table = UsdGeom.Xform.Define(stage, "/World/table").GetPrim()
    table.GetReferences().AddReference("deps/table/asset.usd", "/World/table")

    def add_vessel(path: str, asset: str, prim_path: str, xyz: tuple[float, ...]) -> None:
        prim = UsdGeom.Xform.Define(stage, path).GetPrim()
        prim.GetReferences().AddReference(asset, prim_path)
        xform = UsdGeom.Xformable(prim)
        translate = prim.GetAttribute("xformOp:translate")
        if translate.IsValid():
            value = (
                Gf.Vec3f(*xyz)
                if str(translate.GetTypeName()) == "float3"
                else Gf.Vec3d(*xyz)
            )
            translate.Set(value)
        else:
            xform.AddTranslateOp().Set(Gf.Vec3d(*xyz))

    add_vessel(
        "/World/obj_conical_flask",
        "deps/flask/asset.usd",
        "/World/ConicalFlask90x35Warp",
        (-0.11, -0.06, 1.038),
    )
    add_vessel(
        "/World/obj_beaker",
        "deps/beaker/asset.usd",
        "/World/Beaker325mlSdf",
        (0.11, -0.06, 1.038),
    )
    light = UsdLux.DomeLight.Define(stage, "/World/DirectStageLight")
    light.CreateIntensityAttr(750.0)
    light.CreateColorAttr(Gf.Vec3f(1.0))
    stage.GetRootLayer().Save()
    return destination


def _open_preview_usda() -> str:
    return '''#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
    subLayers = [@scene.usd@]
)

over "World"
{
    over "Oven125"
    {
        over "Door"
        {
            custom double oven:doorAngleDegrees = 100
            double xformOp:rotateZ = 100
        }
    }
}
'''


def build_handoff(output: Path = DEFAULT_OUTPUT) -> DirectSceneHandoff:
    output = output.resolve()
    root = output / HANDOFF_ID
    archive = output / f"{HANDOFF_ID}.zip"
    if output.exists():
        raise FileExistsError(f"refusing to replace output: {output}")
    _validate_oven_source()
    for source in (TABLE_PACKAGE, FLASK_PACKAGE, BEAKER_PACKAGE):
        if not (source / "asset.usd").is_file():
            raise FileNotFoundError(source / "asset.usd")
    root.mkdir(parents=True)
    deps = root / "deps"
    shutil.copytree(OVEN_OUTPUT, deps / "oven")
    shutil.copytree(TABLE_PACKAGE, deps / "table")
    shutil.copytree(FLASK_PACKAGE, deps / "flask")
    shutil.copytree(BEAKER_PACKAGE, deps / "beaker")
    _write_runtime_scene(root)
    (root / "scene_open_preview.usd").write_text(
        _open_preview_usda(), encoding="utf-8"
    )
    (root / "README_CN.md").write_text(
        """# IKA OVEN 125 Task 09/12 direct-stage 包

- 运行入口：`scene.usd`（闭门，Isaac Sim 4.1）
- 查看内部摆放：`scene_open_preview.usd`（100° 开门静态预览）
- 烘箱固定路径：`/World/Oven125`
- 烘箱已内置 0.755 m 标准桌面高度；桌子和机器人世界坐标无需移动。
- 内部下层搁架放置空的 SDF 锥形瓶与烧杯，本包不含 PBD 粒子。
- 首次 Play 需允许 NVIDIA ScriptNode trust；OmniGraph 控制器保持启用。

重要限制：必须直接打开 USD。不得把场景挂到 `/World/_scene`，不得重命名、
父级包裹、平移或随机化烘箱。该包声明 Task 09 + Task 12 固定台面功能，不声明
VR runtime mount、机器人策略、真实温控标定或 benchmark 成功。
""",
        encoding="utf-8",
    )
    oven_manifest = OVEN_OUTPUT / "package/evidence/manifest.json"
    qualification = OVEN_OUTPUT / "qualification/full_report.json"
    manifest = {
        "schema_version": "scenario-forge-ika-oven-task0912-direct-stage/v0.1",
        "status": "static_built_runtime_pending",
        "entrypoints": {
            "runtime_scene": "scene.usd",
            "open_preview": "scene_open_preview.usd",
            "default_prim": "World",
            "oven_prim": "/World/Oven125",
        },
        "source_evidence": {
            "convertasset_manifest": "deps/oven/package/evidence/manifest.json",
            "convertasset_manifest_sha256": _sha256(oven_manifest),
            "qualification": "deps/oven/qualification/full_report.json",
            "qualification_sha256": _sha256(qualification),
            "promotion_receipt": "deps/oven/promotion_receipt.json",
        },
        "claims": {
            "task09_task12_subset": True,
            "full_controller_parity_fixed_mount": True,
            "empty_liquid_ready_vessels": True,
            "vr_scene_mount_allowed": False,
            "oven_randomization_allowed": False,
            "robot_policy_success": False,
            "benchmark_success": False,
        },
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    shutil.make_archive(str(archive.with_suffix("")), "zip", root_dir=output, base_dir=HANDOFF_ID)
    return DirectSceneHandoff(root=root, archive=archive, manifest=manifest_path)


def finalize_handoff(output: Path = DEFAULT_OUTPUT) -> DirectSceneHandoff:
    output = output.resolve()
    root = output / HANDOFF_ID
    archive = output / f"{HANDOFF_ID}.zip"
    manifest_path = root / "manifest.json"
    runtime_path = root / "evidence/runtime/final_scene_interactive_smoke.json"
    render_path = root / "evidence/initial_scene/render_manifest.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    render = json.loads(render_path.read_text(encoding="utf-8"))
    if runtime.get("status") != "PASS" or runtime.get("passed") is not True:
        raise ValueError("final direct scene interactive smoke did not pass")
    if render.get("status") != "pass":
        raise ValueError("final direct scene render did not pass")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "status": "isaac41_runtime_complete",
            "runtime_evidence": {
                "interactive_smoke": "evidence/runtime/final_scene_interactive_smoke.json",
                "interactive_smoke_sha256": _sha256(runtime_path),
                "render_manifest": "evidence/initial_scene/render_manifest.json",
                "render_manifest_sha256": _sha256(render_path),
            },
        }
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    shutil.make_archive(
        str(archive.with_suffix("")), "zip", root_dir=output, base_dir=HANDOFF_ID
    )
    return DirectSceneHandoff(root=root, archive=archive, manifest=manifest_path)


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

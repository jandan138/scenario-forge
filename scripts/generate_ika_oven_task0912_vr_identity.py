#!/usr/bin/env python3
"""Build the standard VR handoff from the promoted identity-root IKA oven."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    REPO_ROOT / "outputs/ika_oven_125_task0912_vr_identity_r2_20260831/handoff"
)
HANDOFF_ID = "ika_oven_125_task0912_vr_identity_r2"
OVEN_OUTPUT = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "ika_oven_125_identity_root_r1_20260831"
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
class VrIdentityHandoff:
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
        raise ValueError("ConvertAsset identity-root IKA oven is not promoted")
    if manifest.get("claims", {}).get("relocatable_task_scoped") is not True:
        raise ValueError("ConvertAsset oven lacks relocatable Task 09/12 scope")
    if receipt.get("tier") not in {
        "relocatable_task_scoped",
        "relocatable_full",
    }:
        raise ValueError("ConvertAsset oven promotion tier is not consumable")
    relocation = manifest.get("relocatability", {})
    if (
        relocation.get("identity_entry") is not True
        or relocation.get("world_anchored_joints_rebound") != 15
    ):
        raise ValueError("ConvertAsset oven is not an identity-root relocation package")


def _write_scene(root: Path) -> Path:
    from pxr import Gf, Usd, UsdGeom, UsdLux, UsdPhysics

    destination = root / "scene.usd"
    stage = Usd.Stage.CreateNew(str(destination))
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    physics_scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
    physics_scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(0.0, 0.0, -1.0))
    physics_scene.CreateGravityMagnitudeAttr().Set(9.81)

    table = UsdGeom.Xform.Define(stage, "/World/table").GetPrim()
    table.GetReferences().AddReference("deps/table/asset.usd", "/World/table")

    oven = UsdGeom.Xform.Define(stage, "/World/obj_oven").GetPrim()
    oven.GetReferences().AddReference(
        "deps/oven/package/asset.usd", "/World/Oven125"
    )
    UsdGeom.Xformable(oven).AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, 0.755))

    def add_vessel(path: str, asset: str, source_prim: str, xyz: tuple[float, ...]) -> None:
        prim = UsdGeom.Xform.Define(stage, path).GetPrim()
        prim.GetReferences().AddReference(asset, source_prim)
        translate = prim.GetAttribute("xformOp:translate")
        if translate.IsValid():
            value = (
                Gf.Vec3f(*xyz)
                if str(translate.GetTypeName()) == "float3"
                else Gf.Vec3d(*xyz)
            )
            translate.Set(value)
        else:
            UsdGeom.Xformable(prim).AddTranslateOp().Set(Gf.Vec3d(*xyz))

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
    light = UsdLux.DomeLight.Define(stage, "/World/SceneLight")
    light.CreateIntensityAttr(750.0)
    light.CreateColorAttr(Gf.Vec3f(1.0))
    stage.GetRootLayer().Save()
    return destination


def _open_preview() -> str:
    return '''#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
    subLayers = [@scene.usd@]
)

over "World"
{
    over "obj_oven"
    {
        over "Door"
        {
            custom double oven:doorAngleDegrees = 100
            double xformOp:rotateZ = 100
        }
    }
}
'''


def _task_config() -> str:
    objects = ("obj_oven", "obj_conical_flask", "obj_beaker")
    entries = "\n".join(
        f'''            {{
                "objs": ["{name}"],
                "mode": "local",
                "yaw_range_degrees": [0.0, 0.0],
                "x_offset_range": [-0.01, 0.01],
                "y_offset_range": [-0.01, 0.01],
            }},'''
        for name in objects
    )
    prims = ",\n".join(f'        "/World/_scene/{name}"' for name in objects)
    return f'''# Merge this TASKS entry into VR Teleop constants/tasks.py.
TASKS = {{
    "ika_oven_125_task0912_vr_identity_r2": {{
        "scene_usd_file_path": {{
            "scene1": str(_ASSETS_DIR / "scenes/ika_oven_125_task0912_vr_identity_r2/scene.usd"),
        }},
        "obj_prim_list": [
{prims}
        ],
        "layout_randomization": {{
            "table": "table",
            "objects": [
{entries}
            ],
        }},
        "robot_cfg": {{
            "position": [0.0, -1.02, 0.31],
            "orientation": [0.7071067812, 0.0, 0.0, 0.7071067812],
        }},
    }},
}}
'''


def build_handoff(output: Path = DEFAULT_OUTPUT) -> VrIdentityHandoff:
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
    _write_scene(root)
    (root / "scene_open_preview.usd").write_text(
        _open_preview(), encoding="utf-8"
    )
    (root / "task_config.py").write_text(_task_config(), encoding="utf-8")
    (root / "README_CN.md").write_text(
        """# IKA OVEN 125 Task 09/12 VR identity-root 包

- 打开 `scene.usd`；运行时用 Isaac Sim 4.1。
- USD 内烘箱为 `/World/obj_oven`；VR 挂载后是 `/World/_scene/obj_oven`。
- 烘箱入口本地 Z=0.755 m，标准桌与机器人坐标没有下移或烘焙补丁。
- `scene_open_preview.usd` 仅用于静态查看内部空 SDF 锥形瓶与烧杯。
- 烘箱、锥形瓶、烧杯均进入 `obj_prim_list`，本地 XY 随机范围为 ±0.01 m。

ConvertAsset claim 是 `relocatable_task_scoped`：三种命名空间的可搬移门禁与
Task 09/12 所需门、按钮、总电源物理功能已在 Isaac 4.1 通过；不继承 full
controller、机器人策略、benchmark、温控标定或电气安全声明。
""",
        encoding="utf-8",
    )
    source_manifest = OVEN_OUTPUT / "package/evidence/manifest.json"
    qualification = OVEN_OUTPUT / "qualification/full_report.json"
    receipt = OVEN_OUTPUT / "promotion_receipt.json"
    manifest = {
        "schema_version": "scenario-forge-ika-oven-task0912-vr-identity/v0.1",
        "status": "static_built_runtime_pending",
        "entrypoints": {
            "runtime_scene": "scene.usd",
            "open_preview": "scene_open_preview.usd",
            "task_config": "task_config.py",
            "default_prim": "World",
            "oven_prim_in_usd": "/World/obj_oven",
            "oven_prim_in_vr_runtime": "/World/_scene/obj_oven",
        },
        "source_evidence": {
            "convertasset_manifest": "deps/oven/package/evidence/manifest.json",
            "convertasset_manifest_sha256": _sha256(source_manifest),
            "qualification": "deps/oven/qualification/full_report.json",
            "qualification_sha256": _sha256(qualification),
            "promotion_receipt": "deps/oven/promotion_receipt.json",
            "promotion_receipt_sha256": _sha256(receipt),
        },
        "claims": {
            "relocatable_task_scoped": True,
            "relocatable_full": False,
            "task09_task12_subset": True,
            "standard_vr_mount": True,
            "empty_liquid_ready_vessels": True,
            "robot_policy_success": False,
            "benchmark_success": False,
        },
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    shutil.make_archive(
        str(archive.with_suffix("")), "zip", root_dir=output, base_dir=HANDOFF_ID
    )
    return VrIdentityHandoff(root=root, archive=archive, manifest=manifest_path)


def _task_scoped_runtime_checks(report: dict) -> dict[str, bool]:
    results = report.get("results", {})
    door = results.get("doorDynamicLimit", {})
    return {
        "door_right_force_open_close": bool(
            int(door.get("successfulForceCalls", 0)) >= 1000
            and float(door.get("openingPeakDegrees", 0.0)) >= 175.0
            and float(door.get("closingFinalDegrees", 180.0)) <= 3.0
            and float(door.get("bodyTranslationDriftMeters", 1.0)) <= 1.0e-6
        ),
        "ten_buttons_press_return": bool(
            results.get("tenButtonsTravelAndReturn", {}).get("passed")
        ),
        "mains_rocker_toggle_return": bool(
            results.get("mainsRockerLimits", {}).get("passed")
        ),
    }


def finalize_handoff(output: Path = DEFAULT_OUTPUT) -> VrIdentityHandoff:
    output = output.resolve()
    root = output / HANDOFF_ID
    archive = output / f"{HANDOFF_ID}.zip"
    manifest_path = root / "manifest.json"
    raw_path = root / "evidence/runtime/physics_smoke.json"
    report = json.loads(raw_path.read_text(encoding="utf-8"))
    checks = _task_scoped_runtime_checks(report)
    if not all(checks.values()):
        raise ValueError(f"Task 09/12 runtime checks did not pass: {checks}")
    summary = {
        "schema_version": "scenario-forge-ika-oven-task0912-runtime/v0.1",
        "status": "pass",
        "runtime": "isaac41",
        "root": "/World/obj_oven",
        "checks": checks,
        "producer_report_status": report.get("status"),
        "producer_report_note": (
            "The producer full report remains FAIL because it expects world-anchored "
            "body0 semantics and includes functions outside the promoted Task 09/12 scope."
        ),
    }
    summary_path = root / "evidence/runtime/task_scoped_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "isaac41_task_scoped_runtime_complete"
    manifest["runtime_evidence"] = {
        "physics_smoke": "evidence/runtime/physics_smoke.json",
        "physics_smoke_sha256": _sha256(raw_path),
        "task_scoped_summary": "evidence/runtime/task_scoped_summary.json",
        "task_scoped_summary_sha256": _sha256(summary_path),
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    shutil.make_archive(
        str(archive.with_suffix("")), "zip", root_dir=output, base_dir=HANDOFF_ID
    )
    return VrIdentityHandoff(root=root, archive=archive, manifest=manifest_path)


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

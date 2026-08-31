#!/usr/bin/env python3
"""Generate the Task 09 r13 materialized-oven VR handoff."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Any, Sequence

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "outputs/scientific_workbench_task09_r13_3_20260831/handoff"
HANDOFF_ID = "scientific_workbench_task09_r13_vr"
CONVERT_ROOT = Path("/cpfs/user/zhuzihou/dev/ConvertAsset/outputs")
OVEN_OUTPUT = CONVERT_ROOT / "ika_oven_125_task09_r13_materialized_20260831"
CART_OUTPUT = CONVERT_ROOT / "task09_r13_compact_oven_cart_20260831"
TABLE_PACKAGE = CONVERT_ROOT / "scientific_workbench_standard_table_20260819/package"
BEAKER_PACKAGE = (
    CONVERT_ROOT / "task09_r13_beaker_325ml_sdf_clean_closure_r2_20260831/package"
)
FLASK_PACKAGE = (
    CONVERT_ROOT / "scientific_workbench_conical_flask_90x35_glass_warp_20260821/package"
)
ENVIRONMENT_PACKAGE = (
    CONVERT_ROOT
    / "generated_scientific_labs_v2_20260804/analytical_instrumentation/package"
)


@dataclass(frozen=True)
class Task09R13Handoff:
    root: Path
    archive: Path
    manifest: Path


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _set_translation(prim: Any, xyz: tuple[float, float, float]) -> None:
    from pxr import Gf, UsdGeom

    attr = prim.GetAttribute("xformOp:translate")
    if attr.IsValid():
        value = Gf.Vec3f(*xyz) if str(attr.GetTypeName()) == "float3" else Gf.Vec3d(*xyz)
        attr.Set(value)
    else:
        UsdGeom.Xformable(prim).AddTranslateOp().Set(Gf.Vec3d(*xyz))


def _write_scene(root: Path) -> Path:
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux

    destination = root / "scene.usd"
    shutil.copy2(root / "deps/oven/package/asset.usd", destination)
    stage = Usd.Stage.Open(str(destination))
    if stage is None or not stage.GetPrimAtPath("/World/obj_oven").IsValid():
        raise RuntimeError("cannot open the materialized Task09 oven stage")
    oven = stage.GetPrimAtPath("/World/obj_oven")
    _set_translation(oven, (1.51, 0.0, 0.755))
    physics_scene = stage.GetPrimAtPath("/World/PhysicsScene")
    physics_scene.CreateAttribute(
        "physxScene:broadphaseType", Sdf.ValueTypeNames.Token, custom=True
    ).Set("GPU")
    physics_scene.CreateAttribute(
        "physxScene:enableGPUDynamics", Sdf.ValueTypeNames.Bool, custom=True
    ).Set(True)

    cart = UsdGeom.Xform.Define(stage, "/World/obj_oven_cart").GetPrim()
    cart.GetReferences().AddReference(
        "deps/oven_cart/package/asset.usd", "/World/OvenCart"
    )
    _set_translation(cart, (1.51, 0.0, 0.0))

    table = UsdGeom.Xform.Define(stage, "/World/table").GetPrim()
    table.GetReferences().AddReference("deps/table/asset.usd", "/World/table")

    background = UsdGeom.Xform.Define(stage, "/World/background").GetPrim()
    background.GetReferences().AddReference("deps/environment/asset.usd", "/World")
    background_xform = UsdGeom.Xformable(background)
    background_xform.SetResetXformStack(True)
    background_xform.AddTranslateOp().Set(Gf.Vec3d(0.002882434, -0.0069055, 0.0))
    background_xform.AddOrientOp().Set(
        Gf.Quatf(-0.7071067812, 0.0, 0.0, -0.7071067812)
    )
    background_xform.AddScaleOp().Set(Gf.Vec3d(1.0))
    for path in (
        "/World/background/Lab_Stool_Left",
        "/World/background/Lab_Stool_Middle",
        "/World/background/Lab_Stool_Right",
    ):
        prim = stage.GetPrimAtPath(path)
        if prim.IsValid():
            prim.SetActive(False)

    def add_vessel(path: str, asset: str, source_prim: str, xyz: tuple[float, ...]) -> None:
        prim = UsdGeom.Xform.Define(stage, path).GetPrim()
        prim.GetReferences().AddReference(asset, source_prim)
        _set_translation(prim, xyz)

    add_vessel(
        "/World/obj_sample_beaker",
        "deps/beaker/asset.usd",
        "/World/Beaker325mlSdf",
        (0.62, -0.16, 0.755),
    )
    add_vessel(
        "/World/obj_context_conical_flask",
        "deps/flask/asset.usd",
        "/World/ConicalFlask90x35Warp",
        (0.40, 0.14, 0.755),
    )

    control = stage.GetPrimAtPath("/World/obj_oven/ControlPanel")
    control.GetAttribute("oven:mainsPower").Set(True)
    control.GetAttribute("oven:heatingEnabled").Set(False)
    control.GetAttribute("oven:heaterActive").Set(False)
    control.GetAttribute("oven:temperatureSetpointC").Set(60.0)
    control.GetAttribute("oven:operatingState").Set("idle")
    control.GetAttribute("ui:page").Set("home")
    control.GetAttribute("ui:selectedField").Set("home")
    stage.GetPrimAtPath("/World/obj_oven/Joints/MainsRocker").GetAttribute(
        "drive:angular:physics:targetPosition"
    ).Set(8.0)
    world = stage.GetPrimAtPath("/World")
    world.SetCustomDataByKey("scenario_forge:taskId", "scientific_workbench_task09_r13")
    if not stage.GetPrimAtPath("/World/Task09SceneLight").IsValid():
        light = UsdLux.DomeLight.Define(stage, "/World/Task09SceneLight")
        light.CreateIntensityAttr(500.0)
        light.CreateColorAttr(Gf.Vec3f(1.0))
    stage.GetRootLayer().Save()
    reopened = Usd.Stage.Open(str(destination))
    if reopened is None:
        raise RuntimeError("final Task09 r13 stage does not reopen")
    return destination


def _task_config() -> str:
    return '''# Merge this TASKS entry into VR Teleop constants/tasks.py.
TASKS = {
    "scientific_workbench_task09_r13_oven_load_start": {
        "scene_usd_file_path": {
            "scene1": str(_ASSETS_DIR / "scenes/scientific_workbench_task09_r13_vr/scene.usd"),
        },
        "obj_prim_list": [
            "/World/_scene/obj_oven_cart",
            "/World/_scene/obj_oven",
            "/World/_scene/obj_sample_beaker",
            "/World/_scene/obj_context_conical_flask",
        ],
        "layout_randomization": {
            "table": "table",
            "objects": [
                {
                    "objs": ["obj_oven_cart", "obj_oven"],
                    "mode": "local",
                    "yaw_range_degrees": [0.0, 0.0],
                    "x_offset_range": [-0.01, 0.01],
                    "y_offset_range": [-0.01, 0.01],
                },
                {
                    "objs": ["obj_sample_beaker"],
                    "mode": "local",
                    "yaw_range_degrees": [0.0, 0.0],
                    "x_offset_range": [-0.01, 0.01],
                    "y_offset_range": [-0.01, 0.01],
                },
                {
                    "objs": ["obj_context_conical_flask"],
                    "mode": "local",
                    "yaw_range_degrees": [0.0, 0.0],
                    "x_offset_range": [-0.01, 0.01],
                    "y_offset_range": [-0.01, 0.01],
                },
            ],
        },
        "robot_cfg": {
            "position": [0.85, -1.02, 0.31],
            "orientation": [0.7071067812, 0.0, 0.0, 0.7071067812],
        },
    },
}
'''


def _task() -> dict[str, Any]:
    return {
        "schema_version": "task/v0.4",
        "task_id": "scientific_workbench_task09_r13_oven_load_start",
        "source_order": 9,
        "instruction": (
            "辅助臂拉开并保持烘箱门；操作臂拿起烧杯并放到烘箱层架；辅助臂关门；"
            "操作臂将设定温度从60°C调到65°C并按下旋钮启动加热。"
        ),
        "target_vessel": "obj_sample_beaker",
        "graspable_context": ["obj_context_conical_flask"],
        "steps": [
            {"id": "open_door", "actor": "auxiliary_arm", "skill": "pull"},
            {"id": "pick_beaker", "actor": "operating_arm", "skill": "pick"},
            {"id": "place_on_shelf", "actor": "operating_arm", "skill": "place"},
            {"id": "close_door", "actor": "auxiliary_arm", "skill": "push"},
            {"id": "set_temperature_65c", "actor": "operating_arm", "skill": "turn"},
            {"id": "press_knob_start", "actor": "operating_arm", "skill": "press"},
        ],
    }


def _metrics() -> dict[str, Any]:
    ids = (
        "door_open",
        "sample_lifted",
        "sample_inside_door_open",
        "sample_supported_inside",
        "door_closed",
        "temperature_set_65c",
        "heating_started",
        "sample_retained",
        "door_retained_closed",
        "heating_retained",
    )
    weights = (0.10, 0.10, 0.10, 0.10, 0.15, 0.15, 0.10, 0.05, 0.05, 0.10)
    return {
        "schema_version": "metrics/v0.4",
        "aggregation": {
            "type": "weighted_progress_score",
            "normalization": "declared_sum",
            "primary_metric_id": "sample_supported_inside",
        },
        "metrics": [
            {
                "id": metric_id,
                "type": "rubric_condition",
                "weight": weight,
                "source_ref": {"source_order": 9, "item": f"时序{index + 1}"},
            }
            for index, (metric_id, weight) in enumerate(zip(ids, weights))
        ],
    }


def build_handoff(output: Path = DEFAULT_OUTPUT) -> Task09R13Handoff:
    output = output.resolve()
    root = output / HANDOFF_ID
    archive = output / f"{HANDOFF_ID}.zip"
    if output.exists():
        raise FileExistsError(f"refusing to replace output: {output}")
    for source, receipt in (
        (OVEN_OUTPUT, OVEN_OUTPUT / "promotion_receipt.json"),
        (CART_OUTPUT, CART_OUTPUT / "promotion_receipt.json"),
        (BEAKER_PACKAGE.parent, BEAKER_PACKAGE.parent / "promotion_receipt.json"),
    ):
        if not receipt.is_file() or json.loads(receipt.read_text()).get("status") != "promoted":
            raise ValueError(f"ConvertAsset package is not promoted: {source}")
    for package in (TABLE_PACKAGE, BEAKER_PACKAGE, FLASK_PACKAGE, ENVIRONMENT_PACKAGE):
        if not (package / "asset.usd").is_file():
            raise FileNotFoundError(package / "asset.usd")
    root.mkdir(parents=True)
    deps = root / "deps"
    shutil.copytree(OVEN_OUTPUT, deps / "oven")
    shutil.copytree(CART_OUTPUT, deps / "oven_cart")
    shutil.copytree(TABLE_PACKAGE, deps / "table")
    shutil.copytree(BEAKER_PACKAGE, deps / "beaker")
    shutil.copytree(FLASK_PACKAGE, deps / "flask")
    shutil.copytree(ENVIRONMENT_PACKAGE, deps / "environment")
    _write_scene(root)
    (root / "task_config.py").write_text(_task_config(), encoding="utf-8")
    (root / "task.yaml").write_text(
        yaml.safe_dump(_task(), allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (root / "metrics.yaml").write_text(
        yaml.safe_dump(_metrics(), allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (root / "README_CN.md").write_text(
        """# Scientific Workbench Task 09 r13 VR

打开 `scene.usd`，运行环境为 Isaac Sim 4.1。烘箱是直接 authored 的
`/World/obj_oven`，不得改成 reference；设备架和烘箱位于主桌右侧，机器人
基座移到两工位接缝前。目标容器是空的 SDF 烧杯；锥形瓶同样动态可抓取，
但不参与本任务评分。初始烘箱已通电、未加热、设定 60°C；转到 65°C 后
按下旋钮启动加热。

本包不声明机器人策略或 benchmark 成功。
""",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "scenario-forge-task09-r13-vr/v0.1",
        "status": "static_built_runtime_pending",
        "entrypoints": {
            "scene": "scene.usd",
            "task_config": "task_config.py",
            "task": "task.yaml",
            "metrics": "metrics.yaml",
        },
        "source_evidence": {
            "oven_receipt": "deps/oven/promotion_receipt.json",
            "oven_receipt_sha256": _sha(OVEN_OUTPUT / "promotion_receipt.json"),
            "oven_cart_receipt": "deps/oven_cart/promotion_receipt.json",
            "oven_cart_receipt_sha256": _sha(CART_OUTPUT / "promotion_receipt.json"),
        },
        "claims": {
            "target_vessel": "obj_sample_beaker",
            "conical_flask_graspable_context": True,
            "empty_sdf_vessels": True,
            "vr_only": True,
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
    return Task09R13Handoff(root=root, archive=archive, manifest=manifest_path)


def finalize_handoff(output: Path = DEFAULT_OUTPUT) -> Task09R13Handoff:
    from pxr import UsdUtils

    output = output.resolve()
    root = output / HANDOFF_ID
    archive = output / f"{HANDOFF_ID}.zip"
    manifest_path = root / "manifest.json"
    static_report = root / "evidence/runtime/static_play_report.json"
    render_manifest = root / "evidence/initial_scene/render_manifest.json"
    visual_review = root / "evidence/initial_scene/visual_review.json"
    for path in (static_report, render_manifest, visual_review):
        if json.loads(path.read_text(encoding="utf-8")).get("status") != "pass":
            raise ValueError(f"final evidence did not pass: {path}")
    layers, assets, unresolved = UsdUtils.ComputeAllDependencies(str(root / "scene.usd"))
    external = [
        str(path)
        for path in assets
        if str(path).startswith("/") and not str(path).startswith(str(root) + "/")
    ]
    closure = {
        "schema_version": "scenario-forge-package-closure/v0.1",
        "status": "pass" if not unresolved and not external else "blocked",
        "layer_count": len(layers),
        "asset_count": len(assets),
        "unresolved": [str(path) for path in unresolved],
        "external_absolute_assets": external,
    }
    closure_path = root / "evidence/package_closure.json"
    closure_path.write_text(
        json.dumps(closure, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if closure["status"] != "pass":
        raise ValueError("final package dependency closure did not pass")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "isaac41_runtime_complete"
    manifest["runtime_evidence"] = {
        "static_play": "evidence/runtime/static_play_report.json",
        "static_play_sha256": _sha(static_report),
        "render_manifest": "evidence/initial_scene/render_manifest.json",
        "render_manifest_sha256": _sha(render_manifest),
        "visual_review": "evidence/initial_scene/visual_review.json",
        "visual_review_sha256": _sha(visual_review),
        "package_closure": "evidence/package_closure.json",
        "package_closure_sha256": _sha(closure_path),
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    shutil.make_archive(
        str(archive.with_suffix("")), "zip", root_dir=output, base_dir=HANDOFF_ID
    )
    return Task09R13Handoff(root=root, archive=archive, manifest=manifest_path)


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

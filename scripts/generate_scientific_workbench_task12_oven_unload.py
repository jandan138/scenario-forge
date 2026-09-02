#!/usr/bin/env python3
"""Generate the dual-glassware oven-unload Task 12 VR handoff."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Any, Sequence

import yaml


ROOT = Path(__file__).resolve().parents[1]
R15_ROOT = (
    ROOT
    / "outputs/scientific_workbench_task09_r15_20260901/handoff/"
    "scientific_workbench_task09_r15_vr"
)
DEFAULT_OUTPUT = (
    ROOT
    / "outputs/scientific_workbench_task12_oven_unload_dual_glassware_vr_r1_20260902/"
    "handoff"
)
HANDOFF_ID = "scientific_workbench_task12_oven_unload_dual_glassware_vr_r1"
TASK_ID = "scientific_workbench_oven_unload_shutdown_dual_glassware"


@dataclass(frozen=True)
class Task12OvenUnloadResult:
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


def _task_config() -> str:
    return f'''# Merge this TASKS entry into VR Teleop constants/tasks.py.
TASKS = {{
    "{HANDOFF_ID}": {{
        "scene_usd_file_path": {{
            "scene1": str(_ASSETS_DIR / "scenes/{HANDOFF_ID}/scene.usd"),
        }},
        "obj_prim_list": [
            "/World/_scene/obj_oven_cart",
            "/World/_scene/obj_oven",
            "/World/_scene/obj_sample_beaker",
            "/World/_scene/obj_sample_conical_flask",
        ],
        "layout_randomization": {{
            "table": "table",
            "objects": [
                {{
                    "objs": [
                        "obj_oven_cart",
                        "obj_oven",
                        "obj_sample_beaker",
                        "obj_sample_conical_flask",
                    ],
                    "mode": "local",
                    "yaw_range_degrees": [0.0, 0.0],
                    "x_offset_range": [-0.01, 0.01],
                    "y_offset_range": [-0.01, 0.01],
                }},
            ],
        }},
        "robot_cfg": {{
            "position": [0.85, -1.02, 0.31],
            "orientation": [0.7071067812, 0.0, 0.0, 0.7071067812],
        }},
    }},
}}
'''


def _task() -> dict[str, Any]:
    return {
        "schema_version": "task/v0.4",
        "task_id": TASK_ID,
        "source_order": 12,
        "variant": "dual_glassware",
        "instruction": (
            "辅助臂打开并保持已完成加热的烘箱门；操作臂依次取出烧杯和锥形瓶并放到"
            "主实验桌指定区域；辅助臂关闭烘箱门；操作臂按下电源摇臂关闭烘箱。"
        ),
        "target_vessels": [
            "obj_sample_beaker",
            "obj_sample_conical_flask",
        ],
        "target_regions": {
            "obj_sample_beaker": {
                "center_xyz_m": [0.62, -0.16, 0.755],
                "xy_tolerance_m": 0.10,
            },
            "obj_sample_conical_flask": {
                "center_xyz_m": [0.40, 0.14, 0.755],
                "xy_tolerance_m": 0.10,
            },
        },
        "steps": [
            {"id": "open_door", "actor": "auxiliary_arm", "skill": "pull"},
            {"id": "remove_beaker", "actor": "operating_arm", "skill": "pick"},
            {
                "id": "place_beaker_on_table",
                "actor": "operating_arm",
                "skill": "place",
            },
            {
                "id": "remove_conical_flask",
                "actor": "operating_arm",
                "skill": "pick",
            },
            {
                "id": "place_conical_flask_on_table",
                "actor": "operating_arm",
                "skill": "place",
            },
            {"id": "close_door", "actor": "auxiliary_arm", "skill": "push"},
            {"id": "power_off", "actor": "operating_arm", "skill": "press"},
        ],
    }


def _metrics() -> dict[str, Any]:
    weighted = (
        ("door_open", 0.15),
        ("beaker_removed", 0.15),
        ("beaker_placed_on_table", 0.10),
        ("conical_flask_removed", 0.15),
        ("conical_flask_placed_on_table", 0.10),
        ("door_closed", 0.15),
        ("oven_powered_off", 0.20),
    )
    return {
        "schema_version": "metrics/v0.4",
        "aggregation": {
            "type": "weighted_progress_score",
            "normalization": "declared_sum",
            "primary_metric_id": "oven_powered_off",
        },
        "metrics": [
            {
                "id": metric_id,
                "type": "rubric_condition",
                "weight": weight,
                "source_ref": {"source_order": 12, "item": f"变体时序{index + 1}"},
            }
            for index, (metric_id, weight) in enumerate(weighted)
        ],
    }


def _configure_scene(scene: Path) -> None:
    from pxr import Gf, Usd, UsdGeom

    stage = Usd.Stage.Open(str(scene))
    if stage is None:
        raise RuntimeError(f"cannot open {scene}")

    cart = stage.GetPrimAtPath("/World/obj_oven_cart")
    cart.GetAttribute("xformOp:scale").Set(Gf.Vec3d(1.0, 1.0, 0.7))
    cart.SetCustomDataByKey("scenario_forge:guiTrsEditable", True)
    cart.SetCustomDataByKey("scenario_forge:heightScale", 0.7)
    cart.SetCustomDataByKey("scenario_forge:scalePolicy", "fixed_xy_z_height_only")

    oven = stage.GetPrimAtPath("/World/obj_oven")
    _set_translation(oven, (1.51, 0.0, 0.5285))
    oven.GetAttribute("xformOp:scale").Set(Gf.Vec3d(1.0, 1.0, 1.0))
    oven.SetCustomDataByKey(
        "scenario_forge:pairedAlignmentRule",
        "same_xy_delta; oven_z=cart_z+0.755*cart_scale_z; oven_scale=1",
    )

    beaker = stage.GetPrimAtPath("/World/obj_sample_beaker")
    _set_translation(beaker, (1.40, -0.05, 0.8135))

    stage.RemovePrim("/World/obj_context_conical_flask")
    flask = UsdGeom.Xform.Define(stage, "/World/obj_sample_conical_flask").GetPrim()
    flask.GetReferences().AddReference(
        "deps/flask/asset.usd", "/World/ConicalFlask90x35Warp"
    )
    _set_translation(flask, (1.61, -0.05, 0.8135))

    control = stage.GetPrimAtPath("/World/obj_oven/Instance/ControlPanel")
    values = {
        "oven:mainsPower": True,
        "oven:heatingEnabled": False,
        "oven:heaterActive": False,
        "oven:chamberLightEnabled": True,
        "oven:temperatureSetpointC": 65.0,
        "oven:actualTemperatureC": 65.0,
        "oven:timerSetSeconds": 1800.0,
        "oven:timerRemainingSeconds": 0.0,
        "oven:elapsedSeconds": 1800.0,
        "oven:operatingState": "complete",
        "ui:page": "home",
        "ui:selectedField": "home",
    }
    for name, value in values.items():
        control.GetAttribute(name).Set(value)
    stage.GetPrimAtPath(
        "/World/obj_oven/Instance/Joints/MainsRocker"
    ).GetAttribute("drive:angular:physics:targetPosition").Set(8.0)
    world = stage.GetPrimAtPath("/World")
    world.SetCustomDataByKey("scenario_forge:taskId", TASK_ID)
    world.SetCustomDataByKey("scenario_forge:taskVariant", "dual_glassware")
    stage.GetRootLayer().Save()


def build_handoff(output: Path = DEFAULT_OUTPUT) -> Task12OvenUnloadResult:
    output = output.resolve()
    root = output / HANDOFF_ID
    if output.exists():
        raise FileExistsError(f"refusing to replace output: {output}")
    if not (R15_ROOT / "scene.usd").is_file():
        raise FileNotFoundError(R15_ROOT / "scene.usd")
    shutil.copytree(R15_ROOT, root)
    shutil.rmtree(root / "evidence")
    for stale in ("task_r15.json", "task_r14.json"):
        path = root / stale
        if path.exists():
            path.unlink()

    _configure_scene(root / "scene.usd")
    (root / "task_config.py").write_text(_task_config(), encoding="utf-8")
    (root / "task.yaml").write_text(
        yaml.safe_dump(_task(), allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (root / "metrics.yaml").write_text(
        yaml.safe_dump(_metrics(), allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (root / "task12.json").write_text(
        json.dumps(
            {
                "schema_version": "scenario-forge-task12-oven-unload-controls/v0.1",
                "door_joint": "obj_oven.Instance.Joints.DoorHinge",
                "shutdown_control": "obj_oven.Instance.ControlPanel.MainsSwitch.Rocker",
                "initial_process_state": "complete",
                "cart_scale_xyz": [1.0, 1.0, 0.7],
                "oven_xyz_m": [1.51, 0.0, 0.5285],
                "shelf": "obj_oven.Instance.Shelves.Shelf_0",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "README_CN.md").write_text(
        """# Scientific Workbench Task 12 双器皿取出 VR

使用 Isaac Sim 4.1 打开 `scene.usd`。初始门关闭；烧杯与锥形瓶均为空的
SDF 薄壁可交互容器，并排位于烘箱下层 `Shelf_0`。面板初始为通电、65°C、
加热完成且腔体灯开启；任务要求依次把两件器皿放到主实验桌，再关门并按
电源摇臂关机。

烘箱采用 `/World/obj_oven/Instance/...` 铰接层级。设备架仅缩短高度：
`obj_oven_cart.scale = (1, 1, 0.7)`；烘箱保持原尺寸，底面高度为 0.5285 m。
在 GUI 移动工位时，设备架、烘箱和两件器皿必须使用相同 XY 位移。

本包只声明场景、静置和设备功能证据，不声明机器人策略或 benchmark 成功。
""",
        encoding="utf-8",
    )

    inherited_manifest = json.loads((R15_ROOT / "manifest.json").read_text())
    manifest = {
        "schema_version": "scenario-forge-task12-oven-unload-vr/v0.1",
        "status": "static_built_runtime_pending",
        "entrypoints": {
            "scene": "scene.usd",
            "task_config": "task_config.py",
            "task": "task.yaml",
            "metrics": "metrics.yaml",
            "controls": "task12.json",
        },
        "source_evidence": inherited_manifest.get("source_evidence", {}),
        "claims": {
            "articulated_instance_layout_v1": True,
            "all_links_under_instance": True,
            "dual_empty_sdf_vessels": True,
            "initial_process_state": "complete",
            "cart_height_scale": 0.7,
            "oven_scale": 1.0,
            "vr_only": True,
            "robot_policy_success": False,
            "benchmark_success": False,
        },
        "lineage": {
            "base_handoff": "scientific_workbench_task09_r15_vr",
            "base_manifest_sha256": _sha(R15_ROOT / "manifest.json"),
        },
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    archive = output / f"{HANDOFF_ID}.zip"
    shutil.make_archive(
        str(archive.with_suffix("")), "zip", root_dir=output, base_dir=HANDOFF_ID
    )
    return Task12OvenUnloadResult(root, archive, manifest_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    print(build_handoff(args.output).archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

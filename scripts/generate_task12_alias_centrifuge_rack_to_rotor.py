#!/usr/bin/env python3
"""Generate the temporary Task 12 alias: rack-to-rotor tube transfer + STOP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import generate_scientific_workbench_task11_vr_r9 as r9  # noqa: E402
from scripts import generate_scientific_workbench_task11_vr_r8 as shared  # noqa: E402


ALIAS_ID = "scientific_workbench_task12_alias_centrifuge_rack_to_rotor"
DEFAULT_OUT = ROOT / "outputs/scientific_workbench_task12_alias_centrifuge_rack_to_rotor_vr_r1_20260827"
TARGET_RACK_SLOT = "slot_15ml_r00_c02"
TARGET_ROTOR_SOCKET = 18
BALANCE_ROTOR_SOCKET = 6
INSTRUCTION = (
    "按下离心机OPEN开盖按钮，从管架中拿起带液体的15 mL离心管，"
    "插入离心机转子目标孔位，释放稳定后按下STOP关机。"
)


def _local_group(names: list[str]) -> dict[str, object]:
    return {
        "objs": names,
        "mode": "local",
        "yaw_range_degrees": [0.0, 0.0],
        "x_offset_range": [-0.01, 0.01],
        "y_offset_range": [-0.01, 0.01],
    }


def build(output: Path) -> Path:
    from pxr import Gf, Usd, UsdGeom

    output = r9.build(output.resolve(), r9.r8.DEFAULT_CENTRIFUGE, r9.DEFAULT_TUBE)
    vr = output / "vr"
    scene = vr / "scene.usd"
    stage = Usd.Stage.Open(str(scene), Usd.Stage.LoadAll)
    stage.SetEditTarget(stage.GetRootLayer())
    rack_frame = stage.GetPrimAtPath(
        f"/World/obj_mixed_rack/__frames/{TARGET_RACK_SLOT}_inserted_bottom"
    )
    if not rack_frame:
        raise RuntimeError(f"materialized rack frame is missing: {TARGET_RACK_SLOT}")
    target_xyz = UsdGeom.XformCache().GetLocalToWorldTransform(
        rack_frame
    ).ExtractTranslation()
    target = stage.GetPrimAtPath("/World/obj_primary_tube")
    target.GetAttribute("xformOp:translate").Set(Gf.Vec3d(*target_xyz))
    target.GetAttribute("xformOp:orient").Set(Gf.Quatf(1.0, Gf.Vec3f(0.0)))
    stage.RemovePrim("/World/obj_balance_tube/VisualLiquid")
    for name in ("obj_bg_50ml_00", "obj_bg_50ml_01"):
        stage.RemovePrim(f"/World/{name}")
    stage.GetRootLayer().Save()
    if (vr / "deps/context50").exists():
        shutil.rmtree(vr / "deps/context50")

    object_names = [
        "obj_centrifuge",
        "obj_mixed_rack",
        "obj_primary_tube",
        "obj_balance_tube",
        *(f"obj_bg_15ml_{index:02d}" for index in range(6)),
        *shared.CONTEXT_LAYOUT,
    ]
    task = {
        "scene_usd_file_path": {"scene1": "__SCENE_PATH__"},
        "obj_prim_list": [f"/World/_scene/{name}" for name in object_names],
        "layout_randomization": {
            "table": "table",
            "objects": [
                _local_group(["obj_centrifuge", "obj_balance_tube"]),
                _local_group(
                    [
                        "obj_mixed_rack",
                        "obj_primary_tube",
                        *(f"obj_bg_15ml_{index:02d}" for index in range(6)),
                    ]
                ),
                *[_local_group([name]) for name in shared.CONTEXT_LAYOUT],
            ],
        },
        "robot_cfg": {
            "position": [0.0, -1.02, 0.31],
            "orientation": [0.7071067812, 0.0, 0.0, 0.7071067812],
        },
        "physx_scene_cfg": {
            "BroadphaseType": "GPU",
            "EnableGPUDynamics": True,
            "SolverType": "TGS",
            "TimeStepsPerSecond": 120,
        },
        "visual_liquid": {
            "mode": "visual_static_liquid",
            "liquid_interactive": False,
            "particle_system_count": 0,
            "instances": ["/World/obj_primary_tube/VisualLiquid"],
        },
        "task_alias": {
            "alias_task_number": 12,
            "canonical_catalog_modified": False,
            "transfer_direction": "rack_to_rotor",
            "target_rack_slot": TARGET_RACK_SLOT,
            "target_rotor_socket": TARGET_ROTOR_SOCKET,
            "balance_rotor_socket": BALANCE_ROTOR_SOCKET,
            "manual_close_and_latch": False,
        },
        "instruction": INSTRUCTION,
        "validation_scope": "scene_static_robot_free_transfer_and_device_mechanics",
    }
    config = (
        "from pathlib import Path\n_ASSETS_DIR = Path(__file__).resolve().parent\nTASKS = "
        + repr({ALIAS_ID: task}).replace(
            "'__SCENE_PATH__'", "str(_ASSETS_DIR / 'scene.usd')"
        )
        + "\n"
    )
    (vr / "task_config.py").write_text(config, encoding="utf-8")

    visual_path = output / "visual_liquid_manifest.json"
    visual = json.loads(visual_path.read_text())
    visual["status"] = "authored_pending_runtime_inspection"
    visual["instances"] = [
        item
        for item in visual["instances"]
        if item["container_prim"] == "/World/obj_primary_tube"
    ]
    visual.pop("scene_usd_sha256", None)
    visual_path.write_text(json.dumps(visual, indent=2, sort_keys=True) + "\n")

    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["schema_version"] = "scenario-forge.task12-alias-rack-to-rotor/v1"
    manifest["scenario_id"] = ALIAS_ID
    manifest["status"] = "alias_scene_pending_runtime"
    manifest["alias_task_number"] = 12
    manifest["canonical_catalog_modified"] = False
    manifest["canonical_task_conflict"] = "official Task 12 remains oven_unload_shutdown"
    manifest["instruction"] = INSTRUCTION
    manifest["target_rack_slot"] = TARGET_RACK_SLOT
    manifest["target_rotor_socket"] = TARGET_ROTOR_SOCKET
    manifest["balance_rotor_socket"] = BALANCE_ROTOR_SOCKET
    manifest["visual_liquids"] = visual["instances"]
    manifest["claims"].update(
        {
            "target_tube_starts_in_rack": True,
            "target_rotor_socket_initially_empty": True,
            "no_50ml_tubes": True,
            "manual_close_and_latch": False,
            "scene_static_stability": False,
            "robot_free_transfer_oracle_success": False,
            "robot_policy_success": False,
            "task_success": False,
            "benchmark_success": False,
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(build(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

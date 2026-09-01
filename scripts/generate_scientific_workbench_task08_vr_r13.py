#!/usr/bin/env python3
"""Generate Task 08 r13 with a USD-contained one-turn assisted thread."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Sequence

from pxr import Gf, Sdf, Usd

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.generate_scientific_workbench_task08_vr_r12 import (  # noqa: E402
    CONTEXT,
    build as build_r12,
)


TASK_ID = "scientific_workbench_tighten_centrifuge_tube_cap_vr_r13"
DEFAULT_OUT = ROOT / "outputs/scientific_workbench_task08_vr_r13_20260901"
ASSISTED_SET = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "scientific_workbench_task08_assisted_thread_r1_20260901"
)
ASSISTED_TUBE_ENTRY = "/World/Tube15LongNeckThreadedBody"
ASSISTED_CAP_ENTRY = "/World/Tube15LongNeckThreadedClosedCap"
CONTROLLER_SOURCE = ROOT / "scripts/task08_assisted_thread_controller.py"
GRAPH_PATH = "/World/TaskRuntime/AssistedThreadGraph"
CONTRACT_PATH = "/World/TaskRuntime/AssistedThreadContract"
LOCK_PATH = "/World/TaskRuntime/ClosedLock"


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _task_config(object_names: list[str]) -> str:
    def group(names: list[str]) -> dict[str, Any]:
        return {
            "objs": names,
            "mode": "local",
            "yaw_range_degrees": [0.0, 0.0],
            "x_offset_range": [-0.01, 0.01],
            "y_offset_range": [-0.01, 0.01],
        }

    task = {
        "scene_usd_file_path": {"scene1": "__SCENE_PATH__"},
        "obj_prim_list": [f"/World/_scene/{name}" for name in object_names],
        "layout_randomization": {
            "table": "table",
            "objects": [
                group(["obj_tube_rack", "obj_tube_00", "obj_tube_01", "obj_tube_02"]),
                group(["obj_steel_plate", "obj_cap_00", "obj_cap_01", "obj_cap_02"]),
                *[group([name]) for name in CONTEXT],
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
        "task_semantics": {
            "target_tube": "obj_tube_01",
            "target_cap": "obj_cap_01",
            "sequence": ["pick_cap", "pick_tube", "align", "mate", "twist", "return_tube"],
            "terminal_cap_release_required": True,
            "thread_success_claimed": False,
        },
        "assisted_thread": {
            "mode": "usd_embedded_virtual_fixture",
            "target_tube_prim": "/World/obj_tube_01",
            "target_cap_prim": "/World/obj_cap_01",
            "tighten_direction_top_view": "clockwise",
            "effective_lead_m_per_turn": 0.0076,
            "close_angle_degrees": 350.0,
            "full_turn_degrees": 360.0,
            "terminal_retention": "usd_embedded_pose_follow_lock",
            "physical_thread_contact": False,
        },
        "visual_liquid": {
            "mode": "visual_static_liquid",
            "fill_fraction": 0.8,
            "interactive": False,
            "particle_system_count": 0,
        },
    }
    return (
        "from pathlib import Path\n"
        "_ASSETS_DIR = Path(__file__).resolve().parent\n"
        "TASKS = "
        + repr({TASK_ID: task}).replace(
            "'__SCENE_PATH__'", "str(_ASSETS_DIR / 'scene.usd')"
        )
        + "\n"
    )


def _author_contract(stage: Usd.Stage) -> None:
    contract = stage.DefinePrim(CONTRACT_PATH, "Scope")
    values = {
        "assistedThread:effectiveLeadMPerTurn": (Sdf.ValueTypeNames.Float, 0.0076),
        "assistedThread:travelM": (Sdf.ValueTypeNames.Float, 0.0076),
        "assistedThread:closedRelativeZM": (Sdf.ValueTypeNames.Float, 0.1074),
        "assistedThread:closeAngleDegrees": (Sdf.ValueTypeNames.Float, 350.0),
        "assistedThread:fullTurnDegrees": (Sdf.ValueTypeNames.Float, 360.0),
        "assistedThread:captureRadialM": (Sdf.ValueTypeNames.Float, 0.006),
        "assistedThread:captureTiltDegrees": (Sdf.ValueTypeNames.Float, 20.0),
        "assistedThread:abortRadialM": (Sdf.ValueTypeNames.Float, 0.012),
        "assistedThread:abortTiltDegrees": (Sdf.ValueTypeNames.Float, 35.0),
        "assistedThread:state": (Sdf.ValueTypeNames.Token, "free"),
        "assistedThread:progress": (Sdf.ValueTypeNames.Float, 0.0),
        "assistedThread:accumulatedClockwiseDegrees": (Sdf.ValueTypeNames.Float, 0.0),
        "assistedThread:rawRadialErrorM": (Sdf.ValueTypeNames.Float, 0.0),
        "assistedThread:rawTiltErrorDegrees": (Sdf.ValueTypeNames.Float, 0.0),
        "assistedThread:rawRelativeZM": (Sdf.ValueTypeNames.Float, 0.0),
        "assistedThread:targetRelativeZM": (Sdf.ValueTypeNames.Float, 0.115),
        "assistedThread:lastCorrectionM": (Sdf.ValueTypeNames.Float, 0.0),
        "assistedThread:closed": (Sdf.ValueTypeNames.Bool, False),
        "assistedThread:physicalThreadContact": (Sdf.ValueTypeNames.Bool, False),
    }
    for name, (type_name, value) in values.items():
        contract.CreateAttribute(name, type_name).Set(value)
    contract.CreateRelationship("assistedThread:targetTube").SetTargets(
        ["/World/obj_tube_01"]
    )
    contract.CreateRelationship("assistedThread:targetCap").SetTargets(
        ["/World/obj_cap_01"]
    )


def _author_lock(stage: Usd.Stage) -> None:
    lock = stage.DefinePrim(LOCK_PATH, "Scope")
    lock.CreateAttribute("assistedThread:active", Sdf.ValueTypeNames.Bool).Set(False)
    lock.CreateAttribute("assistedThread:mode", Sdf.ValueTypeNames.Token).Set(
        "usd_embedded_pose_follow"
    )
    lock.CreateAttribute(
        "assistedThread:relativeYawDegrees", Sdf.ValueTypeNames.Float
    ).Set(0.0)


def _author_graph(stage: Usd.Stage, script: str) -> None:
    graph = stage.DefinePrim(GRAPH_PATH, "OmniGraph")
    graph.CreateAttribute("evaluationMode", Sdf.ValueTypeNames.Token).Set("Automatic")
    graph.CreateAttribute("evaluator:type", Sdf.ValueTypeNames.Token).Set("execution")
    graph.CreateAttribute("fabricCacheBacking", Sdf.ValueTypeNames.Token).Set("Shared")
    graph.CreateAttribute("fileFormatVersion", Sdf.ValueTypeNames.Int2).Set(
        Gf.Vec2i(1, 9)
    )
    graph.CreateAttribute("pipelineStage", Sdf.ValueTypeNames.Token).Set(
        "pipelineStageSimulation"
    )
    graph.CreateAttribute("runtime:execution", Sdf.ValueTypeNames.Token).Set(
        "on_playback_tick"
    )
    graph.CreateAttribute("runtime:graphRole", Sdf.ValueTypeNames.Token).Set(
        "task08_one_turn_assisted_thread"
    )
    tick = stage.DefinePrim(GRAPH_PATH + "/OnPhysicsStep", "OmniGraphNode")
    tick.CreateAttribute("node:type", Sdf.ValueTypeNames.Token).Set(
        "omni.isaac.core_nodes.OnPhysicsStep"
    )
    tick.CreateAttribute("node:typeVersion", Sdf.ValueTypeNames.Int).Set(2)
    controller = stage.DefinePrim(GRAPH_PATH + "/Controller", "OmniGraphNode")
    controller.CreateAttribute("node:type", Sdf.ValueTypeNames.Token).Set(
        "omni.graph.scriptnode.ScriptNode"
    )
    controller.CreateAttribute("node:typeVersion", Sdf.ValueTypeNames.Int).Set(2)
    controller.CreateAttribute("inputs:script", Sdf.ValueTypeNames.String).Set(script)
    controller.CreateAttribute("inputs:usePath", Sdf.ValueTypeNames.Bool).Set(False)
    controller.CreateAttribute("runtime:inlineScriptSha256", Sdf.ValueTypeNames.String).Set(
        sha256(script.encode()).hexdigest()
    )
    controller.CreateAttribute("inputs:execIn", Sdf.ValueTypeNames.UInt).SetConnections(
        [Sdf.Path(GRAPH_PATH + "/OnPhysicsStep.outputs:step")]
    )


def build(output: Path = DEFAULT_OUT) -> Path:
    output = output.resolve()
    assisted_manifest = json.loads((ASSISTED_SET / "asset_set_manifest.json").read_text())
    if assisted_manifest.get("status") != "candidate_runtime_pending":
        raise RuntimeError("ConvertAsset assisted-thread set is unavailable")
    build_r12(output)
    vr = output / "vr"
    for name, package in (
        ("tube", "tube15_long_neck_assisted_thread_body_r1"),
        ("cap", "tube15_long_neck_assisted_thread_cap_r1"),
    ):
        destination = vr / "deps" / name
        shutil.rmtree(destination)
        shutil.copytree(ASSISTED_SET / "packages" / package, destination)
    stage = Usd.Stage.Open(str(vr / "scene.usd"))
    _author_contract(stage)
    _author_lock(stage)
    script = CONTROLLER_SOURCE.read_text()
    _author_graph(stage, script)
    stage.GetRootLayer().Save()
    object_names = [
        "obj_tube_rack",
        "obj_steel_plate",
        "obj_tube_00",
        "obj_tube_01",
        "obj_tube_02",
        "obj_cap_00",
        "obj_cap_01",
        "obj_cap_02",
        *CONTEXT,
    ]
    (vr / "task_config.py").write_text(_task_config(object_names))
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.update(
        {
            "schema_version": "scenario-forge.task08-vr-candidate/v0.13",
            "release_id": "r13",
            "task_id": TASK_ID,
            "status": "r13_assisted_thread_pending_runtime",
            "assisted_thread": {
                "graph_prim": GRAPH_PATH,
                "contract_prim": CONTRACT_PATH,
                "lock_prim": LOCK_PATH,
                "controller_sha256": _sha(CONTROLLER_SOURCE),
                "asset_set": str(ASSISTED_SET),
                "effective_lead_m_per_turn": 0.0076,
                "close_angle_degrees": 350.0,
                "retention": "usd_embedded_pose_follow_lock",
            },
        }
    )
    manifest["claims"].update(
        {
            "vr_action_collection_layout_ready": False,
            "scene_static_stability": False,
            "assisted_thread": True,
            "physical_thread_contact": False,
            "thread_interaction_ready": False,
            "task08_success": False,
            "robot_policy_success": False,
            "benchmark_success": False,
        }
    )
    _write_json(manifest_path, manifest)
    (output / "README_CN.md").write_text(
        "# Task 08 r13 VR 一圈式辅助拧盖候选\n\n"
        "打开 `vr/scene.usd`。目标仍为中间离心管和中间红盖。管帽进入管口附近后，"
        "USD 内置行为图将顺时针约一圈映射为 7.6 mm 下沉；闭合后由 USD 内置位姿锁"
        "保持。视觉细牙保留，但不用于接触求解。该候选在 Isaac 4.1 运行验证完成前不"
        "声明任务成功或机器人策略成功。\n"
    )
    return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    print(build(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

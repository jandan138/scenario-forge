#!/usr/bin/env python3
"""Build the r1.1 dual-runtime Lift2 validation bundle."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Any, Sequence
import zipfile

import yaml


ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "scientific_workbench_traditional_acid_base_titration_vr_r1_1_robot"
DEFAULT_R1 = (
    ROOT
    / "outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_20260904/"
    "handoff/scientific_workbench_traditional_acid_base_titration_vr_r1"
)
DEFAULT_BASE = (
    ROOT
    / "outputs/scientific_workbench_task02_r10_2_fill_sweep_20260819/"
    "packages/fill40/ebench"
)
DEFAULT_OUTPUT = (
    ROOT
    / "outputs/scientific_workbench_traditional_acid_base_titration_"
    "vr_r1_1_robot_20260904"
)
ROBOT_USD = Path(
    "/cpfs/shared/simulation/zhuzihou/dev/GenManip/saved/assets/"
    "robot_usds/lift2/robot.usd"
)
SCENE_REL = Path("assets/scene_usds/scenario_forge/titration_r1_1/scene.usda")
SOURCE_SCENE_REL = SCENE_REL.parent / "source_bundle/vr/scene.usd"
STATION_PRIM = "/World/obj_titration_station"
TASK_OBJECTS = (
    "obj_magnetic_stirrer",
    "obj_receiver_flask",
    "obj_sample_beaker",
    "obj_context_conical_flask",
)


@dataclass(frozen=True)
class RobotBundleResult:
    root: Path
    genmanip: Path
    isaac45: Path
    manifest: Path


def finalize_blocked(root: Path, evidence: Path) -> Path:
    """Attach a failed contact-oracle attempt without promoting robot claims."""

    root = root.resolve()
    evidence = evidence.resolve()
    required = ("report.json", "isaac41_main.mp4", "isaac41_closeup.mp4")
    missing = [name for name in required if not (evidence / name).is_file()]
    if missing:
        raise FileNotFoundError(f"missing robot evidence: {missing}")
    destination = root / "evidence/robot_validation/isaac41"
    destination.mkdir(parents=True, exist_ok=True)
    copied: dict[str, dict[str, Any]] = {}
    attachments = list(required)
    for optional in (
        "full_attempt_report.json",
        "motion_pass_report.json",
        "lower_grasp_failure_report.json",
        "validation_summary.json",
    ):
        if (evidence / optional).is_file():
            attachments.append(optional)
    for name in attachments:
        target = destination / name
        shutil.copy2(evidence / name, target)
        copied[name] = {
            "path": target.relative_to(root).as_posix(),
            "sha256": _sha(target),
            "size_bytes": target.stat().st_size,
        }

    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary_path = evidence / "validation_summary.json"
    summary = (
        json.loads(summary_path.read_text(encoding="utf-8"))
        if summary_path.is_file()
        else None
    )
    if summary is not None:
        if summary.get("status") != "robot_validation_blocked":
            raise ValueError("validation summary must fail closed")
        if any(bool(value) for value in summary.get("claims", {}).values()):
            raise ValueError("blocked validation summary cannot promote claims")
        manifest["status"] = summary["status"]
        manifest["claims"].update(summary["claims"])
        manifest["robot_validation"] = summary["robot_validation"]
        manifest["robot_validation"].setdefault("isaac41", {})["evidence"] = copied
        _write_json(manifest_path, manifest)
        note = root / "ROBOT_VALIDATION_BLOCKED_CN.md"
        note.write_text(
            "# 机器人验证结论\n\n"
            "详细判定见 `evidence/robot_validation/isaac41/validation_summary.json`。"
            "本包保持 fail-closed：脚本机器人、策略、benchmark 与跨运行时成功均未声明。\n",
            encoding="utf-8",
        )
    else:
        manifest["status"] = "robot_validation_blocked"
        manifest["claims"].update(
            {
                "isaac41_scripted_robot_oracle_success": False,
                "isaac45_trace_replay_success": False,
                "scripted_robot_oracle_success": False,
                "robot_policy_success": False,
                "benchmark_success": False,
            }
        )
        manifest["robot_validation"] = {
            "canonical_layout": True,
            "isaac41": {
                "status": "blocked",
                "attempts_completed": 1,
                "required_passes": 3,
                "blocker": "original_40mm_handle_collider_produced_unilateral_contact",
                "handle_visual_span_m": 0.0509125,
                "handle_collision_wing_span_m": 0.04,
                "observed_failed_grasp_inner_gap_m": 0.0638994,
                "observed_gap_is_intrinsic_gripper_minimum": False,
                "observed_one_jaw_peak_angle_deg": 49.9719,
                "reverse_close_reached": False,
                "evidence": copied,
            },
            "isaac45": {
                "status": "not_run_prerequisite_failed",
                "reason": "no successful Isaac 4.1 command trace exists to replay",
                "required_passes": 3,
            },
            "claim_boundary": (
                "The videos prove a real Lift2 contact attempt and one-jaw stopcock "
                "motion only; they do not prove task, policy, benchmark, or runtime "
                "parity success."
            ),
        }
        _write_json(manifest_path, manifest)

        note = root / "ROBOT_VALIDATION_BLOCKED_CN.md"
        note.write_text(
            "# r1.1 机器人验证结论\n\n"
            "Isaac Sim 4.1 中，Lift2 左臂已真实接触并推动原始旋塞；"
            "没有在初始化后直接写旋塞关节或任务物体位姿。\n\n"
            "完整任务未通过：旋塞视觉跨度约 50.9 mm，但原物理碰撞翼片只有 40 mm；"
            "失败姿态下观测到的两指间隙约 63.9 mm，形成了单侧接触。"
            "单侧接触可把旋塞推到约 50°，但不能可靠反向关闭，因此不能完成 "
            "OPEN → FINE → DRIP → CLOSED 与 15.0 ± 0.3 mL。\n\n"
            "63.9 mm 是这次失败抓取的观测值，不是 Lift2 的固有最小开口。\n\n"
            "Isaac 4.5 未执行，因为不存在通过的 4.1 命令轨迹可供冻结回放。"
            "视频是失败诊断证据，不是成功演示。\n",
            encoding="utf-8",
        )

    handoff = root / "handoff"
    handoff.mkdir(exist_ok=True)
    archive = handoff / f"{root.name}_robot_validation_blocked.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or handoff in path.parents:
                continue
            bundle.write(path, Path(root.name) / path.relative_to(root))
    return archive


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _source_pose(stage: Any, path: str) -> tuple[list[float], list[float]]:
    from pxr import UsdGeom

    matrix = UsdGeom.XformCache().GetLocalToWorldTransform(stage.GetPrimAtPath(path))
    point = matrix.ExtractTranslation()
    quat = matrix.ExtractRotationQuat()
    imaginary = quat.GetImaginary()
    return (
        [float(point[index]) for index in range(3)],
        [
            float(quat.GetReal()),
            float(imaginary[0]),
            float(imaginary[1]),
            float(imaginary[2]),
        ],
    )


def _task_version(task_id: str) -> str:
    return task_id.rsplit("_vr_", 1)[-1].removesuffix("_robot")


def _build_genmanip(root: Path, base: Path, task_id: str) -> Path:
    from pxr import Sdf, Usd, UsdGeom, UsdPhysics

    out = root / "adapters/ebench/genmanip"
    adapter_slug = f"titration_{_task_version(task_id)}"
    scene_rel = Path(f"assets/scene_usds/scenario_forge/{adapter_slug}/scene.usda")
    copied_vr = out / scene_rel.parent / "source_bundle/vr"
    shutil.copytree(root, copied_vr, ignore=shutil.ignore_patterns("adapters"))
    copied_scene = Usd.Stage.Open(str(copied_vr / "scene.usd"))
    tick = copied_scene.GetPrimAtPath(
        "/World/obj_titration_station/Instance/Runtime/TitrationFlowGraph/"
        "OnPhysicsStep"
    )
    tick.GetAttribute("node:type").Set("omni.isaac.core_nodes.OnPhysicsStep")
    copied_scene.GetRootLayer().Save()

    wrapper_path = out / scene_rel
    wrapper = Usd.Stage.CreateNew(str(wrapper_path))
    UsdGeom.SetStageMetersPerUnit(wrapper, 1.0)
    UsdGeom.SetStageUpAxis(wrapper, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(wrapper, "/World").GetPrim()
    wrapper.SetDefaultPrim(world)
    scene_root = UsdGeom.Xform.Define(wrapper, "/World/_scene")
    scene_root.GetPrim().GetReferences().AddReference(
        "source_bundle/vr/scene.usd", "/World"
    )
    flat = copied_scene.Flatten(False)
    Sdf.CopySpec(
        flat,
        "/World/PhysicsScene",
        wrapper.GetRootLayer(),
        "/physicsScene",
    )
    wrapper.OverridePrim("/World/_scene/PhysicsScene").SetActive(False)
    table = UsdGeom.Xform.Define(wrapper, "/World/_scene/obj_table")
    table.GetPrim().GetReferences().AddReference(
        "source_bundle/vr/scene.usd", "/World/table"
    )
    wrapper.OverridePrim("/World/_scene/table").SetActive(False)
    wrapper.GetRootLayer().Save()

    config = yaml.safe_load((base / "config.yaml").read_text(encoding="utf-8"))
    evaluation = config["evaluation_configs"][0]
    evaluation.update(
        {
            "task_name": f"scenario_forge/{adapter_slug}",
            "usd_name": scene_rel.with_suffix("").as_posix(),
            "instruction": (
                "左臂抓住滴定管旋塞，依次经过粗滴、细调、逐滴和关闭；"
                "在淡粉终点关闭保持三秒后释放。"
            ),
            "num_steps": 7200,
            "physics_dt": 1.0 / 120.0,
            "rendering_dt": 1.0 / 60.0,
        }
    )
    evaluation["robots"] = [
        {
            "type": "manip/lift2/R5a",
            "position": [0.0, -1.02, 0.31],
            "orientation": [0.7071067812, 0.0, 0.0, 0.7071067812],
        }
    ]
    camera_rel = Path("cameras/fixed_camera_lift2.yml")
    (out / camera_rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(base / camera_rel, out / camera_rel)
    evaluation["domain_randomization"]["cameras"]["config_path"] = str(camera_rel)
    evaluation["generation_config"]["goal"] = []
    evaluation["generation_config"]["articulation"] = {
        "titration_station": {
            "is_articulated": True,
            "target_positions": [0.0],
        }
    }
    evaluation["object_config"] = {
        "titration_station": {
            "type": "existed_object",
            "uid_list": ["titration_station"],
            "is_articulated": True,
            "target_positions": [0.0],
            "articulation_info": {"is_articulated": True, "part": {}},
        },
        **{
            name.removeprefix("obj_"): {
                "type": "existed_object",
                "uid_list": [name.removeprefix("obj_")],
            }
            for name in TASK_OBJECTS
        },
    }
    (out / "config.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    source_scene = Usd.Stage.Open(str(root / "scene.usd"))
    base_episode = json.loads(
        next(base.glob("tasks/scenario_forge/*/002/episode_metadata.json")).read_text()
    )
    base_episode["task_data"]["goal"] = []
    base_layout = base_episode["task_data"]["initial_layout"]
    station_position, station_orientation = _source_pose(source_scene, STATION_PRIM)
    layout: dict[str, Any] = {
        "00000000000000000000000000000000": base_layout[
            "00000000000000000000000000000000"
        ],
        "lift2": base_layout["lift2"],
        "titration_station": {
            "type": "articulation",
            "prim_path": "/World/_scene/obj_titration_station",
            "position": station_position,
            "orientation": station_orientation,
            "scale": [1.0, 1.0, 1.0],
            "joint_positions": [0.0],
        },
    }
    for name in TASK_OBJECTS:
        position, orientation = _source_pose(source_scene, f"/World/{name}")
        prim = source_scene.GetPrimAtPath(f"/World/{name}")
        uid = name.removeprefix("obj_")
        layout[uid] = {
            "type": "rigid" if prim.HasAPI(UsdPhysics.RigidBodyAPI) else "object",
            "prim_path": f"/World/_scene/{name}",
            "path": "",
            "position": position,
            "orientation": orientation,
            "scale": [1.0, 1.0, 1.0],
            "add_colliders": False,
            "add_rigid_body": False,
            "is_articulation_part": False,
        }
    base_episode["task_data"]["initial_layout"] = layout
    base_episode["task_data"]["scenario_forge_runtime_contract"] = {
        "task_id": task_id,
        "operating_arm": "left",
        "auxiliary_arm": "idle",
        "station_uid": "titration_station",
        "handle_prim": (
            "/World/_scene/obj_titration_station/Instance/Burette/"
            "stopcock_handle_link"
        ),
        "required_sequence": ["OPEN", "FINE", "DRIP", "CLOSED"],
        "success_window_ml": [14.7, 15.3],
        "closed_hold_seconds": 3.0,
        "post_initialization_device_joint_writes_allowed": False,
        "post_initialization_object_pose_writes_allowed": False,
    }
    episode_path = out / f"tasks/scenario_forge/{adapter_slug}/001/episode_metadata.json"
    _write_json(episode_path, base_episode)
    _write_json(
        out / "package_manifest.json",
        {
            "schema_version": (
                f"scenario-forge-titration-{_task_version(task_id).replace('_', '.')}"
                "-genmanip/v1"
            ),
            "task_id": task_id,
            "runtime": "isaac_sim_4.1_genmanip_lift2",
            "scene_usd": scene_rel.as_posix(),
            "source_scene_sha256": _sha(root / "scene.usd"),
            "claims": {
                "scripted_robot_oracle_success": False,
                "robot_policy_success": False,
                "benchmark_success": False,
            },
        },
    )
    return out


def _build_isaac45(root: Path, task_id: str) -> Path:
    out = root / "adapters/isaac45/replay"
    out.mkdir(parents=True)
    _write_json(
        out / "replay_contract.json",
        {
            "schema_version": (
                f"scenario-forge-titration-{_task_version(task_id).replace('_', '.')}"
                "-isaac45-replay/v1"
            ),
            "task_id": task_id,
            "scene": "../../../scene.usd",
            "robot": {
                "usd_path": str(ROBOT_USD),
                "usd_sha256": _sha(ROBOT_USD),
                "prim_path": "/World/lift2",
                "position": [0.0, -1.02, 0.31],
                "orientation": [0.7071067812, 0.0, 0.0, 0.7071067812],
            },
            "trace": {
                "manifest_schema": "eeos.titration_lift2_command_trace.v1",
                "npz_arrays": [
                    "time_s",
                    "joint_position_targets",
                    "gripper_position_targets",
                    "phase_id",
                ],
                "physics_dt_s": 1.0 / 120.0,
            },
            "robot_command_mode": "drive_position_targets",
            "post_initialization_device_joint_writes_allowed": False,
            "post_initialization_object_pose_writes_allowed": False,
            "required_cold_start_passes": 3,
        },
    )
    _write_json(
        out / "camera_contract.json",
        {
            "schema_version": "scenario-forge-titration-video-cameras/v1",
            "resolution": [1280, 720],
            "fps": 30,
            "main": {
                "position": [1.55, -2.05, 1.8],
                "target": [0.0, 0.02, 0.95],
                "focal_length_mm": 30.0,
            },
            "closeup": {
                "position": [0.48, -0.72, 1.28],
                "target": [-0.02, 0.03, 1.02],
                "focal_length_mm": 54.0,
            },
            "hud": False,
        },
    )
    return out


def build(
    output: Path = DEFAULT_OUTPUT,
    *,
    r1: Path = DEFAULT_R1,
    base: Path = DEFAULT_BASE,
    task_id: str = TASK_ID,
) -> RobotBundleResult:
    output = output.resolve()
    r1 = r1.resolve()
    base = base.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to replace output: {output}")
    shutil.copytree(r1, output)
    for stale in (output / "evidence/runtime", output / "handoff"):
        if stale.exists():
            shutil.rmtree(stale)
    genmanip = _build_genmanip(output, base, task_id)
    isaac45 = _build_isaac45(output, task_id)
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "schema_version": (
                "scenario-forge-traditional-titration-vr-"
                f"{_task_version(task_id).replace('_', '.')}/v1"
            ),
            "package_id": task_id,
            "status": "robot_validation_pending",
            "robot_validation": {
                "canonical_layout": True,
                "isaac41_required_passes": 3,
                "isaac45_required_passes": 3,
                "videos": [
                    "isaac41_main.mp4",
                    "isaac41_closeup.mp4",
                    "isaac45_replay_main.mp4",
                    "isaac45_replay_closeup.mp4",
                ],
            },
        }
    )
    manifest["claims"].update(
        {
            "scripted_robot_oracle_success": False,
            "isaac41_scripted_robot_oracle_success": False,
            "isaac45_trace_replay_success": False,
            "robot_policy_success": False,
            "benchmark_success": False,
        }
    )
    _write_json(manifest_path, manifest)
    return RobotBundleResult(output, genmanip, isaac45, manifest_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--r1", type=Path, default=DEFAULT_R1)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--task-id", default=TASK_ID)
    args = parser.parse_args(argv)
    print(
        build(args.output, r1=args.r1, base=args.base, task_id=args.task_id).root
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

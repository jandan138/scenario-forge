from __future__ import annotations

import json
from pathlib import Path

import yaml
from pxr import Usd

from scripts.build_traditional_titration_robot_bundle import build, finalize_blocked


def test_builds_isolated_41_and_45_robot_adapters(tmp_path) -> None:
    result = build(tmp_path / "robot_bundle")
    source = Usd.Stage.Open(str(result.root / "scene.usd"))
    source_tick = source.GetPrimAtPath(
        "/World/obj_titration_station/Instance/Runtime/TitrationFlowGraph/"
        "OnPhysicsStep"
    )
    assert source_tick.GetAttribute("node:type").Get() == (
        "isaacsim.core.nodes.OnPhysicsStep"
    )

    copied_scene = Usd.Stage.Open(
        str(result.genmanip / "assets/scene_usds/scenario_forge/titration_r1_1/"
            "source_bundle/vr/scene.usd")
    )
    copied_tick = copied_scene.GetPrimAtPath(
        "/World/obj_titration_station/Instance/Runtime/TitrationFlowGraph/"
        "OnPhysicsStep"
    )
    assert copied_tick.GetAttribute("node:type").Get() == (
        "omni.isaac.core_nodes.OnPhysicsStep"
    )
    wrapper = Usd.Stage.Open(
        str(result.genmanip / "assets/scene_usds/scenario_forge/titration_r1_1/scene.usda")
    )
    assert wrapper.GetPrimAtPath("/World/_scene/obj_titration_station")
    assert wrapper.GetPrimAtPath("/physicsScene")

    replay = json.loads((result.isaac45 / "replay_contract.json").read_text())
    assert replay["post_initialization_device_joint_writes_allowed"] is False
    assert replay["post_initialization_object_pose_writes_allowed"] is False
    assert replay["robot_command_mode"] == "drive_position_targets"


def test_genmanip_contract_registers_one_dof_station_and_left_arm(tmp_path) -> None:
    result = build(tmp_path / "robot_bundle")
    config = yaml.safe_load((result.genmanip / "config.yaml").read_text())
    evaluation = config["evaluation_configs"][0]
    assert evaluation["robots"][0]["type"] == "manip/lift2/R5a"
    assert evaluation["generation_config"]["articulation"] == {
        "titration_station": {"is_articulated": True, "target_positions": [0.0]}
    }
    episode = json.loads(
        next(
            (result.genmanip / "tasks/scenario_forge/titration_r1_1").glob(
                "*/episode_metadata.json"
            )
        ).read_text()
    )
    contract = episode["task_data"]["scenario_forge_runtime_contract"]
    assert contract["operating_arm"] == "left"
    assert contract["auxiliary_arm"] == "idle"
    assert contract["required_sequence"] == ["OPEN", "FINE", "DRIP", "CLOSED"]
    assert contract["success_window_ml"] == [14.7, 15.3]


def test_bundle_starts_with_honest_robot_claims(tmp_path) -> None:
    result = build(tmp_path / "robot_bundle")
    manifest = json.loads(result.manifest.read_text())
    assert manifest["status"] == "robot_validation_pending"
    assert manifest["claims"]["scripted_robot_oracle_success"] is False
    assert manifest["claims"]["robot_policy_success"] is False
    assert manifest["claims"]["benchmark_success"] is False


def test_finalize_blocked_attaches_evidence_without_promoting_claims(tmp_path) -> None:
    result = build(tmp_path / "robot_bundle")
    evidence = tmp_path / "eos_evidence"
    evidence.mkdir()
    (evidence / "report.json").write_text(
        json.dumps(
            {
                "status": "diagnostic_blocked",
                "closed_loop_angle_milestones_deg": {"open": 49.97, "closed": 49.97},
            }
        ),
        encoding="utf-8",
    )
    (evidence / "isaac41_main.mp4").write_bytes(b"main-video")
    (evidence / "isaac41_closeup.mp4").write_bytes(b"closeup-video")

    archive = finalize_blocked(result.root, evidence)

    manifest = json.loads(result.manifest.read_text())
    assert manifest["status"] == "robot_validation_blocked"
    assert manifest["claims"]["scripted_robot_oracle_success"] is False
    assert manifest["claims"]["robot_policy_success"] is False
    assert manifest["claims"]["benchmark_success"] is False
    assert manifest["robot_validation"]["isaac45"]["status"] == (
        "not_run_prerequisite_failed"
    )
    assert archive.is_file()


def test_builds_r1_2_adapter_identity_from_r1_2_source(tmp_path) -> None:
    source = Path(
        "/cpfs/user/zhuzihou/dev/scenario-forge/outputs/"
        "scientific_workbench_traditional_acid_base_titration_vr_r1_2_20260905/"
        "handoff/scientific_workbench_traditional_acid_base_titration_vr_r1_2"
    )
    task_id = "scientific_workbench_traditional_acid_base_titration_vr_r1_2_robot"
    result = build(tmp_path / "robot_bundle", r1=source, task_id=task_id)
    manifest = json.loads(result.manifest.read_text())
    assert manifest["package_id"] == task_id
    config = yaml.safe_load((result.genmanip / "config.yaml").read_text())
    assert config["evaluation_configs"][0]["task_name"] == (
        "scenario_forge/titration_r1_2"
    )
    episode = next(
        (result.genmanip / "tasks/scenario_forge/titration_r1_2").glob(
            "*/episode_metadata.json"
        )
    )
    assert json.loads(episode.read_text())["task_data"][
        "scenario_forge_runtime_contract"
    ]["task_id"] == task_id


def test_finalize_blocked_uses_eos_validation_summary_when_present(tmp_path) -> None:
    result = build(tmp_path / "robot_bundle")
    evidence = tmp_path / "eos_evidence"
    evidence.mkdir()
    (evidence / "report.json").write_text('{"status":"diagnostic_blocked"}')
    (evidence / "isaac41_main.mp4").write_bytes(b"main")
    (evidence / "isaac41_closeup.mp4").write_bytes(b"close")
    summary = {
        "status": "robot_validation_blocked",
        "robot_validation": {
            "isaac41": {"status": "blocked_reproducibility_and_contact_evidence"},
            "isaac45": {"status": "not_run_prerequisite_failed"},
        },
        "claims": {
            "scripted_robot_oracle_success": False,
            "robot_policy_success": False,
            "benchmark_success": False,
        },
    }
    (evidence / "validation_summary.json").write_text(json.dumps(summary))
    finalize_blocked(result.root, evidence)
    manifest = json.loads(result.manifest.read_text())
    assert manifest["robot_validation"]["isaac41"]["status"] == (
        "blocked_reproducibility_and_contact_evidence"
    )
    assert "evidence" in manifest["robot_validation"]["isaac41"]
    assert manifest["status"] == "robot_validation_blocked"

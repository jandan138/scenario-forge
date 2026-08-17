from __future__ import annotations

import json
from math import isclose
from pathlib import Path

import yaml

import scripts.generate_scientific_workbench_r11 as r11
from scenario_forge.artifacts.usd_handoff import USDHandoffArchive
from scenario_forge.core.scenario import ScenarioSpec
from scripts.generate_scientific_workbench_r11 import (
    build_task05_scenario,
    build_task09_scenario,
)


def _object(scenario: dict[str, object], object_id: str) -> dict[str, object]:
    return next(  # type: ignore[return-value]
        item
        for item in scenario["objects"]  # type: ignore[union-attr]
        if item["id"] == object_id
    )


def test_task05_uses_flat_bottom_flask_and_exact_feishu_rubric() -> None:
    scenario = build_task05_scenario()

    ScenarioSpec.from_mapping(scenario)
    flask = _object(scenario, "obj_flask")
    stopper = _object(scenario, "obj_stopper")
    assert flask["asset_id"] == "scientific_workbench_r11_flat_bottom_flask_250ml_29_42"
    assert flask["source_prim_path"] == "/World/FlatBottomFlask2942"
    assert flask["named_frames"]["closure_seat"]["xyz"] == [0.0, 0.0, 0.10372]  # type: ignore[index]
    assert stopper["pose"]["xyz"][2] == 0.84382  # type: ignore[index]
    assert stopper["metadata"]["vr_randomization_group"] == (  # type: ignore[index]
        "task05_closure_assembly"
    )
    assert flask["metadata"]["vr_randomization_group"] == (  # type: ignore[index]
        "task05_closure_assembly"
    )
    twist = next(  # type: ignore[index]
        step
        for step in scenario["steps"]  # type: ignore[index]
        if step["id"] == "grasp_and_twist_stopper"
    )
    assert twist["parameters"]["source_fixture"] == "obj_flask"
    assert twist["parameters"]["source_frame"] == "obj_flask.closure_seat"
    assert twist["parameters"]["source_support_offset_xyz_m"] == [
        0.0,
        0.0,
        -0.0149,
    ]
    weights = [
        item["weight"]
        for item in scenario["success"]["progress_rubric"]["items"]  # type: ignore[index]
    ]
    assert weights == [0.20, 0.40, 0.25, 0.15]
    assert isclose(sum(weights), 1.0)


def test_task09_records_mount_support_sweep_and_exact_feishu_rubric() -> None:
    scenario = build_task09_scenario()

    ScenarioSpec.from_mapping(scenario)
    oven = _object(scenario, "obj_oven")
    assert scenario["schema_version"] == "scenario-spec/v0.6"
    assert oven["asset_id"] == "scientific_workbench_r11_analog_oven"
    assert oven["pose"] == {  # type: ignore[comparison-overlap]
        "xyz": [0.35, 0.0, 0.755],
        "wxyz": [1.0, 0.0, 0.0, 0.0],
    }
    metadata = oven["metadata"]  # type: ignore[assignment]
    assert metadata["articulated_pose_frame"] == "support_plane"  # type: ignore[index]
    assert metadata["tabletop_min_edge_clearance_m"] == 0.04  # type: ignore[index]
    assert metadata["tabletop_support_footprint"]["size_xy_m"] == [0.875, 0.693]  # type: ignore[index]
    assert metadata["visual_envelope_size_xyz_m"] == [0.875, 0.77, 0.9332]  # type: ignore[index]
    assert metadata["door_sweep_clearance_required"] is True  # type: ignore[index]
    conditions = [
        item["condition"]["type"]
        for item in scenario["success"]["progress_rubric"]["items"]  # type: ignore[index]
    ]
    assert conditions.count("articulation_joint_state_reached") == 6
    weights = [
        item["weight"]
        for item in scenario["success"]["progress_rubric"]["items"]  # type: ignore[index]
    ]
    assert weights == [0.10, 0.10, 0.10, 0.10, 0.15, 0.15, 0.10, 0.05, 0.05, 0.10]
    assert isclose(sum(weights), 1.0)
    assert scenario["metadata"]["visual_ready"] is True  # type: ignore[index]
    assert scenario["metadata"]["asset_interaction_ready"] is True  # type: ignore[index]
    assert scenario["metadata"]["task_interaction_ready"] is False  # type: ignore[index]
    assert scenario["metadata"]["robot_policy_success"] is False  # type: ignore[index]


def test_finalize_runtime_release_builds_two_task_handoff(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "r11"
    for task in ("task05", "task09"):
        package = output / "packages" / task
        ebench = package / "adapters/ebench/genmanip"
        vr = package / "adapters/vr_teleop"
        visual = ebench / "evidence/initial_scene"
        visual.mkdir(parents=True)
        (visual / "visual_ready_gate.yaml").write_text("status: passed\n", encoding="utf-8")
        (visual / "scene_overview.png").write_bytes(b"png")
        smoke = vr / "evidence/open_smoke/report.json"
        smoke.parent.mkdir(parents=True)
        smoke.write_text(json.dumps({"status": "pass"}), encoding="utf-8")

    def fake_bundle(**kwargs):
        root = kwargs["output_dir"] / kwargs["archive_id"]
        root.mkdir(parents=True)
        zip_path = kwargs["output_dir"] / f"{kwargs['archive_id']}.zip"
        zip_path.write_bytes(b"zip")
        assert [(item[0], item[1]) for item in kwargs["variants"]] == [
            (5, "remove_vessel_closure"),
            (9, "oven_load_start"),
        ]
        return USDHandoffArchive(root=root, zip_path=zip_path, task_numbers=(5, 9))

    monkeypatch.setattr(r11, "build_multi_task_dual_consumer_bundle", fake_bundle)

    destination = r11.finalize_runtime_release(output_dir=output)
    manifest = yaml.safe_load(destination.read_text(encoding="utf-8"))
    assert manifest["status"] == "runtime_complete_with_bounded_claims"
    assert manifest["task_counts"] == {"task05": 1, "task09": 1}
    assert all(item["runtime_preview"] == "pass" for item in manifest["packages"])
    assert all(item["vr_open_smoke"] == "pass" for item in manifest["packages"])
    for task in ("task05", "task09"):
        gate = yaml.safe_load(
            (output / "packages" / task / "evidence/phase11_visual_review_gate.yaml").read_text(
                encoding="utf-8"
            )
        )
        assert gate["status"] == "passed"

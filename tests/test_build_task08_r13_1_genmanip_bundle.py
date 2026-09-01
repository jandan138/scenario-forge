from __future__ import annotations

import json
from pathlib import Path

from pxr import Usd, UsdUtils
import yaml

from scripts.build_task08_r13_1_genmanip_bundle import build


def test_builds_nested_lift2_bundle_with_instance_aware_graph(tmp_path: Path) -> None:
    output = build(out=tmp_path / "genmanip")
    wrapper = output / "assets/scene_usds/scenario_forge/task08_r13_1/scene.usda"
    stage = Usd.Stage.Open(str(wrapper))
    assert stage.GetPrimAtPath("/World/_scene/obj_tube_01")
    assert stage.GetPrimAtPath("/World/_scene/obj_cap_01")
    assert stage.GetPrimAtPath(
        "/World/_scene/obj_cap_01/__aan_collision_proxy/grasp_box"
    )
    controller = stage.GetPrimAtPath(
        "/World/_scene/TaskRuntime/AssistedThreadGraph/Controller"
    )
    assert controller
    assert "_instance_root_from_node_path" in controller.GetAttribute(
        "inputs:script"
    ).Get()
    _, _, unresolved = UsdUtils.ComputeAllDependencies(str(wrapper))
    assert not unresolved


def test_bundle_declares_robot_inputs_without_promoting_success(tmp_path: Path) -> None:
    output = build(out=tmp_path / "genmanip")
    config = yaml.safe_load((output / "config.yaml").read_text())
    evaluation = config["evaluation_configs"][0]
    assert evaluation["physics_dt"] == 1 / 120
    assert evaluation["robots"][0]["type"] == "manip/lift2/R5a"
    assert {"tube_rack", "steel_plate", "tube_01", "cap_01"}.issubset(
        evaluation["object_config"]
    )
    assert not {
        item.get("type") for item in evaluation.get("preprocess_config", [])
    }.intersection(
        {
            "set_robot_physics_material",
            "set_robot_contact_offset",
            "set_robot_rest_offset",
        }
    )
    episode = json.loads(
        next(output.glob("tasks/scenario_forge/task08_r13_1/*/episode_metadata.json")).read_text()
    )
    layout = episode["task_data"]["initial_layout"]
    assert layout["tube_01"]["prim_path"] == "/World/_scene/obj_tube_01"
    assert layout["cap_01"]["prim_path"] == "/World/_scene/obj_cap_01"
    manifest = json.loads((output / "package_manifest.json").read_text())
    assert manifest["claims"] == {
        "core_robot_assisted_thread_success": False,
        "task08_scripted_oracle_success": False,
        "robot_policy_success": False,
        "benchmark_success": False,
    }

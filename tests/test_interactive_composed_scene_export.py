from __future__ import annotations

import json
from pathlib import Path

import yaml

from scenario_forge.adapters.ebench.genmanip import export_genmanip_collected_package
from scenario_forge.adapters.labutopia import load_labutopia_interactive_scene_handoff
from scenario_forge.adapters.vr_teleop import export_vr_teleop_package
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.package_compiler import compile_scenario_package
from scripts.generate_experimental_pbd_beaker_pour import (
    ASSET_ID,
    PACKAGE_ID,
    SCENARIO_ID,
    scenario_mapping,
)
from tests.test_labutopia_interactive_scene_handoff import write_interactive_handoff


def test_producer_scene_is_not_reinstanced_and_adapters_select_their_entrypoints(
    tmp_path: Path,
) -> None:
    producer, manifest_path = write_interactive_handoff(
        tmp_path / "producer", scenario_id=SCENARIO_ID
    )
    handoff = load_labutopia_interactive_scene_handoff(
        producer,
        manifest_path,
        producer_revision="producer-r1",
        expected_package_id=PACKAGE_ID,
        expected_entrypoints=("native", "genmanip", "vr"),
    )
    package = tmp_path / "compiled"
    compile_scenario_package(
        ScenarioSpec.from_mapping(scenario_mapping()),
        {
            ASSET_ID: handoff.to_local_usd_asset_source(
                asset_id=ASSET_ID, attribution=("LabUtopia",)
            )
        },
        package,
    )

    neutral_scene = (package / "scene/main.usda").read_text(encoding="utf-8")
    assert "native.usda" in neutral_scene
    assert "xformOp:translate" not in neutral_scene
    assert "obj_beaker2" not in neutral_scene

    gen = export_genmanip_collected_package(package)
    gen_scene = next(gen.output_dir.rglob("scene.usda")).read_text(encoding="utf-8")
    assert "genmanip.usdc" in gen_scene
    assert "prepend references" not in gen_scene
    assert 'def Xform "room"' in gen_scene
    config = yaml.safe_load((gen.output_dir / "tasks/config.yaml").read_text())
    evaluation = config["evaluation_configs"][0]
    assert evaluation["physics_dt"] == 1.0 / 600.0
    assert evaluation["physics_scene_config"]["TimeStepsPerSecond"] == 600
    episode = json.loads(next(gen.output_dir.rglob("episode_metadata.json")).read_text())
    layout = episode["task_data"]["initial_layout"]
    assert layout["beaker2"]["add_colliders"] is False
    assert layout["beaker2"]["add_rigid_body"] is False
    preview_request = yaml.safe_load(
        (gen.output_dir / "evidence/render_request.yaml").read_text(encoding="utf-8")
    )
    assert {
        name: view["expected_scene_visibility"]
        for name, view in preview_request["views"].items()
    } == {
        "workspace_closeup": "producer_entrypoint_scene_inherited",
        "scene_overview": "producer_entrypoint_scene_inherited",
        "task_object_closeup": "producer_entrypoint_scene_inherited",
    }
    assert preview_request["views"]["scene_overview"]["camera_reference_view"] == (
        "workspace_closeup"
    )
    assert preview_request["views"]["scene_overview"][
        "camera_distance_multiplier"
    ] == 1.6

    vr = export_vr_teleop_package(
        package, tmp_path / "vr", task_id=SCENARIO_ID
    )
    assert "@deps/scene/vr.usdc@" in vr.scene_usd.read_text(encoding="utf-8")
    config_text = vr.task_config.read_text(encoding="utf-8")
    assert f'"/World/{SCENARIO_ID}/obj_beaker2"' in config_text
    parity = json.loads(vr.parity_manifest.read_text(encoding="utf-8"))
    assert parity["static_support_contract"] == {
        "authority": "producer_entrypoint",
        "consumer_authored_collider": False,
    }

    metrics = yaml.safe_load((package / "metrics/metrics.yaml").read_text())
    by_id = {item["id"]: item for item in metrics["metrics"]}
    assert by_id["liquid_transfer_unscored"]["active"] is False
    assert by_id["release_instruction_only"]["active"] is False

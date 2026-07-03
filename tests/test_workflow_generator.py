from pathlib import Path

import pytest
import yaml

from scenario_forge.generation.workflows.workflow_composer import (
    WorkflowComposeError,
    compose_workflow_artifacts,
)
from scenario_forge.scaffold import scaffold_starter_package


def test_compose_pipette_workflow_writes_graph_assets_predicates_and_safety(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "starter")

    result = compose_workflow_artifacts(
        package_dir,
        task_family="pipette_transfer_light",
        robot_profile="franka_panda_tabletop_v1",
        bindings={
            "pipette": "pipette_001",
            "source_container": "source_tube_001",
            "target_container": "target_vial_001",
        },
    )

    generation_plan = load_yaml(package_dir / "generation_plan.yaml")
    task = load_yaml(package_dir / "task" / "task.yaml")
    graph = load_yaml(package_dir / "task" / "task_graph.yaml")
    predicates = load_yaml(package_dir / "task" / "predicates.yaml")
    safety = load_yaml(package_dir / "task" / "safety_rules.yaml")
    metrics = load_yaml(package_dir / "metrics" / "metrics.yaml")

    assert result.task_family == "pipette_transfer_light"
    assert result.required_asset_roles == ("pipette", "source_container", "target_container")
    assert generation_plan["task_family"] == "pipette_transfer_light"
    assert generation_plan["required_assets"][0]["role"] == "pipette"
    assert task["task_family"] == "pipette_transfer_light"
    assert task["bindings"]["source_container"] == "source_tube_001"
    assert [node["skill"] for node in graph["nodes"]] == [
        "move_to_object",
        "grasp",
        "aspirate",
        "dispense",
    ]
    assert graph["nodes"][2]["source"] == "source_tube_001"
    assert predicates["success_predicates"][0]["type"] == "liquid_transferred"
    assert predicates["success_predicates"][0]["target"] == "target_vial_001"
    assert safety["safety_rules"][0]["type"] == "no_spill"
    assert metrics["metrics"][0]["role"] == "primary_success"
    assert metrics["metrics"][0]["predicate"] == "liquid_transferred"


def test_compose_workflow_rejects_missing_robot_capability(tmp_path: Path) -> None:
    package_dir = scaffold_starter_package(tmp_path / "starter")

    with pytest.raises(
        WorkflowComposeError,
        match="Robot profile simple_gripper_tabletop_v1 missing capabilities: liquid_handling",
    ):
        compose_workflow_artifacts(
            package_dir,
            task_family="pipette_transfer_light",
            robot_profile="simple_gripper_tabletop_v1",
            bindings={
                "pipette": "pipette_001",
                "source_container": "source_tube_001",
                "target_container": "target_vial_001",
            },
        )


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))

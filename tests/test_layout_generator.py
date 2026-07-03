from pathlib import Path

import pytest
import yaml

from scenario_forge.generation.layout.layout_planner import (
    LayoutPlanError,
    plan_layout_artifacts,
)
from scenario_forge.generation.workflows.workflow_composer import compose_workflow_artifacts
from scenario_forge.scaffold import scaffold_starter_package


def test_plan_layout_writes_reachable_instances_and_layout_report(tmp_path: Path) -> None:
    package_dir = scaffold_starter_package(tmp_path / "starter")
    compose_workflow_artifacts(
        package_dir,
        task_family="pick_place",
        bindings={"object": "object_001", "target_zone": "target_zone"},
    )

    result = plan_layout_artifacts(package_dir, difficulty="hard")

    instances = load_yaml(package_dir / "scene" / "instances.yaml")
    layout = load_yaml(package_dir / "scene" / "layout.yaml")
    report = load_yaml(package_dir / "evidence" / "layout_checks.yaml")
    by_id = {instance["id"]: instance for instance in instances["instances"]}
    object_xyz = by_id["object_001"]["pose"]["xyz"]
    target_xyz = by_id["target_zone"]["pose"]["xyz"]

    assert result.difficulty == "hard"
    assert result.instance_count == 2
    assert layout["difficulty"] == "hard"
    assert object_xyz[0] <= 0.75
    assert abs(object_xyz[1]) <= 0.35
    assert round(target_xyz[0] - object_xyz[0], 2) >= 0.35
    assert report["status"] == "passed"
    assert report["checks"][0]["name"] == "robot_workspace_reachability"


def test_plan_layout_reports_unreachable_workspace_with_reason(tmp_path: Path) -> None:
    package_dir = scaffold_starter_package(tmp_path / "starter")
    compose_workflow_artifacts(
        package_dir,
        task_family="pick_place",
        bindings={"object": "object_001", "target_zone": "target_zone"},
    )
    constraints_dir = tmp_path / "constraints"
    constraints_dir.mkdir()
    write_yaml(
        constraints_dir / "layout_constraints.yaml",
        {
            "schema_version": "layout-constraints/v0.1",
            "workspace": {"x_range_m": [0.0, 0.1], "y_range_m": [-0.1, 0.1], "z_m": 0.92},
            "difficulty_profiles": {
                "easy": {
                    "target_distance_range_m": [0.15, 0.25],
                    "distractor_count": 0,
                    "occlusion": "none",
                    "clutter_level": "low",
                }
            },
        },
    )

    with pytest.raises(LayoutPlanError, match="object_001 outside robot workspace"):
        plan_layout_artifacts(package_dir, difficulty="easy", domain_pack_dir=constraints_dir)

    report = load_yaml(package_dir / "evidence" / "layout_checks.yaml")
    assert report["status"] == "failed"
    assert report["checks"][0]["reason"] == "object_001 outside robot workspace"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

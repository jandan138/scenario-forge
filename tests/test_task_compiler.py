from pathlib import Path

import pytest
import yaml

from scenario_forge.scaffold import scaffold_starter_package
from scenario_forge.task.task_compiler import TaskCompileError, compile_task_artifacts


def test_compile_pick_place_writes_task_predicates_and_primary_metric(tmp_path: Path) -> None:
    package_dir = scaffold_starter_package(tmp_path / "starter")

    result = compile_task_artifacts(package_dir, task_family="pick_place")

    task = load_yaml(package_dir / "task" / "task.yaml")
    task_graph = load_yaml(package_dir / "task" / "task_graph.yaml")
    predicates = load_yaml(package_dir / "task" / "predicates.yaml")
    safety_rules = load_yaml(package_dir / "task" / "safety_rules.yaml")
    metrics = load_yaml(package_dir / "metrics" / "metrics.yaml")

    assert result.object_instance_id == "object_001"
    assert result.target_zone_id == "target_zone"
    assert package_dir / "task" / "task.yaml" in result.artifacts
    assert task["task_family"] == "pick_place"
    assert task["bindings"] == {"object": "object_001", "target_zone": "target_zone"}
    assert task_graph["nodes"][0]["id"] == "pick_object_001"
    assert task_graph["nodes"][1]["id"] == "place_object_001_in_target_zone"
    assert predicates["success_predicates"][0]["type"] == "object_in_zone"
    assert predicates["success_predicates"][0]["object"] == "object_001"
    assert predicates["success_predicates"][0]["zone"] == "target_zone"
    assert safety_rules["safety_rules"][0]["object"] == "object_001"
    assert metrics["metrics"][0]["id"] == "task_success"
    assert metrics["metrics"][0]["role"] == "primary_success"
    assert metrics["metrics"][0]["predicate"] == "object_in_zone"
    assert metrics["metrics"][0]["adapter_hints"]["ebench"]["success_metric"] == "task_success"


def test_compile_pick_place_rejects_missing_target_zone(tmp_path: Path) -> None:
    package_dir = scaffold_starter_package(tmp_path / "starter")
    instances = load_yaml(package_dir / "scene" / "instances.yaml")
    for instance in instances["instances"]:
        instance["semantic_tags"] = [
            tag for tag in instance.get("semantic_tags", []) if tag not in {"target", "zone"}
        ]
        if instance["id"] == "target_zone":
            instance["role"] = "scene_object"
    write_yaml(package_dir / "scene" / "instances.yaml", instances)

    with pytest.raises(TaskCompileError, match="Missing required scene role for pick_place: target_zone"):
        compile_task_artifacts(package_dir, task_family="pick_place")


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

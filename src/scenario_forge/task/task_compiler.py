from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.generation.workflows.task_graph import build_pick_place_task_graph
from scenario_forge.scene.instance_binding import SceneInstanceError, load_scene_instances
from scenario_forge.task.metrics import build_primary_success_metric
from scenario_forge.task.predicates import ObjectInZonePredicate, select_pick_place_bindings

TASK_SCHEMA_VERSION = "task/v0.2"
PREDICATES_SCHEMA_VERSION = "predicates/v0.2"
SAFETY_RULES_SCHEMA_VERSION = "safety-rules/v0.2"
METRICS_SCHEMA_VERSION = "metrics/v0.2"


class TaskCompileError(ValueError):
    """Raised when task artifacts cannot be compiled from package contracts."""


@dataclass(frozen=True)
class TaskCompileResult:
    package_root: Path
    artifacts: tuple[Path, ...]
    object_instance_id: str
    target_zone_id: str


def compile_task_artifacts(
    package_root: str | Path,
    task_family: str = "pick_place",
) -> TaskCompileResult:
    if task_family != "pick_place":
        raise TaskCompileError(f"Unsupported task_family: {task_family}")

    root = Path(package_root)
    try:
        instances = load_scene_instances(root / "scene" / "instances.yaml")
        object_instance, target_zone = select_pick_place_bindings(instances)
    except (SceneInstanceError, ValueError) as exc:
        raise TaskCompileError(str(exc)) from exc

    object_id = object_instance.instance_id
    target_zone_id = target_zone.instance_id
    predicate = ObjectInZonePredicate(object_id, target_zone_id)
    graph = build_pick_place_task_graph(object_id, target_zone_id)

    artifacts = (
        write_yaml_artifact(root / "task" / "task.yaml", _task_yaml(object_id, target_zone_id)),
        write_yaml_artifact(root / "task" / "task_graph.yaml", graph.to_yaml()),
        write_yaml_artifact(root / "task" / "predicates.yaml", _predicates_yaml(predicate)),
        write_yaml_artifact(root / "task" / "safety_rules.yaml", _safety_rules_yaml(object_id)),
        write_yaml_artifact(
            root / "metrics" / "metrics.yaml",
            _metrics_yaml(build_primary_success_metric(object_id, target_zone_id)),
        ),
    )
    return TaskCompileResult(
        package_root=root,
        artifacts=artifacts,
        object_instance_id=object_id,
        target_zone_id=target_zone_id,
    )


def _task_yaml(object_instance_id: str, target_zone_id: str) -> dict[str, object]:
    return {
        "schema_version": TASK_SCHEMA_VERSION,
        "task_id": "place_object_on_target",
        "task_family": "pick_place",
        "instruction": "Move the object onto the target zone.",
        "bindings": {
            "object": object_instance_id,
            "target_zone": target_zone_id,
        },
    }


def _predicates_yaml(predicate: ObjectInZonePredicate) -> dict[str, object]:
    return {
        "schema_version": PREDICATES_SCHEMA_VERSION,
        "success_predicates": [predicate.to_yaml()],
    }


def _safety_rules_yaml(object_instance_id: str) -> dict[str, object]:
    return {
        "schema_version": SAFETY_RULES_SCHEMA_VERSION,
        "safety_rules": [{"type": "no_drop", "object": object_instance_id}],
    }


def _metrics_yaml(primary_success_metric: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": METRICS_SCHEMA_VERSION,
        "metrics": [primary_success_metric],
    }

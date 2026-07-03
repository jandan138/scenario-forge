from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scenario_forge.scene.instance_binding import SceneInstance


@dataclass(frozen=True)
class ObjectInZonePredicate:
    object_instance_id: str
    zone_instance_id: str

    def to_yaml(self) -> dict[str, str]:
        return {
            "type": "object_in_zone",
            "object": self.object_instance_id,
            "zone": self.zone_instance_id,
        }


def select_pick_place_bindings(
    instances: tuple[SceneInstance, ...],
) -> tuple[SceneInstance, SceneInstance]:
    object_instance = _first_matching_instance(
        instances,
        role_values={"manipulated_object"},
        tag_values={"pickable"},
    )
    if object_instance is None:
        raise ValueError("Missing required scene role for pick_place: manipulated_object")

    target_zone = _first_matching_instance(
        instances,
        role_values={"target_region", "goal_region"},
        tag_values={"target", "zone"},
    )
    if target_zone is None:
        raise ValueError("Missing required scene role for pick_place: target_zone")

    return object_instance, target_zone


def predicate_bindings_exist(predicate: dict[str, Any], instance_ids: set[str]) -> bool:
    object_id = predicate.get("object")
    zone_id = predicate.get("zone")
    return isinstance(object_id, str) and isinstance(zone_id, str) and {
        object_id,
        zone_id,
    }.issubset(instance_ids)


def _first_matching_instance(
    instances: tuple[SceneInstance, ...],
    role_values: set[str],
    tag_values: set[str],
) -> SceneInstance | None:
    for instance in instances:
        if instance.role in role_values or tag_values.intersection(instance.semantic_tags):
            return instance
    return None

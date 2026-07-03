from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskGraph:
    nodes: tuple[dict[str, str], ...]
    edges: tuple[dict[str, str], ...]

    def to_yaml(self) -> dict[str, object]:
        return {
            "schema_version": "task-graph/v0.2",
            "nodes": list(self.nodes),
            "edges": list(self.edges),
        }


def build_pick_place_task_graph(object_instance_id: str, target_zone_id: str) -> TaskGraph:
    pick_node = f"pick_{object_instance_id}"
    place_node = f"place_{object_instance_id}_in_{target_zone_id}"
    return TaskGraph(
        nodes=(
            {"id": pick_node, "type": "atomic_skill", "skill": "pick", "object": object_instance_id},
            {
                "id": place_node,
                "type": "atomic_skill",
                "skill": "place",
                "object": object_instance_id,
                "zone": target_zone_id,
            },
        ),
        edges=({"from": pick_node, "to": place_node, "condition": "object_grasped"},),
    )

from __future__ import annotations

from scenario_forge.generation.layout.constraints import Workspace


def first_unreachable_instance(
    instances: list[dict[str, object]], workspace: Workspace
) -> str | None:
    for instance in instances:
        pose = instance.get("pose")
        if not isinstance(pose, dict):
            return f"{instance.get('id', '<unknown>')} missing pose"
        xyz = pose.get("xyz")
        if not isinstance(xyz, list) or len(xyz) != 3:
            return f"{instance.get('id', '<unknown>')} missing xyz pose"
        x, y, _z = (float(xyz[0]), float(xyz[1]), float(xyz[2]))
        instance_id = str(instance.get("id", "<unknown>"))
        if x < workspace.x_min or x > workspace.x_max or y < workspace.y_min or y > workspace.y_max:
            return f"{instance_id} outside robot workspace"
    return None

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCENE_INSTANCES_SCHEMA_VERSION = "scene-instances/v0.2"


class SceneInstanceError(ValueError):
    """Raised when a scene instances file is malformed."""


@dataclass(frozen=True)
class SceneInstance:
    instance_id: str
    asset_id: str
    role: str
    xyz: tuple[float, float, float]
    wxyz: tuple[float, float, float, float]
    scale_xyz: tuple[float, float, float]
    semantic_tags: tuple[str, ...]
    initial_state: dict[str, Any]


def load_scene_instances(path: str | Path) -> tuple[SceneInstance, ...]:
    source_path = Path(path)
    if not source_path.exists():
        raise SceneInstanceError(f"Missing scene instances file: {source_path}")

    data = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SceneInstanceError(f"Scene instances must be a mapping: {source_path}")

    schema_version = _require_string(data, "schema_version")
    if schema_version != SCENE_INSTANCES_SCHEMA_VERSION:
        raise SceneInstanceError(
            f"Unsupported scene instances schema_version {schema_version!r}; "
            f"expected {SCENE_INSTANCES_SCHEMA_VERSION!r}"
        )

    raw_instances = data.get("instances")
    if not isinstance(raw_instances, list):
        raise SceneInstanceError("Scene instances field 'instances' must be a list")

    instances: list[SceneInstance] = []
    seen_ids: set[str] = set()
    for index, raw_instance in enumerate(raw_instances):
        if not isinstance(raw_instance, dict):
            raise SceneInstanceError(f"Scene instance at index {index} must be a mapping")

        instance_id = _require_string(raw_instance, "id")
        if instance_id in seen_ids:
            raise SceneInstanceError(f"Duplicate scene instance id: {instance_id}")
        seen_ids.add(instance_id)

        asset_id = _require_string(raw_instance, "asset_id")
        pose = raw_instance.get("pose")
        if not isinstance(pose, dict):
            raise SceneInstanceError(f"Scene instance {instance_id} field 'pose' must be a mapping")

        semantic_tags = raw_instance.get("semantic_tags", [])
        if not isinstance(semantic_tags, list) or not all(
            isinstance(tag, str) for tag in semantic_tags
        ):
            raise SceneInstanceError(
                f"Scene instance {instance_id} field 'semantic_tags' must be a list of strings"
            )

        initial_state = raw_instance.get("initial_state", {})
        if not isinstance(initial_state, dict):
            raise SceneInstanceError(
                f"Scene instance {instance_id} field 'initial_state' must be a mapping"
            )

        instances.append(
            SceneInstance(
                instance_id=instance_id,
                asset_id=asset_id,
                role=_optional_string(raw_instance, "role", default="scene_object"),
                xyz=_require_float_tuple(pose, "xyz", 3, instance_id),
                wxyz=_require_float_tuple(pose, "wxyz", 4, instance_id),
                scale_xyz=_optional_float_tuple(
                    pose,
                    "scale_xyz",
                    3,
                    instance_id,
                    default=(1.0, 1.0, 1.0),
                ),
                semantic_tags=tuple(semantic_tags),
                initial_state=initial_state,
            )
        )

    return tuple(instances)


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise SceneInstanceError(f"Scene instances field {key!r} must be a non-empty string")
    return value


def _optional_string(data: dict[str, Any], key: str, default: str) -> str:
    value = data.get(key, default)
    if not isinstance(value, str) or not value:
        raise SceneInstanceError(f"Scene instances field {key!r} must be a non-empty string")
    return value


def _require_float_tuple(
    data: dict[str, Any], key: str, expected_length: int, instance_id: str
) -> tuple[float, ...]:
    value = data.get(key)
    if not isinstance(value, list) or len(value) != expected_length:
        raise SceneInstanceError(
            f"Scene instance {instance_id} field 'pose.{key}' must have "
            f"{expected_length} numeric values"
        )
    if not all(isinstance(item, int | float) for item in value):
        raise SceneInstanceError(f"Scene instance {instance_id} field 'pose.{key}' must be numeric")
    return tuple(float(item) for item in value)


def _optional_float_tuple(
    data: dict[str, Any],
    key: str,
    expected_length: int,
    instance_id: str,
    *,
    default: tuple[float, ...],
) -> tuple[float, ...]:
    if key not in data:
        return default
    return _require_float_tuple(data, key, expected_length, instance_id)

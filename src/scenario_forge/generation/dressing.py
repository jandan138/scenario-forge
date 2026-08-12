from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import yaml


DRESSING_PRESETS_SCHEMA_VERSION = "scenario-forge-dressing-presets/v0.1"


def load_dressing_presets(path: str | Path) -> dict[str, dict[str, Any]]:
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("dressing preset file must be a mapping")
    if value.get("schema_version") != DRESSING_PRESETS_SCHEMA_VERSION:
        raise ValueError("unsupported dressing preset schema_version")
    raw_presets = value.get("presets")
    if not isinstance(raw_presets, Mapping) or not raw_presets:
        raise ValueError("dressing presets must be a non-empty mapping")
    presets: dict[str, dict[str, Any]] = {}
    for preset_id, raw_preset in raw_presets.items():
        if not isinstance(preset_id, str) or not preset_id:
            raise ValueError("dressing preset ids must be non-empty strings")
        if not isinstance(raw_preset, Mapping):
            raise ValueError(f"dressing preset {preset_id!r} must be a mapping")
        preset = deepcopy(dict(raw_preset))
        _validate_preset(preset_id, preset)
        presets[preset_id] = preset
    return presets


def apply_dressing_preset(
    scenario: Mapping[str, Any],
    *,
    preset_id: str,
    preset: Mapping[str, Any],
) -> dict[str, Any]:
    result = deepcopy(dict(scenario))
    raw_objects = result.get("objects")
    if not isinstance(raw_objects, list):
        raise ValueError("scenario objects must be a list")
    existing_ids = {
        item.get("id") for item in raw_objects if isinstance(item, Mapping)
    }
    context_objects: list[dict[str, Any]] = []
    for raw_item in preset["objects"]:
        item = deepcopy(dict(raw_item))
        object_id = item["id"]
        if object_id in existing_ids:
            raise ValueError(f"dressing object id conflicts with task object: {object_id}")
        item["role"] = "context_prop"
        item["metadata"] = {
            "dressing_preset_id": preset_id,
            "group_id": item.pop("group_id"),
            "metric_participation": "none",
        }
        context_objects.append(item)
    result["objects"] = [*raw_objects, *context_objects]
    metadata = result.setdefault("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("scenario metadata must be a mapping")
    metadata["dressing_preset_id"] = preset_id
    metadata["dressing_policy"] = "fixed_per_background_not_scored"
    return result


def _validate_preset(preset_id: str, preset: Mapping[str, Any]) -> None:
    objects = preset.get("objects")
    if not isinstance(objects, list) or not objects:
        raise ValueError(f"dressing preset {preset_id!r} objects must be non-empty")
    if len(objects) > 10:
        raise ValueError(f"dressing preset {preset_id!r} exceeds 10 dynamic bodies")
    ids: set[str] = set()
    groups: set[str] = set()
    for index, raw_item in enumerate(objects):
        if not isinstance(raw_item, Mapping):
            raise ValueError(f"dressing preset {preset_id!r} object {index} is invalid")
        for field in ("id", "asset_id", "source_prim_path", "group_id"):
            if not isinstance(raw_item.get(field), str) or not raw_item[field]:
                raise ValueError(
                    f"dressing preset {preset_id!r} object {index}.{field} is required"
                )
        object_id = str(raw_item["id"])
        if object_id in ids:
            raise ValueError(f"dressing preset {preset_id!r} has duplicate object ids")
        ids.add(object_id)
        groups.add(str(raw_item["group_id"]))
        pose = raw_item.get("pose")
        if not isinstance(pose, Mapping):
            raise ValueError(f"dressing preset {preset_id!r} object {object_id} needs pose")
        xyz = pose.get("xyz")
        if not isinstance(xyz, list) or len(xyz) != 3:
            raise ValueError(f"dressing preset {preset_id!r} object {object_id} needs xyz")
        x, y = float(xyz[0]), float(xyz[1])
        if not (-0.90 <= x <= 0.90 and -0.30 <= y <= 0.30):
            raise ValueError(
                f"dressing preset {preset_id!r} object {object_id} violates table edge margin"
            )
        if -0.38 <= x <= 0.38 and -0.30 <= y <= 0.20:
            raise ValueError(
                f"dressing preset {preset_id!r} object {object_id} enters task keep-out"
            )
    if not 4 <= len(groups) <= 6:
        raise ValueError(
            f"dressing preset {preset_id!r} must contain 4 to 6 visible groups"
        )

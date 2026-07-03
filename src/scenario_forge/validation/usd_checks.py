from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml

from scenario_forge.assets.lock import AssetLockError, load_asset_lock_file
from scenario_forge.scene.instance_binding import SceneInstanceError, load_scene_instances
from scenario_forge.scene.usd_paths import quote_usda_string, to_usd_identifier

BINDING_KEYS = frozenset(
    {
        "object",
        "zone",
        "instance",
        "target",
        "source",
        "container",
        "tool",
        "receptacle",
        "region",
    }
)


@dataclass(frozen=True)
class USDStaticCheckReport:
    ok: bool
    messages: tuple[str, ...]


def check_usd_scene(
    package_root: str | Path,
    scene_path: str | Path,
    asset_lock_path: str | Path,
    instances_path: str | Path,
    predicates_path: str | Path | None = None,
) -> USDStaticCheckReport:
    package_dir = Path(package_root)
    scene_file = Path(scene_path)
    messages: list[str] = []

    if not scene_file.exists():
        return USDStaticCheckReport(ok=False, messages=(f"Missing USD scene: {scene_file}",))

    try:
        lock = load_asset_lock_file(asset_lock_path)
        instances = load_scene_instances(instances_path)
    except (AssetLockError, SceneInstanceError) as exc:
        return USDStaticCheckReport(ok=False, messages=(str(exc),))

    source = scene_file.read_text(encoding="utf-8")
    locked_paths = {asset.resolved_path for asset in lock.assets.values()}
    for reference in _scan_usd_references(package_dir, scene_file, source):
        if reference not in locked_paths:
            messages.append(f"USD reference is not locked: {reference}")

    for instance in instances:
        prim = f'def Xform "{to_usd_identifier(instance.instance_id)}"'
        if prim not in source:
            messages.append(f"Missing USD prim for scene instance: {instance.instance_id}")
        if f"instance_id = {quote_usda_string(instance.instance_id)}" not in source:
            messages.append(f"Missing customData instance_id for: {instance.instance_id}")
        if f"asset_id = {quote_usda_string(instance.asset_id)}" not in source:
            messages.append(f"Missing customData asset_id for: {instance.instance_id}")

    if predicates_path is not None:
        messages.extend(_check_predicate_bindings(Path(predicates_path), {i.instance_id for i in instances}))

    return USDStaticCheckReport(ok=not messages, messages=tuple(messages))


def _scan_usd_references(package_root: Path, scene_path: Path, source: str) -> tuple[str, ...]:
    references: list[str] = []
    package_root_resolved = package_root.resolve()
    for match in re.finditer(r"@([^@]+)@", source):
        reference = match.group(1)
        if "://" in reference:
            continue
        if not reference.endswith((".usd", ".usda")):
            continue
        resolved = (scene_path.parent / reference).resolve()
        if resolved == package_root_resolved or package_root_resolved in resolved.parents:
            references.append(str(resolved.relative_to(package_root_resolved)))
        else:
            references.append(reference)
    return tuple(references)


def _check_predicate_bindings(predicates_path: Path, instance_ids: set[str]) -> tuple[str, ...]:
    if not predicates_path.exists():
        return ()
    data = yaml.safe_load(predicates_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return (f"Predicates file must be a mapping: {predicates_path}",)

    messages: list[str] = []
    for value in _iter_binding_values(data):
        if value not in instance_ids:
            messages.append(f"Predicate binding references missing instance '{value}'")
    return tuple(messages)


def _iter_binding_values(value: Any) -> tuple[str, ...]:
    bindings: list[str] = []
    if isinstance(value, dict):
        for key, raw_value in value.items():
            if key in BINDING_KEYS and isinstance(raw_value, str):
                bindings.append(raw_value)
            else:
                bindings.extend(_iter_binding_values(raw_value))
    elif isinstance(value, list):
        for item in value:
            bindings.extend(_iter_binding_values(item))
    return tuple(bindings)

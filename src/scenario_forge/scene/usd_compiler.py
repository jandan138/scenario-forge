from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scenario_forge.assets.lock import AssetLockEntry, AssetLockError, load_asset_lock_file
from scenario_forge.scene.instance_binding import SceneInstance, SceneInstanceError, load_scene_instances
from scenario_forge.scene.usd_paths import (
    format_usda_float_tuple,
    format_usda_string_array,
    quote_usda_string,
    scene_relative_reference,
    to_usd_identifier,
)


class USDSceneCompilerError(ValueError):
    """Raised when a USD scene cannot be compiled from package contracts."""


@dataclass(frozen=True)
class USDSceneCompileResult:
    path: Path
    instance_count: int
    references: tuple[str, ...]


def compile_usd_scene(
    package_root: str | Path,
    instances_path: str | Path,
    asset_lock_path: str | Path,
    out_path: str | Path,
) -> USDSceneCompileResult:
    package_dir = Path(package_root)
    output_path = Path(out_path)
    try:
        instances = load_scene_instances(instances_path)
        asset_lock = load_asset_lock_file(asset_lock_path)
    except (SceneInstanceError, AssetLockError) as exc:
        raise USDSceneCompilerError(str(exc)) from exc

    messages: list[str] = []
    resolved_entries: list[tuple[SceneInstance, AssetLockEntry]] = []
    for instance in instances:
        entry = asset_lock.assets.get(instance.asset_id)
        if entry is None:
            messages.append(f"Unresolved asset_id for {instance.instance_id}: {instance.asset_id}")
            continue
        asset_file = _resolve_package_file(package_dir, entry.resolved_path)
        if asset_file is None:
            messages.append(f"Locked asset path escapes package root: {entry.resolved_path}")
            continue
        if not asset_file.exists():
            messages.append(f"Missing locked asset file: {entry.resolved_path}")
            continue
        resolved_entries.append((instance, entry))

    if messages:
        raise USDSceneCompilerError("; ".join(messages))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    references = tuple(entry.resolved_path for _, entry in resolved_entries)
    output_path.write_text(
        _build_usda(package_dir, output_path, resolved_entries),
        encoding="utf-8",
    )
    return USDSceneCompileResult(
        path=output_path,
        instance_count=len(resolved_entries),
        references=references,
    )


def _build_usda(
    package_root: Path,
    scene_path: Path,
    resolved_entries: list[tuple[SceneInstance, AssetLockEntry]],
) -> str:
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "World"',
        "    metersPerUnit = 1",
        '    upAxis = "Z"',
        ")",
        "",
        'def Xform "World"',
        "{",
        '    def Xform "Instances"',
        "    {",
    ]

    for instance, entry in resolved_entries:
        reference = scene_relative_reference(package_root, scene_path, entry.resolved_path)
        lines.extend(_instance_prim_lines(instance, reference))

    lines.extend(
        [
            "    }",
            "",
            *(_robot_spawn_lines(package_root)),
            "",
            '    def DistantLight "KeyLight"',
            "    {",
            "        float intensity = 450",
            "        float angle = 0.25",
            "    }",
            "",
            '    def Camera "Camera"',
            "    {",
            "        double3 xformOp:translate = (1.5, -2, 1.4)",
            "        double3 xformOp:rotateXYZ = (60, 0, 35)",
            '        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]',
            "    }",
            "}",
            "",
        ]
    )
    return "\n".join(lines)


def _instance_prim_lines(instance: SceneInstance, reference: str) -> list[str]:
    prim_name = to_usd_identifier(instance.instance_id)
    return [
        f'        def Xform "{prim_name}" (',
        "            customData = {",
        f"                string instance_id = {quote_usda_string(instance.instance_id)}",
        f"                string asset_id = {quote_usda_string(instance.asset_id)}",
        f"                string role = {quote_usda_string(instance.role)}",
        f"                string[] semantic_tags = {format_usda_string_array(instance.semantic_tags)}",
        "            }",
        "        )",
        "        {",
        f"            double3 xformOp:translate = {format_usda_float_tuple(instance.xyz)}",
        f"            quatd xformOp:orient = {format_usda_float_tuple(instance.wxyz)}",
        f"            double3 xformOp:scale = {format_usda_float_tuple(instance.scale_xyz)}",
        '            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient", "xformOp:scale"]',
        "",
        '            def Xform "Asset" (',
        f"                references = @{reference}@",
        "            )",
        "            {",
        "            }",
        "        }",
        "",
    ]


def _robot_spawn_lines(package_root: Path) -> list[str]:
    robot_id = "unspecified_robot"
    spawn_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    spawn_wxyz: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)
    robot_path = package_root / "robot" / "robot.yaml"
    if robot_path.exists():
        data = yaml.safe_load(robot_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            raw_robot_id = data.get("robot_id")
            if isinstance(raw_robot_id, str) and raw_robot_id:
                robot_id = raw_robot_id
            raw_spawn = data.get("spawn")
            if isinstance(raw_spawn, dict):
                spawn_xyz = _optional_float_tuple(raw_spawn, "xyz", 3, spawn_xyz)
                spawn_wxyz = _optional_float_tuple(raw_spawn, "wxyz", 4, spawn_wxyz)

    return [
        '    def Xform "RobotSpawn" (',
        "        customData = {",
        f"            string robot_id = {quote_usda_string(robot_id)}",
        "        }",
        "    )",
        "    {",
        f"        double3 xformOp:translate = {format_usda_float_tuple(spawn_xyz)}",
        f"        quatd xformOp:orient = {format_usda_float_tuple(spawn_wxyz)}",
        '        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient"]',
        "    }",
    ]


def _optional_float_tuple(
    data: dict[str, Any],
    key: str,
    expected_length: int,
    default: tuple[float, ...],
) -> tuple[float, ...]:
    value = data.get(key)
    if not isinstance(value, list) or len(value) != expected_length:
        return default
    if not all(isinstance(item, int | float) for item in value):
        return default
    return tuple(float(item) for item in value)


def _resolve_package_file(root: Path, relative_path: str) -> Path | None:
    if "://" in relative_path:
        return None
    package_root = root.resolve()
    resolved = (package_root / relative_path).resolve()
    if resolved == package_root or package_root in resolved.parents:
        return resolved
    return None

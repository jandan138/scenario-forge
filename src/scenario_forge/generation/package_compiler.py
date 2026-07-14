from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
from typing import Any, Mapping, cast

from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.assets.checksum import compute_sha256
from scenario_forge.assets.lock import generate_asset_lock, write_asset_lock
from scenario_forge.assets.source import LocalUSDAssetSource
from scenario_forge.core.scenario import ScenarioSpec


@dataclass(frozen=True)
class ScenarioPackageCompileResult:
    package_root: Path
    artifacts: tuple[Path, ...]


@dataclass
class _PrimOverride:
    children: dict[str, "_PrimOverride"] = field(default_factory=dict)
    pose: Mapping[str, Any] | None = None
    active: bool | None = None
    reset_xform_stack: bool = False


def compile_scenario_package(
    spec: ScenarioSpec,
    asset_sources: Mapping[str, LocalUSDAssetSource],
    package_root: str | Path,
) -> ScenarioPackageCompileResult:
    """Compile a simulator-neutral ScenarioSpec into a portable v0.2 package.

    Local asset sources are copied, not converted.  The generated USD layer
    composes those canonical layers and authors only scenario pose overrides.
    Adapter-specific discovery layouts remain the responsibility of adapters.
    """

    root = Path(package_root)
    scenario = cast(dict[str, Any], spec.to_mapping())
    sources = _required_sources(scenario, asset_sources)
    _replace_output(root, sources)

    asset_entries = _copy_asset_closures(root, sources)
    scene_path = root / "scene" / "main.usda"
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    scene_path.write_text(_compile_scene_usda(scenario, sources), encoding="utf-8")

    write_yaml_artifact(root / "scenario.yaml", scenario)
    write_yaml_artifact(root / "scene" / "instances.yaml", _scene_instances(scenario))
    write_yaml_artifact(root / "task" / "task.yaml", _task_contract(scenario))
    write_yaml_artifact(root / "task" / "graph.yaml", _task_graph(scenario))
    write_yaml_artifact(root / "task" / "predicates.yaml", _predicates(scenario))
    write_yaml_artifact(root / "robot" / "robot.yaml", _robot_contract(scenario))
    write_yaml_artifact(root / "metrics" / "metrics.yaml", _metrics(scenario))
    write_yaml_artifact(root / "generation" / "plan.yaml", _generation_plan(scenario, sources))
    write_yaml_artifact(
        root / "assets" / "asset_manifest.yaml",
        {"schema_version": "asset-manifest/v0.2", "assets": asset_entries},
    )
    scenario_id = _string(scenario.get("scenario_id"), "scenario_id")
    write_asset_lock(
        root,
        generate_asset_lock(root, lock_id=f"{scenario_id}_asset_lock"),
    )
    write_yaml_artifact(
        root / "provenance" / "provenance.yaml",
        _provenance(scenario, asset_entries),
    )
    write_yaml_artifact(
        root / "evidence" / "validation_report.yaml",
        _validation_report(scenario, sources),
    )
    write_yaml_artifact(root / "manifest.yaml", _package_manifest(scenario))

    artifacts = tuple(sorted(path for path in root.rglob("*") if path.is_file()))
    return ScenarioPackageCompileResult(package_root=root, artifacts=artifacts)


def _required_sources(
    scenario: Mapping[str, Any],
    asset_sources: Mapping[str, LocalUSDAssetSource],
) -> tuple[LocalUSDAssetSource, ...]:
    scene = _mapping(scenario.get("scene"), "scene")
    objects = _mapping_list(scenario.get("objects"), "objects")
    base_asset_id = _string(scene.get("asset_id"), "scene.asset_id")
    overlay_asset_ids = _string_list(
        scene.get("overlay_asset_ids", []),
        "scene.overlay_asset_ids",
    )
    object_asset_ids = [
        _string(item.get("asset_id"), f"objects[{index}].asset_id")
        for index, item in enumerate(objects)
    ]
    overlay_object_conflicts = sorted(set(overlay_asset_ids).intersection(object_asset_ids))
    if overlay_object_conflicts:
        raise ValueError(
            "scene overlay assets cannot also be object assets: "
            + ", ".join(overlay_object_conflicts)
        )
    required_ids = _dedupe_strings(
        [
            *overlay_asset_ids,
            base_asset_id,
            *object_asset_ids,
        ]
    )

    missing = [asset_id for asset_id in required_ids if asset_id not in asset_sources]
    if missing:
        raise ValueError(f"missing local USD asset source(s): {', '.join(missing)}")

    sources: list[LocalUSDAssetSource] = []
    for asset_id in required_ids:
        source = asset_sources[asset_id]
        if source.asset_id != asset_id:
            raise ValueError(
                f"asset source key {asset_id!r} does not match source asset_id "
                f"{source.asset_id!r}"
            )
        if source.expected_sha256 is not None:
            actual_sha256 = compute_sha256(source.source_usd)
            if actual_sha256 != source.expected_sha256:
                raise ValueError(
                    f"asset source {asset_id!r} canonical USD checksum mismatch"
                )
        sources.append(source)
    misplaced_overlay_sources = [
        source.asset_id
        for source in sources
        if source.role == "scene_overlay" and source.asset_id not in overlay_asset_ids
    ]
    if misplaced_overlay_sources:
        raise ValueError(
            "scene_overlay asset sources must be listed in "
            "scene.overlay_asset_ids: "
            + ", ".join(misplaced_overlay_sources)
        )
    scene_root_prim_path = _string(
        scene.get("root_prim_path"),
        "scene.root_prim_path",
    )
    for overlay_asset_id in overlay_asset_ids:
        overlay = asset_sources[overlay_asset_id]
        if overlay.role != "scene_overlay":
            raise ValueError(
                f"overlay asset {overlay_asset_id!r} role must be 'scene_overlay'"
            )
        if overlay.root_prim_path != scene_root_prim_path:
            raise ValueError(
                f"overlay asset {overlay_asset_id!r} root_prim_path must match "
                "scene.root_prim_path"
            )
    return tuple(sources)


def _replace_output(root: Path, sources: tuple[LocalUSDAssetSource, ...]) -> None:
    output = root.resolve()
    for source in sources:
        source_directories = {
            source.source_usd.parent.resolve(),
            source.source_usd.resolve().parent,
        }
        for source_directory in source_directories:
            if (
                output == source_directory
                or output in source_directory.parents
                or source_directory in output.parents
            ):
                raise ValueError(
                    "package_root and local asset source directories must not overlap"
                )

    if root.is_symlink() or root.is_file():
        root.unlink()
    elif root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)


def _copy_asset_closures(
    root: Path, sources: tuple[LocalUSDAssetSource, ...]
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for source in sources:
        destination = root / "assets" / source.asset_id
        shutil.copytree(
            source.source_usd.parent,
            destination,
            ignore=_copy_ignore(source),
        )
        canonical_path = destination / source.source_usd.name
        canonical_sha256 = compute_sha256(canonical_path)
        if (
            source.expected_sha256 is not None
            and canonical_sha256 != source.expected_sha256
        ):
            raise ValueError(
                f"copied asset {source.asset_id!r} canonical USD checksum mismatch"
            )
        canonical_usd = canonical_path.relative_to(root).as_posix()
        entries.append(
            {
                "asset_id": source.asset_id,
                "role": source.role,
                "asset_type": "usd_scene",
                "canonical_usd": canonical_usd,
                "license": source.license,
                "sha256": canonical_sha256,
                "source_kind": (
                    "external_usd_package"
                    if source.upstream_package is not None
                    else "local_usd_directory"
                ),
                "source_uri": source.portable_source_uri(),
                "resolver_version": (
                    "scenario-forge/upstream-usd-package-v1"
                    if source.upstream_package is not None
                    else "scenario-forge/local-usd-source-v1"
                ),
                "attribution": list(source.attribution),
                "redistributable": source.redistributable,
                "closure_root": destination.relative_to(root).as_posix(),
                **(
                    {"root_prim_path": source.root_prim_path}
                    if source.root_prim_path is not None
                    else {}
                ),
                **(
                    {"upstream_package": source.upstream_package.to_mapping()}
                    if source.upstream_package is not None
                    else {}
                ),
                **(
                    {"excluded_relative_paths": list(source.exclude_relative_paths)}
                    if source.exclude_relative_paths
                    else {}
                ),
            }
        )
    return entries


def _copy_ignore(source: LocalUSDAssetSource) -> Any:
    excluded = set(source.exclude_relative_paths)
    source_root = source.source_usd.parent.resolve()

    def ignore(directory: str, names: list[str]) -> set[str]:
        relative_directory = Path(directory).resolve().relative_to(source_root)
        return {
            name
            for name in names
            if (relative_directory / name).as_posix() in excluded
        }

    return ignore


def _compile_scene_usda(
    scenario: Mapping[str, Any], sources: tuple[LocalUSDAssetSource, ...]
) -> str:
    scene = _mapping(scenario.get("scene"), "scene")
    root_prim_path = _usd_prim_path(
        _string(scene.get("root_prim_path"), "scene.root_prim_path"),
        "scene.root_prim_path",
    )
    objects = _mapping_list(scenario.get("objects"), "objects")
    sources_by_id = {source.asset_id: source for source in sources}
    source_layer_asset_ids = _source_layer_asset_ids(scenario)

    references = [
        (
            f"../assets/{asset_id}/"
            f"{sources_by_id[asset_id].source_usd.name}"
        )
        for asset_id in source_layer_asset_ids
    ]
    lines = [
        "#usda 1.0",
        "(",
        f'    defaultPrim = "{_usd_escape(root_prim_path.parts[0])}"',
        "    metersPerUnit = 1",
        '    upAxis = "Z"',
        "    subLayers = [",
        *[f"        @{reference}@," for reference in references],
        "    ]",
        ")",
        "",
    ]

    tree = _PrimOverride()
    root_node = tree
    for part in root_prim_path.parts:
        root_node = root_node.children.setdefault(part, _PrimOverride())
    source_pose = scene.get("pose")
    if source_pose is not None:
        root_node.pose = _mapping(source_pose, "scene.pose")

    for index, raw_path in enumerate(
        _string_list(scene.get("inactive_prim_paths", []), "scene.inactive_prim_paths")
    ):
        node = _prim_override_node(
            tree,
            root_prim_path,
            _usd_prim_path(raw_path, f"scene.inactive_prim_paths[{index}]"),
            f"scene.inactive_prim_paths[{index}]",
        )
        node.active = False

    for index, raw_path in enumerate(
        _string_list(
            scene.get("world_anchored_prim_paths", []),
            "scene.world_anchored_prim_paths",
        )
    ):
        node = _prim_override_node(
            tree,
            root_prim_path,
            _usd_prim_path(raw_path, f"scene.world_anchored_prim_paths[{index}]"),
            f"scene.world_anchored_prim_paths[{index}]",
        )
        node.reset_xform_stack = True

    seen_paths: set[str] = set()
    for index, item in enumerate(objects):
        field_name = f"objects[{index}].source_prim_path"
        prim_path = _usd_prim_path(_string(item.get("source_prim_path"), field_name), field_name)
        if prim_path.parts[: len(root_prim_path.parts)] != root_prim_path.parts:
            raise ValueError(f"{field_name} must be below scene.root_prim_path")
        if str(prim_path) in seen_paths:
            raise ValueError(f"duplicate source_prim_path: {prim_path}")
        seen_paths.add(str(prim_path))

        cursor = tree
        for part in prim_path.parts:
            cursor = cursor.children.setdefault(part, _PrimOverride())
        cursor.pose = _mapping(item.get("pose"), f"objects[{index}].pose")
        cursor.reset_xform_stack = True

    _render_prim_override(lines, root_prim_path.parts[-1], root_node, 0)
    return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class _USDPrimPath:
    raw: str
    parts: tuple[str, ...]

    def __str__(self) -> str:
        return self.raw


def _usd_prim_path(value: str, field_name: str) -> _USDPrimPath:
    if not value.startswith("/"):
        raise ValueError(f"{field_name} must be an absolute USD prim path")
    parts = tuple(value.split("/")[1:])
    if not parts or any(not part or part in {".", ".."} for part in parts):
        raise ValueError(f"{field_name} must be an absolute USD prim path")
    return _USDPrimPath(value, parts)


def _prim_override_node(
    tree: _PrimOverride,
    root_prim_path: _USDPrimPath,
    prim_path: _USDPrimPath,
    field_name: str,
) -> _PrimOverride:
    if prim_path.parts[: len(root_prim_path.parts)] != root_prim_path.parts:
        raise ValueError(f"{field_name} must be at or below scene.root_prim_path")
    cursor = tree
    for part in prim_path.parts:
        cursor = cursor.children.setdefault(part, _PrimOverride())
    return cursor


def _render_prim_override(
    lines: list[str], name: str, node: _PrimOverride, indentation: int
) -> None:
    indent = "    " * indentation
    metadata: list[str] = []
    if node.active is False:
        metadata.append("active = false")
    if metadata:
        lines.append(f'{indent}over "{_usd_escape(name)}" (')
        lines.extend(f"{indent}    {item}" for item in metadata)
        lines.append(f"{indent})")
    else:
        lines.append(f'{indent}over "{_usd_escape(name)}"')
    lines.append(f"{indent}{{")
    if node.pose is not None:
        pose = node.pose
        xyz = _number_list(pose.get("xyz"), "pose.xyz", 3)
        wxyz = _number_list(pose.get("wxyz"), "pose.wxyz", 4)
        lines.append(f"{indent}    double3 xformOp:translate = {_usda_tuple(xyz)}")
        lines.append(f"{indent}    quatd xformOp:orient = {_usda_tuple(wxyz)}")
        order = ["xformOp:translate", "xformOp:orient"]
        scale = pose.get("scale_xyz")
        if scale is not None:
            scale_xyz = _number_list(scale, "pose.scale_xyz", 3)
            lines.append(f"{indent}    double3 xformOp:scale = {_usda_tuple(scale_xyz)}")
            order.append("xformOp:scale")
        if node.reset_xform_stack:
            order.insert(0, "!resetXformStack!")
        order_text = ", ".join(f'"{item}"' for item in order)
        lines.append(f"{indent}    uniform token[] xformOpOrder = [{order_text}]")
    elif node.reset_xform_stack:
        lines.append(
            f'{indent}    uniform token[] xformOpOrder = ["!resetXformStack!", '
            '"xformOp:translate", "xformOp:orient", "xformOp:scale"]'
        )
    if node.pose is not None and node.children:
        lines.append("")
    for child_index, (child_name, child) in enumerate(node.children.items()):
        _render_prim_override(lines, child_name, child, indentation + 1)
        if child_index < len(node.children) - 1:
            lines.append("")
    lines.append(f"{indent}}}")


def _scene_composition_asset_ids(scene: Mapping[str, Any]) -> tuple[str, ...]:
    overlays = _string_list(
        scene.get("overlay_asset_ids", []),
        "scene.overlay_asset_ids",
    )
    return tuple([*overlays, _string(scene.get("asset_id"), "scene.asset_id")])


def _source_layer_asset_ids(scenario: Mapping[str, Any]) -> tuple[str, ...]:
    scene = _mapping(scenario.get("scene"), "scene")
    scene_asset_ids = _scene_composition_asset_ids(scene)
    object_asset_ids = [
        _string(item.get("asset_id"), f"objects[{index}].asset_id")
        for index, item in enumerate(
            _mapping_list(scenario.get("objects"), "objects")
        )
    ]
    # Dedicated object packages may delete or override opinions authored by the
    # full-scene source (for example a legacy nested rigid body). USD sublayers
    # are strongest first, so those object-specific layers must precede the
    # scene overlay/base stack. Objects sourced from the scene itself are
    # already covered by that stack and must not pull the base layer forward.
    dedicated_object_asset_ids = [
        asset_id for asset_id in object_asset_ids if asset_id not in scene_asset_ids
    ]
    return tuple(
        _dedupe_strings(
            [*dedicated_object_asset_ids, *scene_asset_ids]
        )
    )


def _scene_instances(scenario: Mapping[str, Any]) -> dict[str, Any]:
    instances: list[dict[str, Any]] = []
    for item in _mapping_list(scenario.get("objects"), "objects"):
        instance = dict(item)
        instance.setdefault("semantic_tags", [item["role"]])
        instance.setdefault("initial_state", {})
        instances.append(instance)
    return {
        "schema_version": "scene-instances/v0.2",
        "coordinate_system": {"units": "meters", "up_axis": "Z"},
        "instances": instances,
    }


def _task_contract(scenario: Mapping[str, Any]) -> dict[str, Any]:
    objects = _mapping_list(scenario.get("objects"), "objects")
    robot = _mapping(scenario.get("robot"), "robot")
    actors = _mapping_list(robot.get("actors"), "robot.actors")
    return {
        "schema_version": "task/v0.2",
        "task_id": scenario["scenario_id"],
        "task_family": scenario["task_family"],
        "instruction": scenario["instruction"],
        "bindings": {
            "objects": {str(item["role"]): item["id"] for item in objects},
            "actors": {str(item["id"]): item["end_effector"] for item in actors},
        },
        "steps": scenario["steps"],
        "invariants": scenario["invariants"],
        "success": scenario["success"],
        "max_steps": scenario["max_steps"],
        "seed": scenario["seed"],
    }


def _task_graph(scenario: Mapping[str, Any]) -> dict[str, Any]:
    steps = _mapping_list(scenario.get("steps"), "steps")
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    for item in steps:
        node = {key: value for key, value in item.items() if key != "depends_on"}
        nodes.append(node)
        dependencies = item.get("depends_on", [])
        if not isinstance(dependencies, list):
            raise ValueError("step.depends_on must be a list")
        edges.extend(
            {"from": str(dependency), "to": str(item["id"])}
            for dependency in dependencies
        )
    return {"schema_version": "task-graph/v0.2", "nodes": nodes, "edges": edges}


def _predicates(scenario: Mapping[str, Any]) -> dict[str, Any]:
    success = _mapping(scenario.get("success"), "success")
    predicates = success.get("predicates")
    if not isinstance(predicates, list):
        raise ValueError("success.predicates must be a list")
    return {"schema_version": "predicates/v0.2", "success_predicates": predicates}


def _robot_contract(scenario: Mapping[str, Any]) -> dict[str, Any]:
    robot = dict(_mapping(scenario.get("robot"), "robot"))
    return {"schema_version": "robot/v0.2", **robot}


def _metrics(scenario: Mapping[str, Any]) -> dict[str, Any]:
    success = _mapping(scenario.get("success"), "success")
    predicates = _mapping_list(success.get("predicates"), "success.predicates")
    metrics: list[dict[str, Any]] = []
    for index, predicate in enumerate(predicates):
        metrics.append(
            {
                "id": predicate["id"],
                "type": "predicate_satisfaction",
                "role": "primary_success" if index == 0 else "success_component",
                "predicate": predicate["type"],
                "sequence_index": predicate.get("sequence_index", index),
                "parameters": predicate.get("parameters", {}),
            }
        )
    return {"schema_version": "metrics/v0.2", "metrics": metrics}


def _generation_plan(
    scenario: Mapping[str, Any], sources: tuple[LocalUSDAssetSource, ...]
) -> dict[str, Any]:
    return {
        "schema_version": "scenario-generation-plan/v0.2",
        "package_id": scenario["scenario_id"],
        "source_spec": "scenario.yaml",
        "operations": [
            {
                "type": "copy_usd_closure",
                "asset_id": source.asset_id,
                "destination": f"assets/{source.asset_id}",
                **(
                    {"excluded_relative_paths": list(source.exclude_relative_paths)}
                    if source.exclude_relative_paths
                    else {}
                ),
            }
            for source in sources
        ]
        + [
            {
                "type": "compose_source_layers",
                "output": "scene/main.usda",
                "source_layer_asset_ids_strongest_first": list(
                    _source_layer_asset_ids(scenario)
                ),
            },
            {"type": "compile_portable_contracts"},
        ],
    }


def _provenance(
    scenario: Mapping[str, Any], asset_entries: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "schema_version": "scenario-provenance/v0.2",
        "package_id": scenario["scenario_id"],
        "generator": "scenario-forge",
        "scenario_spec": "scenario.yaml",
        "assets": [
            {
                "asset_id": entry["asset_id"],
                "source_uri": entry["source_uri"],
                "license": entry["license"],
                "attribution": entry["attribution"],
                "redistributable": entry["redistributable"],
                "canonical_usd": entry["canonical_usd"],
                "sha256": entry["sha256"],
                **(
                    {"root_prim_path": entry["root_prim_path"]}
                    if "root_prim_path" in entry
                    else {}
                ),
                **(
                    {"upstream_package": entry["upstream_package"]}
                    if "upstream_package" in entry
                    else {}
                ),
                **(
                    {"excluded_relative_paths": entry["excluded_relative_paths"]}
                    if "excluded_relative_paths" in entry
                    else {}
                ),
            }
            for entry in asset_entries
        ],
    }


def _validation_report(
    scenario: Mapping[str, Any], sources: tuple[LocalUSDAssetSource, ...]
) -> dict[str, Any]:
    return {
        "schema_version": "validation-report/v0.2",
        "package_id": scenario["scenario_id"],
        "status": "passed",
        "overall_level": "asset_locked",
        "checks": [
            {"id": "scenario_spec_compiled", "status": "passed"},
            {
                "id": "local_usd_closures_copied",
                "status": "passed",
                "asset_count": len(sources),
            },
            {"id": "asset_lock_generated", "status": "passed"},
        ],
        "runtime_claims": [],
    }


def _package_manifest(scenario: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "scenario-package/v0.2",
        "package_id": scenario["scenario_id"],
        "scenario_domain": scenario["domain"],
        "package_mode": "fat",
        "targets": ["ebench", "embodied-eval-os"],
        "entrypoints": {
            "generation_plan": "generation/plan.yaml",
            "scenario_spec": "scenario.yaml",
            "scene_usd": "scene/main.usda",
            "scene_instances": "scene/instances.yaml",
            "task": "task/task.yaml",
            "task_graph": "task/graph.yaml",
            "predicates": "task/predicates.yaml",
            "robot": "robot/robot.yaml",
            "metrics": "metrics/metrics.yaml",
        },
        "assets": {
            "manifest": "assets/asset_manifest.yaml",
            "lock": "locks/asset_lock.yaml",
        },
        "validation": {
            "report": "evidence/validation_report.yaml",
            "minimum_required_level": "asset_locked",
        },
        "provenance": {"summary": "provenance/provenance.yaml"},
    }


def _mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
    return cast(Mapping[str, Any], value)


def _mapping_list(value: object, field_name: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return [_mapping(item, f"{field_name}[{index}]") for index, item in enumerate(value)]


def _string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _string_list(value: object, field_name: str) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{field_name} must be a list of non-empty strings")
    return list(value)


def _number_list(value: object, field_name: str, length: int) -> list[float]:
    if (
        not isinstance(value, list)
        or len(value) != length
        or not all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)
    ):
        raise ValueError(f"{field_name} must contain {length} numbers")
    return [float(item) for item in value]


def _dedupe_strings(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _usd_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _usda_tuple(values: list[float]) -> str:
    return "(" + ", ".join(_usda_number(value) for value in values) + ")"


def _usda_number(value: float) -> str:
    text = format(value, ".15g")
    return "0" if text == "-0" else text

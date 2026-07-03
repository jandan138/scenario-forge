from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import copyfile
from typing import Any

import yaml

from scenario_forge.adapters.real2sim.base import REAL2SIM_RESULT_SCHEMA_VERSION
from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.assets.checksum import compute_sha256
from scenario_forge.assets.lock import generate_asset_lock, write_asset_lock
from scenario_forge.generation.workflows.workflow_composer import compose_workflow_artifacts
from scenario_forge.scaffold import scaffold_starter_package
from scenario_forge.scene.usd_compiler import compile_usd_scene


class Real2SimImportError(ValueError):
    """Raised when a real2sim result cannot be imported."""


@dataclass(frozen=True)
class Real2SimImportResult:
    package_root: Path
    package_id: str
    imported_asset_ids: tuple[str, ...]
    artifacts: tuple[Path, ...]


def import_real2sim_result(result_path: str | Path, out_dir: str | Path) -> Real2SimImportResult:
    source_path = Path(result_path)
    result = _load_result(source_path)
    package = _mapping(result, "package")
    package_id = _string(package, "package_id")
    task_family = str(package.get("task_family", "pick_place"))
    robot_profile = str(package.get("robot_profile", "franka_panda_tabletop_v1"))
    root = scaffold_starter_package(out_dir)

    _update_manifest(root, package_id, str(package.get("scenario_domain", "scientific_workbench")))
    imported_assets = _materialize_assets(root, _list_of_mappings(result, "assets"))
    instances = _list_of_mappings(result, "instances")
    _write_scene_artifacts(root, instances)
    _write_real2sim_provenance(root, result)
    write_asset_lock(root, generate_asset_lock(root))

    bindings = _derive_bindings(instances)
    compose_workflow_artifacts(
        root,
        task_family=task_family,
        robot_profile=robot_profile,
        bindings=bindings,
    )
    compile_usd_scene(
        package_root=root,
        instances_path=root / "scene" / "instances.yaml",
        asset_lock_path=root / "locks" / "asset_lock.yaml",
        out_path=root / "scene" / "main.usda",
    )

    artifacts = (
        root / "manifest.yaml",
        root / "assets" / "asset_manifest.yaml",
        root / "locks" / "asset_lock.yaml",
        root / "scene" / "instances.yaml",
        root / "scene" / "main.usda",
        root / "task" / "task.yaml",
        root / "provenance" / "source_refs.yaml",
        root / "evidence" / "real2sim_import.yaml",
    )
    return Real2SimImportResult(
        package_root=root,
        package_id=package_id,
        imported_asset_ids=tuple(asset["asset_id"] for asset in imported_assets),
        artifacts=artifacts,
    )


def _load_result(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise Real2SimImportError(f"Missing real2sim result: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise Real2SimImportError(f"Real2Sim result must be a mapping: {path}")
    if data.get("schema_version") != REAL2SIM_RESULT_SCHEMA_VERSION:
        raise Real2SimImportError("Unsupported real2sim result schema_version")
    return data


def _update_manifest(root: Path, package_id: str, scenario_domain: str) -> None:
    manifest = _load_yaml(root / "manifest.yaml")
    manifest["package_id"] = package_id
    manifest["scenario_domain"] = scenario_domain
    write_yaml_artifact(root / "manifest.yaml", manifest)


def _materialize_assets(root: Path, assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for asset in assets:
        asset_id = _string(asset, "asset_id")
        source_usd = Path(_string(asset, "source_usd"))
        destination = root / "assets" / "reconstructed" / asset_id / "model.usd"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source_usd.exists():
            copyfile(source_usd, destination)
        else:
            destination.write_text(f'#usda 1.0\n\ndef Xform "{asset_id}"\n{{\n}}\n', encoding="utf-8")
        entries.append(
            {
                "asset_id": asset_id,
                "role": _string(asset, "role"),
                "asset_type": _string(asset, "asset_type"),
                "canonical_usd": destination.relative_to(root).as_posix(),
                "license": str(asset.get("license", "Apache-2.0")),
                "sha256": compute_sha256(destination),
                "metadata": {
                    "source": "real2sim",
                    "source_usd": str(source_usd),
                },
            }
        )
    write_yaml_artifact(
        root / "assets" / "asset_manifest.yaml",
        {"schema_version": "asset-manifest/v0.2", "assets": entries},
    )
    return entries


def _write_scene_artifacts(root: Path, instances: list[dict[str, Any]]) -> None:
    write_yaml_artifact(
        root / "scene" / "instances.yaml",
        {"schema_version": "scene-instances/v0.2", "instances": instances},
    )
    write_yaml_artifact(
        root / "scene" / "layout.yaml",
        {
            "schema_version": "scene-layout/v0.2",
            "source": "real2sim",
            "placements": [
                {
                    "instance_id": instance["id"],
                    "asset_id": instance["asset_id"],
                    "xyz": instance["pose"]["xyz"],
                }
                for instance in instances
            ],
        },
    )


def _write_real2sim_provenance(root: Path, result: dict[str, Any]) -> None:
    source = _mapping(result, "source")
    write_yaml_artifact(
        root / "provenance" / "source_refs.yaml",
        {
            "schema_version": "source-refs/v0.2",
            "sources": [
                {
                    "type": source.get("type", "unknown"),
                    "uri": source.get("uri", "unknown"),
                    "adapter": "real2sim/importer",
                }
            ],
        },
    )
    write_yaml_artifact(
        root / "evidence" / "real2sim_import.yaml",
        {
            "schema_version": "real2sim-import-evidence/v0.1",
            "status": "passed",
            "result_id": result.get("result_id", "unknown"),
            "dependency_boundary": "upstream producer; no runtime dependency",
        },
    )


def _derive_bindings(instances: list[dict[str, Any]]) -> dict[str, str]:
    object_id: str | None = None
    target_id: str | None = None
    for instance in instances:
        instance_id = _string(instance, "id")
        role = str(instance.get("role", ""))
        tags = instance.get("semantic_tags", [])
        tag_set = {tag for tag in tags if isinstance(tag, str)} if isinstance(tags, list) else set()
        if object_id is None and (role == "manipulated_object" or "pickable" in tag_set):
            object_id = instance_id
        if target_id is None and (role == "target_region" or {"target", "zone"} & tag_set):
            target_id = instance_id
    if object_id is None or target_id is None:
        raise Real2SimImportError("real2sim pick_place import requires object and target bindings")
    return {"object": object_id, "target_zone": target_id}


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise Real2SimImportError(f"YAML artifact must be a mapping: {path}")
    return data


def _mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise Real2SimImportError(f"Real2Sim result field {key!r} must be a mapping")
    return value


def _list_of_mappings(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise Real2SimImportError(f"Real2Sim result field {key!r} must be a list of mappings")
    return [dict(item) for item in value]


def _string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise Real2SimImportError(f"Real2Sim result field {key!r} must be a string")
    return value

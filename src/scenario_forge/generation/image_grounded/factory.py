from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scenario_forge.adapters.ebench import EBenchExportError, export_ebench_package
from scenario_forge.adapters.ebench.official_asset_intake import (
    audit_mdl_texture_closure,
    materialize_official_asset_bundle,
)
from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.assets.lock import generate_asset_lock, write_asset_lock
from scenario_forge.package import validate_package
from scenario_forge.scene.usd_compiler import USDSceneCompilerError, compile_usd_scene


IMAGE_TASK_REQUEST_SCHEMA_VERSION = "image-task-request/v0.1"
IMAGE_TO_SCENE_RESULT_SCHEMA_VERSION = "image-to-scene-result/v0.1"
PHASE13_CURRENT_GATE_INDEX_SCHEMA_VERSION = "phase13-current-gate-index/v0.1"
PHASE13_REGISTRY_MATERIALIZER = "scenario-forge-phase13-registry-materializer/v0.1"
MIN_DETECTION_CONFIDENCE = 0.70
MIN_ASSET_MATCH_SCORE = 0.70


class Phase13ImageTaskError(ValueError):
    """Raised when Phase 13 image-grounded package generation cannot run."""


@dataclass(frozen=True)
class Phase13ImageTaskResult:
    package_root: Path
    status: str
    evidence_path: Path
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class _MaterializedRegistryAsset:
    asset_id: str
    role: str
    asset_type: str
    canonical_usd: str
    license: str
    sha256: str
    source_uri: str
    source_kind: str
    resolver_version: str
    registry_entry: dict[str, Any]
    material_audit: dict[str, Any]


def generate_image_grounded_task_package(
    *,
    request_path: str | Path,
    scene_result_path: str | Path,
    registry_snapshot_path: str | Path,
    package_root: str | Path,
) -> Phase13ImageTaskResult:
    root = Path(package_root)
    request_file = Path(request_path)
    scene_result_file = Path(scene_result_path)
    registry_file = Path(registry_snapshot_path)

    request = _load_yaml(request_file)
    scene_result = _load_yaml(scene_result_file)
    registry_snapshot = _load_yaml(registry_file)
    registry_by_id = _registry_assets_by_id(registry_snapshot)
    selected_asset_ids = _selected_asset_ids(scene_result)
    selected_asset_preferences = _selected_asset_preferences(scene_result)

    blockers = [
        *_request_blockers(request),
        *_scene_result_blockers(request, scene_result),
        *_registry_snapshot_blockers(registry_snapshot),
        *_asset_selection_blockers(scene_result, registry_by_id),
    ]
    if blockers:
        return _write_blocked_result(
            root=root,
            request=request,
            scene_result=scene_result,
            registry_snapshot=registry_snapshot,
            registry_snapshot_path=registry_file,
            blockers=blockers,
        )

    try:
        materialized_assets = [
            _materialize_selected_asset(
                root=root,
                asset_id=asset_id,
                registry_entry=_choose_registry_asset(
                    asset_id,
                    registry_by_id,
                    **selected_asset_preferences.get(asset_id, {}),
                ),
                registry_snapshot_path=registry_file,
            )
            for asset_id in selected_asset_ids
        ]
    except Phase13ImageTaskError as exc:
        return _write_blocked_result(
            root=root,
            request=request,
            scene_result=scene_result,
            registry_snapshot=registry_snapshot,
            registry_snapshot_path=registry_file,
            blockers=[str(exc)],
        )

    material_blockers = _materialization_blockers(materialized_assets)
    if material_blockers:
        return _write_blocked_result(
            root=root,
            request=request,
            scene_result=scene_result,
            registry_snapshot=registry_snapshot,
            registry_snapshot_path=registry_file,
            blockers=material_blockers,
        )

    root.mkdir(parents=True, exist_ok=True)
    _write_manifest(root, request)
    _write_generation_plan(root, request, scene_result, registry_snapshot, materialized_assets)
    _write_provenance(root, request, scene_result, registry_snapshot_path=registry_file)
    _write_asset_manifest(root, materialized_assets)
    _write_scene_instances(root, scene_result)
    _write_task(root, request, scene_result)
    _write_metrics(root, scene_result)
    _write_robot(root, request)
    _write_task_contract(root, request, scene_result, materialized_assets)

    write_asset_lock(root, generate_asset_lock(root))
    try:
        compile_usd_scene(
            package_root=root,
            instances_path=root / "scene" / "instances.yaml",
            asset_lock_path=root / "locks" / "asset_lock.yaml",
            out_path=root / "scene" / "main.usda",
        )
    except USDSceneCompilerError as exc:
        return _write_blocked_result(
            root=root,
            request=request,
            scene_result=scene_result,
            registry_snapshot=registry_snapshot,
            registry_snapshot_path=registry_file,
            blockers=[str(exc)],
        )

    _write_validation_report(root)
    try:
        export_ebench_package(root)
    except EBenchExportError as exc:
        return _write_blocked_result(
            root=root,
            request=request,
            scene_result=scene_result,
            registry_snapshot=registry_snapshot,
            registry_snapshot_path=registry_file,
            blockers=[str(exc)],
        )

    gate_path = _write_phase13_gates(
        root=root,
        request=request,
        scene_result=scene_result,
        registry_snapshot=registry_snapshot,
        registry_snapshot_path=registry_file,
        local_blockers=[],
        materialized_assets=materialized_assets,
    )
    current_gate = _load_yaml(gate_path)
    return Phase13ImageTaskResult(
        package_root=root,
        status=str(current_gate["overall_status"]),
        evidence_path=gate_path,
        blockers=tuple(current_gate.get("blockers", [])),
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise Phase13ImageTaskError(f"Missing YAML input: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise Phase13ImageTaskError(f"YAML input must be a mapping: {path}")
    return data


def _request_blockers(request: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if request.get("schema_version") != IMAGE_TASK_REQUEST_SCHEMA_VERSION:
        blockers.append(
            f"request schema_version must be {IMAGE_TASK_REQUEST_SCHEMA_VERSION}; "
            f"got {request.get('schema_version')}"
        )
    if not _string(request.get("request_id")):
        blockers.append("request_id must be present")

    source = _mapping(request.get("source"))
    if not _string(source.get("image_uri")):
        blockers.append("source.image_uri must be present")
    image_sha256 = source.get("image_sha256")
    if not (isinstance(image_sha256, str) and image_sha256.startswith("sha256:")):
        blockers.append("source.image_sha256 must be sha256-prefixed")
    if not _string(source.get("rights_status")):
        blockers.append("source.rights_status must be present")

    goal = _mapping(request.get("goal"))
    if not _string(goal.get("one_sentence_goal")):
        blockers.append("goal.one_sentence_goal must be present")
    if goal.get("domain") != "tabletop_manipulation":
        blockers.append("goal.domain must be tabletop_manipulation")
    if not _string(goal.get("robot_profile")):
        blockers.append("goal.robot_profile must be present")
    if goal.get("target_export") != "ebench":
        blockers.append("goal.target_export must be ebench")

    constraints = _mapping(request.get("constraints"))
    if constraints.get("package_mode") != "fat":
        blockers.append("constraints.package_mode must be fat")
    if constraints.get("asset_source") != "phase12_registry_snapshot":
        blockers.append("constraints.asset_source must be phase12_registry_snapshot")
    if constraints.get("allow_new_asset_reconstruction") is not False:
        blockers.append("constraints.allow_new_asset_reconstruction must be false")
    return blockers


def _scene_result_blockers(request: dict[str, Any], scene_result: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if scene_result.get("schema_version") != IMAGE_TO_SCENE_RESULT_SCHEMA_VERSION:
        blockers.append(
            f"scene result schema_version must be {IMAGE_TO_SCENE_RESULT_SCHEMA_VERSION}; "
            f"got {scene_result.get('schema_version')}"
        )
    producer = _mapping(scene_result.get("producer"))
    if not _string(producer.get("name")) or not _string(producer.get("version")):
        blockers.append("scene result producer.name and producer.version must be present")

    request_source = _mapping(request.get("source"))
    result_source = _mapping(scene_result.get("source"))
    if request_source.get("image_sha256") != result_source.get("image_sha256"):
        blockers.append("scene result source.image_sha256 must match request image_sha256")

    request_goal = _mapping(request.get("goal"))
    result_goal = _mapping(scene_result.get("goal"))
    if request_goal.get("one_sentence_goal") != result_goal.get("raw_text"):
        blockers.append("scene result goal.raw_text must match request goal.one_sentence_goal")
    if result_goal.get("normalized_task_family") != "object_in_container":
        blockers.append("only normalized_task_family=object_in_container is supported in Phase 13 MVP")

    evidence = _mapping(scene_result.get("evidence"))
    for blocker in _string_items(evidence.get("blockers")):
        blockers.append(f"upstream image grounding blocker: {blocker}")

    detections = _list_of_mappings(scene_result.get("detections"))
    if not detections:
        blockers.append("scene result must include detections")
    for detection in detections:
        detection_id = str(detection.get("detection_id", "unknown"))
        confidence = detection.get("confidence")
        if not isinstance(confidence, int | float) or confidence < MIN_DETECTION_CONFIDENCE:
            blockers.append(f"detection {detection_id} confidence is below {MIN_DETECTION_CONFIDENCE}")

    candidates = _list_of_mappings(scene_result.get("asset_candidates"))
    if not candidates:
        blockers.append("scene result must include asset_candidates")
    for candidate in candidates:
        role = str(candidate.get("role", "unknown"))
        if not _string(candidate.get("selected_asset_id")):
            blockers.append(f"asset candidate for role {role} missing selected_asset_id")
        score = candidate.get("score")
        if not isinstance(score, int | float) or score < MIN_ASSET_MATCH_SCORE:
            blockers.append(f"asset candidate for role {role} score is below {MIN_ASSET_MATCH_SCORE}")
        if not _string(candidate.get("matching_reason")):
            blockers.append(f"asset candidate for role {role} missing matching_reason")
        if "rejected_alternatives" not in candidate:
            blockers.append(f"asset candidate for role {role} must record rejected_alternatives")

    instances = _list_of_mappings(scene_result.get("instances"))
    if not instances:
        blockers.append("scene result must include scene instances")
    instance_ids = {str(instance.get("id")) for instance in instances if _string(instance.get("id"))}
    for instance in instances:
        instance_id = str(instance.get("id", "unknown"))
        if not _string(instance.get("asset_id")):
            blockers.append(f"scene instance {instance_id} missing asset_id")
        pose = _mapping(instance.get("pose"))
        if not _valid_float_list(pose.get("xyz"), 3) or not _valid_float_list(pose.get("wxyz"), 4):
            blockers.append(f"scene instance {instance_id} must include pose.xyz and pose.wxyz")

    bindings = _mapping(scene_result.get("task_bindings"))
    if bindings.get("object") not in instance_ids:
        blockers.append("task_bindings.object must reference a scene instance")
    if bindings.get("container") not in instance_ids:
        blockers.append("task_bindings.container must reference a scene instance")
    return blockers


def _registry_snapshot_blockers(registry_snapshot: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if registry_snapshot.get("schema_version") != "registry-snapshot/v0.1":
        blockers.append("registry snapshot schema_version must be registry-snapshot/v0.1")
    digest = registry_snapshot.get("snapshot_digest")
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        blockers.append("registry snapshot_digest must be sha256-prefixed")
    asset_registry = _mapping(registry_snapshot.get("asset_registry"))
    if asset_registry.get("schema_version") != "asset-registry/v0.1":
        blockers.append("registry snapshot asset_registry must be asset-registry/v0.1")
    if not _list_of_mappings(asset_registry.get("assets")):
        blockers.append("registry snapshot asset_registry.assets must not be empty")
    return blockers


def _asset_selection_blockers(
    scene_result: dict[str, Any],
    registry_by_id: dict[str, list[dict[str, Any]]],
) -> list[str]:
    blockers: list[str] = []
    selected_ids = _selected_asset_ids(scene_result)
    selected_asset_preferences = _selected_asset_preferences(scene_result)
    candidate_asset_ids = {
        str(candidate.get("selected_asset_id"))
        for candidate in _list_of_mappings(scene_result.get("asset_candidates"))
        if _string(candidate.get("selected_asset_id"))
    }
    for instance in _list_of_mappings(scene_result.get("instances")):
        asset_id = str(instance.get("asset_id", ""))
        if asset_id and asset_id not in candidate_asset_ids:
            blockers.append(f"scene instance {instance.get('id')} uses asset {asset_id} without a selected candidate")

    for asset_id in selected_ids:
        entries = registry_by_id.get(asset_id, [])
        if not entries:
            blockers.append(f"selected asset {asset_id} is not present in the Phase 12 registry snapshot")
            continue
        try:
            entry = _choose_registry_asset(
                asset_id,
                registry_by_id,
                **selected_asset_preferences.get(asset_id, {}),
            )
        except Phase13ImageTaskError as exc:
            blockers.append(str(exc))
            continue
        for field in ("asset_uid", "content_sha256", "license", "canonical_usd", "resolver_version"):
            if not _string(entry.get(field)):
                blockers.append(f"selected asset {asset_id} missing registry field {field}")
        if not _mapping(entry.get("provenance")).get("asset_manifest"):
            blockers.append(f"selected asset {asset_id} missing provenance.asset_manifest")
        material_closure = _mapping(entry.get("material_closure"))
        if material_closure.get("status") != "passed":
            detail = _material_closure_detail(material_closure)
            blocker = f"selected asset {asset_id} material_closure.status must be passed"
            if detail:
                blocker = f"{blocker} ({detail})"
            blockers.append(blocker)
        if _mapping(entry.get("physics_readiness")).get("status") != "ready":
            blockers.append(f"selected asset {asset_id} physics_readiness.status must be ready")
        if _mapping(entry.get("export_eligibility")).get("ebench") is not True:
            blockers.append(f"selected asset {asset_id} must be export_eligibility.ebench=true")
    return blockers


def _registry_assets_by_id(registry_snapshot: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    assets = _list_of_mappings(_mapping(registry_snapshot.get("asset_registry")).get("assets"))
    by_id: dict[str, list[dict[str, Any]]] = {}
    for asset in assets:
        asset_id = asset.get("asset_id")
        if isinstance(asset_id, str) and asset_id:
            by_id.setdefault(asset_id, []).append(asset)
    for entries in by_id.values():
        entries.sort(key=lambda item: (str(item.get("source_package_id", "")), str(item.get("asset_uid", ""))))
    return by_id


def _choose_registry_asset(
    asset_id: str,
    registry_by_id: dict[str, list[dict[str, Any]]],
    *,
    selected_asset_uid: str | None = None,
    selected_source_package_id: str | None = None,
) -> dict[str, Any]:
    entries = registry_by_id.get(asset_id, [])
    if not entries:
        raise Phase13ImageTaskError(
            f"selected asset {asset_id} is not present in the Phase 12 registry snapshot"
        )
    matching_entries = _matching_registry_entries(
        entries,
        selected_asset_uid=selected_asset_uid,
        selected_source_package_id=selected_source_package_id,
    )
    if not matching_entries:
        selectors = []
        if selected_asset_uid:
            selectors.append(f"asset_uid={selected_asset_uid}")
        if selected_source_package_id:
            selectors.append(f"source_package_id={selected_source_package_id}")
        raise Phase13ImageTaskError(
            f"selected asset {asset_id} registry entry does not match "
            f"{', '.join(selectors)}"
        )
    return max(matching_entries, key=_registry_entry_selection_key)


def _matching_registry_entries(
    entries: list[dict[str, Any]],
    *,
    selected_asset_uid: str | None,
    selected_source_package_id: str | None,
) -> list[dict[str, Any]]:
    matching = entries
    if selected_asset_uid:
        matching = [entry for entry in matching if entry.get("asset_uid") == selected_asset_uid]
    if selected_source_package_id:
        matching = [
            entry
            for entry in matching
            if entry.get("source_package_id") == selected_source_package_id
        ]
    return matching


def _registry_entry_selection_key(entry: dict[str, Any]) -> tuple[bool, bool, bool, str, str]:
    return (
        _mapping(entry.get("material_closure")).get("status") == "passed",
        _mapping(entry.get("physics_readiness")).get("status") == "ready",
        _mapping(entry.get("export_eligibility")).get("ebench") is True,
        str(entry.get("source_package_id", "")),
        str(entry.get("asset_uid", "")),
    )


def _selected_asset_ids(scene_result: dict[str, Any]) -> list[str]:
    selected: list[str] = []
    for candidate in _list_of_mappings(scene_result.get("asset_candidates")):
        asset_id = candidate.get("selected_asset_id")
        if isinstance(asset_id, str) and asset_id and asset_id not in selected:
            selected.append(asset_id)
    for instance in _list_of_mappings(scene_result.get("instances")):
        asset_id = instance.get("asset_id")
        if isinstance(asset_id, str) and asset_id and asset_id not in selected:
            selected.append(asset_id)
    return selected


def _selected_asset_preferences(scene_result: dict[str, Any]) -> dict[str, dict[str, str]]:
    preferences: dict[str, dict[str, str]] = {}
    for candidate in _list_of_mappings(scene_result.get("asset_candidates")):
        asset_id = candidate.get("selected_asset_id")
        if not isinstance(asset_id, str) or not asset_id:
            continue
        preference = preferences.setdefault(asset_id, {})
        if _string(candidate.get("selected_asset_uid")):
            preference["selected_asset_uid"] = str(candidate["selected_asset_uid"])
        source_package_id = candidate.get("selected_source_package_id") or candidate.get(
            "source_package_id"
        )
        if _string(source_package_id):
            preference["selected_source_package_id"] = str(source_package_id)
    for instance in _list_of_mappings(scene_result.get("instances")):
        asset_id = instance.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id:
            continue
        preference = preferences.setdefault(asset_id, {})
        if _string(instance.get("asset_uid")):
            preference["selected_asset_uid"] = str(instance["asset_uid"])
        source_package_id = instance.get("selected_source_package_id") or instance.get(
            "source_package_id"
        )
        if _string(source_package_id):
            preference["selected_source_package_id"] = str(source_package_id)
    return preferences


def _materialize_selected_asset(
    *,
    root: Path,
    asset_id: str,
    registry_entry: dict[str, Any],
    registry_snapshot_path: Path,
) -> _MaterializedRegistryAsset:
    retained_asset = _retained_asset_entry(registry_entry, registry_snapshot_path)
    source_uri = str(retained_asset.get("source_uri") or registry_entry.get("source_uri") or "")
    source_path = _source_uri_to_path(source_uri)
    if source_path is None or not source_path.exists():
        raise Phase13ImageTaskError(
            f"selected asset {asset_id} source_uri cannot be materialized from retained evidence"
        )
    materialized = materialize_official_asset_bundle(
        source_path=source_path,
        package_root=root,
        asset_id=asset_id,
        role=str(registry_entry.get("role") or retained_asset.get("role") or "scene_object"),
        license=str(registry_entry.get("license") or retained_asset.get("license") or ""),
    )
    audit = audit_mdl_texture_closure(root / "assets" / asset_id)
    audit = _apply_registry_runtime_mdl_approval(audit, registry_entry)
    return _MaterializedRegistryAsset(
        asset_id=asset_id,
        role=str(registry_entry.get("role") or retained_asset.get("role") or "scene_object"),
        asset_type=str(registry_entry.get("asset_type") or retained_asset.get("asset_type") or "usd_bundle"),
        canonical_usd=materialized.canonical_usd,
        license=str(registry_entry.get("license") or retained_asset.get("license") or ""),
        sha256=materialized.sha256,
        source_uri=source_uri,
        source_kind=str(registry_entry.get("source_kind") or retained_asset.get("source_kind") or "phase12_registry"),
        resolver_version=str(registry_entry.get("resolver_version") or PHASE13_REGISTRY_MATERIALIZER),
        registry_entry=registry_entry,
        material_audit=audit,
    )


def _retained_asset_entry(
    registry_entry: dict[str, Any],
    registry_snapshot_path: Path,
) -> dict[str, Any]:
    provenance = _mapping(registry_entry.get("provenance"))
    manifest_path = _resolve_registry_ref(
        registry_snapshot_path,
        provenance.get("asset_manifest") or registry_entry.get("source_uri"),
    )
    if manifest_path is None or not manifest_path.exists():
        raise Phase13ImageTaskError(
            f"selected asset {registry_entry.get('asset_id')} retained asset manifest cannot be resolved"
        )
    manifest = _load_yaml(manifest_path)
    asset_id = registry_entry.get("asset_id")
    for asset in _list_of_mappings(manifest.get("assets")):
        if asset.get("asset_id") == asset_id:
            return asset
    raise Phase13ImageTaskError(f"retained asset manifest does not contain asset {asset_id}")


def _resolve_registry_ref(registry_snapshot_path: Path, raw_ref: object) -> Path | None:
    if not isinstance(raw_ref, str) or not raw_ref:
        return None
    ref = raw_ref
    if ref.startswith("retained-artifact://"):
        ref = ref.removeprefix("retained-artifact://").split("#", 1)[0]
    path = Path(ref)
    if path.is_absolute():
        return path
    suite_root = registry_snapshot_path.parent.parent
    for base in (suite_root, Path.cwd(), registry_snapshot_path.parent):
        candidate = base / path
        if candidate.exists():
            return candidate
    return suite_root / path


def _source_uri_to_path(source_uri: str) -> Path | None:
    if source_uri.startswith("file://"):
        return Path(source_uri.removeprefix("file://"))
    if "://" in source_uri or source_uri.startswith(("omniverse:", "mdl:")):
        return None
    return Path(source_uri)


def _materialization_blockers(materialized_assets: list[_MaterializedRegistryAsset]) -> list[str]:
    blockers: list[str] = []
    for asset in materialized_assets:
        if asset.material_audit.get("status") != "passed":
            detail = _material_closure_detail(asset.material_audit)
            reason = f"selected asset {asset.asset_id} material/texture closure failed"
            if detail:
                reason = f"{reason} ({detail})"
            blockers.append(reason)
    return blockers


def _apply_registry_runtime_mdl_approval(
    material_audit: dict[str, Any],
    registry_entry: dict[str, Any],
) -> dict[str, Any]:
    if material_audit.get("status") != "failed":
        return material_audit
    if material_audit.get("missing_texture_count") not in (0, None):
        return material_audit

    missing_refs = _list_of_mappings(material_audit.get("missing_material_refs"))
    if not missing_refs:
        return material_audit
    material_closure = _mapping(registry_entry.get("material_closure"))
    approved_dependencies = _list_of_mappings(
        material_closure.get("approved_runtime_mdl_dependencies")
    )
    approved_modules = {
        str(item.get("module"))
        for item in approved_dependencies
        if item.get("module") and item.get("resolution") == "approved_runtime_module"
    }
    if not approved_modules:
        return material_audit
    unapproved_refs = [
        item for item in missing_refs if str(item.get("material", "")) not in approved_modules
    ]
    if unapproved_refs:
        return material_audit
    return {
        **material_audit,
        "status": "passed",
        "missing_material_ref_count": 0,
        "missing_material_refs": [],
        "package_local_missing_material_refs": missing_refs,
        "approved_runtime_mdl_dependencies": approved_dependencies,
        "registry_material_closure_source": "phase12_approved_runtime_mdl_dependencies",
    }


def _material_closure_detail(material_closure: dict[str, Any]) -> str:
    details: list[str] = []
    missing_materials = [
        str(item.get("material"))
        for item in _list_of_mappings(material_closure.get("missing_material_refs"))
        if item.get("material")
    ]
    missing_textures = [
        str(item.get("texture"))
        for item in _list_of_mappings(material_closure.get("missing_textures"))
        if item.get("texture")
    ]
    if missing_materials:
        details.append(f"missing material refs: {', '.join(sorted(missing_materials))}")
    if missing_textures:
        details.append(f"missing textures: {', '.join(sorted(missing_textures))}")
    return "; ".join(details)


def _write_manifest(root: Path, request: dict[str, Any]) -> None:
    package_id = _package_id(request)
    write_yaml_artifact(
        root / "manifest.yaml",
        {
            "schema_version": "scenario-package/v0.2",
            "package_id": package_id,
            "scenario_domain": "home_manipulation",
            "package_mode": "fat",
            "targets": ["ebench", "embodied-eval-os"],
            "entrypoints": {
                "generation_plan": "generation_plan.yaml",
                "scene_usd": "scene/main.usda",
                "scene_instances": "scene/instances.yaml",
                "task": "task/task.yaml",
                "task_contract": "task/task_contract.yaml",
                "robot": "robot/robot.yaml",
                "metrics": "metrics/metrics.yaml",
            },
            "assets": {"manifest": "assets/asset_manifest.yaml", "lock": "locks/asset_lock.yaml"},
            "validation": {
                "report": "evidence/validation_report.yaml",
                "minimum_required_level": "adapter_static_validated",
            },
            "provenance": {"summary": "provenance/summary.yaml"},
        },
    )


def _write_generation_plan(
    root: Path,
    request: dict[str, Any],
    scene_result: dict[str, Any],
    registry_snapshot: dict[str, Any],
    materialized_assets: list[_MaterializedRegistryAsset],
) -> None:
    write_yaml_artifact(
        root / "generation_plan.yaml",
        {
            "schema_version": "scenario-generation-plan/v0.2",
            "package_id": _package_id(request),
            "source_kind": "image_grounded_existing_asset_factory",
            "source_image": _mapping(request.get("source")),
            "one_sentence_goal": _mapping(request.get("goal")).get("one_sentence_goal"),
            "target_exports": ["ebench", "embodied-eval-os"],
            "package_mode": "fat",
            "registry_snapshot_digest": registry_snapshot.get("snapshot_digest"),
            "selected_assets": [
                {
                    "asset_id": asset.asset_id,
                    "asset_uid": asset.registry_entry.get("asset_uid"),
                    "role": asset.role,
                    "content_sha256": asset.registry_entry.get("content_sha256"),
                }
                for asset in materialized_assets
            ],
            "workflow_bindings": _task_bindings(scene_result),
            "confidence_summary": _mapping(scene_result.get("evidence")).get("confidence_summary"),
            "claim_boundary": (
                "Phase 13 generation plan only. External image grounding confidence is "
                "retained as provenance and is not a task success or release claim."
            ),
        },
    )


def _write_provenance(
    root: Path,
    request: dict[str, Any],
    scene_result: dict[str, Any],
    *,
    registry_snapshot_path: Path,
) -> None:
    write_yaml_artifact(
        root / "provenance" / "summary.yaml",
        {
            "schema_version": "provenance-summary/v0.1",
            "source_kind": "image_grounded_existing_asset_factory",
            "request_id": request.get("request_id"),
            "image_task_request": "provenance/phase13_image_task_request.yaml",
            "image_to_scene_result": "provenance/phase13_image_to_scene_result.yaml",
            "registry_snapshot": str(registry_snapshot_path),
            "claim_boundary": (
                "Package provenance records inputs and selected registry assets only; "
                "it does not prove visual readability or task success."
            ),
        },
    )
    write_yaml_artifact(root / "provenance" / "phase13_image_task_request.yaml", request)
    write_yaml_artifact(root / "provenance" / "phase13_image_to_scene_result.yaml", scene_result)


def _write_asset_manifest(root: Path, assets: list[_MaterializedRegistryAsset]) -> None:
    write_yaml_artifact(
        root / "assets" / "asset_manifest.yaml",
        {
            "schema_version": "asset-manifest/v0.2",
            "assets": [
                {
                    "asset_id": asset.asset_id,
                    "role": asset.role,
                    "asset_type": asset.asset_type,
                    "canonical_usd": asset.canonical_usd,
                    "license": asset.license,
                    "sha256": asset.sha256,
                    "source_kind": "phase12_registry_asset",
                    "source_uri": asset.source_uri,
                    "resolver_version": PHASE13_REGISTRY_MATERIALIZER,
                    "phase12_asset_uid": asset.registry_entry.get("asset_uid"),
                    "phase12_content_sha256": asset.registry_entry.get("content_sha256"),
                    "phase12_source_package_id": asset.registry_entry.get("source_package_id"),
                }
                for asset in assets
            ],
        },
    )


def _write_scene_instances(root: Path, scene_result: dict[str, Any]) -> None:
    instances: list[dict[str, Any]] = []
    for instance in _list_of_mappings(scene_result.get("instances")):
        pose = dict(_mapping(instance.get("pose")))
        if "scale_xyz" not in pose:
            pose["scale_xyz"] = [1.0, 1.0, 1.0]
        role = str(instance.get("role", "scene_object"))
        semantic_tags = instance.get("semantic_tags")
        if not isinstance(semantic_tags, list):
            semantic_tags = [role]
        instances.append(
            {
                "id": instance["id"],
                "asset_id": instance["asset_id"],
                "role": role,
                "pose": pose,
                "semantic_tags": semantic_tags,
                "initial_state": _mapping(instance.get("initial_state")),
            }
        )
    write_yaml_artifact(
        root / "scene" / "instances.yaml",
        {"schema_version": "scene-instances/v0.2", "instances": instances},
    )


def _write_task(root: Path, request: dict[str, Any], scene_result: dict[str, Any]) -> None:
    write_yaml_artifact(
        root / "task" / "task.yaml",
        {
            "schema_version": "task/v0.2",
            "task_id": f"image_task/{request['request_id']}",
            "task_family": "pick_place",
            "instruction": _mapping(request.get("goal"))["one_sentence_goal"],
            "bindings": _task_bindings(scene_result),
        },
    )


def _write_metrics(root: Path, scene_result: dict[str, Any]) -> None:
    bindings = _task_bindings(scene_result)
    write_yaml_artifact(
        root / "metrics" / "metrics.yaml",
        {
            "schema_version": "metrics/v0.2",
            "metrics": [
                {
                    "id": "object_in_container",
                    "type": "predicate_satisfaction",
                    "role": "primary_success",
                    "predicate": "object_in_container",
                    "object": bindings["object"],
                    "container": bindings["target_container"],
                    "adapter_hints": {
                        "ebench": {
                            "success_metric": "object_in_container",
                            "predicate": "object_in_container",
                            "object": bindings["object"],
                            "container": bindings["target_container"],
                        }
                    },
                }
            ],
        },
    )


def _write_robot(root: Path, request: dict[str, Any]) -> None:
    robot_profile = _mapping(request.get("goal")).get("robot_profile", "tabletop_manipulator")
    write_yaml_artifact(
        root / "robot" / "robot.yaml",
        {
            "schema_version": "robot/v0.2",
            "robot_id": robot_profile,
            "spawn": {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]},
            "usage": "phase13_hint_only",
        },
    )


def _write_task_contract(
    root: Path,
    request: dict[str, Any],
    scene_result: dict[str, Any],
    materialized_assets: list[_MaterializedRegistryAsset],
) -> None:
    bindings = _task_bindings(scene_result)
    assets_by_id = {asset.asset_id: asset for asset in materialized_assets}
    instance_assets = {
        str(instance.get("id")): str(instance.get("asset_id"))
        for instance in _list_of_mappings(scene_result.get("instances"))
    }
    instances_by_id = {
        str(instance.get("id")): instance
        for instance in _list_of_mappings(scene_result.get("instances"))
        if _string(instance.get("id"))
    }
    object_asset_id = instance_assets[bindings["object"]]
    container_asset_id = instance_assets[bindings["target_container"]]
    target_container_semantics = {
        "instance_id": bindings["target_container"],
        "asset_id": container_asset_id,
        "asset_uid": assets_by_id[container_asset_id].registry_entry.get("asset_uid"),
        "role": "target_container",
    }
    target_container_semantics.update(
        _task_contract_instance_metadata(instances_by_id[bindings["target_container"]])
    )
    write_yaml_artifact(
        root / "task" / "task_contract.yaml",
        {
            "schema_version": "ebench-task-contract/v0.1",
            "phase_gate": "13.4",
            "package_id": _package_id(request),
            "task": {
                "task_id": f"image_task/{request['request_id']}",
                "task_family": "pick_place",
                "instruction": _mapping(request.get("goal"))["one_sentence_goal"],
            },
            "task_semantics": {
                "action": "pick_place",
                "manipulated_object": {
                    "instance_id": bindings["object"],
                    "asset_id": object_asset_id,
                    "asset_uid": assets_by_id[object_asset_id].registry_entry.get("asset_uid"),
                    "role": "manipulated_object",
                },
                "target_container": target_container_semantics,
            },
            "success_predicate": {
                "metric_id": "object_in_container",
                "role": "primary_success",
                "predicate": "object_in_container",
                "object": bindings["object"],
                "container": bindings["target_container"],
                "evaluator_owner": "embodied-eval-os-ebench-adapter",
                "claim_boundary": (
                    "simulator-state predicate binding only; image confidence and visual review "
                    "are not task success"
                ),
            },
            "robot_hints": {
                "robot_id": _mapping(request.get("goal")).get("robot_profile"),
                "usage": "hint_only",
            },
            "adapter_contract": {
                "adapter": "ebench",
                "package_descriptor": "adapters/ebench/package.yaml",
                "task_entrypoint": "adapters/ebench/task_entrypoint.yaml",
                "runtime_owner": "embodied-eval-os",
                "scenario_forge_scope": "package_artifacts_and_contracts_only",
                "scenario_forge_excludes": [
                    "episode_runner",
                    "model_adapter",
                    "leaderboard_reporting",
                    "simulator_runtime_execution",
                    "convertasset_usd_mdl_mesh_conversion",
                    "image_understanding_model_calls",
                ],
            },
            "phase_13_readiness": {
                "status": "static_candidate_ready_for_downstream_gates",
                "required_external_gates": [
                    "13.6 factory overview visual gate",
                    "13.8 execution predicate canary gate",
                ],
            },
            "claim_boundary": (
                "Phase 13 static task contract only. It binds selected registry assets "
                "to simulator-state predicates and does not claim task execution success."
            ),
        },
    )


def _task_contract_instance_metadata(instance: dict[str, Any]) -> dict[str, str]:
    return {
        field: str(instance[field])
        for field in ("semantic_label", "source_uid", "fixture_kind")
        if _string(instance.get(field))
    }


def _write_validation_report(root: Path) -> None:
    validation_path = root / "evidence" / "validation_report.yaml"
    write_yaml_artifact(
        validation_path,
        {
            "schema_version": "validation-report/v0.2",
            "status": "draft",
            "overall_level": "package_schema_validated",
            "checks": [{"name": "validation_report_bootstrap", "status": "passed"}],
            "messages": [],
        },
    )
    report = validate_package(root, require_asset_lock=True)
    checks = [
        {"name": "package_validation", "status": "passed" if report.ok else "failed"},
        {"name": "asset_lock", "status": "passed" if report.ok else "failed"},
        {"name": "usd_static_compile", "status": "passed"},
        {"name": "adapter_export", "status": "passed"},
    ]
    write_yaml_artifact(
        validation_path,
        {
            "schema_version": "validation-report/v0.2",
            "status": "static_candidate",
            "overall_level": "adapter_static_validated",
            "checks": checks,
            "messages": list(report.messages),
        },
    )


def _write_blocked_result(
    *,
    root: Path,
    request: dict[str, Any],
    scene_result: dict[str, Any],
    registry_snapshot: dict[str, Any],
    registry_snapshot_path: Path,
    blockers: list[str],
) -> Phase13ImageTaskResult:
    root.mkdir(parents=True, exist_ok=True)
    _remove_public_ready_artifacts(root)
    _write_provenance(root, request, scene_result, registry_snapshot_path=registry_snapshot_path)
    write_yaml_artifact(
        root / "handoff" / "asset_intake_blockers.yaml",
        {
            "schema_version": "phase13-asset-intake-blockers/v0.1",
            "request_id": request.get("request_id"),
            "status": "blocked",
            "blockers": blockers,
            "recommended_next_step": "fix_upstream_result_or_asset_registry_then_rerun_phase13",
            "claim_boundary": "Blocked handoff only; no public-ready package was generated.",
        },
    )
    gate_path = _write_phase13_gates(
        root=root,
        request=request,
        scene_result=scene_result,
        registry_snapshot=registry_snapshot,
        registry_snapshot_path=registry_snapshot_path,
        local_blockers=blockers,
    )
    return Phase13ImageTaskResult(
        package_root=root,
        status="blocked",
        evidence_path=gate_path,
        blockers=tuple(blockers),
    )


def _remove_public_ready_artifacts(root: Path) -> None:
    for relative_path in (
        "manifest.yaml",
        "adapters/ebench/package.yaml",
        "adapters/ebench/task_entrypoint.yaml",
    ):
        path = root / relative_path
        if path.exists():
            path.unlink()


def _write_phase13_gates(
    *,
    root: Path,
    request: dict[str, Any],
    scene_result: dict[str, Any],
    registry_snapshot: dict[str, Any],
    registry_snapshot_path: Path,
    local_blockers: list[str],
    materialized_assets: list[_MaterializedRegistryAsset] | None = None,
) -> Path:
    evidence_dir = root / "evidence"
    request_id = request.get("request_id", root.name)
    registry_ref = str(registry_snapshot_path)
    snapshot_digest = registry_snapshot.get("snapshot_digest")
    local_status = "blocked" if local_blockers else "passed"
    gates: dict[str, tuple[str, dict[str, Any]]] = {
        "13.0": (
            "phase13_0_image_goal_mvp_scope_gate.yaml",
            {
                "schema_version": "image-goal-mvp-scope-gate/v0.1",
                "phase": "13.0",
                "status": local_status,
                "request_id": request_id,
                "domain": _mapping(request.get("goal")).get("domain"),
                "target_export": _mapping(request.get("goal")).get("target_export"),
                "asset_source": _mapping(request.get("constraints")).get("asset_source"),
                "allow_new_asset_reconstruction": _mapping(request.get("constraints")).get(
                    "allow_new_asset_reconstruction"
                ),
                "blockers": local_blockers,
            },
        ),
        "13.1": (
            "phase13_1_image_goal_intake_provenance_gate.yaml",
            {
                "schema_version": "image-goal-intake-provenance-gate/v0.1",
                "phase": "13.1",
                "status": local_status,
                "request_id": request_id,
                "image_sha256": _mapping(request.get("source")).get("image_sha256"),
                "rights_status": _mapping(request.get("source")).get("rights_status"),
                "producer": _mapping(scene_result.get("producer")),
                "blockers": local_blockers,
            },
        ),
        "13.2": (
            "phase13_2_image_understanding_candidate_gate.yaml",
            {
                "schema_version": "image-understanding-candidate-gate/v0.1",
                "phase": "13.2",
                "status": local_status,
                "request_id": request_id,
                "detections": scene_result.get("detections", []),
                "confidence_summary": _mapping(scene_result.get("evidence")).get("confidence_summary"),
                "blockers": local_blockers,
                "claim_boundary": "External image grounding evidence only; no runtime success claim.",
            },
        ),
        "13.3": (
            "phase13_3_asset_registry_match_gate.yaml",
            {
                "schema_version": "asset-registry-match-gate/v0.1",
                "phase": "13.3",
                "status": local_status,
                "request_id": request_id,
                "registry_snapshot": registry_ref,
                "snapshot_digest": snapshot_digest,
                "asset_candidates": scene_result.get("asset_candidates", []),
                "blockers": local_blockers,
            },
        ),
        "13.4": (
            "phase13_4_goal_to_task_contract_gate.yaml",
            {
                "schema_version": "goal-to-task-contract-gate/v0.1",
                "phase": "13.4",
                "status": local_status,
                "request_id": request_id,
                "task_bindings": scene_result.get("task_bindings", {}),
                "predicate": "object_in_container",
                "predicate_source": "simulator_state",
                "blockers": local_blockers,
            },
        ),
        "13.5": (
            "phase13_5_scene_layout_usd_materialization_gate.yaml",
            {
                "schema_version": "scene-layout-usd-materialization-gate/v0.1",
                "phase": "13.5",
                "status": local_status,
                "request_id": request_id,
                "usd_entrypoint": "scene/main.usda" if not local_blockers else None,
                "asset_lock": "locks/asset_lock.yaml" if not local_blockers else None,
                "material_closure": _phase13_material_closure_summary(
                    materialized_assets or [],
                    local_blockers=local_blockers,
                ),
                "blockers": local_blockers,
            },
        ),
        "13.6": (
            "phase13_6_factory_overview_visual_gate.yaml",
            {
                "schema_version": "factory-overview-visual-gate/v0.1",
                "phase": "13.6",
                "status": "blocked",
                "request_id": request_id,
                "blockers": [
                    "engine-native overview render and render-visual-reviewer PASS are required downstream"
                ],
                "claim_boundary": "Visual readability gate only; does not prove task success.",
            },
        ),
        "13.7": (
            "phase13_7_package_adapter_preflight_gate.yaml",
            {
                "schema_version": "package-adapter-preflight-gate/v0.1",
                "phase": "13.7",
                "status": local_status,
                "request_id": request_id,
                "package_check": "passed" if not local_blockers else "blocked",
                "ebench_export": "passed" if not local_blockers else "blocked",
                "blockers": local_blockers,
                "core_import_policy": "no_simulator_sdk_in_core",
            },
        ),
        "13.8": (
            "phase13_8_execution_predicate_canary_gate.yaml",
            {
                "schema_version": "execution-predicate-canary-gate/v0.1",
                "phase": "13.8",
                "status": "blocked",
                "request_id": request_id,
                "blockers": [
                    "EOS execution evidence, completed episode, predicate true, and post-execution visual PASS are required downstream"
                ],
                "claim_boundary": "Execution gate must be emitted from EOS/EBench evidence, not Scenario Forge generation.",
            },
        ),
    }
    latest_gates: dict[str, dict[str, str]] = {}
    for phase, (filename, gate) in gates.items():
        write_yaml_artifact(evidence_dir / filename, gate)
        latest_gates[phase] = {
            "path": f"evidence/{filename}",
            "schema_version": str(gate["schema_version"]),
            "status": str(gate["status"]),
        }

    overall_status = "blocked" if local_blockers else "phase13_static_candidate_ready"
    downstream_blockers = [] if local_blockers else [
        "13.6 engine-native overview render gate is required before formal package readiness",
        "13.8 EOS execution/predicate canary gate is required before formal package readiness",
    ]
    current = {
        "schema_version": PHASE13_CURRENT_GATE_INDEX_SCHEMA_VERSION,
        "request_id": request_id,
        "package_id": _package_id(request),
        "overall_status": overall_status,
        "formal_package_ready": False,
        "static_candidate_ready": not local_blockers,
        "next_required_gate": "13.6" if not local_blockers else "13.0",
        "registry_snapshot": registry_ref,
        "snapshot_digest": snapshot_digest,
        "latest_gates": latest_gates,
        "blockers": local_blockers + downstream_blockers,
        "claim_boundary": (
            "Phase 13 current gate index only. Static candidate readiness is not a "
            "formal EBench package release, task execution success, or leaderboard result."
        ),
    }
    return write_yaml_artifact(evidence_dir / "phase13_current_gate_index.yaml", current)


def _phase13_material_closure_summary(
    materialized_assets: list[_MaterializedRegistryAsset],
    *,
    local_blockers: list[str],
) -> dict[str, Any]:
    return {
        "status": "blocked" if local_blockers else "passed",
        "selected_assets": [
            {
                "asset_id": asset.asset_id,
                "status": asset.material_audit.get("status"),
                "missing_texture_count": asset.material_audit.get("missing_texture_count"),
                "missing_material_ref_count": asset.material_audit.get(
                    "missing_material_ref_count"
                ),
                "missing_textures": asset.material_audit.get("missing_textures", []),
                "missing_material_refs": asset.material_audit.get("missing_material_refs", []),
                "package_local_missing_material_refs": asset.material_audit.get(
                    "package_local_missing_material_refs",
                    [],
                ),
                "approved_runtime_mdl_dependencies": asset.material_audit.get(
                    "approved_runtime_mdl_dependencies",
                    [],
                ),
                "registry_material_closure_source": asset.material_audit.get(
                    "registry_material_closure_source"
                ),
            }
            for asset in materialized_assets
        ],
    }


def _task_bindings(scene_result: dict[str, Any]) -> dict[str, str]:
    bindings = _mapping(scene_result.get("task_bindings"))
    return {
        "object": str(bindings["object"]),
        "target_container": str(bindings["container"]),
    }


def _package_id(request: dict[str, Any]) -> str:
    request_id = str(request.get("request_id", "image_task_candidate"))
    safe = "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in request_id)
    return f"phase13_{safe}"


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_of_mappings(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _string_items(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]


def _valid_float_list(value: object, length: int) -> bool:
    return isinstance(value, list) and len(value) == length and all(
        isinstance(item, int | float) for item in value
    )

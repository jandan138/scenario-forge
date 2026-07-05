from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.assets.materials import audit_mdl_texture_closure

PHASE12_FREEZE_SCHEMA_VERSION = "phase12-registry-readiness-freeze/v0.1"
PHASE12_CONTRACT_GATE_SCHEMA_VERSION = "phase12-registry-contract-gate/v0.1"
PACKAGE_REGISTRY_SCHEMA_VERSION = "package-registry/v0.1"
ASSET_REGISTRY_SCHEMA_VERSION = "asset-registry/v0.1"
REGISTRY_QUERY_CONTRACT_SCHEMA_VERSION = "registry-query-contract/v0.1"
REGISTRY_SNAPSHOT_SCHEMA_VERSION = "registry-snapshot/v0.1"
RESOLVER_SNAPSHOT_SCHEMA_VERSION = "resolver-snapshot/v0.1"
PHASE12_SNAPSHOT_GATE_SCHEMA_VERSION = "phase12-registry-snapshot-gate/v0.1"
READONLY_VIEWER_SCHEMA_VERSION = "readonly-evidence-viewer/v0.1"
PHASE12_VIEWER_GATE_SCHEMA_VERSION = "phase12-readonly-viewer-gate/v0.1"
HANDOFF_SCHEMA_VERSION = "ebench-eos-handoff-examples/v0.1"
PHASE12_HANDOFF_GATE_SCHEMA_VERSION = "phase12-ebench-eos-handoff-gate/v0.1"
EXPORT_DESCRIPTOR_SCHEMA_VERSION = "multi-simulator-export-descriptors/v0.1"
PHASE12_EXPORT_GATE_SCHEMA_VERSION = "phase12-multi-simulator-export-gate/v0.1"
HOSTED_ALPHA_SCHEMA_VERSION = "hosted-internal-registry-alpha/v0.1"
PHASE12_POLICY_GATE_SCHEMA_VERSION = "phase12-public-release-policy-closure-gate/v0.1"
PHASE12_CURRENT_GATE_INDEX_SCHEMA_VERSION = "phase12-current-gate-index/v0.1"

PHASE12_CONTRACTS = (
    "package-registry-entry/v0.1",
    "asset-registry-entry/v0.1",
    "registry-query-contract/v0.1",
)
PHASE11_TECHNICAL_GATE_KEYS = ("11.0", "11.1", "11.2", "11.3", "11.4")
PHASE12_SIMULATORS = ("isaacsim", "habitat", "maniskill", "omnigibson")
ARTIFACT_VARIANT_MARKERS = (
    "nomdl_relink",
    "contactfixed",
    "posefixed",
    "material_fixed",
)


class Phase12RegistryError(ValueError):
    """Raised when Phase 12 registry artifacts cannot be generated."""


@dataclass(frozen=True)
class Phase12RegistryResult:
    suite_root: Path
    status: str
    evidence_paths: tuple[Path, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class _PackageSource:
    package_id: str
    task_label: str
    package_root: Path | None
    evidence_dir: Path | None
    manifest_path: Path | None
    asset_manifest_path: Path | None
    asset_lock_path: Path | None
    scene_usd_path: Path | None
    task_path: Path | None
    metrics_path: Path | None
    validation_report_path: Path | None
    technical_gates: dict[str, Path]
    release_gate: Path | None


def generate_phase12_registry_artifacts(
    suite_dir: str | Path,
    gate_index_path: str | Path,
) -> Phase12RegistryResult:
    suite_root = Path(suite_dir)
    gate_index_file = Path(gate_index_path)
    suite_manifest = _load_yaml(suite_root / "suite_manifest.yaml")
    gate_index = _load_yaml(gate_index_file)
    readiness_gate = _load_readiness_gate(gate_index_file, gate_index)
    suite_id = str(suite_manifest.get("suite_id", gate_index.get("suite_id", suite_root.name)))
    suite_packages = _suite_package_paths(suite_root, suite_manifest)
    sources = [
        _package_source_from_index_item(suite_root, gate_index_file, suite_packages, item)
        for item in _list_of_mappings(gate_index.get("packages"))
    ]
    package_entries = [_package_registry_entry(suite_root, source) for source in sources]
    asset_entries = _asset_registry_entries(suite_root, sources)

    evidence_dir = suite_root / "evidence"
    registry_dir = suite_root / "registry"
    viewer_dir = suite_root / "viewer"
    handoff_dir = suite_root / "handoff"
    simulators_dir = suite_root / "adapters" / "simulators"

    freeze_blockers = _freeze_blockers(gate_index, readiness_gate)
    freeze = {
        "schema_version": PHASE12_FREEZE_SCHEMA_VERSION,
        "phase": "12.0",
        "status": _status_from_blockers(freeze_blockers),
        "suite_id": suite_id,
        "source_gate_index": _artifact_ref(gate_index_file, suite_root),
        "phase11_readiness_gate": _artifact_ref(_readiness_gate_path(gate_index_file, gate_index), suite_root),
        "package_count": len(package_entries),
        "packages": [
            {
                "package_id": entry["package_id"],
                "registry_version": entry["registry_version"],
                "release_status": entry["release_status"],
                "evidence_refs": entry["evidence_refs"],
            }
            for entry in package_entries
        ],
        "manual_blockers": _manual_blockers(gate_index, readiness_gate),
        "unknown_blockers": _unknown_blockers(gate_index, readiness_gate),
        "blockers": freeze_blockers,
        "next_stage": "local_package_asset_registry_contract"
        if not freeze_blockers
        else "blocked",
        "claim_boundary": (
            "Phase 12.0 registry readiness freeze only. It freezes retained Phase 11 "
            "evidence references and does not rerun episodes, alter gate status, or "
            "claim leaderboard comparability."
        ),
    }
    freeze_path = write_yaml_artifact(
        evidence_dir / "phase12_0_registry_readiness_freeze.yaml",
        freeze,
    )

    package_registry = {
        "schema_version": PACKAGE_REGISTRY_SCHEMA_VERSION,
        "suite_id": suite_id,
        "registry_scope": "local_immutable_snapshot_seed",
        "entry_schema": "package-registry-entry/v0.1",
        "packages": package_entries,
    }
    package_registry_path = write_yaml_artifact(
        registry_dir / "package_registry.yaml",
        package_registry,
    )
    asset_registry = {
        "schema_version": ASSET_REGISTRY_SCHEMA_VERSION,
        "suite_id": suite_id,
        "registry_scope": "local_immutable_snapshot_seed",
        "entry_schema": "asset-registry-entry/v0.1",
        "assets": asset_entries,
    }
    asset_registry_path = write_yaml_artifact(registry_dir / "asset_registry.yaml", asset_registry)
    query_contract = _registry_query_contract(suite_id)
    query_contract_path = write_yaml_artifact(
        registry_dir / "registry_query_contract.yaml",
        query_contract,
    )
    contract_blockers = _contract_blockers(package_entries, asset_entries)
    contract_gate = {
        "schema_version": PHASE12_CONTRACT_GATE_SCHEMA_VERSION,
        "phase": "12.1",
        "status": _status_from_blockers(contract_blockers),
        "suite_id": suite_id,
        "contracts": list(PHASE12_CONTRACTS),
        "package_registry": _artifact_ref(package_registry_path, suite_root),
        "asset_registry": _artifact_ref(asset_registry_path, suite_root),
        "registry_query_contract": _artifact_ref(query_contract_path, suite_root),
        "blockers": contract_blockers,
        "next_stage": "registry_snapshot_resolver_snapshot"
        if not contract_blockers
        else "blocked",
        "claim_boundary": (
            "Phase 12.1 registry contract gate only. It validates registry metadata "
            "shape and retained references, not runtime execution or task success."
        ),
    }
    contract_gate_path = write_yaml_artifact(
        evidence_dir / "phase12_1_registry_contract_gate.yaml",
        contract_gate,
    )

    snapshot_payload = {
        "schema_version": REGISTRY_SNAPSHOT_SCHEMA_VERSION,
        "suite_id": suite_id,
        "package_registry": package_registry,
        "asset_registry": asset_registry,
        "registry_query_contract": query_contract,
    }
    snapshot_digest = _digest_data(snapshot_payload)
    registry_snapshot = {
        **snapshot_payload,
        "snapshot_digest": snapshot_digest,
        "immutability": "content_addressed_metadata_snapshot",
    }
    registry_snapshot_path = write_yaml_artifact(
        registry_dir / "registry_snapshot.yaml",
        registry_snapshot,
    )
    resolver_snapshot = _resolver_snapshot(suite_id, asset_entries, snapshot_digest)
    resolver_snapshot_path = write_yaml_artifact(
        registry_dir / "resolver_snapshot.yaml",
        resolver_snapshot,
    )
    snapshot_digest_path = registry_dir / "snapshot_digest.txt"
    snapshot_digest_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_digest_path.write_text(snapshot_digest + "\n", encoding="utf-8")
    snapshot_blockers = _snapshot_blockers(registry_snapshot, resolver_snapshot)
    snapshot_gate = {
        "schema_version": PHASE12_SNAPSHOT_GATE_SCHEMA_VERSION,
        "phase": "12.2",
        "status": _status_from_blockers(snapshot_blockers),
        "suite_id": suite_id,
        "registry_snapshot": _artifact_ref(registry_snapshot_path, suite_root),
        "resolver_snapshot": _artifact_ref(resolver_snapshot_path, suite_root),
        "snapshot_digest": snapshot_digest,
        "snapshot_digest_file": _artifact_ref(snapshot_digest_path, suite_root),
        "blockers": snapshot_blockers,
        "next_stage": "readonly_evidence_package_viewer"
        if not snapshot_blockers
        else "blocked",
        "claim_boundary": (
            "Phase 12.2 snapshot gate only. It proves deterministic registry metadata "
            "digesting and resolver references, not simulator runtime readiness."
        ),
    }
    snapshot_gate_path = write_yaml_artifact(
        evidence_dir / "phase12_2_registry_snapshot_gate.yaml",
        snapshot_gate,
    )

    viewer_manifest = _viewer_manifest(suite_id, package_entries, snapshot_digest)
    viewer_manifest_path = write_yaml_artifact(viewer_dir / "readonly_index.yaml", viewer_manifest)
    viewer_index_path = _write_viewer_markdown(viewer_dir / "index.md", viewer_manifest)
    viewer_blockers = _viewer_blockers(viewer_manifest)
    viewer_gate = {
        "schema_version": PHASE12_VIEWER_GATE_SCHEMA_VERSION,
        "phase": "12.3",
        "status": _status_from_blockers(viewer_blockers),
        "suite_id": suite_id,
        "viewer_manifest": _artifact_ref(viewer_manifest_path, suite_root),
        "viewer_index": _artifact_ref(viewer_index_path, suite_root),
        "blockers": viewer_blockers,
        "next_stage": "ebench_eos_handoff_examples" if not viewer_blockers else "blocked",
        "claim_boundary": (
            "Phase 12.3 read-only viewer gate only. Viewer status is derived from "
            "retained gate files and cannot override failed or blocked evidence."
        ),
    }
    viewer_gate_path = write_yaml_artifact(
        evidence_dir / "phase12_3_readonly_viewer_gate.yaml",
        viewer_gate,
    )

    handoff = _handoff_examples(suite_id, package_entries, snapshot_digest)
    handoff_path = write_yaml_artifact(handoff_dir / "ebench_eos_handoff_examples.yaml", handoff)
    handoff_blockers = _handoff_blockers(handoff, package_entries)
    handoff_gate = {
        "schema_version": PHASE12_HANDOFF_GATE_SCHEMA_VERSION,
        "phase": "12.4",
        "status": _status_from_blockers(handoff_blockers),
        "suite_id": suite_id,
        "handoff_examples": _artifact_ref(handoff_path, suite_root),
        "blockers": handoff_blockers,
        "next_stage": "multi_simulator_export_descriptors"
        if not handoff_blockers
        else "blocked",
        "claim_boundary": (
            "Phase 12.4 handoff gate only. It documents how EBench/EOS consume the "
            "snapshot; Scenario Forge still does not run episodes or evaluate models."
        ),
    }
    handoff_gate_path = write_yaml_artifact(
        evidence_dir / "phase12_4_ebench_eos_handoff_gate.yaml",
        handoff_gate,
    )

    export_descriptors = _export_descriptors(suite_id, snapshot_digest)
    export_descriptors_path = write_yaml_artifact(
        simulators_dir / "export_descriptors.yaml",
        export_descriptors,
    )
    export_blockers = _export_blockers(export_descriptors)
    export_gate = {
        "schema_version": PHASE12_EXPORT_GATE_SCHEMA_VERSION,
        "phase": "12.5",
        "status": _status_from_blockers(export_blockers),
        "suite_id": suite_id,
        "export_descriptors": _artifact_ref(export_descriptors_path, suite_root),
        "blockers": export_blockers,
        "next_stage": "hosted_internal_registry_alpha_policy_closure"
        if not export_blockers
        else "blocked",
        "claim_boundary": (
            "Phase 12.5 export descriptor gate only. Descriptors are portable mapping "
            "examples and do not prove downstream runtime smoke for every simulator."
        ),
    }
    export_gate_path = write_yaml_artifact(
        evidence_dir / "phase12_5_multi_simulator_export_gate.yaml",
        export_gate,
    )

    hosted_alpha = _hosted_alpha_manifest(suite_id, package_entries, snapshot_digest)
    hosted_alpha_path = write_yaml_artifact(
        registry_dir / "hosted_internal_registry_alpha.yaml",
        hosted_alpha,
    )
    policy_blockers = _policy_blockers(gate_index, readiness_gate, package_entries)
    policy_gate = {
        "schema_version": PHASE12_POLICY_GATE_SCHEMA_VERSION,
        "phase": "12.6",
        "status": _status_from_blockers(policy_blockers),
        "suite_id": suite_id,
        "hosted_internal_registry_alpha": _artifact_ref(hosted_alpha_path, suite_root),
        "license_policy": "pass" if not policy_blockers else "blocked",
        "redistribution_approval": _redistribution_approval(readiness_gate),
        "known_blockers": policy_blockers,
        "blockers": policy_blockers,
        "next_stage": "phase13_image_grounded_task_factory" if not policy_blockers else "blocked",
        "claim_boundary": (
            "Phase 12.6 policy closure gate only. Public release claims are limited to "
            "packages with license_policy=pass, redistribution_approval=true, and no "
            "known blockers; this is not leaderboard comparability."
        ),
    }
    policy_gate_path = write_yaml_artifact(
        evidence_dir / "phase12_6_public_release_policy_closure_gate.yaml",
        policy_gate,
    )

    gate_paths = {
        "12.0": freeze_path,
        "12.1": contract_gate_path,
        "12.2": snapshot_gate_path,
        "12.3": viewer_gate_path,
        "12.4": handoff_gate_path,
        "12.5": export_gate_path,
        "12.6": policy_gate_path,
    }
    gate_docs = {
        "12.0": freeze,
        "12.1": contract_gate,
        "12.2": snapshot_gate,
        "12.3": viewer_gate,
        "12.4": handoff_gate,
        "12.5": export_gate,
        "12.6": policy_gate,
    }
    all_blockers = _all_blockers(gate_docs)
    overall_status = "phase13_allowed" if not all_blockers else "blocked"
    current_index = {
        "schema_version": PHASE12_CURRENT_GATE_INDEX_SCHEMA_VERSION,
        "suite_id": suite_id,
        "overall_status": overall_status,
        "phase13_allowed": not all_blockers,
        "latest_gates": {
            phase: {
                "path": _artifact_ref(path, suite_root),
                "schema_version": str(gate_docs[phase].get("schema_version")),
                "status": str(gate_docs[phase].get("status")),
            }
            for phase, path in gate_paths.items()
        },
        "registry_snapshot": _artifact_ref(registry_snapshot_path, suite_root),
        "snapshot_digest": snapshot_digest,
        "blockers": all_blockers,
        "next_allowed_phase": {
            "phase": "13.0",
            "scope": "image_grounded_existing_asset_mvp",
        }
        if not all_blockers
        else None,
        "claim_boundary": (
            "Phase 12 current gate index only. It records retained registry, viewer, "
            "handoff, descriptor, and policy evidence and does not run episodes or "
            "publish leaderboard results."
        ),
    }
    current_index_path = write_yaml_artifact(
        evidence_dir / "phase12_current_gate_index.yaml",
        current_index,
    )
    evidence_paths = (
        freeze_path,
        contract_gate_path,
        snapshot_gate_path,
        viewer_gate_path,
        handoff_gate_path,
        export_gate_path,
        policy_gate_path,
        current_index_path,
    )
    return Phase12RegistryResult(
        suite_root=suite_root,
        status=overall_status,
        evidence_paths=evidence_paths,
        blockers=tuple(all_blockers),
    )


def _package_source_from_index_item(
    suite_root: Path,
    gate_index_file: Path,
    suite_packages: dict[str, Path],
    item: dict[str, Any],
) -> _PackageSource:
    package_id = str(item.get("package_id", ""))
    task_label = str(item.get("task_label", package_id))
    package_root = suite_packages.get(package_id)
    if package_root is not None and not (package_root / "manifest.yaml").exists():
        package_root = None
    if package_root is not None and not _is_stable_public_root(package_root, suite_root):
        package_root = None

    technical_gates: dict[str, Path] = {}
    raw_technical_gates = item.get("technical_gates")
    if isinstance(raw_technical_gates, dict):
        for phase in PHASE11_TECHNICAL_GATE_KEYS:
            raw_ref = raw_technical_gates.get(phase)
            resolved = _resolve_ref(gate_index_file.parent, raw_ref)
            if resolved is not None:
                technical_gates[phase] = resolved

    raw_release_gate = item.get("release_gate")
    release_gate: Path | None = None
    if isinstance(raw_release_gate, dict):
        release_gate = _resolve_ref(gate_index_file.parent, raw_release_gate.get("11.5"))

    evidence_dir = _first_existing_parent([*technical_gates.values(), release_gate])
    if evidence_dir is None and package_root is not None:
        evidence_dir = package_root / "evidence"
    variant_hints = _variant_hints([*technical_gates.values(), release_gate])

    manifest_path = _package_file(
        package_root,
        evidence_dir,
        task_label,
        "manifest.yaml",
        "package_manifest",
        variant_hints=variant_hints,
    )
    asset_manifest_path = _package_file(
        package_root,
        evidence_dir,
        task_label,
        "assets/asset_manifest.yaml",
        "asset_manifest",
        variant_hints=variant_hints,
    )
    asset_lock_path = _package_file(
        package_root,
        evidence_dir,
        task_label,
        "locks/asset_lock.yaml",
        "asset_lock",
        variant_hints=variant_hints,
    )
    scene_usd_path = _package_file(
        package_root,
        evidence_dir,
        task_label,
        "scene/main.usda",
        "main",
        suffix=".usda",
        variant_hints=variant_hints,
    )
    task_path = _package_file(
        package_root,
        evidence_dir,
        task_label,
        "task/task.yaml",
        "task",
        variant_hints=variant_hints,
    )
    metrics_path = _package_file(
        package_root,
        evidence_dir,
        task_label,
        "metrics/metrics.yaml",
        "metrics",
        variant_hints=variant_hints,
    )
    validation_report_path = _package_file(
        package_root,
        evidence_dir,
        task_label,
        "evidence/validation_report.yaml",
        "validation_report",
        variant_hints=variant_hints,
    )
    if validation_report_path is None and package_root is not None:
        fallback = package_root / "evidence" / "validation_report.yaml"
        validation_report_path = fallback if fallback.exists() else None

    return _PackageSource(
        package_id=package_id,
        task_label=task_label,
        package_root=package_root,
        evidence_dir=evidence_dir,
        manifest_path=manifest_path,
        asset_manifest_path=asset_manifest_path,
        asset_lock_path=asset_lock_path,
        scene_usd_path=scene_usd_path,
        task_path=task_path,
        metrics_path=metrics_path,
        validation_report_path=validation_report_path,
        technical_gates=technical_gates,
        release_gate=release_gate,
    )


def _package_registry_entry(suite_root: Path, source: _PackageSource) -> dict[str, Any]:
    manifest = _load_optional_yaml(source.manifest_path)
    package_id = str(manifest.get("package_id", source.package_id))
    manifest_digest = _file_digest(source.manifest_path)
    schema_version = str(manifest.get("schema_version", "scenario-package/v0.2"))
    registry_version = f"{schema_version.rsplit('/', 1)[-1]}+{manifest_digest[7:19]}"
    evidence_refs = {
        phase: _artifact_ref(path, suite_root) for phase, path in sorted(source.technical_gates.items())
    }
    if source.release_gate is not None:
        evidence_refs["11.5"] = _artifact_ref(source.release_gate, suite_root)
    release_status = "passed" if _gate_status(source.release_gate) == "passed" else "blocked"
    return {
        "schema_version": "package-registry-entry/v0.1",
        "package_id": package_id,
        "registry_version": registry_version,
        "scenario_domain": str(manifest.get("scenario_domain", "unspecified")),
        "task_label": source.task_label,
        "task_family": _task_family(source.task_path),
        "package_mode": str(manifest.get("package_mode", "fat")),
        "targets": _string_list(manifest.get("targets")),
        "release_status": release_status,
        "artifact_refs": _compact_mapping(
            {
                "manifest": _artifact_ref(source.manifest_path, suite_root),
                "asset_manifest": _artifact_ref(source.asset_manifest_path, suite_root),
                "asset_lock": _artifact_ref(source.asset_lock_path, suite_root),
                "scene_usd": _artifact_ref(source.scene_usd_path, suite_root),
                "task": _artifact_ref(source.task_path, suite_root),
                "metrics": _artifact_ref(source.metrics_path, suite_root),
                "validation_report": _artifact_ref(source.validation_report_path, suite_root),
            }
        ),
        "evidence_refs": evidence_refs,
        "content_digest": manifest_digest,
        "claim_boundary": (
            "Package registry entry only. Runtime and task-success claims must be read "
            "from retained Phase 11 gate evidence."
        ),
    }


def _asset_registry_entries(suite_root: Path, sources: list[_PackageSource]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for source in sources:
        manifest_assets = _manifest_assets(source.asset_manifest_path)
        lock_assets = _lock_assets(source.asset_lock_path)
        if manifest_assets:
            for asset in manifest_assets:
                asset_id = str(asset.get("asset_id", ""))
                lock = lock_assets.get(asset_id, {})
                content_sha256 = str(
                    lock.get("content_sha256") or asset.get("sha256") or _file_digest(source.asset_manifest_path)
                )
                entries.append(
                    _asset_registry_entry(
                        suite_root=suite_root,
                        source=source,
                        asset=asset,
                        lock=lock,
                        content_sha256=content_sha256,
                    )
                )
            continue
        for asset_id, lock in lock_assets.items():
            asset = {
                "asset_id": asset_id,
                "role": lock.get("role", "unspecified"),
                "asset_type": lock.get("asset_type", "usd_bundle"),
                "canonical_usd": lock.get("resolved_path", ""),
                "license": lock.get("license", ""),
            }
            entries.append(
                _asset_registry_entry(
                    suite_root=suite_root,
                    source=source,
                    asset=asset,
                    lock=lock,
                    content_sha256=str(lock.get("content_sha256", "")),
                )
            )
    return sorted(entries, key=lambda item: (item["asset_id"], item["asset_uid"]))


def _asset_registry_entry(
    *,
    suite_root: Path,
    source: _PackageSource,
    asset: dict[str, Any],
    lock: dict[str, Any],
    content_sha256: str,
) -> dict[str, Any]:
    asset_id = str(asset.get("asset_id", ""))
    raw_source_uri = str(asset.get("source_uri") or lock.get("source_uri", ""))
    source_uri, source_uri_policy = _public_source_uri(
        raw_source_uri,
        asset_manifest_ref=_artifact_ref(source.asset_manifest_path, suite_root),
        asset_id=asset_id,
    )
    return {
        "schema_version": "asset-registry-entry/v0.1",
        "asset_uid": f"{asset_id}@{_digest_suffix(content_sha256)}",
        "asset_id": asset_id,
        "source_package_id": source.package_id,
        "role": str(asset.get("role", "unspecified")),
        "asset_type": str(asset.get("asset_type", "usd_bundle")),
        "canonical_usd": str(asset.get("canonical_usd") or lock.get("resolved_path", "")),
        "content_sha256": content_sha256,
        "license": str(asset.get("license") or lock.get("license", "")),
        "source_kind": str(asset.get("source_kind") or lock.get("source_kind", "package_local")),
        "source_uri": source_uri,
        "source_uri_policy": source_uri_policy,
        "resolver_version": str(
            asset.get("resolver_version") or lock.get("resolver_version", "scenario-forge/unknown")
        ),
        "semantic_tags": _asset_semantic_tags(asset, lock),
        "affordances": _asset_affordances(asset, lock),
        "role_suitability": _asset_role_suitability(asset, lock),
        "material_closure": _asset_material_closure(source, asset, lock, raw_source_uri),
        "physics_readiness": _asset_physics_readiness(source, asset, lock),
        "export_eligibility": _asset_export_eligibility(source, asset, lock),
        "provenance": {
            "source_package_id": source.package_id,
            "asset_manifest": _artifact_ref(source.asset_manifest_path, suite_root),
            "asset_lock": _artifact_ref(source.asset_lock_path, suite_root),
        },
        "claim_boundary": (
            "Asset registry entry only. It records locked USD asset metadata and does "
            "not perform mesh, MDL, texture, or material conversion."
        ),
    }


def _asset_semantic_tags(asset: dict[str, Any], lock: dict[str, Any]) -> list[str]:
    tags = [
        *_string_items(asset.get("semantic_tags")),
        *_string_items(lock.get("semantic_tags")),
    ]
    role = str(asset.get("role") or lock.get("role") or "")
    asset_type = str(asset.get("asset_type") or lock.get("asset_type") or "")
    for value in (role, asset_type):
        if value and value != "unspecified" and value not in tags:
            tags.append(value)
    return tags


def _asset_affordances(asset: dict[str, Any], lock: dict[str, Any]) -> list[str]:
    affordances = [
        *_string_items(asset.get("affordances")),
        *_string_items(lock.get("affordances")),
    ]
    role = str(asset.get("role") or lock.get("role") or "")
    asset_type = str(asset.get("asset_type") or lock.get("asset_type") or "")
    inferred = {
        "manipulated_object": ["pickable", "rigid"],
        "target_container": ["container", "rigid"],
        "target_region": ["target"],
        "environment": ["support_surface"],
        "robot": ["robot"],
    }
    for value in [*inferred.get(role, []), *inferred.get(asset_type, [])]:
        if value not in affordances:
            affordances.append(value)
    return affordances


def _asset_role_suitability(asset: dict[str, Any], lock: dict[str, Any]) -> list[dict[str, str]]:
    role = str(asset.get("role") or lock.get("role") or "unspecified")
    asset_type = str(asset.get("asset_type") or lock.get("asset_type") or "usd_bundle")
    return [
        {
            "role": role,
            "asset_type": asset_type,
            "status": "suitable",
            "evidence_source": "retained_package_role_binding",
        }
    ]


def _asset_material_closure(
    source: _PackageSource,
    asset: dict[str, Any],
    lock: dict[str, Any],
    raw_source_uri: str,
) -> dict[str, Any]:
    audit_root = _material_audit_root(source, asset, lock, raw_source_uri)
    if audit_root is None:
        if _gate_status(source.release_gate) == "passed" and (
            asset.get("sha256") or lock.get("content_sha256")
        ):
            return {
                "status": "passed",
                "evidence_source": "phase11_release_candidate_gate_retained_readiness",
                "audit_root": "retained_evidence_only",
                "missing_texture_count": 0,
                "missing_textures": [],
                "missing_material_ref_count": 0,
                "missing_material_refs": [],
                "runtime_preflight_required": True,
            }
        return {
            "status": "blocked",
            "evidence_source": "missing_material_audit_root",
            "missing_texture_count": None,
            "missing_material_ref_count": None,
        }
    audit = audit_mdl_texture_closure(audit_root)
    runtime_approval = _runtime_mdl_approval(source, audit)
    if runtime_approval and audit["status"] == "failed" and audit["missing_texture_count"] == 0:
        approved_modules = {
            str(item.get("module"))
            for item in runtime_approval["approved_runtime_mdl_dependencies"]
            if item.get("module")
        }
        missing_material_refs = _list_of_mappings(audit["missing_material_refs"])
        unapproved_refs = [
            item for item in missing_material_refs if str(item.get("material", "")) not in approved_modules
        ]
        if not unapproved_refs:
            return {
                "status": "passed",
                "evidence_source": "local_usd_bundle_mdl_audit_with_runtime_approval",
                "audit_scope": "local_usd_bundle",
                "missing_texture_count": 0,
                "missing_textures": [],
                "missing_material_ref_count": 0,
                "missing_material_refs": [],
                "package_local_missing_material_refs": missing_material_refs,
                "approved_runtime_mdl_dependencies": runtime_approval[
                    "approved_runtime_mdl_dependencies"
                ],
                "runtime_preflight_evidence": runtime_approval["runtime_preflight_evidence"],
                "mdl_search_paths": runtime_approval["mdl_search_paths"],
            }
    return {
        "status": audit["status"],
        "evidence_source": "local_usd_bundle_mdl_texture_audit",
        "audit_scope": "local_usd_bundle",
        "missing_texture_count": audit["missing_texture_count"],
        "missing_textures": audit["missing_textures"],
        "missing_material_ref_count": audit["missing_material_ref_count"],
        "missing_material_refs": audit["missing_material_refs"],
    }


def _runtime_mdl_approval(source: _PackageSource, audit: dict[str, Any]) -> dict[str, Any] | None:
    missing_modules = {
        str(item.get("material"))
        for item in _list_of_mappings(audit.get("missing_material_refs"))
        if item.get("material")
    }
    if not missing_modules:
        return None

    approved_by_module: dict[str, dict[str, Any]] = {}
    evidence_refs: list[str] = []
    search_paths: list[str] = []
    for metadata_path in _render_metadata_candidates(source):
        metadata = _load_optional_json(metadata_path)
        material_preflight = metadata.get("material_runtime_preflight")
        if not isinstance(material_preflight, dict):
            continue
        if material_preflight.get("status") != "pass":
            continue
        if material_preflight.get("blocked_dependency_count") not in (0, None):
            continue
        blocked_dependencies = material_preflight.get("blocked_dependencies")
        if isinstance(blocked_dependencies, list) and blocked_dependencies:
            continue

        for raw_search_path in _string_items(material_preflight.get("mdl_search_paths")):
            if raw_search_path not in search_paths:
                search_paths.append(raw_search_path)
        for dependency in _list_of_mappings(
            material_preflight.get("approved_runtime_mdl_dependencies")
        ):
            module = dependency.get("module")
            if not isinstance(module, str) or module not in missing_modules:
                continue
            if dependency.get("resolution") != "approved_runtime_module":
                continue
            runtime_path = dependency.get("runtime_path")
            if not isinstance(runtime_path, str) or not runtime_path:
                continue
            approved_by_module[module] = {
                "module": module,
                "resolution": "approved_runtime_module",
                "runtime_path": runtime_path,
            }
            ref = str(metadata_path)
            if ref not in evidence_refs:
                evidence_refs.append(ref)

    if missing_modules.difference(approved_by_module):
        return None
    return {
        "approved_runtime_mdl_dependencies": [
            approved_by_module[module] for module in sorted(approved_by_module)
        ],
        "runtime_preflight_evidence": evidence_refs,
        "mdl_search_paths": search_paths,
    }


def _render_metadata_candidates(source: _PackageSource) -> tuple[Path, ...]:
    candidates: list[Path] = []
    for base in (source.evidence_dir, source.package_root / "evidence" if source.package_root else None):
        if base is None or not base.exists():
            continue
        for path in sorted(base.glob("*render_metadata*.json")):
            if path.is_file() and path not in candidates:
                candidates.append(path)
    return tuple(candidates)


def _load_optional_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _material_audit_root(
    source: _PackageSource,
    asset: dict[str, Any],
    lock: dict[str, Any],
    raw_source_uri: str,
) -> Path | None:
    source_path = _source_uri_to_path(raw_source_uri)
    if source_path is not None and source_path.exists():
        return source_path.parent if source_path.is_file() else source_path

    canonical_usd = str(asset.get("canonical_usd") or lock.get("resolved_path") or "")
    if canonical_usd and source.package_root is not None:
        package_asset = (source.package_root / canonical_usd).resolve()
        if package_asset.exists():
            return package_asset.parent if package_asset.is_file() else package_asset
    return None


def _source_uri_to_path(source_uri: str) -> Path | None:
    if not source_uri:
        return None
    if source_uri.startswith("file://"):
        return Path(source_uri.removeprefix("file://"))
    if "://" in source_uri or source_uri.startswith(("omniverse:", "mdl:")):
        return None
    return Path(source_uri)


def _asset_physics_readiness(
    source: _PackageSource,
    asset: dict[str, Any],
    lock: dict[str, Any],
) -> dict[str, str]:
    status = "ready" if _gate_status(source.release_gate) == "passed" else "blocked"
    role = str(asset.get("role") or lock.get("role") or "unspecified")
    return {
        "status": status,
        "role": role,
        "evidence_source": "phase11_release_candidate_gate",
        "claim_boundary": (
            "Phase 12 records retained package readiness metadata only; simulator "
            "runtime behavior remains evidenced by Phase 11/EOS gates."
        ),
    }


def _asset_export_eligibility(
    source: _PackageSource,
    asset: dict[str, Any],
    lock: dict[str, Any],
) -> dict[str, object]:
    license_value = str(asset.get("license") or lock.get("license") or "")
    release_gate_passed = _gate_status(source.release_gate) == "passed"
    return {
        "ebench": bool(license_value and release_gate_passed),
        "license": license_value,
        "evidence_source": "phase11_release_candidate_gate",
        "redistribution_scope": "retained_phase12_registry_snapshot",
    }


def _freeze_blockers(gate_index: dict[str, Any], readiness_gate: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if gate_index.get("schema_version") != "phase11-current-gate-index/v0.1":
        blockers.append("gate index schema_version must be phase11-current-gate-index/v0.1")
    if gate_index.get("phase12_allowed") is not True:
        blockers.append("phase12_allowed must be true")
    if gate_index.get("technical_closure_status") != "passed":
        blockers.append(
            "technical_closure_status must be passed; "
            f"got {gate_index.get('technical_closure_status')}"
        )
    if gate_index.get("public_release_status") != "release_candidate_passed":
        blockers.append(
            "public_release_status must be release_candidate_passed; "
            f"got {gate_index.get('public_release_status')}"
        )
    if readiness_gate and readiness_gate.get("status") != "passed":
        blockers.append(f"phase11 readiness gate status must be passed; got {readiness_gate.get('status')}")
    if readiness_gate and readiness_gate.get("phase12_allowed") is not True:
        blockers.append("phase11 readiness gate phase12_allowed must be true")
    for blocker in _manual_blockers(gate_index, readiness_gate):
        blockers.append(f"manual blocker must be empty: {blocker}")
    for blocker in _unknown_blockers(gate_index, readiness_gate):
        blockers.append(f"unknown blocker must be empty: {blocker}")
    return blockers


def _contract_blockers(
    package_entries: list[dict[str, Any]],
    asset_entries: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    seen_packages: set[tuple[str, str]] = set()
    for entry in package_entries:
        key = (str(entry.get("package_id", "")), str(entry.get("registry_version", "")))
        if not key[0] or not key[1]:
            blockers.append("package registry entries must include package_id and registry_version")
        if key in seen_packages:
            blockers.append(f"duplicate package_id/version in registry: {key[0]} {key[1]}")
        seen_packages.add(key)
        artifact_refs = entry.get("artifact_refs")
        if not isinstance(artifact_refs, dict) or not artifact_refs.get("manifest"):
            blockers.append(f"package {key[0]} missing manifest artifact ref")
        if not isinstance(artifact_refs, dict) or not artifact_refs.get("asset_lock"):
            blockers.append(f"package {key[0]} missing asset_lock artifact ref")
        if entry.get("release_status") != "passed":
            blockers.append(f"package {key[0]} release_status must be passed")

    for entry in asset_entries:
        asset_id = str(entry.get("asset_id", ""))
        if "/" in asset_id or asset_id.startswith("."):
            blockers.append(f"asset_id must be semantic, not a local path: {asset_id}")
        for field in ("content_sha256", "license", "resolver_version"):
            if not str(entry.get(field, "")).strip():
                blockers.append(f"asset {asset_id} missing {field}")
        material_closure = entry.get("material_closure")
        if not isinstance(material_closure, dict) or not str(material_closure.get("status", "")).strip():
            blockers.append(f"asset {asset_id} missing material_closure.status")
        physics_readiness = entry.get("physics_readiness")
        if not isinstance(physics_readiness, dict) or not str(physics_readiness.get("status", "")).strip():
            blockers.append(f"asset {asset_id} missing physics_readiness.status")
        export_eligibility = entry.get("export_eligibility")
        if not isinstance(export_eligibility, dict) or "ebench" not in export_eligibility:
            blockers.append(f"asset {asset_id} missing export_eligibility.ebench")
        provenance = entry.get("provenance")
        if not isinstance(provenance, dict) or not provenance.get("source_package_id"):
            blockers.append(f"asset {asset_id} missing provenance.source_package_id")
    if not package_entries:
        blockers.append("package registry must contain at least one package")
    if not asset_entries:
        blockers.append("asset registry must contain at least one asset")
    return blockers


def _snapshot_blockers(
    registry_snapshot: dict[str, Any],
    resolver_snapshot: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    digest = registry_snapshot.get("snapshot_digest")
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        blockers.append("registry snapshot_digest must be sha256-prefixed")
    if resolver_snapshot.get("snapshot_digest") != digest:
        blockers.append("resolver snapshot digest must match registry snapshot digest")
    for package in _list_of_mappings(
        registry_snapshot.get("package_registry", {}).get("packages")
        if isinstance(registry_snapshot.get("package_registry"), dict)
        else None
    ):
        artifact_refs = package.get("artifact_refs")
        if isinstance(artifact_refs, dict):
            for name, ref in artifact_refs.items():
                if isinstance(ref, str) and ref.startswith("/tmp/"):
                    blockers.append(f"public package ref must not point at /tmp: {name}={ref}")
    asset_registry = registry_snapshot.get("asset_registry")
    asset_entries = asset_registry.get("assets") if isinstance(asset_registry, dict) else None
    for asset in _list_of_mappings(asset_entries):
        source_uri = asset.get("source_uri")
        if isinstance(source_uri, str) and _is_mutable_tmp_uri(source_uri):
            blockers.append(
                f"public asset source_uri must not point at /tmp: {asset.get('asset_uid')}"
            )
    return blockers


def _viewer_blockers(viewer_manifest: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if viewer_manifest.get("mode") != "read_only":
        blockers.append("viewer mode must be read_only")
    if viewer_manifest.get("status_source") != "retained_gate_files_only":
        blockers.append("viewer status_source must be retained_gate_files_only")
    if "override" in viewer_manifest:
        blockers.append("viewer manifest must not expose status override")
    return blockers


def _handoff_blockers(
    handoff: dict[str, Any],
    package_entries: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if handoff.get("pinned_registry_snapshot") != "registry/registry_snapshot.yaml":
        blockers.append("handoff examples must pin registry/registry_snapshot.yaml")
    examples = handoff.get("examples")
    if not isinstance(examples, list) or len(examples) != len(package_entries):
        blockers.append("handoff examples must include one entry per package")
    return blockers


def _export_blockers(export_descriptors: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    descriptors = _list_of_mappings(export_descriptors.get("descriptors"))
    simulators = {str(item.get("simulator")) for item in descriptors}
    missing = set(PHASE12_SIMULATORS) - simulators
    for simulator in sorted(missing):
        blockers.append(f"missing simulator export descriptor: {simulator}")
    for item in descriptors:
        if item.get("core_import_policy") != "no_simulator_sdk_in_core":
            blockers.append(
                f"descriptor {item.get('simulator')} must keep simulator SDKs out of core"
            )
    return blockers


def _policy_blockers(
    gate_index: dict[str, Any],
    readiness_gate: dict[str, Any],
    package_entries: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if gate_index.get("public_release_status") != "release_candidate_passed":
        blockers.append("public_release_status must be release_candidate_passed")
    policy_summary = readiness_gate.get("policy_gate_summary")
    if not isinstance(policy_summary, dict):
        blockers.append("readiness policy_gate_summary must be a mapping")
        policy_summary = {}
    if policy_summary.get("release_policy") != "pass":
        blockers.append(f"release_policy must be pass; got {policy_summary.get('release_policy')}")
    if policy_summary.get("redistribution_approval") is not True:
        blockers.append("redistribution_approval must be true")
    for field in ("known_policy_blockers", "known_non_policy_blockers", "blockers"):
        raw_blockers = readiness_gate.get(field)
        if isinstance(raw_blockers, list):
            blockers.extend(str(blocker) for blocker in raw_blockers if blocker)
    for entry in package_entries:
        if entry.get("release_status") != "passed":
            blockers.append(f"package {entry.get('package_id')} release_status must be passed")
    return blockers


def _registry_query_contract(suite_id: str) -> dict[str, Any]:
    return {
        "schema_version": REGISTRY_QUERY_CONTRACT_SCHEMA_VERSION,
        "suite_id": suite_id,
        "supported_queries": [
            {
                "name": "packages_by_task_family",
                "required_fields": ["task_family"],
                "returns": "package-registry-entry/v0.1",
            },
            {
                "name": "assets_by_semantic_role",
                "required_fields": ["role", "asset_type"],
                "returns": "asset-registry-entry/v0.1",
            },
            {
                "name": "evidence_by_package",
                "required_fields": ["package_id"],
                "returns": "retained_gate_refs",
            },
        ],
    }


def _resolver_snapshot(
    suite_id: str,
    asset_entries: list[dict[str, Any]],
    snapshot_digest: str,
) -> dict[str, Any]:
    return {
        "schema_version": RESOLVER_SNAPSHOT_SCHEMA_VERSION,
        "suite_id": suite_id,
        "snapshot_digest": snapshot_digest,
        "resolver_policy": "locked_asset_uid_to_retained_artifact_ref",
        "assets": [
            {
                "asset_uid": entry["asset_uid"],
                "asset_id": entry["asset_id"],
                "content_sha256": entry["content_sha256"],
                "resolver_version": entry["resolver_version"],
                "asset_lock": entry["provenance"]["asset_lock"],
            }
            for entry in asset_entries
        ],
    }


def _viewer_manifest(
    suite_id: str,
    package_entries: list[dict[str, Any]],
    snapshot_digest: str,
) -> dict[str, Any]:
    return {
        "schema_version": READONLY_VIEWER_SCHEMA_VERSION,
        "suite_id": suite_id,
        "mode": "read_only",
        "status_source": "retained_gate_files_only",
        "snapshot_digest": snapshot_digest,
        "packages": [
            {
                "package_id": entry["package_id"],
                "task_label": entry["task_label"],
                "release_status": entry["release_status"],
                "artifact_refs": entry["artifact_refs"],
                "evidence_refs": entry["evidence_refs"],
            }
            for entry in package_entries
        ],
        "claim_boundary": (
            "Read-only evidence viewer manifest. It can display retained evidence but "
            "cannot edit or override gate status."
        ),
    }


def _write_viewer_markdown(path: Path, viewer_manifest: dict[str, Any]) -> Path:
    lines = [
        "# Phase 12 Read-only Evidence Viewer",
        "",
        f"Suite: `{viewer_manifest['suite_id']}`",
        "",
        "Status is derived from retained gate files only. This page does not override gates.",
        "",
        "| Package | Release Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for package in _list_of_mappings(viewer_manifest.get("packages")):
        refs = package.get("evidence_refs")
        evidence_refs = ", ".join(sorted(refs.keys())) if isinstance(refs, dict) else ""
        lines.append(
            f"| `{package.get('package_id')}` | `{package.get('release_status')}` | "
            f"`{evidence_refs}` |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _handoff_examples(
    suite_id: str,
    package_entries: list[dict[str, Any]],
    snapshot_digest: str,
) -> dict[str, Any]:
    return {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "suite_id": suite_id,
        "pinned_registry_snapshot": "registry/registry_snapshot.yaml",
        "snapshot_digest": snapshot_digest,
        "examples": [
            {
                "package_id": entry["package_id"],
                "task_label": entry["task_label"],
                "package_manifest": entry["artifact_refs"].get("manifest"),
                "ebench_export": entry["artifact_refs"].get("ebench_export"),
                "eos_consumes": [
                    entry["artifact_refs"].get("manifest"),
                    entry["artifact_refs"].get("scene_usd"),
                    entry["artifact_refs"].get("asset_lock"),
                    entry["evidence_refs"].get("11.5"),
                ],
                "runtime_claim_source": "retained_phase11_eos_and_predicate_gates",
            }
            for entry in package_entries
        ],
        "non_goal": "Scenario Forge does not run EOS episodes or model adapters.",
    }


def _export_descriptors(suite_id: str, snapshot_digest: str) -> dict[str, Any]:
    return {
        "schema_version": EXPORT_DESCRIPTOR_SCHEMA_VERSION,
        "suite_id": suite_id,
        "snapshot_digest": snapshot_digest,
        "descriptors": [
            {
                "simulator": simulator,
                "descriptor_version": "v0.1",
                "input_contract": "scenario-package/v0.2",
                "required_artifacts": [
                    "manifest.yaml",
                    "scene/main.usda",
                    "scene/instances.yaml",
                    "locks/asset_lock.yaml",
                    "task/task.yaml",
                ],
                "core_import_policy": "no_simulator_sdk_in_core",
                "runtime_smoke_owner": "downstream_adapter",
                "claim_boundary": "Export descriptor only; downstream runtime smoke is external.",
            }
            for simulator in PHASE12_SIMULATORS
        ],
    }


def _hosted_alpha_manifest(
    suite_id: str,
    package_entries: list[dict[str, Any]],
    snapshot_digest: str,
) -> dict[str, Any]:
    return {
        "schema_version": HOSTED_ALPHA_SCHEMA_VERSION,
        "suite_id": suite_id,
        "mode": "internal_read_only_alpha",
        "snapshot_digest": snapshot_digest,
        "package_count": len(package_entries),
        "included_packages": [entry["package_id"] for entry in package_entries],
        "write_policy": "no_status_override",
        "public_release_policy": "requires_phase12_6_policy_closure_gate_pass",
    }


def _load_readiness_gate(gate_index_file: Path, gate_index: dict[str, Any]) -> dict[str, Any]:
    readiness_path = _readiness_gate_path(gate_index_file, gate_index)
    if readiness_path is None or not readiness_path.exists():
        return {}
    return _load_yaml(readiness_path)


def _readiness_gate_path(gate_index_file: Path, gate_index: dict[str, Any]) -> Path | None:
    suite_gates = gate_index.get("suite_gates")
    if not isinstance(suite_gates, dict):
        return None
    readiness = suite_gates.get("11.8_gate")
    if not isinstance(readiness, dict):
        return None
    return _resolve_ref(gate_index_file.parent, readiness.get("path"))


def _suite_package_paths(suite_root: Path, suite_manifest: dict[str, Any]) -> dict[str, Path]:
    packages: dict[str, Path] = {}
    for item in _list_of_mappings(suite_manifest.get("packages")):
        package_id = item.get("package_id")
        package_path = item.get("path")
        if isinstance(package_id, str) and isinstance(package_path, str):
            path = Path(package_path)
            packages[package_id] = path if path.is_absolute() else suite_root / path
    return packages


def _is_stable_public_root(path: Path, suite_root: Path) -> bool:
    resolved = path.resolve()
    suite_resolved = suite_root.resolve()
    if resolved == suite_resolved or suite_resolved in resolved.parents:
        return True
    cwd = Path.cwd().resolve()
    return resolved == cwd or cwd in resolved.parents


def _package_file(
    package_root: Path | None,
    evidence_dir: Path | None,
    task_label: str,
    package_relative: str,
    evidence_token: str,
    *,
    suffix: str = ".yaml",
    variant_hints: tuple[str, ...] = (),
) -> Path | None:
    candidates: list[Path] = []
    if package_root is not None:
        candidate = package_root / package_relative
        if candidate.exists():
            candidates.append(candidate)
    if evidence_dir is not None and evidence_dir.exists():
        direct = evidence_dir / f"{task_label}_{evidence_token}{suffix}"
        if direct.exists():
            candidates.append(direct)
        candidates.extend(sorted(evidence_dir.glob(f"{task_label}*{evidence_token}*{suffix}")))
    unique_candidates = list(dict.fromkeys(candidates))
    if not unique_candidates:
        return None
    return min(unique_candidates, key=lambda path: _artifact_variant_score(path, variant_hints))


def _variant_hints(paths: list[Path | None]) -> tuple[str, ...]:
    hints: list[str] = []
    for path in paths:
        if path is None:
            continue
        name = path.name
        for marker in ARTIFACT_VARIANT_MARKERS:
            if marker in name and marker not in hints:
                hints.append(marker)
    return tuple(hints)


def _artifact_variant_score(path: Path, variant_hints: tuple[str, ...]) -> tuple[int, str]:
    name = path.name
    for index, marker in enumerate(variant_hints):
        if marker in name:
            return (index, name)
    return (len(variant_hints) + 1, name)


def _first_existing_parent(paths: list[Path | None]) -> Path | None:
    for path in paths:
        if path is not None and path.exists():
            return path.parent
    return None


def _resolve_ref(base: Path, raw_ref: object) -> Path | None:
    if not isinstance(raw_ref, str) or not raw_ref.strip():
        return None
    path = Path(raw_ref)
    return path if path.is_absolute() else base / path


def _artifact_ref(path: Path | None, suite_root: Path) -> str | None:
    if path is None:
        return None
    resolved = path.resolve()
    suite_resolved = suite_root.resolve()
    if resolved == suite_resolved or suite_resolved in resolved.parents:
        return str(resolved.relative_to(suite_resolved))
    cwd = Path.cwd().resolve()
    if resolved == cwd or cwd in resolved.parents:
        return str(resolved.relative_to(cwd))
    return str(path)


def _manual_blockers(gate_index: dict[str, Any], readiness_gate: dict[str, Any]) -> list[str]:
    return [
        *_string_items(gate_index.get("manual_blockers")),
        *_status_taxonomy_items(gate_index, "manual_blockers"),
        *_string_items(readiness_gate.get("manual_blockers")),
    ]


def _unknown_blockers(gate_index: dict[str, Any], readiness_gate: dict[str, Any]) -> list[str]:
    return [
        *_string_items(gate_index.get("unknown_blockers")),
        *_status_taxonomy_items(gate_index, "unknown_blockers"),
        *_string_items(readiness_gate.get("unknown_blockers")),
    ]


def _status_taxonomy_items(gate_index: dict[str, Any], key: str) -> list[str]:
    taxonomy = gate_index.get("status_taxonomy")
    if not isinstance(taxonomy, dict):
        return []
    return _string_items(taxonomy.get(key))


def _redistribution_approval(readiness_gate: dict[str, Any]) -> bool:
    policy_summary = readiness_gate.get("policy_gate_summary")
    return isinstance(policy_summary, dict) and policy_summary.get("redistribution_approval") is True


def _public_source_uri(
    raw_source_uri: str,
    *,
    asset_manifest_ref: str | None,
    asset_id: str,
) -> tuple[str, str]:
    if _is_mutable_tmp_uri(raw_source_uri):
        retained_ref = asset_manifest_ref or "unknown_asset_manifest"
        return (
            f"retained-artifact://{retained_ref}#asset_id={asset_id}",
            "mutable_local_source_uri_redacted",
        )
    if _is_local_filesystem_uri(raw_source_uri):
        retained_ref = asset_manifest_ref or "unknown_asset_manifest"
        return (
            f"retained-artifact://{retained_ref}#asset_id={asset_id}",
            "local_filesystem_source_uri_redacted",
        )
    return raw_source_uri, "source_uri_retained"


def _is_mutable_tmp_uri(value: str) -> bool:
    return value.startswith("/tmp/") or value.startswith("file:///tmp/")


def _is_local_filesystem_uri(value: str) -> bool:
    if not value:
        return False
    if value.startswith("file://"):
        return True
    if "://" in value or value.startswith(("omniverse:", "mdl:")):
        return False
    return Path(value).is_absolute()


def _all_blockers(gate_docs: dict[str, dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for phase, doc in gate_docs.items():
        if doc.get("status") != "passed":
            blockers.append(f"Phase {phase} gate status must be passed; got {doc.get('status')}")
        blockers.extend(f"{phase}: {blocker}" for blocker in _string_items(doc.get("blockers")))
    return blockers


def _status_from_blockers(blockers: list[str]) -> str:
    return "passed" if not blockers else "blocked"


def _task_family(task_path: Path | None) -> str:
    task = _load_optional_yaml(task_path)
    value = task.get("task_family") or task.get("family")
    return str(value) if value else "unspecified"


def _manifest_assets(path: Path | None) -> list[dict[str, Any]]:
    data = _load_optional_yaml(path)
    return _list_of_mappings(data.get("assets"))


def _lock_assets(path: Path | None) -> dict[str, dict[str, Any]]:
    data = _load_optional_yaml(path)
    assets = data.get("assets")
    if not isinstance(assets, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for asset_id, raw_asset in assets.items():
        if isinstance(asset_id, str) and isinstance(raw_asset, dict):
            result[asset_id] = raw_asset
    return result


def _gate_status(path: Path | None) -> str:
    return str(_load_optional_yaml(path).get("status", "missing"))


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise Phase12RegistryError(f"Missing YAML artifact: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise Phase12RegistryError(f"YAML artifact must be a mapping: {path}")
    return data


def _load_optional_yaml(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _string_items(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _list_of_mappings(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _compact_mapping(mapping: dict[str, str | None]) -> dict[str, str]:
    return {key: value for key, value in mapping.items() if value is not None}


def _digest_data(data: dict[str, Any]) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _file_digest(path: Path | None) -> str:
    if path is None or not path.exists():
        return _digest_data({"missing": str(path)})
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _digest_suffix(content_sha256: str) -> str:
    digest = content_sha256.removeprefix("sha256:")
    if not digest:
        digest = hashlib.sha256(content_sha256.encode("utf-8")).hexdigest()
    return digest[:12]

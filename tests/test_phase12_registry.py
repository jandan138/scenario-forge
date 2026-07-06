import json
from pathlib import Path
import shutil

import yaml

from scenario_forge.cli import main
from scenario_forge.scaffold import scaffold_starter_package


def test_suite_phase12_generates_registry_snapshot_viewer_handoff_and_policy_closure(
    tmp_path: Path,
) -> None:
    suite_dir, gate_index_path = write_phase12_ready_suite(tmp_path)

    code = main(
        [
            "suite",
            "phase12",
            "--suite",
            str(suite_dir),
            "--gate-index",
            str(gate_index_path),
            "--strict",
        ]
    )

    evidence_dir = suite_dir / "evidence"
    registry_dir = suite_dir / "registry"
    viewer_dir = suite_dir / "viewer"
    handoff_dir = suite_dir / "handoff"
    descriptors_dir = suite_dir / "adapters" / "simulators"

    freeze = load_yaml(evidence_dir / "phase12_0_registry_readiness_freeze.yaml")
    contract_gate = load_yaml(evidence_dir / "phase12_1_registry_contract_gate.yaml")
    package_registry = load_yaml(registry_dir / "package_registry.yaml")
    asset_registry = load_yaml(registry_dir / "asset_registry.yaml")
    registry_snapshot = load_yaml(registry_dir / "registry_snapshot.yaml")
    resolver_snapshot = load_yaml(registry_dir / "resolver_snapshot.yaml")
    snapshot_gate = load_yaml(evidence_dir / "phase12_2_registry_snapshot_gate.yaml")
    viewer_manifest = load_yaml(viewer_dir / "readonly_index.yaml")
    viewer_gate = load_yaml(evidence_dir / "phase12_3_readonly_viewer_gate.yaml")
    handoff = load_yaml(handoff_dir / "ebench_eos_handoff_examples.yaml")
    handoff_gate = load_yaml(evidence_dir / "phase12_4_ebench_eos_handoff_gate.yaml")
    export_descriptors = load_yaml(descriptors_dir / "export_descriptors.yaml")
    export_gate = load_yaml(evidence_dir / "phase12_5_multi_simulator_export_gate.yaml")
    hosted_alpha = load_yaml(registry_dir / "hosted_internal_registry_alpha.yaml")
    policy_gate = load_yaml(evidence_dir / "phase12_6_public_release_policy_closure_gate.yaml")
    current_index = load_yaml(evidence_dir / "phase12_current_gate_index.yaml")

    assert code == 0
    assert freeze["schema_version"] == "phase12-registry-readiness-freeze/v0.1"
    assert freeze["phase"] == "12.0"
    assert freeze["status"] == "passed"
    assert freeze["package_count"] == 3
    assert freeze["manual_blockers"] == []
    assert freeze["unknown_blockers"] == []

    assert package_registry["schema_version"] == "package-registry/v0.1"
    assert len(package_registry["packages"]) == 3
    first_package = package_registry["packages"][0]
    assert first_package["package_id"] == "phase12_pkg_0"
    assert first_package["registry_version"].startswith("v0.2+")
    assert first_package["release_status"] == "passed"
    assert first_package["artifact_refs"]["manifest"] == "packages/phase12_pkg_0/manifest.yaml"
    assert first_package["evidence_refs"]["11.5"].endswith(
        "packages/phase12_pkg_0/evidence/phase11_single_task_release_candidate_gate.yaml"
    )

    assert asset_registry["schema_version"] == "asset-registry/v0.1"
    assert len(asset_registry["assets"]) >= 6
    first_asset = asset_registry["assets"][0]
    assert first_asset["asset_uid"].startswith(first_asset["asset_id"] + "@")
    assert first_asset["license"]
    assert first_asset["content_sha256"]
    assert first_asset["provenance"]["source_package_id"]
    assert first_asset["resolver_version"]
    assert first_asset["material_closure"]["status"] == "passed"
    assert first_asset["physics_readiness"]["status"] == "ready"
    assert first_asset["export_eligibility"]["ebench"] is True
    assert first_asset["role_suitability"]

    assert contract_gate["schema_version"] == "phase12-registry-contract-gate/v0.1"
    assert contract_gate["phase"] == "12.1"
    assert contract_gate["status"] == "passed"
    assert contract_gate["contracts"] == [
        "package-registry-entry/v0.1",
        "asset-registry-entry/v0.1",
        "registry-query-contract/v0.1",
    ]

    digest = (registry_dir / "snapshot_digest.txt").read_text(encoding="utf-8").strip()
    assert digest.startswith("sha256:")
    assert registry_snapshot["schema_version"] == "registry-snapshot/v0.1"
    assert registry_snapshot["snapshot_digest"] == digest
    assert resolver_snapshot["schema_version"] == "resolver-snapshot/v0.1"
    assert snapshot_gate["schema_version"] == "phase12-registry-snapshot-gate/v0.1"
    assert snapshot_gate["phase"] == "12.2"
    assert snapshot_gate["status"] == "passed"

    assert viewer_manifest["schema_version"] == "readonly-evidence-viewer/v0.1"
    assert viewer_manifest["mode"] == "read_only"
    assert viewer_manifest["status_source"] == "retained_gate_files_only"
    assert "override" not in viewer_manifest
    assert (viewer_dir / "index.md").exists()
    assert viewer_gate["phase"] == "12.3"
    assert viewer_gate["status"] == "passed"

    assert handoff["schema_version"] == "ebench-eos-handoff-examples/v0.1"
    assert handoff["pinned_registry_snapshot"] == "registry/registry_snapshot.yaml"
    assert len(handoff["examples"]) == 3
    assert handoff_gate["phase"] == "12.4"
    assert handoff_gate["status"] == "passed"

    assert export_descriptors["schema_version"] == "multi-simulator-export-descriptors/v0.1"
    assert {item["simulator"] for item in export_descriptors["descriptors"]} == {
        "isaacsim",
        "habitat",
        "maniskill",
        "omnigibson",
    }
    assert all(item["core_import_policy"] == "no_simulator_sdk_in_core" for item in export_descriptors["descriptors"])
    assert export_gate["phase"] == "12.5"
    assert export_gate["status"] == "passed"

    assert hosted_alpha["schema_version"] == "hosted-internal-registry-alpha/v0.1"
    assert hosted_alpha["mode"] == "internal_read_only_alpha"
    assert policy_gate["schema_version"] == "phase12-public-release-policy-closure-gate/v0.1"
    assert policy_gate["phase"] == "12.6"
    assert policy_gate["status"] == "passed"
    assert policy_gate["license_policy"] == "pass"
    assert policy_gate["redistribution_approval"] is True
    assert policy_gate["known_blockers"] == []

    assert current_index["schema_version"] == "phase12-current-gate-index/v0.1"
    assert current_index["overall_status"] == "phase13_allowed"
    assert current_index["phase13_allowed"] is True
    assert current_index["latest_gates"]["12.6"]["status"] == "passed"


def test_suite_phase12_strict_blocks_when_phase11_readiness_is_not_allowed(
    tmp_path: Path,
) -> None:
    suite_dir, gate_index_path = write_phase12_ready_suite(tmp_path)
    gate_index = load_yaml(gate_index_path)
    gate_index["phase12_allowed"] = False
    gate_index["overall_status"] = "blocked"
    gate_index["technical_closure_status"] = "blocked"
    write_yaml(gate_index_path, gate_index)

    code = main(
        [
            "suite",
            "phase12",
            "--suite",
            str(suite_dir),
            "--gate-index",
            str(gate_index_path),
            "--strict",
        ]
    )

    freeze = load_yaml(suite_dir / "evidence" / "phase12_0_registry_readiness_freeze.yaml")
    current_index = load_yaml(suite_dir / "evidence" / "phase12_current_gate_index.yaml")
    assert code == 1
    assert freeze["status"] == "blocked"
    assert "phase12_allowed must be true" in freeze["blockers"]
    assert current_index["overall_status"] == "blocked"
    assert current_index["phase13_allowed"] is False


def test_suite_phase12_prefers_retained_evidence_over_external_tmp_package_root(
    tmp_path: Path,
) -> None:
    suite_dir, gate_index_path = write_phase12_ready_suite(tmp_path)
    package_id = "phase12_pkg_1"
    external_package_root = tmp_path / "external_runtime_tmp_package"
    scaffold_starter_package(external_package_root)
    rewrite_package_id(external_package_root, package_id)
    suite_manifest_path = suite_dir / "suite_manifest.yaml"
    suite_manifest = load_yaml(suite_manifest_path)
    suite_manifest["packages"][1]["path"] = str(external_package_root)
    write_yaml(suite_manifest_path, suite_manifest)

    retained_dir = suite_dir / "packages" / package_id / "evidence"
    original_package_root = suite_dir / "packages" / package_id
    shutil.copyfile(
        original_package_root / "manifest.yaml",
        retained_dir / f"{package_id}_package_manifest.yaml",
    )
    shutil.copyfile(
        original_package_root / "assets" / "asset_manifest.yaml",
        retained_dir / f"{package_id}_asset_manifest.yaml",
    )
    retained_asset_manifest_path = retained_dir / f"{package_id}_asset_manifest.yaml"
    retained_asset_manifest = load_yaml(retained_asset_manifest_path)
    retained_asset_manifest["assets"][0]["source_uri"] = "/tmp/mutable-runtime-source/model.usd"
    write_yaml(retained_asset_manifest_path, retained_asset_manifest)
    shutil.copyfile(
        original_package_root / "locks" / "asset_lock.yaml",
        retained_dir / f"{package_id}_asset_lock.yaml",
    )

    code = main(
        [
            "suite",
            "phase12",
            "--suite",
            str(suite_dir),
            "--gate-index",
            str(gate_index_path),
            "--strict",
        ]
    )

    package_registry = load_yaml(suite_dir / "registry" / "package_registry.yaml")
    asset_registry_text = (suite_dir / "registry" / "asset_registry.yaml").read_text(
        encoding="utf-8"
    )
    asset_registry = load_yaml(suite_dir / "registry" / "asset_registry.yaml")
    package = package_registry["packages"][1]
    assert code == 0
    assert package["package_id"] == package_id
    assert package["artifact_refs"]["manifest"] == (
        f"packages/{package_id}/evidence/{package_id}_package_manifest.yaml"
    )
    assert not package["artifact_refs"]["manifest"].startswith("/tmp/")
    assert "/tmp/" not in asset_registry_text
    assert any(
        asset["source_uri"].startswith("retained-artifact://")
        for asset in asset_registry["assets"]
        if asset["source_package_id"] == package_id
    )


def test_suite_phase12_redacts_absolute_local_source_uris_from_public_snapshot(
    tmp_path: Path,
) -> None:
    suite_dir, gate_index_path = write_phase12_ready_suite(tmp_path)
    package_id = "phase12_pkg_1"
    external_package_root = tmp_path / "external_runtime_tmp_package"
    scaffold_starter_package(external_package_root)
    rewrite_package_id(external_package_root, package_id)
    suite_manifest_path = suite_dir / "suite_manifest.yaml"
    suite_manifest = load_yaml(suite_manifest_path)
    suite_manifest["packages"][1]["path"] = str(external_package_root)
    write_yaml(suite_manifest_path, suite_manifest)

    retained_dir = suite_dir / "packages" / package_id / "evidence"
    original_package_root = suite_dir / "packages" / package_id
    shutil.copyfile(
        original_package_root / "manifest.yaml",
        retained_dir / f"{package_id}_package_manifest.yaml",
    )
    shutil.copyfile(
        original_package_root / "assets" / "asset_manifest.yaml",
        retained_dir / f"{package_id}_asset_manifest.yaml",
    )
    shutil.copyfile(
        original_package_root / "locks" / "asset_lock.yaml",
        retained_dir / f"{package_id}_asset_lock.yaml",
    )
    retained_asset_manifest_path = retained_dir / f"{package_id}_asset_manifest.yaml"
    retained_asset_manifest = load_yaml(retained_asset_manifest_path)
    retained_asset_manifest["assets"][0]["source_uri"] = (
        "/cpfs/shared/simulation/zhuzihou/dev/_datasets/EBench-Assets/object.usd"
    )
    write_yaml(retained_asset_manifest_path, retained_asset_manifest)

    code = main(
        [
            "suite",
            "phase12",
            "--suite",
            str(suite_dir),
            "--gate-index",
            str(gate_index_path),
            "--strict",
        ]
    )

    asset_registry_text = (suite_dir / "registry" / "asset_registry.yaml").read_text(
        encoding="utf-8"
    )
    registry_snapshot_text = (suite_dir / "registry" / "registry_snapshot.yaml").read_text(
        encoding="utf-8"
    )
    asset_registry = load_yaml(suite_dir / "registry" / "asset_registry.yaml")
    package_assets = [
        asset for asset in asset_registry["assets"] if asset["source_package_id"] == package_id
    ]
    assert code == 0
    assert "/cpfs/" not in asset_registry_text
    assert "/cpfs/" not in registry_snapshot_text
    assert any(
        asset["source_uri"].startswith("retained-artifact://")
        and asset["source_uri_policy"] == "local_filesystem_source_uri_redacted"
        for asset in package_assets
    )


def test_suite_phase12_classifies_mdl_with_retained_runtime_approval_as_passed(
    tmp_path: Path,
) -> None:
    suite_dir, gate_index_path = write_phase12_ready_suite(tmp_path)
    package_id = "phase12_pkg_0"
    package_root = suite_dir / "packages" / package_id
    source_usd = tmp_path / "source_assets" / "runtime_approved" / "object.usd"
    source_usd.parent.mkdir(parents=True)
    source_usd.write_bytes(b"\x00token\x00gltf/pbr.mdl\r\x00")

    asset_manifest_path = package_root / "assets" / "asset_manifest.yaml"
    asset_manifest = load_yaml(asset_manifest_path)
    asset_manifest["assets"][0]["source_uri"] = str(source_usd)
    write_yaml(asset_manifest_path, asset_manifest)
    write_json(
        package_root / "evidence" / "tabletop_overview_render_metadata.json",
        {
            "render_status": "pass",
            "material_runtime_preflight": {
                "status": "pass",
                "blocked_dependency_count": 0,
                "blocked_dependencies": [],
                "approved_runtime_mdl_dependencies": [
                    {
                        "module": "gltf/pbr.mdl",
                        "resolution": "approved_runtime_module",
                        "runtime_path": "/isaac-sim/kit/mdl/core/mdl/gltf/pbr.mdl",
                    }
                ],
                "mdl_search_paths": [
                    "/isaac-sim/kit/mdl/core/mdl",
                    "/cpfs/shared/simulation/runtime/mdl",
                ],
            },
        },
    )

    code = main(
        [
            "suite",
            "phase12",
            "--suite",
            str(suite_dir),
            "--gate-index",
            str(gate_index_path),
            "--strict",
        ]
    )

    asset_registry = load_yaml(suite_dir / "registry" / "asset_registry.yaml")
    asset_registry_text = (suite_dir / "registry" / "asset_registry.yaml").read_text(
        encoding="utf-8"
    )
    approved_asset = next(
        asset
        for asset in asset_registry["assets"]
        if asset["source_package_id"] == package_id
        and asset["asset_id"] == asset_manifest["assets"][0]["asset_id"]
    )
    assert code == 0
    assert approved_asset["material_closure"]["status"] == "passed"
    assert approved_asset["material_closure"]["missing_material_ref_count"] == 0
    assert approved_asset["material_closure"]["approved_runtime_mdl_dependencies"] == [
        {
            "module": "gltf/pbr.mdl",
            "resolution": "approved_runtime_module",
            "runtime_path": "/isaac-sim/kit/mdl/core/mdl/gltf/pbr.mdl",
        }
    ]
    assert "/tmp/" not in asset_registry_text
    assert "/cpfs/" not in asset_registry_text


def test_suite_phase12_asset_handoff_overlay_registers_clean_s2d12_asset(
    tmp_path: Path,
) -> None:
    suite_dir, gate_index_path = write_phase12_ready_suite(tmp_path)
    add_old_ebench_scene_asset(suite_dir, "phase12_pkg_0")
    handoff_path = write_s2d12_asset_handoff(tmp_path / "s2d12_registry_mapping.yaml")

    code = main(
        [
            "suite",
            "phase12",
            "--suite",
            str(suite_dir),
            "--gate-index",
            str(gate_index_path),
            "--asset-handoff",
            str(handoff_path),
            "--strict",
        ]
    )

    registry_dir = suite_dir / "registry"
    handoff_dir = suite_dir / "handoff"
    asset_registry_text = (registry_dir / "asset_registry.yaml").read_text(encoding="utf-8")
    registry_snapshot_text = (registry_dir / "registry_snapshot.yaml").read_text(encoding="utf-8")
    resolver_snapshot_text = (registry_dir / "resolver_snapshot.yaml").read_text(encoding="utf-8")
    eos_handoff_text = (handoff_dir / "ebench_eos_handoff_examples.yaml").read_text(
        encoding="utf-8"
    )
    asset_registry = load_yaml(registry_dir / "asset_registry.yaml")
    registry_snapshot = load_yaml(registry_dir / "registry_snapshot.yaml")
    resolver_snapshot = load_yaml(registry_dir / "resolver_snapshot.yaml")
    eos_handoff = load_yaml(handoff_dir / "ebench_eos_handoff_examples.yaml")
    current_index = load_yaml(suite_dir / "evidence" / "phase12_current_gate_index.yaml")

    old_uid = "official_ebench_scene@e1cf0d5b4d76"
    clean_uid = "official_ebench_scene@e1cf0d5b4d76_native_phase12_clean"
    asset_uids = {asset["asset_uid"] for asset in asset_registry["assets"]}
    clean_asset = next(asset for asset in asset_registry["assets"] if asset["asset_uid"] == clean_uid)
    resolver_asset = next(asset for asset in resolver_snapshot["assets"] if asset["asset_uid"] == clean_uid)
    asset_handoff = eos_handoff["asset_handoffs"][0]
    retained_asset_manifest_ref = clean_asset["provenance"]["asset_manifest"]
    retained_asset_lock_ref = clean_asset["provenance"]["asset_lock"]
    retained_asset_manifest = load_yaml(suite_dir / retained_asset_manifest_ref)
    retained_asset_lock = load_yaml(suite_dir / retained_asset_lock_ref)

    assert code == 0
    assert old_uid in asset_uids
    assert clean_uid in asset_uids
    assert clean_asset["asset_id"] == "official_ebench_scene"
    assert clean_asset["source_package_id"] == "s2d12_native_mdl_phase12_clean"
    assert clean_asset["role"] == "target_container"
    assert clean_asset["asset_type"] == "usd_bundle"
    assert clean_asset["canonical_usd"] == "asset.usda"
    assert clean_asset["content_sha256"] == (
        "sha256:1fedd44093435591458cf10c303bdf2e856e20b18608307ed7e7dc59b71f0673"
    )
    assert clean_asset["source_kind"] == "external_asset_handoff"
    assert clean_asset["source_uri"] == (
        "retained-handoff://official_ebench_scene@e1cf0d5b4d76_native_phase12_clean"
    )
    assert clean_asset["material_closure"]["status"] == "passed"
    assert clean_asset["material_closure"]["missing_texture_count"] == 0
    assert clean_asset["material_closure"]["missing_textures"] == []
    assert clean_asset["material_closure"]["missing_material_ref_count"] == 0
    assert clean_asset["material_closure"]["missing_material_refs"] == []
    assert clean_asset["material_closure"]["approved_runtime_mdl_dependencies"] == [
        {
            "module": "gltf/pbr.mdl",
            "resolution": "approved_runtime_module",
            "runtime_path": "/isaac-sim/kit/mdl/core/mdl/gltf/pbr.mdl",
        }
    ]
    assert clean_asset["physics_readiness"]["status"] == "ready"
    assert clean_asset["export_eligibility"]["ebench"] is True
    assert retained_asset_manifest_ref.startswith("handoff/asset_handoffs/")
    assert retained_asset_lock_ref.startswith("handoff/asset_handoffs/")
    assert retained_asset_manifest["assets"][0]["asset_id"] == "official_ebench_scene"
    assert retained_asset_manifest["assets"][0]["source_uri"].startswith("/cpfs/")
    assert retained_asset_lock["assets"]["official_ebench_scene"]["source_uri"].startswith("/cpfs/")
    assert clean_asset["provenance"]["asset_handoff"]["source_policy"] == (
        "external_local_path_redacted"
    )
    assert resolver_asset["asset_lock"] == retained_asset_lock_ref
    assert resolver_asset["asset_handoff"]["replacement_asset_uid"] == clean_uid
    assert asset_handoff["selected_asset_ref"] == old_uid
    assert asset_handoff["replacement_asset_uid"] == clean_uid
    assert asset_handoff["source_package_id"] == "s2d12_native_mdl_phase12_clean"
    assert asset_handoff["material_closure_status"] == "passed"
    assert registry_snapshot["snapshot_digest"] == resolver_snapshot["snapshot_digest"]
    assert current_index["overall_status"] == "phase13_allowed"
    assert "/cpfs/" not in asset_registry_text
    assert "/cpfs/" not in registry_snapshot_text
    assert "/cpfs/" not in resolver_snapshot_text
    assert "/cpfs/" not in eos_handoff_text


def test_suite_phase12_strict_blocks_failed_asset_handoff_material_closure(
    tmp_path: Path,
) -> None:
    suite_dir, gate_index_path = write_phase12_ready_suite(tmp_path)
    handoff_path = write_s2d12_asset_handoff(
        tmp_path / "s2d12_failed_registry_mapping.yaml",
        material_status="failed",
    )

    code = main(
        [
            "suite",
            "phase12",
            "--suite",
            str(suite_dir),
            "--gate-index",
            str(gate_index_path),
            "--asset-handoff",
            str(handoff_path),
            "--strict",
        ]
    )

    contract_gate = load_yaml(suite_dir / "evidence" / "phase12_1_registry_contract_gate.yaml")
    current_index = load_yaml(suite_dir / "evidence" / "phase12_current_gate_index.yaml")
    assert code == 1
    assert contract_gate["status"] == "blocked"
    assert any(
        "asset handoff official_ebench_scene@e1cf0d5b4d76_native_phase12_clean "
        "material_closure.status must be passed"
        in blocker
        for blocker in contract_gate["blockers"]
    )
    assert current_index["overall_status"] == "blocked"
    assert current_index["phase13_allowed"] is False


def test_suite_phase12_strict_blocks_asset_handoff_without_runtime_approval(
    tmp_path: Path,
) -> None:
    suite_dir, gate_index_path = write_phase12_ready_suite(tmp_path)
    handoff_path = write_s2d12_asset_handoff(
        tmp_path / "s2d12_missing_runtime_approval.yaml",
        include_runtime_approval=False,
    )

    code = main(
        [
            "suite",
            "phase12",
            "--suite",
            str(suite_dir),
            "--gate-index",
            str(gate_index_path),
            "--asset-handoff",
            str(handoff_path),
            "--strict",
        ]
    )

    contract_gate = load_yaml(suite_dir / "evidence" / "phase12_1_registry_contract_gate.yaml")
    assert code == 1
    assert contract_gate["status"] == "blocked"
    assert any(
        "approved_runtime_mdl_dependencies must include approved runtime modules" in blocker
        for blocker in contract_gate["blockers"]
    )


def test_suite_phase12_strict_blocks_asset_handoff_uid_asset_id_mismatch(
    tmp_path: Path,
) -> None:
    suite_dir, gate_index_path = write_phase12_ready_suite(tmp_path)
    handoff_path = write_s2d12_asset_handoff(
        tmp_path / "s2d12_uid_mismatch.yaml",
        replacement_asset_uid="wrong_scene@e1cf0d5b4d76_native_phase12_clean",
    )

    code = main(
        [
            "suite",
            "phase12",
            "--suite",
            str(suite_dir),
            "--gate-index",
            str(gate_index_path),
            "--asset-handoff",
            str(handoff_path),
            "--strict",
        ]
    )

    contract_gate = load_yaml(suite_dir / "evidence" / "phase12_1_registry_contract_gate.yaml")
    assert code == 1
    assert contract_gate["status"] == "blocked"
    assert any(
        "replacement_asset_uid must start with phase12_registry_asset_id@" in blocker
        for blocker in contract_gate["blockers"]
    )


def test_suite_phase12_prefers_retained_artifact_variant_named_by_current_gate(
    tmp_path: Path,
) -> None:
    suite_dir, gate_index_path = write_phase12_ready_suite(tmp_path)
    package_id = "phase12_pkg_2"
    external_package_root = tmp_path / "external_runtime_tmp_package"
    scaffold_starter_package(external_package_root)
    rewrite_package_id(external_package_root, package_id)

    suite_manifest_path = suite_dir / "suite_manifest.yaml"
    suite_manifest = load_yaml(suite_manifest_path)
    suite_manifest["packages"][2]["path"] = str(external_package_root)
    write_yaml(suite_manifest_path, suite_manifest)

    retained_dir = suite_dir / "packages" / package_id / "evidence"
    original_package_root = suite_dir / "packages" / package_id
    shutil.copyfile(
        original_package_root / "manifest.yaml",
        retained_dir / f"{package_id}_package_manifest.yaml",
    )
    shutil.copyfile(
        original_package_root / "manifest.yaml",
        retained_dir / f"{package_id}_package_manifest_contactfixed.yaml",
    )
    shutil.copyfile(
        original_package_root / "locks" / "asset_lock.yaml",
        retained_dir / f"{package_id}_asset_lock.yaml",
    )
    shutil.copyfile(
        original_package_root / "locks" / "asset_lock.yaml",
        retained_dir / f"{package_id}_asset_lock_contactfixed.yaml",
    )
    shutil.copyfile(
        original_package_root / "scene" / "main.usda",
        retained_dir / f"{package_id}_main.usda",
    )
    shutil.copyfile(
        original_package_root / "scene" / "main.usda",
        retained_dir / f"{package_id}_main_contactfixed.usda",
    )
    contactfixed_gate = retained_dir / f"{package_id}_phase11_visual_review_gate_contactfixed_pass.yaml"
    write_yaml(
        contactfixed_gate,
        {
            "schema_version": "phase11-visual-review-gate/v0.1",
            "phase": "11.0",
            "status": "passed",
            "package_id": package_id,
            "blockers": [],
        },
    )
    gate_index = load_yaml(gate_index_path)
    gate_index["packages"][2]["technical_gates"]["11.0"] = (
        f"packages/{package_id}/evidence/{contactfixed_gate.name}"
    )
    write_yaml(gate_index_path, gate_index)

    code = main(
        [
            "suite",
            "phase12",
            "--suite",
            str(suite_dir),
            "--gate-index",
            str(gate_index_path),
            "--strict",
        ]
    )

    package_registry = load_yaml(suite_dir / "registry" / "package_registry.yaml")
    package = package_registry["packages"][2]
    assert code == 0
    assert package["artifact_refs"]["manifest"].endswith(
        f"{package_id}_package_manifest_contactfixed.yaml"
    )
    assert package["artifact_refs"]["asset_lock"].endswith(
        f"{package_id}_asset_lock_contactfixed.yaml"
    )
    assert package["artifact_refs"]["scene_usd"].endswith(f"{package_id}_main_contactfixed.usda")


def write_phase12_ready_suite(tmp_path: Path) -> tuple[Path, Path]:
    suite_dir = tmp_path / "phase12_suite"
    packages_dir = suite_dir / "packages"
    package_entries: list[dict[str, str]] = []
    gate_index_packages: list[dict] = []

    for index in range(3):
        package_id = f"phase12_pkg_{index}"
        package_root = scaffold_starter_package(packages_dir / package_id)
        rewrite_package_id(package_root, package_id)
        write_phase11_package_gates(package_root, package_id)
        package_entries.append(
            {
                "package_id": package_id,
                "path": f"packages/{package_id}",
                "split": "dev",
                "difficulty": "easy",
                "task_family": "pick_place",
            }
        )
        gate_index_packages.append(
            {
                "package_id": package_id,
                "task_label": package_id,
                "technical_gates": {
                    "11.0": f"packages/{package_id}/evidence/phase11_visual_review_gate.yaml",
                    "11.1": f"packages/{package_id}/evidence/phase11_task_execution_gate.yaml",
                    "11.2": f"packages/{package_id}/evidence/phase11_executed_episode_gate.yaml",
                    "11.3": f"packages/{package_id}/evidence/phase11_success_predicate_gate.yaml",
                    "11.4": f"packages/{package_id}/evidence/phase11_post_execution_visual_review_gate.yaml",
                },
                "release_gate": {
                    "11.5": (
                        f"packages/{package_id}/evidence/"
                        "phase11_single_task_release_candidate_gate.yaml"
                    )
                },
                "current_status": "single_task_rc_passed",
                "current_blocker_class": "none",
            }
        )

    write_yaml(
        suite_dir / "suite_manifest.yaml",
        {
            "schema_version": "scenario-suite/v0.2",
            "suite_id": "phase12_ready_three_task_suite",
            "packages": package_entries,
        },
    )
    write_yaml(
        suite_dir / "evidence" / "phase11_small_multi_task_canary_gate.yaml",
        {
            "schema_version": "phase11-small-multi-task-canary-gate/v0.1",
            "phase": "11.6",
            "status": "passed",
            "suite_id": "phase12_ready_three_task_suite",
            "blockers": [],
        },
    )
    write_yaml(
        suite_dir / "evidence" / "phase11_automated_release_gate.yaml",
        {
            "schema_version": "phase11-automated-release-gate/v0.1",
            "phase": "11.7",
            "status": "passed",
            "release_status": "passed",
            "suite_id": "phase12_ready_three_task_suite",
            "known_blockers": [],
            "blockers": [],
        },
    )
    readiness_gate = {
        "schema_version": "phase11-phase12-readiness-gate/v0.1",
        "phase": "11.8",
        "status": "passed",
        "phase12_status": "allowed",
        "phase12_allowed": True,
        "suite_id": "phase12_ready_three_task_suite",
        "technical_gate_summary": {
            "package_check": "pass",
            "asset_lock_check": "pass",
            "adapter_contract": "pass",
            "overview_visual_review": "pass",
            "eos_execution": "pass",
            "completed_episode": "pass",
            "success_predicate": "pass",
            "post_execution_visual_review": "pass",
            "material_runtime_closure": "pass",
        },
        "policy_gate_summary": {
            "release_policy": "pass",
            "asset_license_status": "redistribution-approved-by-ebench-author",
            "redistribution_approval": True,
        },
        "manual_blockers": [],
        "unknown_blockers": [],
        "known_policy_blockers": [],
        "known_non_policy_blockers": [],
        "blockers": [],
    }
    write_yaml(suite_dir / "evidence" / "phase11_phase12_readiness_gate.yaml", readiness_gate)
    gate_index_path = suite_dir / "phase11_current_gate_index.yaml"
    write_yaml(
        gate_index_path,
        {
            "schema_version": "phase11-current-gate-index/v0.1",
            "indexed_at_utc": "2026-07-05T12:00:00Z",
            "index_owner": "scenario-forge-roadmap-release-owner",
            "suite_id": "phase12_ready_three_task_suite",
            "overall_status": "phase12_allowed",
            "technical_closure_status": "passed",
            "public_release_status": "release_candidate_passed",
            "phase12_allowed": True,
            "status_taxonomy": {"manual_blockers": [], "unknown_blockers": []},
            "authorization_evidence": "evidence/authorization.yaml",
            "packages": gate_index_packages,
            "suite_gates": {
                "11.6": {
                    "path": "evidence/phase11_small_multi_task_canary_gate.yaml",
                    "status": "passed",
                    "blocker_class": "none",
                },
                "11.7": {
                    "path": "evidence/phase11_automated_release_gate.yaml",
                    "status": "passed",
                    "blocker_class": "none",
                },
                "11.8_gate": {
                    "path": "evidence/phase11_phase12_readiness_gate.yaml",
                    "status": "passed",
                    "blocker_class": "none",
                },
            },
            "next_allowed_phase": {"phase": "12.0", "scope": "registry_readiness_freeze"},
        },
    )
    write_yaml(suite_dir / "evidence" / "authorization.yaml", {"status": "passed"})
    return suite_dir, gate_index_path


def rewrite_package_id(package_root: Path, package_id: str) -> None:
    manifest_path = package_root / "manifest.yaml"
    manifest = load_yaml(manifest_path)
    manifest["package_id"] = package_id
    write_yaml(manifest_path, manifest)

    generation_plan_path = package_root / "generation_plan.yaml"
    generation_plan = load_yaml(generation_plan_path)
    generation_plan["package_id"] = package_id
    write_yaml(generation_plan_path, generation_plan)


def write_phase11_package_gates(package_root: Path, package_id: str) -> None:
    gate_specs = [
        ("phase11_visual_review_gate.yaml", "phase11-visual-review-gate/v0.1", "11.0"),
        ("phase11_task_execution_gate.yaml", "phase11-task-execution-gate/v0.1", "11.1"),
        ("phase11_executed_episode_gate.yaml", "phase11-executed-episode-gate/v0.1", "11.2"),
        ("phase11_success_predicate_gate.yaml", "phase11-success-predicate-gate/v0.1", "11.3"),
        (
            "phase11_post_execution_visual_review_gate.yaml",
            "phase11-post-execution-visual-review-gate/v0.1",
            "11.4",
        ),
        (
            "phase11_single_task_release_candidate_gate.yaml",
            "phase11-single-task-release-candidate-gate/v0.1",
            "11.5",
        ),
    ]
    for filename, schema_version, phase in gate_specs:
        write_yaml(
            package_root / "evidence" / filename,
            {
                "schema_version": schema_version,
                "phase": phase,
                "status": "passed",
                "package_id": package_id,
                "task_id": "place_object_on_target",
                "blockers": [],
            },
        )


def add_old_ebench_scene_asset(suite_dir: Path, package_id: str) -> None:
    package_root = suite_dir / "packages" / package_id
    old_sha = "sha256:" + "e1cf0d5b4d76" + ("0" * 52)
    asset_manifest_path = package_root / "assets" / "asset_manifest.yaml"
    asset_manifest = load_yaml(asset_manifest_path)
    asset_manifest["assets"].append(
        {
            "asset_id": "official_ebench_scene",
            "role": "target_container",
            "asset_type": "usd_bundle",
            "canonical_usd": "assets/scenes/official_ebench_scene/asset.usda",
            "license": "ebench_author_redistribution_approved",
            "sha256": old_sha,
            "source_kind": "official_ebench_asset",
            "semantic_tags": ["soap_dish", "environment_fixture"],
        }
    )
    write_yaml(asset_manifest_path, asset_manifest)

    asset_lock_path = package_root / "locks" / "asset_lock.yaml"
    asset_lock = load_yaml(asset_lock_path)
    asset_lock["assets"]["official_ebench_scene"] = {
        "source_kind": "official_ebench_asset",
        "source_uri": "assets/scenes/official_ebench_scene/asset.usda",
        "resolved_path": "assets/scenes/official_ebench_scene/asset.usda",
        "content_sha256": old_sha,
        "license": "ebench_author_redistribution_approved",
        "resolver_version": "scenario-forge/phase11-official-ebench",
        "role": "target_container",
        "asset_type": "usd_bundle",
        "semantic_tags": ["soap_dish", "environment_fixture"],
    }
    write_yaml(asset_lock_path, asset_lock)


def write_s2d12_asset_handoff(
    path: Path,
    *,
    material_status: str = "passed",
    include_runtime_approval: bool = True,
    replacement_asset_uid: str = "official_ebench_scene@e1cf0d5b4d76_native_phase12_clean",
) -> Path:
    write_yaml(
        path,
        {
            "schema_version": "convertasset.s2d12_phase12_clean_registry_mapping.v0.1",
            "created_utc": "2026-07-05",
            "asset": {
                "asset_id": "official_ebench_scene_e1cf0d5b4d76_soap_to_dish",
                "phase12_registry_asset_id": "official_ebench_scene",
                "selected_asset_ref": "official_ebench_scene@e1cf0d5b4d76",
                "replacement_asset_uid": replacement_asset_uid,
                "source_package_id": "s2d12_native_mdl_phase12_clean",
                "role": "target_container",
                "required_prim": "/root/obj__01",
            },
            "package": {
                "root": "/cpfs/user/zhuzihou/assets/convertasset/task3",
                "canonical_usd": "/cpfs/user/zhuzihou/assets/convertasset/task3/asset.usda",
                "canonical_usd_sha256": (
                    "1fedd44093435591458cf10c303bdf2e856e20b18608307ed7e7dc59b71f0673"
                ),
                "canonical_usd_size_bytes": 814317445,
                "official_source_modified": False,
            },
            "phase12_material_closure_mapping": {
                "projection_path": "/cpfs/user/zhuzihou/assets/convertasset/projection.json",
                "material_closure": {
                    "status": material_status,
                    "evidence_source": "local_usd_bundle_mdl_audit_with_runtime_approval",
                    "audit_scope": "local_usd_bundle",
                    "missing_texture_count": 0,
                    "missing_textures": [],
                    "missing_material_ref_count": 0 if material_status == "passed" else 1,
                    "missing_material_refs": []
                    if material_status == "passed"
                    else [
                        {
                            "usd": "asset.usda",
                            "material": "O.mdl",
                            "resolved_path": "O.mdl",
                        }
                    ],
                    "package_local_missing_material_refs": [
                        {
                            "usd": "asset.usda",
                            "material": "gltf/pbr.mdl",
                            "resolved_path": "gltf/pbr.mdl",
                        }
                    ],
                    "approved_runtime_mdl_dependencies": [
                        {
                            "module": "gltf/pbr.mdl",
                            "resolution": "approved_runtime_module",
                            "runtime_path": "/isaac-sim/kit/mdl/core/mdl/gltf/pbr.mdl",
                        }
                    ]
                    if include_runtime_approval
                    else [],
                    "runtime_preflight_evidence": [
                        "/cpfs/user/zhuzihou/assets/convertasset/render_metadata.json"
                    ],
                    "mdl_search_paths": [
                        "/isaac-sim/kit/mdl/core/mdl",
                        "/cpfs/user/zhuzihou/assets/convertasset/task3/SubUSDs/materials",
                    ],
                },
            },
            "runtime_evidence": {
                "status": "pass",
                "root_usd": "/cpfs/user/zhuzihou/assets/convertasset/task3/asset.usda",
            },
            "source_evidence": {
                "runtime_render_metadata": (
                    "/cpfs/user/zhuzihou/assets/convertasset/render_metadata.json"
                )
            },
        },
    )
    return path


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

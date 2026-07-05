from hashlib import sha256
from pathlib import Path

import yaml

from scenario_forge.cli import main
from scenario_forge.generation.image_grounded.factory import _choose_registry_asset


def test_image_task_compile_generates_existing_asset_package_candidate(tmp_path: Path) -> None:
    registry_snapshot = _write_registry_snapshot(
        tmp_path,
        (
            _AssetSeed("official_ebench_apple", "manipulated_object", "apple", ("fruit", "pickable")),
            _AssetSeed("official_ebench_bowl", "target_container", "bowl", ("container", "rigid")),
        ),
    )
    request = _write_image_task_request(tmp_path)
    scene_result = _write_image_scene_result(tmp_path)
    package_dir = tmp_path / "out" / "phase13_tabletop_photo_goal_001"

    code = main(
        [
            "image-task",
            "compile",
            "--request",
            str(request),
            "--scene-result",
            str(scene_result),
            "--registry-snapshot",
            str(registry_snapshot),
            "--out",
            str(package_dir),
            "--strict",
        ]
    )

    assert code == 0
    manifest = _load_yaml(package_dir / "manifest.yaml")
    assert manifest["schema_version"] == "scenario-package/v0.2"
    assert manifest["package_id"] == "phase13_tabletop_photo_goal_001"
    assert manifest["entrypoints"]["task_contract"] == "task/task_contract.yaml"

    scene = (package_dir / "scene/main.usda").read_text(encoding="utf-8")
    assert "official_ebench_apple" in scene
    assert "official_ebench_bowl" in scene
    assert "starter_rigid_object" not in scene
    assert "target_marker" not in scene

    task = _load_yaml(package_dir / "task/task.yaml")
    assert task["task_id"] == "image_task/tabletop_photo_goal_001"
    assert task["instruction"] == "Put the apple into the bowl."
    assert task["bindings"] == {"object": "apple_001", "target_container": "bowl_001"}

    metrics = _load_yaml(package_dir / "metrics/metrics.yaml")
    assert metrics["metrics"][0]["predicate"] == "object_in_container"
    assert metrics["metrics"][0]["object"] == "apple_001"
    assert metrics["metrics"][0]["container"] == "bowl_001"

    contract = _load_yaml(package_dir / "task/task_contract.yaml")
    assert contract["phase_gate"] == "13.4"
    assert contract["success_predicate"]["claim_boundary"] == (
        "simulator-state predicate binding only; image confidence and visual review are not task success"
    )
    assert contract["adapter_contract"]["scenario_forge_excludes"] == [
        "episode_runner",
        "model_adapter",
        "leaderboard_reporting",
        "simulator_runtime_execution",
        "convertasset_usd_mdl_mesh_conversion",
        "image_understanding_model_calls",
    ]

    asset_manifest = _load_yaml(package_dir / "assets/asset_manifest.yaml")
    assert {asset["asset_id"] for asset in asset_manifest["assets"]} == {
        "official_ebench_apple",
        "official_ebench_bowl",
    }
    assert all(asset["source_kind"] == "phase12_registry_asset" for asset in asset_manifest["assets"])

    adapter = _load_yaml(package_dir / "adapters/ebench/package.yaml")
    assert adapter["source_package"]["package_id"] == "phase13_tabletop_photo_goal_001"
    assert adapter["entrypoints"]["scene_usd"] == "../../scene/main.usda"

    validation_report = _load_yaml(package_dir / "evidence/validation_report.yaml")
    assert validation_report["overall_level"] == "adapter_static_validated"
    assert {check["status"] for check in validation_report["checks"]} == {"passed"}
    assert validation_report["messages"] == []

    current_gate = _load_yaml(package_dir / "evidence/phase13_current_gate_index.yaml")
    assert current_gate["schema_version"] == "phase13-current-gate-index/v0.1"
    assert current_gate["overall_status"] == "phase13_static_candidate_ready"
    assert current_gate["formal_package_ready"] is False
    assert current_gate["next_required_gate"] == "13.6"
    assert current_gate["latest_gates"]["13.5"]["status"] == "passed"
    assert current_gate["latest_gates"]["13.6"]["status"] == "blocked"
    assert current_gate["latest_gates"]["13.8"]["status"] == "blocked"


def test_image_task_compile_preserves_target_container_semantic_label(tmp_path: Path) -> None:
    registry_snapshot = _write_registry_snapshot(
        tmp_path,
        (
            _AssetSeed("official_ebench_remote_control", "manipulated_object", "remote", ("pickable", "rigid")),
            _AssetSeed("official_ebench_scene", "target_container", "scene", ("container", "rigid")),
        ),
    )
    request = _write_image_task_request(
        tmp_path,
        request_id="tabletop_photo_goal_remote_to_holder",
        goal_text="Put the remote control into the remote control holder.",
    )
    scene_result = _write_image_scene_result(
        tmp_path,
        result_id="tabletop_photo_goal_remote_to_holder_result",
        goal_text="Put the remote control into the remote control holder.",
        object_asset_id="official_ebench_remote_control",
        object_instance_id="remote_001",
        object_detection_label="remote control",
        container_asset_id="official_ebench_scene",
        container_instance_id="remote_holder_fixture",
        container_detection_label="remote control holder",
        container_semantic_label="remote_control_holder",
        container_fixture_kind="environment_fixture",
        container_source_uid="_00",
    )
    package_dir = tmp_path / "out" / "phase13_tabletop_photo_goal_remote_to_holder"

    code = main(
        [
            "image-task",
            "compile",
            "--request",
            str(request),
            "--scene-result",
            str(scene_result),
            "--registry-snapshot",
            str(registry_snapshot),
            "--out",
            str(package_dir),
            "--strict",
        ]
    )

    assert code == 0
    contract = _load_yaml(package_dir / "task/task_contract.yaml")
    target_container = contract["task_semantics"]["target_container"]
    assert target_container["instance_id"] == "remote_holder_fixture"
    assert target_container["asset_id"] == "official_ebench_scene"
    assert target_container["semantic_label"] == "remote_control_holder"
    assert target_container["fixture_kind"] == "environment_fixture"
    assert target_container["source_uid"] == "_00"


def test_registry_asset_selection_prefers_release_ready_duplicate_entries() -> None:
    blocked_scene = {
        "asset_id": "official_ebench_scene",
        "source_package_id": "aaa_blocked_scene",
        "asset_uid": "official_ebench_scene@blocked",
        "material_closure": {"status": "failed"},
        "physics_readiness": {"status": "ready"},
        "export_eligibility": {"ebench": True},
    }
    release_ready_scene = {
        "asset_id": "official_ebench_scene",
        "source_package_id": "zzz_release_ready_scene",
        "asset_uid": "official_ebench_scene@ready",
        "material_closure": {"status": "passed"},
        "physics_readiness": {"status": "ready"},
        "export_eligibility": {"ebench": True},
    }

    chosen = _choose_registry_asset(
        "official_ebench_scene",
        {"official_ebench_scene": [blocked_scene, release_ready_scene]},
    )

    assert chosen["source_package_id"] == "zzz_release_ready_scene"


def test_registry_asset_selection_honors_selected_asset_uid_for_duplicate_ids() -> None:
    remote_scene = {
        "asset_id": "official_ebench_scene",
        "source_package_id": "ebench_remote_to_holder_canary",
        "asset_uid": "official_ebench_scene@remote",
        "material_closure": {"status": "passed"},
        "physics_readiness": {"status": "ready"},
        "export_eligibility": {"ebench": True},
    }
    soap_scene = {
        "asset_id": "official_ebench_scene",
        "source_package_id": "ebench_soap_to_dish_canary",
        "asset_uid": "official_ebench_scene@soap",
        "material_closure": {"status": "passed"},
        "physics_readiness": {"status": "ready"},
        "export_eligibility": {"ebench": True},
    }

    chosen = _choose_registry_asset(
        "official_ebench_scene",
        {"official_ebench_scene": [remote_scene, soap_scene]},
        selected_asset_uid="official_ebench_scene@remote",
    )

    assert chosen["source_package_id"] == "ebench_remote_to_holder_canary"


def test_image_task_compile_strict_fails_closed_for_unregistered_asset(tmp_path: Path) -> None:
    registry_snapshot = _write_registry_snapshot(
        tmp_path,
        (_AssetSeed("official_ebench_bowl", "target_container", "bowl", ("container", "rigid")),),
    )
    request = _write_image_task_request(tmp_path)
    scene_result = _write_image_scene_result(tmp_path)
    package_dir = tmp_path / "out" / "blocked"

    code = main(
        [
            "image-task",
            "compile",
            "--request",
            str(request),
            "--scene-result",
            str(scene_result),
            "--registry-snapshot",
            str(registry_snapshot),
            "--out",
            str(package_dir),
            "--strict",
        ]
    )

    assert code == 1
    assert not (package_dir / "manifest.yaml").exists()
    current_gate = _load_yaml(package_dir / "evidence/phase13_current_gate_index.yaml")
    assert current_gate["overall_status"] == "blocked"
    assert current_gate["formal_package_ready"] is False
    assert (
        "selected asset official_ebench_apple is not present in the Phase 12 registry snapshot"
        in current_gate["blockers"]
    )
    assert (
        package_dir / "handoff" / "asset_intake_blockers.yaml"
    ).exists(), "blocked requests should retain an asset-intake handoff instead of a fake package"


def test_image_task_compile_strict_fails_closed_for_missing_mdl_dependency(tmp_path: Path) -> None:
    registry_snapshot = _write_registry_snapshot(
        tmp_path,
        (
            _AssetSeed(
                "official_ebench_apple",
                "manipulated_object",
                "apple",
                ("fruit", "pickable"),
                usd_asset_refs=("gltf/pbr.mdl",),
            ),
            _AssetSeed("official_ebench_bowl", "target_container", "bowl", ("container", "rigid")),
        ),
    )
    request = _write_image_task_request(tmp_path)
    scene_result = _write_image_scene_result(tmp_path)
    package_dir = tmp_path / "out" / "blocked_material"

    code = main(
        [
            "image-task",
            "compile",
            "--request",
            str(request),
            "--scene-result",
            str(scene_result),
            "--registry-snapshot",
            str(registry_snapshot),
            "--out",
            str(package_dir),
            "--strict",
        ]
    )

    assert code == 1
    assert not (package_dir / "manifest.yaml").exists()
    current_gate = _load_yaml(package_dir / "evidence/phase13_current_gate_index.yaml")
    assert current_gate["overall_status"] == "blocked"
    assert any(
        blocker.startswith("selected asset official_ebench_apple material/texture closure failed")
        and "gltf/pbr.mdl" in blocker
        for blocker in current_gate["blockers"]
    )
    blockers = _load_yaml(package_dir / "handoff/asset_intake_blockers.yaml")
    assert blockers["recommended_next_step"] == "fix_upstream_result_or_asset_registry_then_rerun_phase13"


def test_image_task_compile_strict_reports_registry_material_dependency_blocker(
    tmp_path: Path,
) -> None:
    registry_snapshot = _write_registry_snapshot(
        tmp_path,
        (
            _AssetSeed(
                "official_ebench_apple",
                "manipulated_object",
                "apple",
                ("fruit", "pickable"),
                material_closure={
                    "status": "failed",
                    "missing_texture_count": 0,
                    "missing_textures": [],
                    "missing_material_ref_count": 1,
                    "missing_material_refs": [{"material": "gltf/pbr.mdl"}],
                },
            ),
            _AssetSeed("official_ebench_bowl", "target_container", "bowl", ("container", "rigid")),
        ),
    )
    request = _write_image_task_request(tmp_path)
    scene_result = _write_image_scene_result(tmp_path)
    package_dir = tmp_path / "out" / "registry_material_blocked"

    code = main(
        [
            "image-task",
            "compile",
            "--request",
            str(request),
            "--scene-result",
            str(scene_result),
            "--registry-snapshot",
            str(registry_snapshot),
            "--out",
            str(package_dir),
            "--strict",
        ]
    )

    assert code == 1
    current_gate = _load_yaml(package_dir / "evidence/phase13_current_gate_index.yaml")
    assert any("gltf/pbr.mdl" in blocker for blocker in current_gate["blockers"])


def test_image_task_compile_allows_registry_approved_runtime_mdl_dependency(
    tmp_path: Path,
) -> None:
    registry_snapshot = _write_registry_snapshot(
        tmp_path,
        (
            _AssetSeed(
                "official_ebench_apple",
                "manipulated_object",
                "apple",
                ("fruit", "pickable"),
                usd_asset_refs=("gltf/pbr.mdl",),
                material_closure={
                    "status": "passed",
                    "missing_texture_count": 0,
                    "missing_textures": [],
                    "missing_material_ref_count": 0,
                    "missing_material_refs": [],
                    "package_local_missing_material_refs": [{"material": "gltf/pbr.mdl"}],
                    "approved_runtime_mdl_dependencies": [
                        {
                            "module": "gltf/pbr.mdl",
                            "resolution": "approved_runtime_module",
                            "runtime_path": "/isaac-sim/kit/mdl/core/mdl/gltf/pbr.mdl",
                        }
                    ],
                },
            ),
            _AssetSeed("official_ebench_bowl", "target_container", "bowl", ("container", "rigid")),
        ),
    )
    request = _write_image_task_request(tmp_path)
    scene_result = _write_image_scene_result(tmp_path)
    package_dir = tmp_path / "out" / "runtime_approved"

    code = main(
        [
            "image-task",
            "compile",
            "--request",
            str(request),
            "--scene-result",
            str(scene_result),
            "--registry-snapshot",
            str(registry_snapshot),
            "--out",
            str(package_dir),
            "--strict",
        ]
    )

    assert code == 0
    current_gate = _load_yaml(package_dir / "evidence/phase13_current_gate_index.yaml")
    assert current_gate["overall_status"] == "phase13_static_candidate_ready"
    material_gate = _load_yaml(package_dir / "evidence/phase13_5_scene_layout_usd_materialization_gate.yaml")
    apple_material = material_gate["material_closure"]["selected_assets"][0]
    assert apple_material["asset_id"] == "official_ebench_apple"
    assert apple_material["status"] == "passed"
    assert apple_material["approved_runtime_mdl_dependencies"][0]["module"] == "gltf/pbr.mdl"


def test_image_task_overview_visual_gate_promotes_candidate_after_visual_review_pass(
    tmp_path: Path,
) -> None:
    registry_snapshot = _write_registry_snapshot(
        tmp_path,
        (
            _AssetSeed("official_ebench_apple", "manipulated_object", "apple", ("fruit", "pickable")),
            _AssetSeed("official_ebench_bowl", "target_container", "bowl", ("container", "rigid")),
        ),
    )
    request = _write_image_task_request(tmp_path)
    scene_result = _write_image_scene_result(tmp_path)
    package_dir = tmp_path / "out" / "phase13_visual"
    compile_code = main(
        [
            "image-task",
            "compile",
            "--request",
            str(request),
            "--scene-result",
            str(scene_result),
            "--registry-snapshot",
            str(registry_snapshot),
            "--out",
            str(package_dir),
            "--strict",
        ]
    )
    review_path = _write_phase13_visual_review(package_dir)

    visual_code = main(
        [
            "image-task",
            "overview-visual",
            "--package",
            str(package_dir),
            "--visual-review",
            str(review_path),
            "--strict",
        ]
    )

    assert compile_code == 0
    assert visual_code == 0
    visual_gate = _load_yaml(package_dir / "evidence/phase13_6_factory_overview_visual_gate.yaml")
    assert visual_gate["status"] == "passed"
    assert visual_gate["visual_review"]["reviewer"] == "render-visual-reviewer"
    current_gate = _load_yaml(package_dir / "evidence/phase13_current_gate_index.yaml")
    assert current_gate["overall_status"] == "phase13_visual_candidate_ready"
    assert current_gate["next_required_gate"] == "13.8"
    assert current_gate["latest_gates"]["13.6"]["status"] == "passed"
    assert current_gate["formal_package_ready"] is False
    assert current_gate["blockers"] == [
        "13.8 EOS execution/predicate canary gate is required before formal package readiness"
    ]


def test_image_task_overview_visual_gate_requires_render_metadata(tmp_path: Path) -> None:
    registry_snapshot = _write_registry_snapshot(
        tmp_path,
        (
            _AssetSeed("official_ebench_apple", "manipulated_object", "apple", ("fruit", "pickable")),
            _AssetSeed("official_ebench_bowl", "target_container", "bowl", ("container", "rigid")),
        ),
    )
    request = _write_image_task_request(tmp_path)
    scene_result = _write_image_scene_result(tmp_path)
    package_dir = tmp_path / "out" / "phase13_visual_missing_metadata"
    assert (
        main(
            [
                "image-task",
                "compile",
                "--request",
                str(request),
                "--scene-result",
                str(scene_result),
                "--registry-snapshot",
                str(registry_snapshot),
                "--out",
                str(package_dir),
                "--strict",
            ]
        )
        == 0
    )
    review_path = _write_phase13_visual_review(package_dir, include_render_metadata=False)

    visual_code = main(
        [
            "image-task",
            "overview-visual",
            "--package",
            str(package_dir),
            "--visual-review",
            str(review_path),
            "--strict",
        ]
    )

    assert visual_code == 1
    visual_gate = _load_yaml(package_dir / "evidence/phase13_6_factory_overview_visual_gate.yaml")
    assert visual_gate["status"] == "failed"
    assert "phase13 visual review render_metadata_path is required for 13.6" in visual_gate["blockers"]
    current_gate = _load_yaml(package_dir / "evidence/phase13_current_gate_index.yaml")
    assert current_gate["overall_status"] == "blocked"
    assert current_gate["formal_package_ready"] is False
    assert current_gate["overview_visual_ready"] is False
    assert current_gate["next_required_gate"] == "13.6"


def test_image_task_execution_predicate_gate_promotes_visual_candidate_to_formal_package(
    tmp_path: Path,
) -> None:
    registry_snapshot = _write_registry_snapshot(
        tmp_path,
        (
            _AssetSeed("official_ebench_apple", "manipulated_object", "apple", ("fruit", "pickable")),
            _AssetSeed("official_ebench_bowl", "target_container", "bowl", ("container", "rigid")),
        ),
    )
    request = _write_image_task_request(tmp_path)
    scene_result = _write_image_scene_result(tmp_path)
    package_dir = tmp_path / "out" / "phase13_execution"
    assert (
        main(
            [
                "image-task",
                "compile",
                "--request",
                str(request),
                "--scene-result",
                str(scene_result),
                "--registry-snapshot",
                str(registry_snapshot),
                "--out",
                str(package_dir),
                "--strict",
            ]
        )
        == 0
    )
    review_path = _write_phase13_visual_review(package_dir)
    assert (
        main(
            [
                "image-task",
                "overview-visual",
                "--package",
                str(package_dir),
                "--visual-review",
                str(review_path),
                "--strict",
            ]
        )
        == 0
    )
    rc_gate_path = _write_phase13_passed_phase11_execution_chain(package_dir)

    execution_code = main(
        [
            "image-task",
            "execution-predicate",
            "--package",
            str(package_dir),
            "--single-task-rc-gate",
            str(rc_gate_path),
            "--strict",
        ]
    )

    assert execution_code == 0
    execution_gate = _load_yaml(package_dir / "evidence/phase13_8_execution_predicate_canary_gate.yaml")
    assert execution_gate["status"] == "passed"
    assert execution_gate["phase11_chain"]["phase11_single_task_release_candidate_gate"]["status"] == "passed"
    assert execution_gate["next_stage"] == "batch_factory_quality_gate"
    current_gate = _load_yaml(package_dir / "evidence/phase13_current_gate_index.yaml")
    assert current_gate["overall_status"] == "phase13_formal_package_ready"
    assert current_gate["formal_package_ready"] is True
    assert current_gate["execution_predicate_ready"] is True
    assert current_gate["next_required_gate"] == "13.9"
    assert current_gate["latest_gates"]["13.8"]["status"] == "passed"
    assert current_gate["blockers"] == [
        "13.9 batch factory quality gate is required before batch factory readiness"
    ]


def test_image_task_blocked_rerun_removes_previous_public_ready_manifest(tmp_path: Path) -> None:
    request = _write_image_task_request(tmp_path)
    scene_result = _write_image_scene_result(tmp_path)
    package_dir = tmp_path / "out" / "rerun"
    passing_registry = _write_registry_snapshot(
        tmp_path,
        (
            _AssetSeed("official_ebench_apple", "manipulated_object", "apple", ("fruit", "pickable")),
            _AssetSeed("official_ebench_bowl", "target_container", "bowl", ("container", "rigid")),
        ),
    )
    blocked_registry = _write_registry_snapshot(
        tmp_path / "blocked_case",
        (_AssetSeed("official_ebench_bowl", "target_container", "bowl", ("container", "rigid")),),
    )

    passing_code = main(
        [
            "image-task",
            "compile",
            "--request",
            str(request),
            "--scene-result",
            str(scene_result),
            "--registry-snapshot",
            str(passing_registry),
            "--out",
            str(package_dir),
            "--strict",
        ]
    )
    blocked_code = main(
        [
            "image-task",
            "compile",
            "--request",
            str(request),
            "--scene-result",
            str(scene_result),
            "--registry-snapshot",
            str(blocked_registry),
            "--out",
            str(package_dir),
            "--strict",
        ]
    )

    assert passing_code == 0
    assert blocked_code == 1
    assert not (package_dir / "manifest.yaml").exists()
    current_gate = _load_yaml(package_dir / "evidence/phase13_current_gate_index.yaml")
    assert current_gate["overall_status"] == "blocked"


class _AssetSeed:
    def __init__(
        self,
        asset_id: str,
        role: str,
        asset_type: str,
        semantic_tags: tuple[str, ...],
        usd_asset_refs: tuple[str, ...] = (),
        material_closure: dict | None = None,
    ) -> None:
        self.asset_id = asset_id
        self.role = role
        self.asset_type = asset_type
        self.semantic_tags = semantic_tags
        self.usd_asset_refs = usd_asset_refs
        self.material_closure = material_closure


def _write_registry_snapshot(tmp_path: Path, seeds: tuple[_AssetSeed, ...]) -> Path:
    suite_root = tmp_path / "phase12_suite"
    registry_dir = suite_root / "registry"
    evidence_dir = suite_root / "evidence"
    registry_dir.mkdir(parents=True)
    evidence_dir.mkdir()

    retained_assets = []
    lock_assets = {}
    registry_assets = []
    for seed in seeds:
        source_usd = _write_source_usd(tmp_path / "source_assets" / seed.asset_id, seed.usd_asset_refs)
        digest = f"sha256:{sha256(source_usd.read_bytes()).hexdigest()}"
        canonical_usd = f"assets/{seed.asset_id}/{source_usd.name}"
        retained_assets.append(
            {
                "asset_id": seed.asset_id,
                "role": seed.role,
                "asset_type": seed.asset_type,
                "canonical_usd": canonical_usd,
                "license": "research-use",
                "sha256": digest,
                "source_kind": "official_ebench_asset",
                "source_uri": str(source_usd),
                "resolver_version": "scenario-forge-ebench-official-asset-intake/v0.1",
            }
        )
        lock_assets[seed.asset_id] = {
            "source_kind": "official_ebench_asset",
            "source_uri": str(source_usd),
            "resolved_path": canonical_usd,
            "content_sha256": digest,
            "license": "research-use",
            "resolver_version": "scenario-forge-ebench-official-asset-intake/v0.1",
        }
        registry_assets.append(
            {
                "schema_version": "asset-registry-entry/v0.1",
                "asset_uid": f"{seed.asset_id}@{digest[7:19]}",
                "asset_id": seed.asset_id,
                "source_package_id": "phase13_seed_assets",
                "role": seed.role,
                "asset_type": seed.asset_type,
                "canonical_usd": canonical_usd,
                "content_sha256": digest,
                "license": "research-use",
                "source_kind": "official_ebench_asset",
                "source_uri": (
                    f"retained-artifact://evidence/retained_asset_manifest.yaml#asset_id={seed.asset_id}"
                ),
                "source_uri_policy": "local_filesystem_source_uri_redacted",
                "resolver_version": "scenario-forge-ebench-official-asset-intake/v0.1",
                "semantic_tags": list(seed.semantic_tags),
                "affordances": list(seed.semantic_tags),
                "material_closure": seed.material_closure or {"status": "passed"},
                "physics_readiness": {"status": "ready"},
                "export_eligibility": {"ebench": True},
                "provenance": {
                    "source_package_id": "phase13_seed_assets",
                    "asset_manifest": "evidence/retained_asset_manifest.yaml",
                    "asset_lock": "evidence/retained_asset_lock.yaml",
                },
                "claim_boundary": "test registry asset only",
            }
        )

    _write_yaml(
        evidence_dir / "retained_asset_manifest.yaml",
        {"schema_version": "asset-manifest/v0.2", "assets": retained_assets},
    )
    _write_yaml(
        evidence_dir / "retained_asset_lock.yaml",
        {
            "schema_version": "asset-lock/v0.2",
            "lock_id": "phase13_seed_assets_asset_lock",
            "created_by": "scenario-forge",
            "assets": lock_assets,
        },
    )
    snapshot = {
        "schema_version": "registry-snapshot/v0.1",
        "suite_id": "phase13_seed_suite",
        "snapshot_digest": "sha256:" + "0" * 64,
        "package_registry": {"schema_version": "package-registry/v0.1", "packages": []},
        "asset_registry": {
            "schema_version": "asset-registry/v0.1",
            "entry_schema": "asset-registry-entry/v0.1",
            "assets": registry_assets,
        },
        "registry_query_contract": {
            "schema_version": "registry-query-contract/v0.1",
            "supported_queries": [],
        },
    }
    return _write_yaml(registry_dir / "registry_snapshot.yaml", snapshot)


def _write_image_task_request(
    tmp_path: Path,
    *,
    request_id: str = "tabletop_photo_goal_001",
    goal_text: str = "Put the apple into the bowl.",
) -> Path:
    image_path = tmp_path / "inputs" / "tabletop_001.jpg"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"fake-jpg")
    return _write_yaml(
        tmp_path / "image_task_request.yaml",
        {
            "schema_version": "image-task-request/v0.1",
            "request_id": request_id,
            "source": {
                "image_uri": f"file://{image_path}",
                "image_sha256": f"sha256:{sha256(image_path.read_bytes()).hexdigest()}",
                "rights_status": "user_provided_for_task_generation",
            },
            "goal": {
                "one_sentence_goal": goal_text,
                "domain": "tabletop_manipulation",
                "robot_profile": "franka_panda_tabletop_v1",
                "target_export": "ebench",
            },
            "constraints": {
                "package_mode": "fat",
                "asset_source": "phase12_registry_snapshot",
                "allow_new_asset_reconstruction": False,
            },
        },
    )


def _write_image_scene_result(
    tmp_path: Path,
    *,
    result_id: str = "tabletop_photo_goal_001_result",
    goal_text: str = "Put the apple into the bowl.",
    object_asset_id: str = "official_ebench_apple",
    object_instance_id: str = "apple_001",
    object_detection_label: str = "apple",
    container_asset_id: str = "official_ebench_bowl",
    container_instance_id: str = "bowl_001",
    container_detection_label: str = "bowl",
    container_semantic_label: str | None = None,
    container_fixture_kind: str | None = None,
    container_source_uid: str | None = None,
) -> Path:
    image_path = tmp_path / "inputs" / "tabletop_001.jpg"
    container_instance = {
        "id": container_instance_id,
        "role": "target_container",
        "asset_id": container_asset_id,
        "pose": {"xyz": [0.33, 0.04, 0.78], "wxyz": [1.0, 0.0, 0.0, 0.0]},
    }
    if container_semantic_label is not None:
        container_instance["semantic_label"] = container_semantic_label
    if container_fixture_kind is not None:
        container_instance["fixture_kind"] = container_fixture_kind
    if container_source_uid is not None:
        container_instance["source_uid"] = container_source_uid
    return _write_yaml(
        tmp_path / "image_scene_result.yaml",
        {
            "schema_version": "image-to-scene-result/v0.1",
            "result_id": result_id,
            "producer": {"name": "external-image-grounding-adapter", "version": "v0.1"},
            "source": {
                "image_uri": f"file://{image_path}",
                "image_sha256": f"sha256:{sha256(image_path.read_bytes()).hexdigest()}",
            },
            "goal": {
                "raw_text": goal_text,
                "normalized_task_family": "object_in_container",
            },
            "scene": {"coordinate_system": "tabletop_right_handed_z_up", "units": "meters"},
            "detections": [
                {
                    "detection_id": "det_apple",
                    "label": object_detection_label,
                    "bbox_xywh": [120, 200, 80, 75],
                    "confidence": 0.91,
                    "semantic_tags": ["fruit", "pickable"],
                    "affordance_guesses": ["pickable"],
                },
                {
                    "detection_id": "det_bowl",
                    "label": container_detection_label,
                    "bbox_xywh": [250, 205, 110, 85],
                    "confidence": 0.88,
                    "semantic_tags": ["container"],
                    "affordance_guesses": ["container"],
                },
            ],
            "asset_requirements": [
                {
                    "role": "object",
                    "detection_id": "det_apple",
                    "asset_type": object_detection_label,
                    "required_affordances": ["pickable", "rigid"],
                },
                {
                    "role": "target_container",
                    "detection_id": "det_bowl",
                    "asset_type": container_detection_label,
                    "required_affordances": ["container", "rigid"],
                },
            ],
            "asset_candidates": [
                {
                    "role": "object",
                    "detection_id": "det_apple",
                    "selected_asset_id": object_asset_id,
                    "score": 0.84,
                    "matching_reason": "category_and_size_match",
                    "rejected_alternatives": [],
                },
                {
                    "role": "target_container",
                    "detection_id": "det_bowl",
                    "selected_asset_id": container_asset_id,
                    "score": 0.86,
                    "matching_reason": "category_and_affordance_match",
                    "rejected_alternatives": [],
                },
            ],
            "instances": [
                {
                    "id": object_instance_id,
                    "role": "manipulated_object",
                    "asset_id": object_asset_id,
                    "pose": {"xyz": [0.12, 0.04, 0.78], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                },
                container_instance,
            ],
            "task_bindings": {"object": object_instance_id, "container": container_instance_id},
            "evidence": {"confidence_summary": "usable_with_review", "blockers": []},
        },
    )


def _write_source_usd(root: Path, usd_asset_refs: tuple[str, ...] = ()) -> Path:
    root.mkdir(parents=True)
    usd = root / "model.usd"
    asset_ref_lines = [
        f'        custom asset scenarioForgeMaterialDependency{index} = @{asset_ref}@'
        for index, asset_ref in enumerate(usd_asset_refs)
    ]
    usd.write_text(
        "\n".join(
            [
                "#usda 1.0",
                "(",
                '    defaultPrim = "World"',
                ")",
                'def Xform "World"',
                "{",
                *asset_ref_lines,
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return usd


def _write_phase13_visual_review(package_dir: Path, *, include_render_metadata: bool = True) -> Path:
    evidence_dir = package_dir / "evidence"
    image_path = evidence_dir / "phase13_overview.png"
    runtime_log_path = evidence_dir / "phase13_overview_runtime.log"
    metadata_path = evidence_dir / "phase13_overview_render_metadata.json"
    review_path = evidence_dir / "phase13_overview_visual_review.yaml"
    image_path.write_bytes(b"fake-render-png")
    runtime_log_path.write_text("render completed without blocking material signals\n", encoding="utf-8")
    if include_render_metadata:
        metadata_path.write_text(
            "\n".join(
                [
                    "{",
                    '  "render_status": "pass",',
                    '  "runtime_log_path": "phase13_overview_runtime.log",',
                    '  "material_runtime_preflight": {',
                    '    "status": "pass",',
                    '    "blocked_dependency_count": 0,',
                    '    "blocked_dependencies": []',
                    "  }",
                    "}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    review = {
        "schema_version": "phase11-visual-review/v0.1",
        "reviewer": "render-visual-reviewer",
        "review_mode": "clean_room_visual_skill",
        "verdict": "PASS",
        "image_path": "phase13_overview.png",
        "visible_evidence": [
            {"target": "tabletop", "status": "visible"},
            {"target": "apple", "status": "visible"},
            {"target": "bowl", "status": "visible"},
        ],
        "retake_recommendation": "none",
    }
    if include_render_metadata:
        review["render_metadata_path"] = "phase13_overview_render_metadata.json"
    return _write_yaml(review_path, review)


def _write_phase13_passed_phase11_execution_chain(package_dir: Path) -> Path:
    evidence_dir = package_dir / "evidence"
    manifest = _load_yaml(package_dir / "manifest.yaml")
    task = _load_yaml(package_dir / "task" / "task.yaml")
    package_id = manifest["package_id"]
    task_id = task["task_id"]
    gate_specs = (
        ("phase11_task_execution_gate.yaml", "phase11-task-execution-gate/v0.1", "11.1"),
        ("phase11_executed_episode_gate.yaml", "phase11-executed-episode-gate/v0.1", "11.2"),
        ("phase11_success_predicate_gate.yaml", "phase11-success-predicate-gate/v0.1", "11.3"),
        (
            "phase11_post_execution_visual_review_gate.yaml",
            "phase11-post-execution-visual-review-gate/v0.1",
            "11.4",
        ),
    )
    required_gates: dict[str, dict[str, str]] = {}
    for filename, schema_version, phase in gate_specs:
        _write_yaml(
            evidence_dir / filename,
            {
                "schema_version": schema_version,
                "phase": phase,
                "status": "passed",
                "package_id": package_id,
                "task_id": task_id,
                "blockers": [],
            },
        )
        required_gates[filename] = {
            "path": str(evidence_dir / filename),
            "schema_version": schema_version,
            "status": "passed",
        }
    return _write_yaml(
        evidence_dir / "phase11_single_task_release_candidate_gate.yaml",
        {
            "schema_version": "phase11-single-task-release-candidate-gate/v0.1",
            "phase": "11.5",
            "status": "passed",
            "package_id": package_id,
            "task_id": task_id,
            "required_gates": required_gates,
            "release_policy": {
                "schema_version": "phase11-release-policy/v0.1",
                "policy_owner": "scenario-forge-policy-gate",
                "release_policy_status": "pass",
                "asset_license_status": "pass",
                "redistribution_approval": "pass",
            },
            "blockers": [],
        },
    )


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data

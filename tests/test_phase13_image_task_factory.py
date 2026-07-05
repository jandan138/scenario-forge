from hashlib import sha256
from pathlib import Path

import yaml

from scenario_forge.cli import main


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


def _write_image_task_request(tmp_path: Path) -> Path:
    image_path = tmp_path / "inputs" / "tabletop_001.jpg"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"fake-jpg")
    return _write_yaml(
        tmp_path / "image_task_request.yaml",
        {
            "schema_version": "image-task-request/v0.1",
            "request_id": "tabletop_photo_goal_001",
            "source": {
                "image_uri": f"file://{image_path}",
                "image_sha256": f"sha256:{sha256(image_path.read_bytes()).hexdigest()}",
                "rights_status": "user_provided_for_task_generation",
            },
            "goal": {
                "one_sentence_goal": "Put the apple into the bowl.",
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


def _write_image_scene_result(tmp_path: Path) -> Path:
    image_path = tmp_path / "inputs" / "tabletop_001.jpg"
    return _write_yaml(
        tmp_path / "image_scene_result.yaml",
        {
            "schema_version": "image-to-scene-result/v0.1",
            "result_id": "tabletop_photo_goal_001_result",
            "producer": {"name": "external-image-grounding-adapter", "version": "v0.1"},
            "source": {
                "image_uri": f"file://{image_path}",
                "image_sha256": f"sha256:{sha256(image_path.read_bytes()).hexdigest()}",
            },
            "goal": {
                "raw_text": "Put the apple into the bowl.",
                "normalized_task_family": "object_in_container",
            },
            "scene": {"coordinate_system": "tabletop_right_handed_z_up", "units": "meters"},
            "detections": [
                {
                    "detection_id": "det_apple",
                    "label": "apple",
                    "bbox_xywh": [120, 200, 80, 75],
                    "confidence": 0.91,
                    "semantic_tags": ["fruit", "pickable"],
                    "affordance_guesses": ["pickable"],
                },
                {
                    "detection_id": "det_bowl",
                    "label": "bowl",
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
                    "asset_type": "apple",
                    "required_affordances": ["pickable", "rigid"],
                },
                {
                    "role": "target_container",
                    "detection_id": "det_bowl",
                    "asset_type": "bowl",
                    "required_affordances": ["container", "rigid"],
                },
            ],
            "asset_candidates": [
                {
                    "role": "object",
                    "detection_id": "det_apple",
                    "selected_asset_id": "official_ebench_apple",
                    "score": 0.84,
                    "matching_reason": "category_and_size_match",
                    "rejected_alternatives": [],
                },
                {
                    "role": "target_container",
                    "detection_id": "det_bowl",
                    "selected_asset_id": "official_ebench_bowl",
                    "score": 0.86,
                    "matching_reason": "category_and_affordance_match",
                    "rejected_alternatives": [],
                },
            ],
            "instances": [
                {
                    "id": "apple_001",
                    "role": "manipulated_object",
                    "asset_id": "official_ebench_apple",
                    "pose": {"xyz": [0.12, 0.04, 0.78], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                },
                {
                    "id": "bowl_001",
                    "role": "target_container",
                    "asset_id": "official_ebench_bowl",
                    "pose": {"xyz": [0.33, 0.04, 0.78], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                },
            ],
            "task_bindings": {"object": "apple_001", "container": "bowl_001"},
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


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data

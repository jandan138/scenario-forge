from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from scenario_forge.adapters.convert_asset import (
    ConvertAssetCommandPlan,
    ConvertAssetHandoffError,
    NormalizeAssetCommandPlan,
    load_convert_asset_package_handoff,
)


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_source_bound_handoff(
    root: Path,
    *,
    source_usd: Path | None = None,
) -> tuple[Path, Path, Path, dict[str, object]]:
    if source_usd is None:
        source_usd = root / "source" / "lab_001.usd"
        source_usd.parent.mkdir(parents=True)
        source_usd.write_text(
            """#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    kilogramsPerUnit = 1
    upAxis = "Z"
    timeCodesPerSecond = 60
    framesPerSecond = 24
)
def Xform "World" {}
""",
            encoding="utf-8",
        )
    source_sha = _digest(source_usd)

    package_dir = root / "convert_asset_package"
    profile = package_dir / "physics" / "profile.json"
    profile.parent.mkdir(parents=True)
    profile.write_text('{"schema_version":"aan.physics_profile.v1"}\n', encoding="utf-8")
    profile_sha = _digest(profile)

    overlay = package_dir / "overlays" / "physics_profile.usda"
    overlay.parent.mkdir(parents=True)
    overlay.write_text(
        """#usda 1.0
over "World" {
    over "DryingBox_03" {
        over "body" {
            float physics:mass = 12
            float3 physics:diagonalInertia = (1, 2, 3)
            point3f physics:centerOfMass = (0, 0, 0)
            quatf physics:principalAxes = (1, 0, 0, 0)
        }
    }
}
""",
        encoding="utf-8",
    )
    scoped = package_dir / "deps" / "usd" / "scoped_source.usda"
    scoped.parent.mkdir(parents=True)
    scoped.write_text(
        """#usda 1.0
def Xform "World" {
    def Scope "Looks" { def Material "DryingBoxMaterial" {} }
    def Xform "DryingBox_03" { def Xform "body" { float physics:mass = -1 } }
}
""",
        encoding="utf-8",
    )
    root_usd = package_dir / "asset.usd"
    root_usd.write_text(
        """#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    kilogramsPerUnit = 1
    upAxis = "Z"
    timeCodesPerSecond = 60
    framesPerSecond = 24
    subLayers = [@overlays/physics_profile.usda@, @deps/usd/scoped_source.usda@]
)
""",
        encoding="utf-8",
    )
    root_sha = _digest(root_usd)
    metrics = {
        "meters_per_unit": 1.0,
        "kilograms_per_unit": 1.0,
        "up_axis": "Z",
        "time_codes_per_second": 60.0,
        "frames_per_second": 24.0,
    }
    scope = "/World/DryingBox_03"
    manifest: dict[str, object] = {
        "schema_version": "asset_application_normalizer.v1",
        "package_id": "dryingbox03_dynamic_package",
        "asset_id": "upstream_dryingbox03_dynamic",
        "asset_role": "dynamic",
        "overall_status": "pass",
        "source": {"path": "/producer/source/lab_001.usd", "sha256": source_sha},
        "target": {
            "target_runtime_profile": "isaac41",
            "target_benchmark_profile": "scenario-forge",
        },
        "entrypoints": {
            "root_usd": "asset.usd",
            "default_prim": "World",
            "asset_entry_prim": scope,
            "asset_scope_prims": [scope],
            "consumer_profile": "scenario-forge",
        },
        "asset_scope_prim_paths": [scope],
        "source_integrity": {
            "sha256_before": source_sha,
            "sha256_after": source_sha,
            "unchanged": True,
        },
        "dependency_closure": {
            "scope_extraction": {
                "status": "pass",
                "retained_subtree_prims": [scope, "/World/Looks/DryingBoxMaterial"],
                "retained_material_prims": ["/World/Looks/DryingBoxMaterial"],
                "preserved_stage_metadata": dict(metrics),
            }
        },
        "physics_closure": {
            "status": "pass",
            "role": "dynamic",
            "scope": {"mode": "asset_scope_prims", "asset_scope_prims": [scope]},
            "profile_admission": {
                "status": "pass",
                "profile_sha256": profile_sha,
                "profile_id": "dryingbox.profile",
                "revision": "r1",
                "source_binding": {
                    "sha256": source_sha,
                    "stage_metrics": dict(metrics),
                },
                "source_sha256": source_sha,
                "unmatched_rigid_bodies": [],
                "ambiguous_rigid_bodies": [],
                "invalid_body_rules": [],
                "quality_tier": "provisional_geometry",
                "evidence": {
                    "claim_boundary": "Simulation-safe provisional values; not measured physics.",
                    "replacement_contract": "Replace the complete upstream profile bundle.",
                },
                "errors": [],
                "package_profile_path": "physics/profile.json",
                "overlay_path": "overlays/physics_profile.usda",
                "packaged_profile_sha256": profile_sha,
                "resolved_body_count": 3,
            },
        },
        "runtime_evidence": {
            "status": "pass",
            "runtime_profile": "isaac41",
            "expected_root_usd_sha256": root_sha,
            "root_usd_sha256": root_sha,
            "cold_load": {"status": "pass"},
            "physics_step": {"status": "pass"},
            "reset": {"status": "pass", "reset_cycles": 2},
            "physics_warning_gate": {
                "status": "pass",
                "scope_prims": [scope],
                "scope_validation": {"status": "pass", "scope_prims": [scope], "errors": []},
                "binding_validation": {"status": "pass", "mapping_kind": "identity", "errors": []},
                "summary": {
                    "scoped_event_count": 0,
                    "out_of_scope_event_count": 0,
                    "unattributed_event_count": 0,
                },
            },
        },
        "claims_forbidden": [
            "Measured, BOM, CAD, or real-world physical-parameter parity is verified."
        ],
        "tool_version": "convert_asset.asset_application_normalizer.v1",
        "git_commit": None,
    }
    manifest_path = root / "manifest.json"
    embedded_manifest = package_dir / "evidence" / "manifest.json"
    embedded_manifest.parent.mkdir(parents=True)
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    manifest_path.write_text(payload, encoding="utf-8")
    embedded_manifest.write_text(payload, encoding="utf-8")
    return source_usd, package_dir, manifest_path, manifest


def test_convert_asset_plan_builds_command_without_executing_conversion() -> None:
    plan = ConvertAssetCommandPlan(
        convert_asset_root="/tools/ConvertAsset",
        input_usd="/data/raw/beaker.usd",
        output_usd="/data/raw/beaker_noMDL.usd",
        operations=("no-mdl", "mesh-faces"),
    )

    commands = plan.commands()

    assert commands == (
        (
            "/tools/ConvertAsset/scripts/isaac_python.sh",
            "/tools/ConvertAsset/main.py",
            "no-mdl",
            "/data/raw/beaker.usd",
        ),
        (
            "/tools/ConvertAsset/scripts/isaac_python.sh",
            "/tools/ConvertAsset/main.py",
            "mesh-faces",
            "/data/raw/beaker_noMDL.usd",
        ),
    )


def test_normalize_asset_plan_uses_convert_asset_public_cli_boundary() -> None:
    plan = NormalizeAssetCommandPlan(
        convert_asset_root="/tools/ConvertAsset",
        source_usd="/data/raw/beaker.usd",
        package_dir="/tmp/normalized/beaker",
    )

    assert plan.command() == (
        "/tools/ConvertAsset/scripts/isaac_python.sh",
        "/tools/ConvertAsset/main.py",
        "normalize-asset",
        "/data/raw/beaker.usd",
        "--package-dir",
        "/tmp/normalized/beaker",
    )


def _persist_manifest(
    manifest: dict[str, object],
    manifest_path: Path,
    package_dir: Path,
    *,
    embedded: bool = True,
) -> None:
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    manifest_path.write_text(payload, encoding="utf-8")
    if embedded:
        (package_dir / "evidence" / "manifest.json").write_text(
            payload,
            encoding="utf-8",
        )


def test_load_source_bound_handoff_maps_verified_package_to_neutral_asset_source(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, _ = _write_source_bound_handoff(tmp_path)

    handoff = load_convert_asset_package_handoff(
        package_dir,
        manifest_path,
        source_usd,
        expected_scope_prims=("/World/DryingBox_03",),
        producer_revision="324ce6e6d4395ccfda1e59e5ae89de9389cdf225",
    )

    assert handoff.package_id == "dryingbox03_dynamic_package"
    assert handoff.source_sha256 == _digest(source_usd)
    assert handoff.root_usd == package_dir / "asset.usd"
    assert handoff.root_prim_path == "/World"
    assert handoff.scope_prims == ("/World/DryingBox_03",)
    assert handoff.quality_tier == "provisional_geometry"
    assert handoff.profile_id == "dryingbox.profile"
    assert handoff.profile_revision == "r1"
    assert handoff.scoped_physics_warning_count == 0
    assert handoff.manifest_sha256 == _digest(manifest_path)

    source = handoff.to_local_usd_asset_source(
        asset_id="scientific_workbench_dryingbox_03_dynamic",
        license="CC-BY-NC-4.0",
        attribution=("ConvertAsset source-bound dynamic package",),
        redistributable=False,
        exclude_relative_paths=("evidence",),
    )
    assert source.role == "scene_overlay"
    assert source.root_prim_path == "/World"
    assert source.expected_sha256 == "sha256:" + _digest(package_dir / "asset.usd")
    assert source.exclude_relative_paths == ("evidence",)
    assert source.upstream_package is not None
    assert source.upstream_package.producer == "ConvertAsset"
    assert source.upstream_package.revision == (
        "324ce6e6d4395ccfda1e59e5ae89de9389cdf225"
    )
    assert source.upstream_package.manifest_sha256 == "sha256:" + _digest(manifest_path)
    assert source.upstream_package.metadata["quality_tier"] == "provisional_geometry"
    assert source.upstream_package.metadata["claims_forbidden"] == [
        "Measured, BOM, CAD, or real-world physical-parameter parity is verified."
    ]


def test_load_source_bound_handoff_rejects_source_hash_mismatch(tmp_path: Path) -> None:
    source_usd, package_dir, manifest_path, _ = _write_source_bound_handoff(tmp_path)
    source_usd.write_text("#usda 1.0\n# changed\n", encoding="utf-8")

    with pytest.raises(ConvertAssetHandoffError, match="source SHA-256"):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World/DryingBox_03",),
            producer_revision="324ce6e",
        )


def test_load_source_bound_handoff_rejects_external_embedded_manifest_mismatch(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_source_bound_handoff(tmp_path)
    manifest["package_id"] = "mutated_external_manifest"
    _persist_manifest(manifest, manifest_path, package_dir, embedded=False)

    with pytest.raises(ConvertAssetHandoffError, match="embedded manifest"):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World/DryingBox_03",),
            producer_revision="324ce6e",
        )


@pytest.mark.parametrize(
    ("relative_field", "unsafe_path"),
    [
        ("root_usd", "../asset.usd"),
        ("package_profile_path", "/outside/profile.json"),
        ("overlay_path", "overlays/../../outside.usda"),
    ],
)
def test_load_source_bound_handoff_rejects_unsafe_package_paths(
    tmp_path: Path,
    relative_field: str,
    unsafe_path: str,
) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_source_bound_handoff(tmp_path)
    if relative_field == "root_usd":
        entrypoints = manifest["entrypoints"]
        assert isinstance(entrypoints, dict)
        entrypoints[relative_field] = unsafe_path
    else:
        physics = manifest["physics_closure"]
        assert isinstance(physics, dict)
        admission = physics["profile_admission"]
        assert isinstance(admission, dict)
        admission[relative_field] = unsafe_path
    _persist_manifest(manifest, manifest_path, package_dir)

    with pytest.raises(ConvertAssetHandoffError, match=relative_field):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World/DryingBox_03",),
            producer_revision="324ce6e",
        )


def test_load_source_bound_handoff_rejects_failed_scoped_warning_gate(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_source_bound_handoff(tmp_path)
    runtime = manifest["runtime_evidence"]
    assert isinstance(runtime, dict)
    warning_gate = runtime["physics_warning_gate"]
    assert isinstance(warning_gate, dict)
    summary = warning_gate["summary"]
    assert isinstance(summary, dict)
    summary["scoped_event_count"] = 1
    _persist_manifest(manifest, manifest_path, package_dir)

    with pytest.raises(ConvertAssetHandoffError, match="scoped_event_count"):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World/DryingBox_03",),
            producer_revision="324ce6e",
        )


def test_load_source_bound_handoff_rejects_stage_metric_drift(tmp_path: Path) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_source_bound_handoff(tmp_path)
    dependency = manifest["dependency_closure"]
    assert isinstance(dependency, dict)
    extraction = dependency["scope_extraction"]
    assert isinstance(extraction, dict)
    metrics = extraction["preserved_stage_metadata"]
    assert isinstance(metrics, dict)
    metrics["meters_per_unit"] = 0.01
    _persist_manifest(manifest, manifest_path, package_dir)

    with pytest.raises(ConvertAssetHandoffError, match="stage metrics"):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World/DryingBox_03",),
            producer_revision="324ce6e",
        )


def test_load_source_bound_handoff_rejects_root_or_profile_hash_mismatch(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, _ = _write_source_bound_handoff(tmp_path)
    (package_dir / "physics" / "profile.json").write_text(
        '{"changed":true}\n', encoding="utf-8"
    )

    with pytest.raises(ConvertAssetHandoffError, match="profile SHA-256"):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World/DryingBox_03",),
            producer_revision="324ce6e",
        )

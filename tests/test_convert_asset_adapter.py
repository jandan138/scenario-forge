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


def _canonical_json_digest(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _write_source_bound_handoff(
    root: Path,
    *,
    source_usd: Path | None = None,
    with_interaction_contract: bool = False,
    with_disabled_source_collider: bool = False,
    observed_collider_approximation: str = "convexDecomposition",
    interaction_root: str = "/World/DryingBox_03",
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
    interaction_root_name = interaction_root.rpartition("/")[2]
    if not interaction_root.startswith("/World/") or not interaction_root_name:
        raise ValueError("interaction_root must be a direct child of /World")
    package_stem = (
        "dryingbox03"
        if interaction_root_name == "DryingBox_03"
        else interaction_root_name.lower()
    )
    opening_pose = {
        "conical_bottle03": (
            [0.0, 0.1965674179, 0.0],
            [0.7071067811865476, -0.7071067811865475, 0.0, 0.0],
        ),
        "graduated_cylinder_03": (
            [0.0, 0.2722941904, 0.0],
            [0.7071067811865476, -0.7071067811865475, 0.0, 0.0],
        ),
    }.get(interaction_root_name, ([0.0, 0.0, 0.2], [1.0, 0.0, 0.0, 0.0]))

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
    over "__INTERACTION_ROOT__" {
        over "body" {
            float physics:mass = 12
            float3 physics:diagonalInertia = (1, 2, 3)
            point3f physics:centerOfMass = (0, 0, 0)
            quatf physics:principalAxes = (1, 0, 0, 0)
        }
    }
}
""".replace("__INTERACTION_ROOT__", interaction_root_name),
        encoding="utf-8",
    )
    scoped = package_dir / "deps" / "usd" / "scoped_source.usda"
    scoped.parent.mkdir(parents=True)
    scoped.write_text(
        """#usda 1.0
def Xform "World"
{
    def Scope "Looks"
    {
        def Material "DryingBoxMaterial"
        {
        }
    }
    def Xform "__INTERACTION_ROOT__"
    {
        def Xform "body"
        {
            float physics:mass = -1
        }
    }
}
""".replace("__INTERACTION_ROOT__", interaction_root_name),
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

    interaction_contract: dict[str, object] | None = None
    if with_interaction_contract:
        qualification_report = (
            package_dir
            / "evidence"
            / "interaction_runtime_qualification"
            / "report.json"
        )
        qualification_report.parent.mkdir(parents=True, exist_ok=True)
        qualification_report.write_text(
            json.dumps(
                {
                    "schema_version": "aan.interaction_runtime_qualification.v1",
                    "status": "pass",
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        qualification_report_sha = _digest(qualification_report)

        def qualification_evidence(
            probe_id: str,
            *,
            claim_boundary: str | None = None,
        ) -> dict[str, object]:
            evidence: dict[str, object] = {
                "status": "pass",
                "probe_id": probe_id,
                "report_path": (
                    "evidence/interaction_runtime_qualification/report.json"
                ),
                "report_sha256": qualification_report_sha,
                "observations": [{"probe": probe_id, "status": "pass"}],
                "errors": [],
                "prequalification_contract_payload_sha256": "1" * 64,
            }
            if claim_boundary is not None:
                evidence["claim_boundary"] = claim_boundary
            return evidence

        interaction_profile = package_dir / "interaction" / "profile.json"
        interaction_profile.parent.mkdir(parents=True)
        interaction_profile.write_text(
            '{"schema_version":"aan.object_interaction_profile.v1"}\n',
            encoding="utf-8",
        )
        interaction_overlay = package_dir / "overlays" / "interaction.usda"
        interaction_overlay.write_text(
            '#usda 1.0\nover "World" { over "__INTERACTION_ROOT__" {} }\n'.replace(
                "__INTERACTION_ROOT__", interaction_root_name
            ),
            encoding="utf-8",
        )
        rigid_root = interaction_root
        collider_prims = [
            {
                "prim_path": f"{rigid_root}/body",
                "mode": "preserve",
                "collision_enabled": True,
                "purpose": ["simulation", "grasp"],
                "requested_approximation": None,
                "observed_approximation": observed_collider_approximation,
            }
        ]
        if with_disabled_source_collider:
            collider_prims.append(
                {
                    "prim_path": f"{rigid_root}/source_mesh",
                    "mode": "disable",
                    "collision_enabled": False,
                    "purpose": [],
                    "requested_approximation": None,
                    "observed_approximation": None,
                }
            )
        interaction_contract = {
            "schema_version": "aan.interaction_contract.v1",
            "status": "pass",
            "profile": {
                "schema_version": "aan.object_interaction_profile.v1",
                "profile_id": "dryingbox.interaction",
                "revision": "r1",
                "source_sha256": source_sha,
                "profile_sha256": _digest(interaction_profile),
                "package_path": "interaction/profile.json",
                "overlay_path": "overlays/interaction.usda",
            },
            "asset_entry_prim": rigid_root,
            "runtime_identity": {
                "rigid_root_prim": rigid_root,
                "exactly_one_active_rigid_body": True,
                "active_rigid_body_prims": [rigid_root],
            },
            "disabled_source_rigid_bodies": [
                {
                    "prim_path": f"{rigid_root}/body",
                    "rigid_body_api_removed": True,
                    "rigid_body_disabled": True,
                    "mass_api_removed": True,
                }
            ],
            "collider_prims": collider_prims,
            "open_top": {
                "required": True,
                "axis_body_local": [0.0, 0.0, 1.0],
                "aperture_frame": "opening",
                "status": "pass",
                "evidence": qualification_evidence("open_top"),
            },
            "named_frames": {
                "opening": {
                    "prim_path": f"{rigid_root}/frames/opening",
                    "parent_prim": rigid_root,
                    "translation_body_local_usd": opening_pose[0],
                    "rotation_body_local_wxyz": opening_pose[1],
                    "authoritative": True,
                },
                "grasp": {
                    "prim_path": f"{rigid_root}/frames/grasp",
                    "parent_prim": rigid_root,
                    "translation_body_local_usd": [0.0, 0.0, 0.1],
                    "rotation_body_local_wxyz": [1.0, 0.0, 0.0, 0.0],
                    "authoritative": True,
                },
                "support": {
                    "prim_path": f"{rigid_root}/frames/support",
                    "parent_prim": rigid_root,
                    "translation_body_local_usd": [0.0, 0.0, 0.0],
                    "rotation_body_local_wxyz": [1.0, 0.0, 0.0, 0.0],
                    "authoritative": True,
                },
            },
            "root_motion_gate": {
                "status": "pass",
                "required": True,
                "min_translation_m": 0.05,
                "evidence": qualification_evidence("root_motion"),
            },
            "stable_support_gate": {
                "status": "pass",
                "required": True,
                "evidence": qualification_evidence("stable_support"),
            },
            "gripper_collision_gate": {
                "status": "pass",
                "required": True,
                "evidence": qualification_evidence(
                    "gripper_collision",
                    claim_boundary=(
                        "Collision-proxy qualification only; no grasp-success claim."
                    ),
                ),
            },
        }
        artifact_paths = [
            "asset.usd",
            "deps/usd/scoped_source.usda",
            "interaction/profile.json",
            "overlays/interaction.usda",
            "overlays/physics_profile.usda",
            "physics/profile.json",
        ]
        artifacts = [
            {"path": path, "sha256": _digest(package_dir / path)}
            for path in sorted(artifact_paths)
        ]
        contract_payload = {
            key: interaction_contract[key]
            for key in (
                "schema_version",
                "asset_entry_prim",
                "runtime_identity",
                "disabled_source_rigid_bodies",
                "collider_prims",
                "open_top",
                "named_frames",
            )
        }
        interaction_contract["closure"] = {
            "status": "pass",
            "digest_algorithm": "sha256",
            "contract_encoding": "canonical_json_interaction_payload_v1",
            "contract_payload_sha256": _canonical_json_digest(contract_payload),
            "tree_encoding": "canonical_json_artifact_list_v1",
            "runtime_tree_sha256": _canonical_json_digest(artifacts),
            "artifacts": artifacts,
        }
    metrics = {
        "meters_per_unit": 1.0,
        "kilograms_per_unit": 1.0,
        "up_axis": "Z",
        "time_codes_per_second": 60.0,
        "frames_per_second": 24.0,
    }
    scope = interaction_root
    manifest: dict[str, object] = {
        "schema_version": "asset_application_normalizer.v1",
        "package_id": f"{package_stem}_dynamic_package",
        "asset_id": f"upstream_{package_stem}_dynamic",
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
    if interaction_contract is not None:
        manifest["interaction_contract"] = interaction_contract
    manifest_path = root / "manifest.json"
    embedded_manifest = package_dir / "evidence" / "manifest.json"
    embedded_manifest.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    manifest_path.write_text(payload, encoding="utf-8")
    embedded_manifest.write_text(payload, encoding="utf-8")
    return source_usd, package_dir, manifest_path, manifest


def _write_visual_static_handoff(
    root: Path,
    *,
    source_usd: Path | None = None,
    scope: str = "/World/lab_015",
    producer_asset_role: str = "visual_static",
    physics_role: str = "visual_static",
) -> tuple[Path, Path, Path, dict[str, object]]:
    """Write the minimal ConvertAsset visual-static consumer handoff."""

    if source_usd is None:
        source_usd = root / "source" / "Scene1_hard.usd"
        source_usd.parent.mkdir(parents=True)
        source_usd.write_text(
            '#usda 1.0\n(\n    defaultPrim = "World"\n    metersPerUnit = 1\n'
            '    upAxis = "Z"\n)\ndef Xform "World" {}\n',
            encoding="utf-8",
        )
    source_sha = _digest(source_usd)
    package_dir = root / "visual_static_package"
    scoped = package_dir / "deps" / "usd" / "scoped_source.usda"
    scoped.parent.mkdir(parents=True)
    scope_name = scope.rpartition("/")[2]
    scoped_body = (
        '    def Xform "complete_room"\n'
        '    {\n'
        '    }\n'
        if scope == "/World"
        else (
            f'    def Xform "{scope_name}"\n'
            '    {\n'
            '    }\n'
        )
    )
    scoped.write_text(
        f'''#usda 1.0
def Xform "World"
{{
{scoped_body}}}
''',
        encoding="utf-8",
    )
    root_usd = package_dir / "asset.usd"
    root_usd.write_text(
        '#usda 1.0\n(\n    defaultPrim = "World"\n    metersPerUnit = 1\n'
        '    upAxis = "Z"\n    subLayers = [@deps/usd/scoped_source.usda@]\n)\n',
        encoding="utf-8",
    )
    root_sha = _digest(root_usd)
    manifest: dict[str, object] = {
        "schema_version": "asset_application_normalizer.v1",
        "package_id": "scene1_hard_visual_static_package",
        "asset_id": "LabUtopia_Scene1_hard_visual_static",
        "asset_role": producer_asset_role,
        "overall_status": "pass",
        "source": {"path": "/producer/source/Scene1_hard.usd", "sha256": source_sha},
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
                "retained_subtree_prims": [scope],
                "retained_material_prims": [],
                "preserved_stage_metadata": {
                    "meters_per_unit": 1.0,
                    "up_axis": "Z",
                },
            }
        },
        "physics_closure": {
            "status": "pass",
            "role": physics_role,
            "scope": {"mode": "asset_scope_prims", "asset_scope_prims": [scope]},
            "physical_frame": {
                "status": "pass",
                "source": {
                    "meters_per_unit": 1.0,
                    "kilograms_per_unit": 1.0,
                    "up_axis": "Z",
                    "time_codes_per_second": 60.0,
                    "frames_per_second": 24.0,
                    "start_time_code": 0.0,
                    "end_time_code": 100.0,
                },
                "package": {
                    "meters_per_unit": 1.0,
                    "kilograms_per_unit": 1.0,
                    "up_axis": "Z",
                    "time_codes_per_second": 60.0,
                    "frames_per_second": 24.0,
                    "start_time_code": 0.0,
                    "end_time_code": 100.0,
                },
                "metric_mismatches": [],
                "scope_bounds": [
                    {
                        "path": scope,
                        "source_world_bound_m": {
                            "min": [0.0, 0.0, 0.0],
                            "max": [1.0, 1.0, 1.0],
                        },
                        "package_world_bound_m": {
                            "min": [0.0, 0.0, 0.0],
                            "max": [1.0, 1.0, 1.0],
                        },
                        "status": "pass",
                    }
                ],
                "blocked_scope_prims": [],
            },
        },
        "output_role_admission": {
            "status": "pass",
            "scope": [scope],
            "summary": {
                "active_articulation_root_count": 0,
                "active_collision_count": 0,
                "active_joint_count": 0,
                "active_rigid_body_count": 0,
            },
            "residue": [],
        },
        "visual_preservation_fingerprint": {"status": "pass"},
        "runtime_evidence": {
            "status": "pass",
            "runtime_profile": "isaac41",
            "expected_root_usd_sha256": root_sha,
            "root_usd_sha256": root_sha,
            "cold_load": {"status": "pass"},
            "render_readback": {"status": "pass"},
            "physics_step": {"status": "pass"},
            "reset": {"status": "pass"},
            "physics_warning_gate": {
                "status": "pass",
                "scope_prims": [scope],
                "scope_validation": {
                    "status": "pass",
                    "scope_prims": [scope],
                    "errors": [],
                },
                "binding_validation": {
                    "status": "pass",
                    "mapping_kind": "identity",
                    "errors": [],
                },
                "summary": {
                    "scoped_event_count": 0,
                    "out_of_scope_event_count": 0,
                    "unattributed_event_count": 0,
                },
            },
        },
        "claims_forbidden": [
            "The visual_static asset is dynamic-physics-ready."
        ],
    }
    manifest_path = root / "visual_static_manifest.json"
    embedded_manifest = package_dir / "evidence" / "manifest.json"
    embedded_manifest.parent.mkdir(parents=True, exist_ok=True)
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
        "--out",
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


@pytest.mark.parametrize(
    ("usage", "expected_role"),
    [
        ("visual_static_environment", "environment"),
        ("visual_static_object", "static_object"),
    ],
)
def test_visual_static_handoff_maps_to_nonphysical_scene_sources(
    tmp_path: Path,
    usage: str,
    expected_role: str,
) -> None:
    source_usd, package_dir, manifest_path, _ = _write_visual_static_handoff(tmp_path)

    handoff = load_convert_asset_package_handoff(
        package_dir,
        manifest_path,
        source_usd,
        expected_scope_prims=("/World/lab_015",),
        producer_revision="f81e953cd2652d6e0552187d5d732e86ae1e76ac",
        usage=usage,
    )
    source = handoff.to_local_usd_asset_source(
        asset_id=f"scene1_{expected_role}",
        license="CC-BY-NC-4.0",
    )

    assert handoff.producer_asset_role == "visual_static"
    assert handoff.interaction_contract is None
    assert source.role == expected_role
    assert source.upstream_package is not None
    assert source.upstream_package.metadata["producer_asset_role"] == "visual_static"
    assert source.upstream_package.metadata["consumer_usage"] == usage


def test_visual_static_environment_producer_role_is_accepted(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, _ = _write_visual_static_handoff(
        tmp_path,
        scope="/World",
        producer_asset_role="visual_static_environment",
        physics_role="visual_static_environment",
    )

    handoff = load_convert_asset_package_handoff(
        package_dir,
        manifest_path,
        source_usd,
        expected_scope_prims=("/World",),
        producer_revision="2026-07-24-producer-source-fix-2",
        usage="visual_static_environment",
    )

    assert handoff.producer_asset_role == "visual_static_environment"
    source = handoff.to_local_usd_asset_source(
        asset_id="scientific_environment_081",
        license="CC-BY-NC-4.0",
    )
    assert source.role == "environment"


def test_visual_static_handoff_rejects_physics_residue(tmp_path: Path) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_visual_static_handoff(
        tmp_path
    )
    admission = manifest["output_role_admission"]
    assert isinstance(admission, dict)
    summary = admission["summary"]
    assert isinstance(summary, dict)
    summary["active_collision_count"] = 1
    _persist_manifest(manifest, manifest_path, package_dir)

    with pytest.raises(ConvertAssetHandoffError, match="active_collision_count"):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World/lab_015",),
            producer_revision="f81e953",
            usage="visual_static_environment",
        )


def test_visual_static_handoff_rejects_physical_frame_mismatch(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_visual_static_handoff(
        tmp_path
    )
    physics = manifest["physics_closure"]
    assert isinstance(physics, dict)
    frame = physics["physical_frame"]
    assert isinstance(frame, dict)
    package_frame = frame["package"]
    assert isinstance(package_frame, dict)
    package_frame["meters_per_unit"] = 0.001
    _persist_manifest(manifest, manifest_path, package_dir)

    with pytest.raises(ConvertAssetHandoffError, match="physical_frame"):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World/lab_015",),
            producer_revision="f81e953",
            usage="visual_static_environment",
        )


def test_task_ready_interaction_handoff_maps_to_rigid_object_without_local_repair(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, _ = _write_source_bound_handoff(
        tmp_path,
        with_interaction_contract=True,
    )

    handoff = load_convert_asset_package_handoff(
        package_dir,
        manifest_path,
        source_usd,
        expected_scope_prims=("/World/DryingBox_03",),
        producer_revision="324ce6e",
        usage="rigid_object",
    )
    source = handoff.to_local_usd_asset_source(
        asset_id="qualified_rigid_object",
        license="CC-BY-NC-4.0",
    )

    assert handoff.interaction_contract is not None
    assert handoff.interaction_contract.asset_entry_prim == "/World/DryingBox_03"
    assert handoff.interaction_contract.rigid_root_prim == "/World/DryingBox_03"
    assert handoff.interaction_contract.active_rigid_body_prims == (
        "/World/DryingBox_03",
    )
    assert handoff.interaction_contract.task_ready is True
    assert source.role == "rigid_object"
    assert source.upstream_package is not None
    interaction = source.upstream_package.metadata["interaction_contract"]
    assert interaction["asset_entry_prim"] == "/World/DryingBox_03"
    assert interaction["runtime_identity"]["rigid_root_prim"] == (
        "/World/DryingBox_03"
    )
    assert interaction["closure"]["tree_encoding"] == (
        "canonical_json_artifact_list_v1"
    )


def test_task_ready_interaction_handoff_accepts_disabled_source_collider(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, _ = _write_source_bound_handoff(
        tmp_path,
        with_interaction_contract=True,
        with_disabled_source_collider=True,
    )

    handoff = load_convert_asset_package_handoff(
        package_dir,
        manifest_path,
        source_usd,
        expected_scope_prims=("/World/DryingBox_03",),
        producer_revision="324ce6e",
        usage="rigid_object",
    )

    assert handoff.interaction_contract is not None
    assert handoff.interaction_contract.task_ready is True


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("entry_root_mismatch", "asset_entry_prim"),
        ("multiple_rigid_bodies", "exactly one|active_rigid_body_prims"),
        ("non_authoritative_frame", "authoritative"),
        ("missing_collider", "collider_prims"),
        ("runtime_gate_not_run", "task-ready|root_motion_gate"),
        ("payload_digest_mismatch", "contract_payload_sha256"),
    ],
)
def test_rigid_object_handoff_rejects_incomplete_interaction_contract(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_source_bound_handoff(
        tmp_path,
        with_interaction_contract=True,
    )
    interaction = manifest["interaction_contract"]
    assert isinstance(interaction, dict)
    if mutation == "entry_root_mismatch":
        interaction["asset_entry_prim"] = "/World/Other"
    elif mutation == "multiple_rigid_bodies":
        identity = interaction["runtime_identity"]
        assert isinstance(identity, dict)
        identity["active_rigid_body_prims"] = [
            "/World/DryingBox_03",
            "/World/DryingBox_03/body",
        ]
    elif mutation == "non_authoritative_frame":
        frames = interaction["named_frames"]
        assert isinstance(frames, dict)
        opening = frames["opening"]
        assert isinstance(opening, dict)
        opening["authoritative"] = False
    elif mutation == "missing_collider":
        interaction["collider_prims"] = []
    elif mutation == "runtime_gate_not_run":
        gate = interaction["root_motion_gate"]
        assert isinstance(gate, dict)
        gate["status"] = "not_run"
    else:
        closure = interaction["closure"]
        assert isinstance(closure, dict)
        closure["contract_payload_sha256"] = "0" * 64
    _persist_manifest(manifest, manifest_path, package_dir)

    with pytest.raises(ConvertAssetHandoffError, match=message):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World/DryingBox_03",),
            producer_revision="324ce6e",
            usage="rigid_object",
        )


def test_rigid_object_handoff_rejects_runtime_closure_artifact_tampering(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, _ = _write_source_bound_handoff(
        tmp_path,
        with_interaction_contract=True,
    )
    (package_dir / "overlays" / "interaction.usda").write_text(
        "#usda 1.0\n# tampered\n",
        encoding="utf-8",
    )

    with pytest.raises(ConvertAssetHandoffError, match="artifact.*sha256|closure"):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World/DryingBox_03",),
            producer_revision="324ce6e",
            usage="rigid_object",
        )


@pytest.mark.parametrize("mutation", ["missing", "tampered"])
def test_rigid_object_handoff_verifies_runtime_qualification_report(
    tmp_path: Path,
    mutation: str,
) -> None:
    source_usd, package_dir, manifest_path, _ = _write_source_bound_handoff(
        tmp_path,
        with_interaction_contract=True,
    )
    report = package_dir / "evidence/interaction_runtime_qualification/report.json"
    if mutation == "missing":
        report.unlink()
    else:
        report.write_text('{"status":"tampered"}\n', encoding="utf-8")

    with pytest.raises(ConvertAssetHandoffError, match="report_path|report_sha256"):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World/DryingBox_03",),
            producer_revision="324ce6e",
            usage="rigid_object",
        )


def test_rigid_object_source_cannot_exclude_qualification_report(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, _ = _write_source_bound_handoff(
        tmp_path,
        with_interaction_contract=True,
    )
    handoff = load_convert_asset_package_handoff(
        package_dir,
        manifest_path,
        source_usd,
        expected_scope_prims=("/World/DryingBox_03",),
        producer_revision="324ce6e",
        usage="rigid_object",
    )

    with pytest.raises(ValueError, match="qualification report"):
        handoff.to_local_usd_asset_source(
            asset_id="qualified_rigid_object",
            license="CC-BY-NC-4.0",
            exclude_relative_paths=("evidence",),
        )


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

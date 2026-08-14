from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path

import pytest

from scenario_forge.adapters.convert_asset import (
    ConvertAssetCommandPlan,
    ConvertAssetHandoffError,
    NormalizeAssetCommandPlan,
    load_convert_asset_package_handoff,
    load_gpu_pbd_static_container_handoff,
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
    open_top_required: bool = True,
    with_disabled_source_collider: bool = False,
    observed_collider_approximation: str = "convexDecomposition",
    interaction_root: str = "/World/DryingBox_03",
    interaction_profile_schema_version: str = "aan.object_interaction_profile.v1",
    entry_world_transform: list[list[float]] | None = None,
    identity_facade_frames: bool = False,
    with_interaction_regions: bool = False,
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
            [0.0, 0.0, 0.1965674179]
            if identity_facade_frames
            else [0.0, 0.1965674179, 0.0],
            [1.0, 0.0, 0.0, 0.0]
            if identity_facade_frames
            else [0.7071067811865476, -0.7071067811865475, 0.0, 0.0],
        ),
        "graduated_cylinder_03": (
            [0.0, 0.0, 0.2722941904]
            if identity_facade_frames
            else [0.0, 0.2722941904, 0.0],
            [1.0, 0.0, 0.0, 0.0]
            if identity_facade_frames
            else [0.7071067811865476, -0.7071067811865475, 0.0, 0.0],
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
            json.dumps({"schema_version": interaction_profile_schema_version}) + "\n",
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
                "schema_version": interaction_profile_schema_version,
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
                "required": open_top_required,
                "axis_body_local": (
                    [0.0, 0.0, 1.0] if open_top_required else None
                ),
                "aperture_frame": "opening" if open_top_required else None,
                "status": "pass" if open_top_required else "not_applicable",
                "evidence": (
                    qualification_evidence("open_top")
                    if open_top_required
                    else {}
                ),
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
        if with_interaction_regions:
            interaction_contract["interaction_regions"] = {
                "interior_safe": {
                    "shape": "cylinder",
                    "frame": "opening",
                    "axis_frame_local": [0.0, 0.0, 1.0],
                    "radius_body_local_usd": 0.08,
                    "half_height_body_local_usd": 0.12,
                    "purpose": ["containment", "tool_motion"],
                    "authoritative": True,
                }
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
        if "interaction_regions" in interaction_contract:
            contract_payload["interaction_regions"] = interaction_contract[
                "interaction_regions"
            ]
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
    if entry_world_transform is None:
        entry_world_transform = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    package_world_bound_m = {
        "min": [-0.16, -0.175, 0.0],
        "max": [0.16, 0.175, 0.226],
    }
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
            "physical_frame": {
                "status": "pass",
                "source": dict(metrics),
                "package": dict(metrics),
                "metric_mismatches": [],
                "scope_bounds": [
                    {
                        "path": scope,
                        "source_world_bound_m": dict(package_world_bound_m),
                        "package_world_bound_m": dict(package_world_bound_m),
                        "status": "pass",
                    }
                ],
                "blocked_scope_prims": [],
            },
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
        "visual_preservation_fingerprint": {
            "status": "pass",
            "package_before_physics_profile": {
                "scope_world_transforms": {
                    scope: entry_world_transform,
                }
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


def _write_static_support_handoff(
    root: Path,
) -> tuple[Path, Path, Path, dict[str, object]]:
    """Write a minimal source-bound static-support consumer handoff."""
    source_usd = root / "source" / "lab_001.usd"
    source_usd.parent.mkdir(parents=True)
    source_usd.write_text(
        '#usda 1.0\n(\n    defaultPrim = "World"\n    metersPerUnit = 1\n'
        '    upAxis = "Z"\n)\n'
        'def Xform "World"\n{\n    def Xform "table"\n    {\n    }\n}\n',
        encoding="utf-8",
    )
    source_sha = _digest(source_usd)
    package_dir = root / "static_support_package"
    profile = package_dir / "static_support" / "profile.json"
    profile.parent.mkdir(parents=True)
    profile.write_text(
        json.dumps({"schema_version": "aan.static_support_profile.v1"}) + "\n",
        encoding="utf-8",
    )
    overlay = package_dir / "overlays" / "static_support.usda"
    overlay.parent.mkdir(parents=True)
    overlay.write_text('#usda 1.0\nover "World" { over "table" {} }\n', encoding="utf-8")
    root_usd = package_dir / "asset.usd"
    root_usd.write_text(
        '#usda 1.0\n(\n    defaultPrim = "World"\n    metersPerUnit = 1\n'
        '    upAxis = "Z"\n    subLayers = [@overlays/static_support.usda@]\n)\n'
        'def Xform "World"\n{\n    def Xform "table"\n    {\n    }\n}\n',
        encoding="utf-8",
    )
    root_sha = _digest(root_usd)
    qualification = {
        "schema_version": "aan.static_support_runtime_qualification.v1",
        "status": "pass",
        "probe_count": 6,
        "probe_results": [
            {"probe": name, "status": "pass"}
            for name in (
                "center_drop",
                "north_edge_drop",
                "south_edge_drop",
                "east_edge_drop",
                "west_edge_drop",
                "side_impact",
            )
        ],
    }
    qualification_path = (
        package_dir / "evidence" / "static_support" / "runtime_qualification.json"
    )
    qualification_path.parent.mkdir(parents=True)
    qualification_path.write_text(
        json.dumps(qualification, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    scope = "/World/table"
    required_probes = [item["probe"] for item in qualification["probe_results"]]
    contract = {
        "schema_version": "aan.static_support_contract.v1",
        "status": "pass",
        "profile_id": "tests.table.static-support",
        "profile_revision": "r1",
        "asset_entry_prim": scope,
        "collider_policy": "prefer_source_then_proxy",
        "collider_selection": "preserved_source",
        "colliders": [
            {
                "prim_path": "/World/table/surface/mesh",
                "collision_enabled": True,
                "source": "qualified_source",
            }
        ],
        "support_surface": {
            "top_z": 0.8,
            "x_range": [-1.0, 1.0],
            "y_range": [-0.6, 0.6],
            "edge_band_m": 0.05,
        },
        "physics_material": {
            "prim_path": "/World/table/__aan_static_support_material",
            "static_friction": 0.5,
            "dynamic_friction": 0.5,
            "restitution": 0.0,
            "friction_combine_mode": "max",
            "restitution_combine_mode": "multiply",
            "calibration_status": "provisional_unmeasured",
        },
        "profile": {
            "package_path": "static_support/profile.json",
            "sha256": _digest(profile),
            "source_usd_sha256": source_sha,
        },
        "overlay_path": "overlays/static_support.usda",
        "qualification": {
            "status": "pass",
            "schema_version": "aan.static_support_runtime_qualification.v1",
            "report_path": "evidence/static_support/runtime_qualification.json",
            "report_sha256": _digest(qualification_path),
            "probe_count": 6,
            "required_probes": required_probes,
        },
    }
    frame = {
        "status": "pass",
        "source": {"meters_per_unit": 1.0, "kilograms_per_unit": 1.0, "up_axis": "Z", "time_codes_per_second": 60.0, "frames_per_second": 24.0},
        "package": {"meters_per_unit": 1.0, "kilograms_per_unit": 1.0, "up_axis": "Z", "time_codes_per_second": 60.0, "frames_per_second": 24.0},
        "metric_mismatches": [],
        "scope_bounds": [{"path": scope, "source_world_bound_m": {"min": [-1, -0.6, 0], "max": [1, 0.6, 0.8]}, "package_world_bound_m": {"min": [-1, -0.6, 0], "max": [1, 0.6, 0.8]}, "status": "pass"}],
        "blocked_scope_prims": [],
    }
    manifest: dict[str, object] = {
        "schema_version": "asset_application_normalizer.v1",
        "package_id": "lab001_table_static_support",
        "asset_id": "Lab001Table",
        "asset_role": "static_support",
        "overall_status": "pass",
        "source": {"path": str(source_usd), "sha256": source_sha},
        "target": {"target_runtime_profile": "isaac41", "target_benchmark_profile": "scenario-forge"},
        "entrypoints": {"root_usd": "asset.usd", "default_prim": "World", "asset_entry_prim": scope, "asset_scope_prims": [scope], "consumer_profile": "scenario-forge"},
        "asset_scope_prim_paths": [scope],
        "source_integrity": {"sha256_before": source_sha, "sha256_after": source_sha, "unchanged": True},
        "dependency_closure": {"scope_extraction": {"status": "pass", "retained_subtree_prims": [scope], "retained_material_prims": [], "preserved_stage_metadata": {"meters_per_unit": 1.0, "up_axis": "Z"}}},
        "physics_closure": {
            "status": "pass",
            "role": "static_support",
            "scope": {"mode": "asset_scope_prims", "asset_scope_prims": [scope]},
            "physical_frame": frame,
            "static_support_contract": {
                **contract,
                "qualification": {
                    "status": "pending_runtime",
                    "required_probes": required_probes,
                },
            },
        },
        "output_role_admission": {"status": "pass", "role": "static_support", "declared_colliders": ["/World/table/surface/mesh"], "observed_active_colliders": ["/World/table/surface/mesh"], "zero_dynamic_semantics": True},
        "static_support_contract": contract,
        "support_audit": {
            "overall_status": "not_requested",
            "blocked_reasons": [],
            "support_closure": {},
        },
        "visual_preservation_fingerprint": {"status": "pass"},
        "runtime_evidence": {"status": "pass", "runtime_profile": "isaac41", "expected_root_usd_sha256": root_sha, "root_usd_sha256": root_sha, "cold_load": {"status": "pass"}, "render_readback": {"status": "pass"}, "physics_step": {"status": "pass"}, "reset": {"status": "pass"}, "static_support_qualification": qualification, "physics_warning_gate": {"status": "pass", "scope_prims": [scope], "scope_validation": {"status": "pass", "scope_prims": [scope], "errors": []}, "binding_validation": {"status": "pass", "mapping_kind": "identity", "errors": []}, "summary": {"scoped_event_count": 0, "out_of_scope_event_count": 0, "unattributed_event_count": 0}}},
        "claims_forbidden": ["Measured contact parameters are verified."],
    }
    manifest_path = root / "static_support_manifest.json"
    embedded_manifest = package_dir / "evidence" / "manifest.json"
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    manifest_path.write_text(payload, encoding="utf-8")
    embedded_manifest.write_text(payload, encoding="utf-8")
    return source_usd, package_dir, manifest_path, manifest


def _write_articulated_handoff(
    root: Path,
) -> tuple[Path, Path, Path, dict[str, object]]:
    source_usd, package_dir, manifest_path, manifest = _write_source_bound_handoff(
        root,
        interaction_root="/World/Centrifuge",
    )
    source_sha = _digest(source_usd)
    articulation_root = "/World/Centrifuge"
    joint_specs = (
        ("lid", "/World/Centrifuge/lid", "PhysicsRevoluteJoint", "X", -90.0, 0.0, -89.0),
        (
            "start_button",
            "/World/Centrifuge/start_button",
            "PhysicsPrismaticJoint",
            "Z",
            -0.004,
            0.0,
            0.0,
        ),
        ("rotor", "/World/Centrifuge/rotor", "PhysicsRevoluteJoint", "Y", -180.0, 0.0, 0.0),
    )
    states = {
        "lid": {
            "open": [math.radians(-90.0), math.radians(-80.0)],
            "closed": [math.radians(-5.0), 0.0],
        },
        "start_button": {
            "pressed": [-0.004, -0.003],
            "released": [-0.0005, 0.0],
        },
        "rotor": {"parked": [math.radians(-1.0), 0.0]},
    }
    reset_states = {
        "lid": "open",
        "start_button": "released",
        "rotor": "parked",
    }
    joints: list[dict[str, object]] = []
    dof_mapping: list[dict[str, object]] = []
    reset_values: list[dict[str, object]] = []
    semantic_joints: dict[str, object] = {}
    for dof_index, (
        semantic_name,
        part_prim,
        joint_type,
        axis,
        lower,
        upper,
        reset,
    ) in enumerate(joint_specs):
        joint_prim = f"{articulation_root}/{semantic_name}_joint"
        reset_record = {
            "value": reset,
            "value_source": "authored",
            "status": "pass",
            "attribute": f"{joint_prim}.state:physics:position",
            "provenance_status": "pass",
        }
        joints.append(
            {
                "prim_path": joint_prim,
                "joint_type": joint_type,
                "owning_layer": "overlays/physics_profile.usda",
                "axis": {
                    "value": axis,
                    "value_source": "authored",
                    "status": "pass",
                    "attribute": f"{joint_prim}.physics:axis",
                    "provenance_status": "pass",
                },
                "limits": {
                    "lower": {
                        "value": lower,
                        "value_source": "authored",
                        "status": "pass",
                        "attribute": f"{joint_prim}.physics:lowerLimit",
                        "provenance_status": "pass",
                    },
                    "upper": {
                        "value": upper,
                        "value_source": "authored",
                        "status": "pass",
                        "attribute": f"{joint_prim}.physics:upperLimit",
                        "provenance_status": "pass",
                    },
                    "status": "pass",
                },
                "enabled": {
                    "value": True,
                    "value_source": "authored",
                    "status": "pass",
                    "attribute": f"{joint_prim}.physics:jointEnabled",
                    "provenance_status": "pass",
                },
                "collision_enabled": {
                    "value": False,
                    "value_source": "fallback",
                    "status": "pass",
                    "attribute": f"{joint_prim}.physics:collisionEnabled",
                    "provenance_status": "not_applicable",
                },
                "drive_status": "authored",
                "reset_value": dict(reset_record),
            }
        )
        dof_mapping.append(
            {
                "dof_index": dof_index,
                "joint_prim": joint_prim,
                "joint_type": joint_type,
                "axis": axis,
                "value_source": "authored",
            }
        )
        reset_values.append(
            {
                "joint_prim": joint_prim,
                "joint_type": joint_type,
                "reset_value": dict(reset_record),
            }
        )
        semantic_joints[semantic_name] = {
            "joint_prim": joint_prim,
            "part_prim": part_prim,
            "dof_index": dof_index,
            "runtime_reset_value": (
                math.radians(reset)
                if joint_type == "PhysicsRevoluteJoint"
                else reset
            ),
            "reset_state": reset_states[semantic_name],
            "states": states[semantic_name],
        }

    manifest["articulation_closure"] = {
        "status": "pass",
        "root_usd": str(package_dir / "asset.usd"),
        "scope": {
            "mode": "asset_scope_prims",
            "asset_scope_prims": [articulation_root],
        },
        "articulation_roots": [
            {
                "prim_path": articulation_root,
                "type_name": "Xform",
                "owning_layer": "overlays/physics_profile.usda",
                "value_source": "authored",
            }
        ],
        "joints": joints,
        "dof_mapping": dof_mapping,
        "reset_values": reset_values,
        "summary": {
            "articulation_root_count": 1,
            "joint_count": len(joints),
            "controllable_dof_count": len(dof_mapping),
        },
    }

    device_profile = {
        "schema_version": "aan.articulated_device_profile.v1",
        "profile_id": "hci955350.centrifuge",
        "revision": "r1",
        "source_sha256": source_sha,
        "asset_entry_prim": articulation_root,
        "articulation_root_prim": articulation_root,
        "runtime_units": {
            "revolute": "radian",
            "prismatic": "meter",
        },
        "required_runtime_task_gates": [
            "lid_contact_cycle",
            "button_contact_cycle",
            "button_reset_stability",
            "rotor_reset_stability",
            "socket_insertion_clearance",
        ],
        "semantic_joints": semantic_joints,
        "named_frames": {
            frame_name: {
                "parent_prim": parent_prim,
                "translation_parent_local_m": translation,
                "rotation_parent_local_wxyz": [1.0, 0.0, 0.0, 0.0],
                "authoritative": True,
            }
            for frame_name, parent_prim, translation in (
                ("support", articulation_root, [0.0, 0.0, 0.0]),
                ("lid_handle", f"{articulation_root}/lid", [-0.15, 0.0, 0.03]),
                (
                    "start_button_press",
                    f"{articulation_root}/panel",
                    [-0.15, -0.1, 0.14],
                ),
                (
                    "tube_socket_0",
                    f"{articulation_root}/rotor",
                    [0.0, 0.02, 0.09],
                ),
            )
        },
    }
    device_profile_path = package_dir / "articulation" / "device_profile.json"
    device_profile_path.parent.mkdir(parents=True)
    device_profile_path.write_text(
        json.dumps(device_profile, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _persist_manifest(manifest, manifest_path, package_dir)
    prequalification_manifest_sha256 = _digest(manifest_path)
    asset_sha256 = _digest(package_dir / "asset.usd")
    qualification_report = (
        package_dir
        / "evidence"
        / "articulation_runtime_qualification"
        / "report.json"
    )
    qualification_report.parent.mkdir(parents=True)
    qualification_report.write_text(
        json.dumps(
            {
                "schema_version": "aan.articulation_runtime_qualification.v1",
                "status": "pass",
                "runtime": {"runtime_profile": "isaac41"},
                "inputs": {
                    "device_profile": {
                        "schema_version": "aan.articulated_device_profile.v1",
                        "profile_sha256": _digest(device_profile_path),
                        "source_sha256": source_sha,
                    },
                    "integrity": {
                        "status": "pass",
                        "centrifuge_manifest_sha256": prequalification_manifest_sha256,
                        "centrifuge_asset_usd_sha256_before": asset_sha256,
                        "centrifuge_asset_usd_sha256_after": asset_sha256,
                    },
                    "qualified_package": {
                        "asset_path": "asset.usd",
                        "asset_entry_prim": articulation_root,
                        "runtime_profile": "isaac41",
                        "prequalification_manifest_sha256": prequalification_manifest_sha256,
                        "asset_usd_sha256_before": asset_sha256,
                        "asset_usd_sha256_after": asset_sha256,
                    },
                },
                "drive_integrity": {"status": "pass"},
                "runtime_dof_mapping": [
                    {
                        "dof_index": dof_index,
                        "dof_name": semantic_name,
                        "joint_prim": (
                            f"{articulation_root}/{semantic_name}_joint"
                        ),
                    }
                    for dof_index, (
                        semantic_name,
                        _,
                        _,
                        _,
                        _,
                        _,
                        _,
                    ) in enumerate(joint_specs)
                ],
                "task_gates": {
                    gate_name: {"status": "pass"}
                    for gate_name in (
                        "lid_contact_cycle",
                        "button_contact_cycle",
                        "button_reset_stability",
                        "rotor_reset_stability",
                        "socket_insertion_clearance",
                    )
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    manifest["articulation_contract"] = {
        "schema_version": "aan.articulation_contract.v1",
        "status": "pass",
        "profile": {
            "schema_version": "aan.articulated_device_profile.v1",
            "profile_id": "hci955350.centrifuge",
            "revision": "r1",
            "source_sha256": source_sha,
            "profile_sha256": _digest(device_profile_path),
            "package_path": "articulation/device_profile.json",
        },
        "runtime_qualification": {
            "status": "pass",
            "report_path": (
                "evidence/articulation_runtime_qualification/report.json"
            ),
            "report_sha256": _digest(qualification_report),
        },
    }
    _persist_manifest(manifest, manifest_path, package_dir)
    _write_articulation_promotion(
        package_dir,
        manifest_path,
        manifest,
        prequalification_manifest_sha256=prequalification_manifest_sha256,
    )
    return source_usd, package_dir, manifest_path, manifest


def _add_fixed_base_mounting_contract(
    package_dir: Path,
    manifest_path: Path,
    manifest: dict[str, object],
) -> dict[str, object]:
    """Add the producer-qualified fixed-base mounting ABI to a fixture."""

    contract = manifest["articulation_contract"]
    assert isinstance(contract, dict)
    profile_metadata = contract["profile"]
    runtime_metadata = contract["runtime_qualification"]
    assert isinstance(profile_metadata, dict)
    assert isinstance(runtime_metadata, dict)
    profile_path = package_dir / str(profile_metadata["package_path"])
    report_path = package_dir / str(runtime_metadata["report_path"])
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    source_sha256 = str(profile["source_sha256"])
    mounting = {
        "schema_version": "aan.articulated_mounting.v1",
        "motion_mode": "fixed_base",
        "asset_entry_prim": "/World/Centrifuge",
        "coordinate_semantics": {
            "stage_up_axis": "Z",
            "linear_units": "meter",
            "quaternion_order": "wxyz",
            "support_frame": "runtime_articulation_root_pose_local",
            "mount_pose": (
                "support_plane_to_runtime_articulation_root_pose_world_axes_"
                "at_yaw_zero"
            ),
            "qualified_extents": (
                "world_axis_aligned_at_mount_pose_after_joint_reset"
            ),
        },
        "support_frame_root_local": {
            "translation_m": [0.0, -0.10363300144672394, 0.0],
            "rotation_wxyz": [1.0, 0.0, 0.0, 0.0],
        },
        "support_plane_to_root_mount_pose": {
            "translation_m": [0.0, 0.0, 0.10363300144672394],
            "rotation_wxyz": [0.5, 0.5, 0.5, 0.5],
        },
        "initial_joint_reset_positions": [
            {"dof_index": 0, "position": math.radians(-89.0)},
            {"dof_index": 1, "position": 0.0},
            {"dof_index": 2, "position": 0.0},
        ],
        "qualified_reset_geometry": {
            "warmup_frames": 50,
            "warmup_extent_world_aabb_m": [0.3893976, 0.35, 0.4448730],
            "settle_frames": 240,
            "final_extent_world_aabb_m": [0.3893976, 0.35, 0.4448730],
        },
        "verification_required": "benchtop_stability",
    }
    required_gates = profile["required_runtime_task_gates"]
    assert isinstance(required_gates, list)
    required_gates.append("benchtop_stability")
    profile["mounting"] = mounting
    profile_path.write_text(
        json.dumps(profile, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    profile_sha256 = _digest(profile_path)
    profile_metadata["profile_sha256"] = profile_sha256
    report_inputs = report["inputs"]
    assert isinstance(report_inputs, dict)
    report_profile = report_inputs["device_profile"]
    assert isinstance(report_profile, dict)
    report_profile["profile_sha256"] = profile_sha256
    task_gates = report["task_gates"]
    assert isinstance(task_gates, dict)
    task_gates["benchtop_stability"] = {"status": "pass"}
    report["qualified_consumer_placement"] = {
        **mounting,
        "status": "pass",
        "profile_sha256": profile_sha256,
        "source_sha256": source_sha256,
    }
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_sha256 = _digest(report_path)
    runtime_metadata["report_sha256"] = report_sha256
    contract["mounting"] = {
        **mounting,
        "status": "pass",
        "profile_sha256": profile_sha256,
        "runtime_report_sha256": report_sha256,
        "source_sha256": source_sha256,
    }
    _persist_manifest(manifest, manifest_path, package_dir)
    _write_articulation_promotion(package_dir, manifest_path, manifest)
    return mounting


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


def _write_articulation_promotion(
    package_dir: Path,
    manifest_path: Path,
    manifest: dict[str, object],
    *,
    prequalification_manifest_sha256: str | None = None,
) -> None:
    promotion_path = (
        package_dir
        / "evidence"
        / "articulation_runtime_qualification"
        / "promotion.json"
    )
    if prequalification_manifest_sha256 is None:
        existing = json.loads(promotion_path.read_text(encoding="utf-8"))
        prequalification_manifest_sha256 = existing[
            "prequalification_manifest_sha256"
        ]
    contract = manifest["articulation_contract"]
    assert isinstance(contract, dict)
    profile = contract["profile"]
    runtime = contract["runtime_qualification"]
    assert isinstance(profile, dict)
    assert isinstance(runtime, dict)
    promotion_path.write_text(
        json.dumps(
            {
                "schema_version": "aan.articulation_package_promotion.v1",
                "status": "pass",
                "prequalification_manifest_sha256": prequalification_manifest_sha256,
                "final_manifest_sha256": _digest(manifest_path),
                "asset_usd_sha256": _digest(package_dir / "asset.usd"),
                "profile_path": profile["package_path"],
                "profile_sha256": profile["profile_sha256"],
                "runtime_report_path": runtime["report_path"],
                "runtime_report_sha256": runtime["report_sha256"],
                "claim_boundary": "Package USD and physical properties were not changed during promotion.",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
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


def test_static_support_handoff_maps_qualified_table_contract(tmp_path: Path) -> None:
    source_usd, package_dir, manifest_path, _ = _write_static_support_handoff(tmp_path)

    handoff = load_convert_asset_package_handoff(
        package_dir,
        manifest_path,
        source_usd,
        expected_scope_prims=("/World/table",),
        producer_revision="static-support-r1",
        usage="static_support_object",
    )
    source = handoff.to_local_usd_asset_source(
        asset_id="scientific_workbench_ebench_table",
        license="CC-BY-NC-4.0",
    )

    assert handoff.producer_asset_role == "static_support"
    assert handoff.static_support_contract is not None
    assert handoff.static_support_contract.collider_prims == (
        "/World/table/surface/mesh",
    )
    assert handoff.static_support_contract.qualification_report_path == (
        "evidence/static_support/runtime_qualification.json"
    )
    assert source.role == "static_support_object"
    assert source.upstream_package is not None
    assert source.upstream_package.metadata["consumer_usage"] == "static_support_object"
    assert source.upstream_package.metadata["static_support_contract"]["status"] == "pass"


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


def test_generated_room_handoff_carries_passing_support_certificate(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_visual_static_handoff(
        tmp_path,
        scope="/World",
        producer_asset_role="visual_static_environment",
        physics_role="visual_static_environment",
    )
    support = {
        "schema_version": "aan.generated_room_support_audit.v1",
        "overall_status": "pass",
        "blocked_reasons": [],
        "source_sha256": "a" * 64,
        "producer_review": {"status": "pass", "reviewer": "reviewer"},
        "relations": [
            {
                "object_prim": "/Room/Beaker",
                "support_prim": "/Room/Bench",
                "producer_status": "pass",
                "independent_status": "pass",
            }
        ],
        "support_closure": {"/Room/Bench": ["/Room/Beaker"]},
    }
    report = package_dir / "evidence/support_audit/report.json"
    report.parent.mkdir(parents=True)
    report.write_text(json.dumps(support, sort_keys=True) + "\n", encoding="utf-8")
    manifest["support_audit"] = support
    _persist_manifest(manifest, manifest_path, package_dir)

    handoff = load_convert_asset_package_handoff(
        package_dir,
        manifest_path,
        source_usd,
        expected_scope_prims=("/World",),
        producer_revision="support-audit-r1",
        usage="visual_static_environment",
    )

    assert handoff.support_audit is not None
    assert handoff.support_audit.source_sha256 == "a" * 64
    assert handoff.support_audit.relation_count == 1
    source = handoff.to_local_usd_asset_source(
        asset_id="generated_room",
        license="LicenseRef-Internal-Generated",
        exclude_relative_paths=("evidence",),
    )
    assert source.upstream_package is not None
    assert source.upstream_package.metadata["support_audit"]["status"] == "pass"


def test_generated_room_handoff_rejects_blocked_support_certificate(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_visual_static_handoff(
        tmp_path,
        scope="/World",
        producer_asset_role="visual_static_environment",
        physics_role="visual_static_environment",
    )
    manifest["support_audit"] = {
        "schema_version": "aan.generated_room_support_audit.v1",
        "overall_status": "blocked",
        "blocked_reasons": ["floating object"],
    }
    _persist_manifest(manifest, manifest_path, package_dir)

    with pytest.raises(ConvertAssetHandoffError, match="support_audit"):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World",),
            producer_revision="support-audit-r1",
            usage="visual_static_environment",
        )


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
    geometry = source.upstream_package.metadata["task_interactive_geometry"]
    assert handoff.interaction_contract is not None
    assert geometry == {
        "schema_version": "scenario-forge-task-interactive-geometry/v0.1",
        "asset_entry_prim": "/World/DryingBox_03",
        "entry_world_transform": [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        "package_world_bound_m": {
            "min": [-0.16, -0.175, 0.0],
            "max": [0.16, 0.175, 0.226],
        },
        "extent_m": [0.32, 0.35, 0.226],
        "identity_tolerance": 1e-06,
        "support_frame": "support",
        "support_frame_local_matrix": [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        "support_frame_source_sha256": (
            handoff.interaction_contract.contract_payload_sha256
        ),
    }
    interaction = source.upstream_package.metadata["interaction_contract"]
    assert interaction["asset_entry_prim"] == "/World/DryingBox_03"
    assert interaction["runtime_identity"]["rigid_root_prim"] == (
        "/World/DryingBox_03"
    )
    assert interaction["closure"]["tree_encoding"] == (
        "canonical_json_artifact_list_v1"
    )


def test_task_ready_interaction_handoff_accepts_profile_v2(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, _ = _write_source_bound_handoff(
        tmp_path,
        with_interaction_contract=True,
        interaction_profile_schema_version="aan.object_interaction_profile.v2",
        with_interaction_regions=True,
    )

    handoff = load_convert_asset_package_handoff(
        package_dir,
        manifest_path,
        source_usd,
        expected_scope_prims=("/World/DryingBox_03",),
        producer_revision="interaction-profile-v2",
        usage="rigid_object",
    )

    assert handoff.interaction_contract is not None
    assert (
        handoff.interaction_contract.payload["profile"]["schema_version"]
        == "aan.object_interaction_profile.v2"
    )
    assert handoff.interaction_contract.interaction_regions["interior_safe"][
        "frame"
    ] == "opening"


def test_task_ready_interaction_handoff_rejects_region_with_unknown_frame(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_source_bound_handoff(
        tmp_path,
        with_interaction_contract=True,
        interaction_profile_schema_version="aan.object_interaction_profile.v2",
        with_interaction_regions=True,
    )
    interaction = manifest["interaction_contract"]
    assert isinstance(interaction, dict)
    regions = interaction["interaction_regions"]
    assert isinstance(regions, dict)
    region = regions["interior_safe"]
    assert isinstance(region, dict)
    region["frame"] = "guessed_center"
    closure = interaction["closure"]
    assert isinstance(closure, dict)
    contract_payload = {
        key: interaction[key]
        for key in (
            "schema_version",
            "asset_entry_prim",
            "runtime_identity",
            "disabled_source_rigid_bodies",
            "collider_prims",
            "open_top",
            "named_frames",
            "interaction_regions",
        )
    }
    closure["contract_payload_sha256"] = _canonical_json_digest(contract_payload)
    _persist_manifest(manifest, manifest_path, package_dir)

    with pytest.raises(ConvertAssetHandoffError, match="interaction_regions.*frame"):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World/DryingBox_03",),
            producer_revision="interaction-region-unknown-frame",
            usage="rigid_object",
        )


def test_task_interactive_handoff_rejects_missing_authoritative_support_frame(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_source_bound_handoff(
        tmp_path,
        with_interaction_contract=True,
    )
    interaction = manifest["interaction_contract"]
    assert isinstance(interaction, dict)
    frames = interaction["named_frames"]
    assert isinstance(frames, dict)
    frames.pop("support")
    closure = interaction["closure"]
    assert isinstance(closure, dict)
    contract_payload = {
        key: interaction[key]
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
    closure["contract_payload_sha256"] = _canonical_json_digest(contract_payload)
    _persist_manifest(manifest, manifest_path, package_dir)

    with pytest.raises(
        ConvertAssetHandoffError,
        match="authoritative root-local support frame",
    ):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World/DryingBox_03",),
            producer_revision="support-frame-required",
            usage="rigid_object",
        )


def test_task_qualification_report_is_verified_and_propagated(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_source_bound_handoff(
        tmp_path,
        with_interaction_contract=True,
    )
    report_path = package_dir / "evidence" / "tube_insertion" / "report.json"
    report_path.parent.mkdir(parents=True)
    report_path.write_text(
        '{"schema_version":"fixture","status":"pass"}\n',
        encoding="utf-8",
    )
    manifest["task_qualifications"] = [
        {
            "qualification_id": "tube_insertion",
            "status": "pass",
            "report_path": "evidence/tube_insertion/report.json",
            "report_sha256": _digest(report_path),
        }
    ]
    _persist_manifest(manifest, manifest_path, package_dir)

    handoff = load_convert_asset_package_handoff(
        package_dir,
        manifest_path,
        source_usd,
        expected_scope_prims=("/World/DryingBox_03",),
        producer_revision="task-qualification-fixture",
        usage="rigid_object",
    )
    source = handoff.to_local_usd_asset_source(
        asset_id="qualified_rigid_object",
        license="CC-BY-NC-4.0",
    )

    assert handoff.task_qualifications[0].qualification_id == "tube_insertion"
    assert source.upstream_package is not None
    assert source.upstream_package.metadata["task_qualifications"] == [
        {
            "qualification_id": "tube_insertion",
            "status": "pass",
            "report_path": "evidence/tube_insertion/report.json",
            "report_sha256": _digest(report_path),
        }
    ]
    with pytest.raises(ValueError, match="qualification report"):
        handoff.to_local_usd_asset_source(
            asset_id="qualified_rigid_object",
            license="CC-BY-NC-4.0",
            exclude_relative_paths=("evidence/tube_insertion",),
        )


def test_task_qualification_rejects_report_hash_mismatch(tmp_path: Path) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_source_bound_handoff(
        tmp_path,
        with_interaction_contract=True,
    )
    report_path = package_dir / "evidence" / "tube_insertion" / "report.json"
    report_path.parent.mkdir(parents=True)
    report_path.write_text('{"status":"pass"}\n', encoding="utf-8")
    manifest["task_qualifications"] = [
        {
            "qualification_id": "tube_insertion",
            "status": "pass",
            "report_path": "evidence/tube_insertion/report.json",
            "report_sha256": "0" * 64,
        }
    ]
    _persist_manifest(manifest, manifest_path, package_dir)

    with pytest.raises(
        ConvertAssetHandoffError,
        match="task_qualifications.*report_sha256",
    ):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World/DryingBox_03",),
            producer_revision="task-qualification-fixture",
            usage="rigid_object",
        )


@pytest.mark.parametrize("usage", ["rigid_object", "articulated_object"])
def test_task_interactive_handoff_rejects_non_identity_entry_transform(
    tmp_path: Path,
    usage: str,
) -> None:
    non_identity = [
        [0.0, 0.175, 0.0, 0.0],
        [0.0, 0.0, 0.175, 0.0],
        [0.175, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.103633, 1.0],
    ]
    if usage == "articulated_object":
        source_usd, package_dir, manifest_path, manifest = (
            _write_articulated_handoff(tmp_path)
        )
        fingerprint = manifest["visual_preservation_fingerprint"]
        assert isinstance(fingerprint, dict)
        package_fingerprint = fingerprint["package_before_physics_profile"]
        assert isinstance(package_fingerprint, dict)
        package_fingerprint["scope_world_transforms"] = {
            "/World/Centrifuge": non_identity
        }
        _persist_manifest(manifest, manifest_path, package_dir)
        _write_articulation_promotion(package_dir, manifest_path, manifest)
        expected_scope = "/World/Centrifuge"
    else:
        source_usd, package_dir, manifest_path, _ = _write_source_bound_handoff(
            tmp_path,
            with_interaction_contract=True,
            entry_world_transform=non_identity,
        )
        expected_scope = "/World/DryingBox_03"

    with pytest.raises(
        ConvertAssetHandoffError,
        match="task-interactive asset entry transform must be identity",
    ):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=(expected_scope,),
            producer_revision="identity-root-required",
            usage=usage,
        )


def test_scene_overlay_keeps_legacy_non_identity_entry_transform_compatibility(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, _ = _write_source_bound_handoff(
        tmp_path,
        entry_world_transform=[
            [0.0, 0.175, 0.0, 0.0],
            [0.0, 0.0, 0.175, 0.0],
            [0.175, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.103633, 1.0],
        ],
    )

    handoff = load_convert_asset_package_handoff(
        package_dir,
        manifest_path,
        source_usd,
        expected_scope_prims=("/World/DryingBox_03",),
        producer_revision="legacy-overlay",
        usage="scene_overlay",
    )

    assert handoff.usage == "scene_overlay"


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


def test_task_ready_interaction_handoff_accepts_not_applicable_open_top(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, _ = _write_source_bound_handoff(
        tmp_path,
        with_interaction_contract=True,
        open_top_required=False,
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


def test_articulated_handoff_maps_validated_device_contract_without_local_repair(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, _ = _write_articulated_handoff(
        tmp_path
    )

    handoff = load_convert_asset_package_handoff(
        package_dir,
        manifest_path,
        source_usd,
        expected_scope_prims=("/World/Centrifuge",),
        producer_revision="convertasset-articulation-r1",
        usage="articulated_object",
    )
    source = handoff.to_local_usd_asset_source(
        asset_id="qualified_centrifuge",
        license="LicenseRef-Internal-Restricted",
    )

    assert handoff.articulation_contract is not None
    assert handoff.articulation_contract.articulation_root_prim == (
        "/World/Centrifuge"
    )
    assert tuple(
        item["dof_index"]
        for item in handoff.articulation_contract.dof_mapping
    ) == (0, 1, 2)
    assert source.role == "articulated_object"
    assert source.upstream_package is not None
    contract = source.upstream_package.metadata["articulation_contract"]
    assert contract["schema_version"] == (
        "scenario-forge-articulation-contract/v0.1"
    )
    assert contract["closure"]["dof_mapping"][1]["joint_prim"] == (
        "/World/Centrifuge/start_button_joint"
    )
    assert contract["runtime_units"] == {
        "revolute": "radian",
        "prismatic": "meter",
    }
    assert contract["joints"]["lid"]["runtime_reset_value"] == pytest.approx(
        math.radians(-89.0)
    )
    assert contract["joints"]["lid"]["states"]["open"] == pytest.approx(
        [math.radians(-90.0), math.radians(-80.0)]
    )
    assert contract["named_frames"]["start_button_press"][
        "authoritative"
    ] is True
    geometry = source.upstream_package.metadata["task_interactive_geometry"]
    assert geometry["support_frame"] == "support"
    assert geometry["support_frame_local_matrix"][3] == [0.0, 0.0, 0.0, 1.0]
    assert geometry["support_frame_source_sha256"] == (
        handoff.articulation_contract.profile_sha256
    )


def test_articulated_handoff_verifies_and_propagates_fixed_base_mounting(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_articulated_handoff(
        tmp_path
    )
    mounting = _add_fixed_base_mounting_contract(
        package_dir,
        manifest_path,
        manifest,
    )

    handoff = load_convert_asset_package_handoff(
        package_dir,
        manifest_path,
        source_usd,
        expected_scope_prims=("/World/Centrifuge",),
        producer_revision="convertasset-articulation-mounting-r1",
        usage="articulated_object",
    )
    source = handoff.to_local_usd_asset_source(
        asset_id="qualified_fixed_base_device",
        license="LicenseRef-Internal-Restricted",
    )

    assert handoff.articulation_contract is not None
    assert handoff.articulation_contract.mounting is not None
    assert handoff.articulation_contract.mounting["motion_mode"] == "fixed_base"
    assert source.upstream_package is not None
    geometry = source.upstream_package.metadata["task_interactive_geometry"]
    assert geometry["schema_version"] == (
        "scenario-forge-task-interactive-geometry/v0.2"
    )
    propagated = geometry["mounting"]
    assert propagated["schema_version"] == "aan.articulated_mounting.v1"
    assert propagated["status"] == "pass"
    assert propagated["profile_sha256"] == (
        manifest["articulation_contract"]["profile"]["profile_sha256"]
    )
    assert propagated["runtime_report_sha256"] == (
        manifest["articulation_contract"]["runtime_qualification"][
            "report_sha256"
        ]
    )
    assert propagated["qualified_reset_geometry"] == (
        mounting["qualified_reset_geometry"]
    )
    assert geometry["support_frame_local_matrix"][3] == [
        0.0,
        -0.10363300144672394,
        0.0,
        1.0,
    ]
    assert geometry["support_frame_source_sha256"] == (
        propagated["runtime_report_sha256"]
    )


def test_articulated_handoff_rejects_mounting_that_disagrees_with_profile(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_articulated_handoff(
        tmp_path
    )
    _add_fixed_base_mounting_contract(package_dir, manifest_path, manifest)
    contract = manifest["articulation_contract"]
    assert isinstance(contract, dict)
    mounting = contract["mounting"]
    assert isinstance(mounting, dict)
    geometry = mounting["qualified_reset_geometry"]
    assert isinstance(geometry, dict)
    geometry["warmup_extent_world_aabb_m"] = [9.0, 9.0, 9.0]
    _persist_manifest(manifest, manifest_path, package_dir)
    _write_articulation_promotion(package_dir, manifest_path, manifest)

    with pytest.raises(
        ConvertAssetHandoffError,
        match="mounting.*packaged device profile",
    ):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World/Centrifuge",),
            producer_revision="convertasset-articulation-mounting-r1",
            usage="articulated_object",
        )


def test_articulated_handoff_accepts_duplicate_runtime_dof_names(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_articulated_handoff(
        tmp_path
    )
    contract = manifest["articulation_contract"]
    assert isinstance(contract, dict)
    runtime = contract["runtime_qualification"]
    assert isinstance(runtime, dict)
    report_path = package_dir / str(runtime["report_path"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    runtime_dof_mapping = report["runtime_dof_mapping"]
    assert isinstance(runtime_dof_mapping, list)
    for item in (runtime_dof_mapping[0], runtime_dof_mapping[2]):
        assert isinstance(item, dict)
        item["dof_name"] = "RevoluteJoint"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    runtime["report_sha256"] = _digest(report_path)
    _persist_manifest(manifest, manifest_path, package_dir)
    _write_articulation_promotion(package_dir, manifest_path, manifest)

    handoff = load_convert_asset_package_handoff(
        package_dir,
        manifest_path,
        source_usd,
        expected_scope_prims=("/World/Centrifuge",),
        producer_revision="convertasset-articulation-r1",
        usage="articulated_object",
    )

    assert handoff.articulation_contract is not None
    assert tuple(
        item["joint_prim"] for item in handoff.articulation_contract.dof_mapping
    ) == (
        "/World/Centrifuge/lid_joint",
        "/World/Centrifuge/start_button_joint",
        "/World/Centrifuge/rotor_joint",
    )


def test_articulated_handoff_ignores_not_requested_interaction_contract(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_articulated_handoff(
        tmp_path
    )
    manifest["interaction_contract"] = {
        "schema_version": "aan.interaction_contract.v1",
        "status": "not_requested",
    }
    _persist_manifest(manifest, manifest_path, package_dir)
    _write_articulation_promotion(package_dir, manifest_path, manifest)

    handoff = load_convert_asset_package_handoff(
        package_dir,
        manifest_path,
        source_usd,
        expected_scope_prims=("/World/Centrifuge",),
        producer_revision="convertasset-articulation-r1",
        usage="articulated_object",
    )

    assert handoff.interaction_contract is None
    assert handoff.articulation_contract is not None


def test_articulated_handoff_rejects_a_stale_promotion_manifest_hash(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, _ = _write_articulated_handoff(tmp_path)
    promotion_path = (
        package_dir
        / "evidence"
        / "articulation_runtime_qualification"
        / "promotion.json"
    )
    promotion = json.loads(promotion_path.read_text(encoding="utf-8"))
    promotion["final_manifest_sha256"] = "0" * 64
    promotion_path.write_text(
        json.dumps(promotion, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ConvertAssetHandoffError, match="promotion.*final_manifest"):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World/Centrifuge",),
            producer_revision="convertasset-articulation-r1",
            usage="articulated_object",
        )


def test_articulated_handoff_rejects_nonstandard_json_runtime_report(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_articulated_handoff(
        tmp_path
    )
    contract = manifest["articulation_contract"]
    assert isinstance(contract, dict)
    runtime = contract["runtime_qualification"]
    assert isinstance(runtime, dict)
    report_path = package_dir / str(runtime["report_path"])
    report_path.write_text('{"status": Infinity}\n', encoding="utf-8")
    runtime["report_sha256"] = _digest(report_path)
    _persist_manifest(manifest, manifest_path, package_dir)
    _write_articulation_promotion(package_dir, manifest_path, manifest)

    with pytest.raises(ConvertAssetHandoffError, match="not valid JSON"):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World/Centrifuge",),
            producer_revision="convertasset-articulation-r1",
            usage="articulated_object",
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing_contract", "articulation_contract"),
        ("multiple_roots", "exactly one|articulation_root_count"),
        ("duplicate_dof", "dof_index.*unique|contiguous"),
        ("gapped_dof", "contiguous"),
        ("missing_reset", "reset"),
        ("reset_out_of_limits", "reset.*limits"),
        ("semantic_joint_mismatch", "semantic_joints.*DOF|dof_index"),
        ("runtime_reset_unit_mismatch", "runtime_reset_value"),
        ("profile_hash_mismatch", "profile_sha256"),
        ("runtime_report_hash_mismatch", "report_sha256"),
        ("runtime_dof_order_mismatch", "runtime_dof_mapping"),
        ("runtime_task_gate_blocked", "button_contact_cycle"),
        ("runtime_report_profile_mismatch", "device_profile.profile_sha256"),
        ("runtime_report_profile_source_mismatch", "device_profile.source_sha256"),
        ("qualified_package_entry_mismatch", "qualified package\\.asset_entry_prim"),
        ("runtime_not_pass", "runtime_qualification"),
    ],
)
def test_articulated_handoff_rejects_incomplete_or_unbound_contract(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    source_usd, package_dir, manifest_path, manifest = _write_articulated_handoff(
        tmp_path
    )
    closure = manifest["articulation_closure"]
    assert isinstance(closure, dict)
    contract = manifest["articulation_contract"]
    assert isinstance(contract, dict)
    if mutation == "missing_contract":
        del manifest["articulation_contract"]
    elif mutation == "multiple_roots":
        roots = closure["articulation_roots"]
        assert isinstance(roots, list)
        roots.append(
            {
                "prim_path": "/World/Centrifuge/other_root",
                "type_name": "Xform",
                "owning_layer": "overlays/physics_profile.usda",
                "value_source": "authored",
            }
        )
        summary = closure["summary"]
        assert isinstance(summary, dict)
        summary["articulation_root_count"] = 2
    elif mutation == "duplicate_dof":
        mapping = closure["dof_mapping"]
        assert isinstance(mapping, list)
        assert isinstance(mapping[1], dict)
        mapping[1]["dof_index"] = 0
    elif mutation == "gapped_dof":
        mapping = closure["dof_mapping"]
        assert isinstance(mapping, list)
        assert isinstance(mapping[2], dict)
        mapping[2]["dof_index"] = 3
    elif mutation == "missing_reset":
        reset_values = closure["reset_values"]
        assert isinstance(reset_values, list)
        reset_values.pop()
    elif mutation == "reset_out_of_limits":
        reset_values = closure["reset_values"]
        assert isinstance(reset_values, list)
        reset = reset_values[0]
        assert isinstance(reset, dict)
        reset_record = reset["reset_value"]
        assert isinstance(reset_record, dict)
        reset_record["value"] = 10.0
        joints = closure["joints"]
        assert isinstance(joints, list)
        joint = joints[0]
        assert isinstance(joint, dict)
        joint_reset_record = joint["reset_value"]
        assert isinstance(joint_reset_record, dict)
        joint_reset_record["value"] = 10.0
    elif mutation == "semantic_joint_mismatch":
        profile_path = package_dir / "articulation/device_profile.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["semantic_joints"]["lid"]["dof_index"] = 2
        profile_path.write_text(
            json.dumps(profile, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        profile_metadata = contract["profile"]
        assert isinstance(profile_metadata, dict)
        profile_metadata["profile_sha256"] = _digest(profile_path)
    elif mutation == "runtime_reset_unit_mismatch":
        profile_path = package_dir / "articulation/device_profile.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["semantic_joints"]["lid"]["runtime_reset_value"] = -89.0
        profile_path.write_text(
            json.dumps(profile, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        profile_metadata = contract["profile"]
        assert isinstance(profile_metadata, dict)
        profile_metadata["profile_sha256"] = _digest(profile_path)
    elif mutation == "profile_hash_mismatch":
        profile_metadata = contract["profile"]
        assert isinstance(profile_metadata, dict)
        profile_metadata["profile_sha256"] = "0" * 64
    elif mutation == "runtime_report_hash_mismatch":
        runtime = contract["runtime_qualification"]
        assert isinstance(runtime, dict)
        runtime["report_sha256"] = "0" * 64
    elif mutation == "runtime_dof_order_mismatch":
        runtime = contract["runtime_qualification"]
        assert isinstance(runtime, dict)
        report_path = package_dir / str(runtime["report_path"])
        report = json.loads(report_path.read_text(encoding="utf-8"))
        first = report["runtime_dof_mapping"][0]
        second = report["runtime_dof_mapping"][1]
        first["joint_prim"], second["joint_prim"] = (
            second["joint_prim"],
            first["joint_prim"],
        )
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        runtime["report_sha256"] = _digest(report_path)
    elif mutation == "runtime_task_gate_blocked":
        runtime = contract["runtime_qualification"]
        assert isinstance(runtime, dict)
        report_path = package_dir / str(runtime["report_path"])
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["task_gates"]["button_contact_cycle"]["status"] = "blocked"
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        runtime["report_sha256"] = _digest(report_path)
    elif mutation == "runtime_report_profile_mismatch":
        runtime = contract["runtime_qualification"]
        assert isinstance(runtime, dict)
        report_path = package_dir / str(runtime["report_path"])
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["inputs"]["device_profile"]["profile_sha256"] = "0" * 64
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        runtime["report_sha256"] = _digest(report_path)
    elif mutation == "runtime_report_profile_source_mismatch":
        runtime = contract["runtime_qualification"]
        assert isinstance(runtime, dict)
        report_path = package_dir / str(runtime["report_path"])
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["inputs"]["device_profile"]["source_sha256"] = "0" * 64
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        runtime["report_sha256"] = _digest(report_path)
    elif mutation == "qualified_package_entry_mismatch":
        runtime = contract["runtime_qualification"]
        assert isinstance(runtime, dict)
        report_path = package_dir / str(runtime["report_path"])
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["inputs"]["qualified_package"]["asset_entry_prim"] = "/World/Other"
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        runtime["report_sha256"] = _digest(report_path)
    else:
        runtime = contract["runtime_qualification"]
        assert isinstance(runtime, dict)
        runtime["status"] = "blocked"
    _persist_manifest(manifest, manifest_path, package_dir)
    if mutation != "missing_contract":
        _write_articulation_promotion(package_dir, manifest_path, manifest)

    with pytest.raises(ConvertAssetHandoffError, match=message):
        load_convert_asset_package_handoff(
            package_dir,
            manifest_path,
            source_usd,
            expected_scope_prims=("/World/Centrifuge",),
            producer_revision="convertasset-articulation-r1",
            usage="articulated_object",
        )


@pytest.mark.parametrize(
    "excluded_path",
    [
        "articulation",
        "evidence",
        "evidence/articulation_runtime_qualification/promotion.json",
    ],
)
def test_articulated_source_cannot_exclude_bound_profile_or_runtime_report(
    tmp_path: Path,
    excluded_path: str,
) -> None:
    source_usd, package_dir, manifest_path, _ = _write_articulated_handoff(
        tmp_path
    )
    handoff = load_convert_asset_package_handoff(
        package_dir,
        manifest_path,
        source_usd,
        expected_scope_prims=("/World/Centrifuge",),
        producer_revision="convertasset-articulation-r1",
        usage="articulated_object",
    )

    with pytest.raises(ValueError, match="qualification/profile artifact"):
        handoff.to_local_usd_asset_source(
            asset_id="qualified_centrifuge",
            license="LicenseRef-Internal-Restricted",
            exclude_relative_paths=(excluded_path,),
        )


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


def _write_gpu_pbd_static_container_handoff(root: Path) -> tuple[Path, Path]:
    package = root / "gpu_pbd_container"
    evidence = package / "evidence"
    evidence.mkdir(parents=True)
    (package / "asset.usd").write_text("#usda 1.0\n", encoding="utf-8")
    report = evidence / "gpu_pbd_static_qualification_report.json"
    run = {
        "overall_status": "pass",
        "resolved_particle_semantics": {"fluid": True, "self_collision": True},
        "static_hold": {
            "minimum_inside_ratio": 1.0,
            "maximum_below_support": 0,
            "final": {"particle_count": 548},
        },
        "performance": {"mean_rtx_fps": 80.0},
        "hard_runtime_errors": [],
    }
    report.write_text(
        json.dumps(
            {
                "overall_status": "pass",
                "required_cold_runs": 3,
                "runs": [run, run, run],
            }
        ),
        encoding="utf-8",
    )
    fixture = evidence / "gpu_pbd_static_fixture.json"
    fixture.write_text(
        json.dumps(
            {
                "particle_count": 548,
                "particle_parameters": {
                    "initial_state": {"kind": "normalized_reference_particle_cloud"}
                },
            }
        ),
        encoding="utf-8",
    )
    points = evidence / "gpu_pbd_initial_particle_state.json"
    points.write_text(json.dumps([[0.0, 0.0, 0.02]]), encoding="utf-8")
    profile = package / "gpu_pbd_static_container_profile.json"
    profile.write_text(
        json.dumps(
            {
                "schema_version": "aan.gpu_pbd_static_container_profile.v1",
                "entrypoint": "asset.usd",
                "entry_prim": "/World/GraduatedCylinder250ml",
                "role": "gpu_pbd_static_container",
                "claim": "gpu_pbd_static_container",
                "collision": {
                    "strategy": "source_derived_low_vertex_gpu_convex_partition",
                    "source_derived_not_primitive_proxy": True,
                    "piece_approximation": "convexDecomposition",
                },
                "promotion": {
                    "status": "qualified",
                    "report": str(report.relative_to(package)),
                    "report_sha256": _digest(report),
                    "fixture": str(fixture.relative_to(package)),
                    "fixture_sha256": _digest(fixture),
                    "initial_particle_state": str(points.relative_to(package)),
                    "initial_particle_state_sha256": _digest(points),
                    "cold_runs": 3,
                    "runtime": "isaac41",
                },
                "claim_boundary": "Static containment only.",
            }
        ),
        encoding="utf-8",
    )
    manifest = evidence / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "aan.source_bound_package_manifest.v1",
                "package_id": "graduated-cylinder-250ml.gpu-pbd-static.r1",
                "overall_status": "pass",
                "entrypoints": {
                    "root_usd": "asset.usd",
                    "asset_entry_prim": "/World/GraduatedCylinder250ml",
                },
                "gpu_pbd_static_container": {
                    "status": "qualified",
                    "profile": profile.name,
                    "report": str(report.relative_to(package)),
                    "report_sha256": _digest(report),
                    "fixture": str(fixture.relative_to(package)),
                    "fixture_sha256": _digest(fixture),
                    "initial_particle_state": str(points.relative_to(package)),
                    "initial_particle_state_sha256": _digest(points),
                    "cold_runs": 3,
                    "runtime": "isaac41",
                },
                "promotion": {
                    "allowed": True,
                    "claim": "gpu_pbd_static_container",
                },
            }
        ),
        encoding="utf-8",
    )
    return package, manifest


def test_loads_qualified_gpu_pbd_container_without_consumer_physics_patch(
    tmp_path: Path,
) -> None:
    package, manifest = _write_gpu_pbd_static_container_handoff(tmp_path)

    handoff = load_gpu_pbd_static_container_handoff(package, manifest)
    source = handoff.to_local_usd_asset_source(
        asset_id="graduated-cylinder-250ml-gpu-pbd",
        license="internal",
    )

    assert handoff.particle_count == 548
    assert handoff.collision_strategy == (
        "source_derived_low_vertex_gpu_convex_partition"
    )
    assert source.role == "rigid_object"
    assert source.upstream_package is not None
    assert source.upstream_package.metadata["consumer_physics_patch_allowed"] is False


def test_gpu_pbd_container_handoff_rejects_tampered_qualification(
    tmp_path: Path,
) -> None:
    package, manifest = _write_gpu_pbd_static_container_handoff(tmp_path)
    report = package / "evidence/gpu_pbd_static_qualification_report.json"
    report.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ConvertAssetHandoffError, match="SHA-256"):
        load_gpu_pbd_static_container_handoff(package, manifest)

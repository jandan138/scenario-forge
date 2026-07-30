from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
import yaml

from scenario_forge.assets.source import LocalUSDAssetSource
from scenario_forge.core.scenario import ScenarioSpec
from tests.test_scenario_spec import _scenario_mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/generate_scientific_workbench_background_variants.py"
BASE_SPEC = REPO_ROOT / "examples/scientific_workbench/bimanual_pour/scenario.yaml"


def test_variant_spec_changes_only_background_identity_and_package_id() -> None:
    module = _load_module()
    base = yaml.safe_load(BASE_SPEC.read_text(encoding="utf-8"))
    spec = module.load_scenario_spec(BASE_SPEC)

    variant = module.make_variant_spec(
        spec,
        candidate_id="scientific_environment_084",
    )

    base_mapping = spec.to_mapping()
    variant_mapping = variant.to_mapping()
    assert variant_mapping["scenario_id"] == ("scientific_workbench_bimanual_pour_env_084")
    assert variant_mapping["scene"]["asset_id"] == "scientific_environment_084"
    assert variant_mapping["scene"]["pose"] == base["scene"]["pose"]
    assert variant_mapping["objects"] == base_mapping["objects"]
    assert variant_mapping["robot"] == base_mapping["robot"]
    assert variant_mapping["steps"] == base_mapping["steps"]
    assert variant_mapping["success"] == base_mapping["success"]


def test_variant_generator_stays_simulator_and_converter_neutral() -> None:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    forbidden = {
        name
        for name in imported
        if name == "pxr"
        or name.startswith("pxr.")
        or name == "omni"
        or name.startswith("omni.")
        or name == "isaacsim"
        or name.startswith("isaacsim.")
    }
    assert forbidden == set()


def test_load_admitted_backgrounds_requires_pass_visual_static_packages(
    tmp_path: Path,
) -> None:
    module = _load_module()
    package_root = tmp_path / "packages"
    package = package_root / "scientific_environment_081"
    package.mkdir(parents=True)
    asset = package / "asset.usd"
    asset.write_bytes(b"#usda 1.0\n")
    source = tmp_path / "lab_081.usd"
    source.write_bytes(b"source")
    source_sha = module.file_sha256(source)
    manifest = {
        "schema_version": "asset_application_normalizer.v1",
        "asset_id": "scientific_environment_081",
        "asset_role": "visual_static_environment",
        "overall_status": "pass",
        "blocked_reasons": [],
        "source": {"sha256": source_sha.removeprefix("sha256:")},
        "entrypoints": {
            "root_usd": "asset.usd",
            "default_prim": "World",
            "asset_entry_prim": "/World",
            "asset_scope_prims": ["/World"],
            "consumer_profile": "scenario-forge",
        },
        "physics_closure": {
            "physical_frame": {
                "package": {"meters_per_unit": 0.001},
                "scope_bounds": [
                    {
                        "package_world_bound_m": {
                            "min": [-1.0, -1.0, 0.0],
                            "max": [1.0, 1.0, 2.0],
                        }
                    }
                ],
            }
        },
        "visual_preservation_fingerprint": {
            "package_after_role": {
                "scope_world_transforms": {
                    "/World": [
                        [1.0, 0.0, 0.0, 0.0],
                        [0.0, 1.0, 0.0, 0.0],
                        [0.0, 0.0, 1.0, 0.0],
                        [0.0, 0.0, 0.0, 1.0],
                    ]
                }
            }
        },
    }
    (package / "evidence").mkdir()
    (package / "evidence" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    request = {
        "request_id": "scientific_environment_visual_static_test",
        "target": {
            "runtime_profile": "isaac41",
            "asset_role": "visual_static_environment",
        },
        "producer_source_updates": {"revision": "producer-revision-test"},
        "items": [
            {
                "candidate_id": "scientific_environment_081",
                "source_usd": str(source),
                "source_sha256": source_sha.removeprefix("sha256:"),
                "source_scope": "/World",
                "required_return": {"overall_status": "pass"},
            }
        ],
    }
    request_path = tmp_path / "convertasset_batch_admission.yaml"
    request_path.write_text(yaml.safe_dump(request, sort_keys=False), encoding="utf-8")

    candidates = module.load_admitted_backgrounds(
        request_path,
        package_root,
    )

    assert len(candidates) == 1
    assert candidates[0].candidate_id == "scientific_environment_081"
    assert candidates[0].package_dir == package
    assert candidates[0].source_usd == source
    assert candidates[0].meters_per_unit == pytest.approx(0.001)
    assert candidates[0].physical_bounds_m == ((-1.0, -1.0, 0.0), (1.0, 1.0, 2.0))


def test_consumer_facade_transform_uses_package_not_raw_source(tmp_path: Path) -> None:
    module = _load_module()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "visual_preservation_fingerprint": {
                    "raw_source": {
                        "scope_world_transforms": {
                            "/world": [
                                [1.0, 0.0, 0.0, 0.0],
                                [0.0, 1.0, 0.0, 0.0],
                                [0.0, 0.0, 1.0, 0.0],
                                [100.0, 200.0, 300.0, 1.0],
                            ]
                        }
                    },
                    "package_after_role": {
                        "scope_world_transforms": {
                            "/World": [
                                [0.5, 0.0, 0.0, 0.0],
                                [0.0, 0.5, 0.0, 0.0],
                                [0.0, 0.0, 0.5, 0.0],
                                [1.0, 2.0, 3.0, 1.0],
                            ]
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    assert module._source_root_transform(
        manifest_path,
        candidate_id="scientific_environment_3fo4k5c9jd44",
    ) == ((0.5, 0.5, 0.5), (1.0, 2.0, 3.0), 0.0)


def test_blender_root_basis_yaw_is_preserved_without_negative_scale(
    tmp_path: Path,
) -> None:
    module = _load_module()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "visual_preservation_fingerprint": {
                    "package_after_role": {
                        "scope_world_transforms": {
                            "/World": [
                                [-1.0, 0.0, 0.0, 0.0],
                                [0.0, -1.0, 0.0, 0.0],
                                [0.0, 0.0, 1.0, 0.0],
                                [0.0, 0.0, 0.0, 1.0],
                            ]
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    scale, translate, yaw = module._source_root_transform(
        manifest_path,
        candidate_id="scientific_environment_code_room_example4_v1",
    )

    assert scale == pytest.approx((1.0, 1.0, 1.0))
    assert translate == pytest.approx((0.0, 0.0, 0.0))
    assert abs(abs(yaw) - 180.0) < 1e-9


def test_world_facade_survives_real_package_and_genmanip_export(tmp_path: Path) -> None:
    module = _load_module()
    facade_asset_id = "scientific_environment_facade"
    facade_usd = tmp_path / "facade" / "asset.usda"
    facade_usd.parent.mkdir()
    facade_usd.write_text(
        '''#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{
    def Scope "Looks"
    {
        def Material "TableMat" {}
        def Material "GlassFlask" {}
        def Material "GlassCylinder" {}
    }
    def Xform "table" {}
    def Xform "conical_bottle03" {}
    def Xform "graduated_cylinder_03" {}
    def Xform "background_fixture" {}
    def Xform "facade_room_geometry"
    {
        custom string scenarioForge:facade = "complete-room"
    }
}
''',
        encoding="utf-8",
    )
    base = ScenarioSpec.from_mapping(_scenario_mapping())
    variant = module.make_variant_spec(base, facade_asset_id)
    source = LocalUSDAssetSource(
        asset_id=facade_asset_id,
        source_usd=facade_usd,
        role="environment",
        license="LicenseRef-Internal-Restricted",
        source_uri="restricted-environment://restricted/test/facade",
        redistributable=False,
    )
    # The small source fixture also satisfies the legacy fixture objects; this
    # keeps the test focused on the scene reference path rather than physics.
    compiled = module.compile_scenario_package(
        variant,
        {
            facade_asset_id: source,
            "scientific_workbench_environment": LocalUSDAssetSource(
                asset_id="scientific_workbench_environment",
                source_usd=facade_usd,
                role="environment",
                license="CC-BY-NC-4.0",
                source_uri="example://legacy-fixture",
                redistributable=False,
            ),
        },
        tmp_path / "package",
    )

    exported = module.export_genmanip_collected_package(compiled.package_root)
    scene = (
        exported.output_dir
        / "assets"
        / "scene_usds"
        / "scenario_forge"
        / variant.scenario_id
        / "scene.usda"
    ).read_text(encoding="utf-8")
    facade_copy = (
        exported.output_dir
        / "assets"
        / "scene_usds"
        / "scenario_forge"
        / variant.scenario_id
        / "source_bundle"
        / facade_asset_id
        / "asset.usda"
    )

    assert f"source_bundle/{facade_asset_id}/asset.usda@</World>" in scene
    assert 'def Xform "facade_room_geometry"' in facade_copy.read_text(encoding="utf-8")


def test_non_world_source_scope_requires_convertasset_consumer_facade(tmp_path: Path) -> None:
    module = _load_module()
    source = tmp_path / "world.usda"
    source.write_text("#usda 1.0\n", encoding="utf-8")
    request_path = tmp_path / "admission.yaml"
    request_path.write_text(
        yaml.safe_dump(
            {
                "target": {
                    "runtime_profile": "isaac41",
                    "asset_role": "visual_static_environment",
                },
                "producer_source_updates": {"revision": "r1"},
                "items": [
                    {
                        "candidate_id": "scientific_environment_3fo4k5c9jd44",
                        "source_usd": str(source),
                        "source_sha256": module.file_sha256(source).removeprefix("sha256:"),
                        "source_scope": "/world",
                        "required_return": {"overall_status": "pass"},
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="consumer facade scope /World"):
        module.load_admitted_backgrounds(request_path, tmp_path / "packages")


def test_background_placement_is_instance_only_and_fits_visual_envelope() -> None:
    module = _load_module()
    spec = module.load_scenario_spec(BASE_SPEC)
    candidate = module.BackgroundCandidate(
        candidate_id="scientific_environment_081",
        package_dir=Path("/tmp/package"),
        manifest_path=Path("/tmp/manifest.json"),
        source_usd=Path("/tmp/source.usd"),
        source_sha256="a" * 64,
        source_scope="/World",
        producer_revision="r1",
        meters_per_unit=0.001,
        root_scale_xyz=(1.0, 1.0, 1.0),
        root_translate_xyz=(0.0, 0.0, 0.0),
        physical_bounds_m=((-1.0, -2.0, 0.0), (1.0, 2.0, 4.0)),
        authored_camera=None,
    )

    placement = module.background_placement(spec, candidate)
    variant = module.make_variant_spec(
        spec,
        candidate.candidate_id,
        scene_pose=placement["scene_pose"],
    )

    assert placement["effective_scale"] == pytest.approx(0.001)
    assert variant.objects == spec.objects
    assert variant.robot == spec.robot
    assert variant.scene.pose is not None
    assert variant.scene.pose.scale_xyz == pytest.approx((0.001,) * 3)


def test_workspace_anchor_maps_background_tabletop_to_fixed_ebench_surface() -> None:
    module = _load_module()
    spec = module.load_scenario_spec(BASE_SPEC)
    candidate = module.BackgroundCandidate(
        candidate_id="scientific_environment_084",
        package_dir=Path("/tmp/package"),
        manifest_path=Path("/tmp/manifest.json"),
        source_usd=Path("/tmp/source.usd"),
        source_sha256="a" * 64,
        source_scope="/World",
        producer_revision="r1",
        meters_per_unit=1.0,
        root_scale_xyz=(0.001, 0.001, 0.001),
        root_translate_xyz=(0.0, 0.0, 0.0),
        physical_bounds_m=((-15.0, -13.0, -2.0), (16.0, 13.0, 2.0)),
        authored_camera=None,
    )

    anchor = module.workspace_anchor_for(candidate)
    placement = module.background_placement(spec, candidate)
    pose = placement["scene_pose"]
    scale = placement["effective_scale"]
    root_translate = placement["source_root_translate_xyz"]
    # The selected source tabletop top center must land on the existing eBench
    # tabletop frame; this is a room-instance transform, not a workspace edit.
    mapped = [
        pose["xyz"][index]
        + scale
        * (anchor.source_anchor_xyz_m[index] / candidate.meters_per_unit - root_translate[index])
        for index in range(3)
    ]
    assert mapped == pytest.approx(list(anchor.target_xyz))

    variant = module.make_variant_spec(
        spec,
        candidate.candidate_id,
        scene_pose=pose,
        inactive_prim_paths=anchor.hide_prim_paths,
    )
    assert variant.scene.inactive_prim_paths == anchor.hide_prim_paths


def test_reviewed_084_anchor_replaces_one_complete_source_island() -> None:
    module = _load_module()
    anchor = module.workspace_anchor_for(
        module.BackgroundCandidate(
            candidate_id="scientific_environment_084",
            package_dir=Path("/tmp/package"),
            manifest_path=Path("/tmp/manifest.json"),
            source_usd=Path("/tmp/source.usd"),
            source_sha256="a" * 64,
            source_scope="/World",
            producer_revision="r1",
            meters_per_unit=1.0,
            root_scale_xyz=(0.001, 0.001, 0.001),
            root_translate_xyz=(0.0, 0.0, 0.0),
            physical_bounds_m=((-15.0, -13.0, -2.0), (16.0, 13.0, 2.0)),
            authored_camera=None,
        )
    )

    assert anchor is not None
    assert anchor.source_prim_path == "/World/group_078/mesh_027"
    assert anchor.hide_prim_paths == ("/World/group_078",)
    assert anchor.note == "central wet-lab island assembly top surface"


@pytest.mark.parametrize(
    "candidate_id",
    ["scientific_environment_067", "scientific_environment_081"],
)
def test_rejected_composition_candidates_do_not_receive_workspace_anchors(
    candidate_id: str,
) -> None:
    module = _load_module()
    candidate = module.BackgroundCandidate(
        candidate_id=candidate_id,
        package_dir=Path("/tmp/package"),
        manifest_path=Path("/tmp/manifest.json"),
        source_usd=Path("/tmp/source.usd"),
        source_sha256="a" * 64,
        source_scope="/World",
        producer_revision="r1",
        meters_per_unit=1.0,
        root_scale_xyz=(1.0, 1.0, 1.0),
        root_translate_xyz=(0.0, 0.0, 0.0),
        physical_bounds_m=((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0)),
        authored_camera=None,
    )

    assert module.workspace_anchor_for(candidate) is None


def test_workspace_profile_uses_declared_source_composed_metric_scale(
    tmp_path: Path,
) -> None:
    module = _load_module()
    candidate = _workspace_profile_candidate(
        "scientific_environment_083",
        meters_per_unit=0.001,
        root_scale_xyz=(0.001, 0.001, 0.001),
        physical_bounds_m=((-0.008, -0.004, 0.0), (0.009, 0.005, 0.007)),
    )
    manifest_path = _write_workspace_profile_handoff(
        tmp_path,
        candidate,
        status="profiled",
        anchor_xyz_m=(2.8, -2.59, 1.793),
        inactive_roots=(
            "/World/group_025",
            "/World/group_026",
            "/World/group_027",
        ),
        optional_inactive_paths=("/World/mesh_164", "/World/mesh_167"),
        source_composed_meters_per_unit=1.0,
    )

    profiles = module.load_workspace_profiles(manifest_path, (candidate,))
    profile = profiles[candidate.candidate_id]

    assert profile.status == "profiled"
    assert profile.raw_anchor_xyz_m == pytest.approx((2.8, -2.59, 1.793))
    assert profile.anchor is not None
    assert profile.anchor.source_anchor_xyz_m == pytest.approx((2.8, -2.59, 1.793))
    assert profile.anchor.source_composed_meters_per_unit == pytest.approx(1.0)
    assert profile.anchor.hide_prim_paths == (
        "/World/group_025",
        "/World/group_026",
        "/World/group_027",
    )
    # Optional drain decals are evidence, not a default anonymous deletion.
    assert profile.optional_inactive_prim_paths == (
        "/World/mesh_164",
        "/World/mesh_167",
    )

    spec = module.load_scenario_spec(BASE_SPEC)
    placement = module.background_placement(spec, candidate, anchor=profile.anchor)
    raw_anchor = profile.raw_anchor_xyz_m
    rotated_anchor = module._rotate_z(tuple(raw_anchor), placement["composition_yaw_deg"])
    mapped = [
        placement["scene_pose"]["xyz"][index]
        + placement["scene_pose"]["scale_xyz"][index]
        * rotated_anchor[index]
        / candidate.root_scale_xyz[index]
        for index in range(3)
    ]
    assert placement["composition_yaw_deg"] == pytest.approx(90.0)
    assert mapped == pytest.approx(list(module.EBENCH_WORKSPACE_TARGET_XYZ))


def test_workspace_profile_preserves_declared_workspace_metric_scale(
    tmp_path: Path,
) -> None:
    module = _load_module()
    candidate = _workspace_profile_candidate(
        "scientific_environment_066",
        meters_per_unit=0.001,
        physical_bounds_m=(
            (-0.3777394445, -0.2680592239, -0.0474216658),
            (0.5168325109, 0.1650115667, 0.2238658877),
        ),
    )
    source_composed_meters_per_unit = 1.0 / 19.15
    manifest_path = _write_workspace_profile_handoff(
        tmp_path,
        candidate,
        status="profiled",
        anchor_xyz_m=(-18.96, 4.23, 18.194),
        inactive_roots=("/World/group_111",),
        source_composed_meters_per_unit=source_composed_meters_per_unit,
    )

    profile = module.load_workspace_profiles(manifest_path, (candidate,))[candidate.candidate_id]
    assert profile.anchor is not None
    assert profile.anchor.source_anchor_xyz_m == pytest.approx(
        tuple(value * source_composed_meters_per_unit for value in (-18.96, 4.23, 18.194))
    )

    placement = module.background_placement(
        module.load_scenario_spec(BASE_SPEC),
        candidate,
        anchor=profile.anchor,
    )
    # A profile clearance is defined for the fixed eBench footprint.  Fitting
    # its room into an arbitrary visual envelope would silently shrink that
    # cleared footprint, so the declared source metric scale is preserved.
    assert placement["fit_factor"] == pytest.approx(1.0)
    assert placement["effective_scale"] == pytest.approx(source_composed_meters_per_unit)
    assert placement["source_bounds_m"][0] == pytest.approx(
        [
            -0.3777394445 / 0.001 * source_composed_meters_per_unit,
            -0.2680592239 / 0.001 * source_composed_meters_per_unit,
            -0.0474216658 / 0.001 * source_composed_meters_per_unit,
        ]
    )
    assert placement["source_bounds_m"][1] == pytest.approx(
        [
            0.5168325109 / 0.001 * source_composed_meters_per_unit,
            0.1650115667 / 0.001 * source_composed_meters_per_unit,
            0.2238658877 / 0.001 * source_composed_meters_per_unit,
        ]
    )
    mapped = [
        placement["scene_pose"]["xyz"][index]
        + placement["scene_pose"]["scale_xyz"][index] * (-18.96, 4.23, 18.194)[index]
        for index in range(3)
    ]
    assert mapped == pytest.approx(list(module.EBENCH_WORKSPACE_TARGET_XYZ))


def test_workspace_profile_rejects_missing_machine_readable_coordinate_mapping(
    tmp_path: Path,
) -> None:
    module = _load_module()
    candidate = _workspace_profile_candidate("scientific_environment_066")
    manifest_path = _write_workspace_profile_handoff(
        tmp_path,
        candidate,
        status="profiled",
        anchor_xyz_m=(-18.96, 4.23, 18.194),
        inactive_roots=("/World/group_111",),
        source_composed_meters_per_unit=None,
    )

    with pytest.raises(ValueError, match="coordinate_mapping"):
        module.load_workspace_profiles(manifest_path, (candidate,))


def test_workspace_zone_profiles_reuse_one_background_asset_for_multiple_packages(
    tmp_path: Path,
) -> None:
    module = _load_module()
    # The raw external source uses multiple top-level namespaces. ConvertAsset
    # must expose its admitted consolidated consumer facade at ``/World``;
    # profiles are intentionally written against that facade, not raw `/world`.
    candidate = _workspace_profile_candidate(
        "scientific_environment_3fo4k5c9jd44",
    )
    manifest_path = _write_workspace_zone_profile_handoff(
        tmp_path,
        candidate,
        zones={
            "north_island": {
                "status": "profiled",
                "anchor_xyz_su": (12.0, -3.0, 1.2),
                "inactive_roots": ("/World/group_north",),
                "optional_inactive_paths": ("/World/prop_north",),
                "yaw_deg": 0.0,
            },
            "south_bench": {
                "status": "profiled",
                "anchor_xyz_su": (-8.0, 4.0, 1.2),
                "inactive_roots": ("/World/group_south",),
                "optional_inactive_paths": ("/World/prop_south_a", "/World/prop_south_b"),
                "yaw_deg": 90.0,
            },
            "blocked_corner": {
                "status": "not_applicable",
                "not_applicable_reason": "clearance intersects loose source props",
            },
        },
    )

    zones = module.load_workspace_zone_profiles(manifest_path, (candidate,))
    selected, excluded = module.select_workspace_zone_variants((candidate,), zones)

    assert [item.variant_id for item in selected] == [
        "scientific_environment_3fo4k5c9jd44__north_island",
        "scientific_environment_3fo4k5c9jd44__south_bench",
    ]
    assert all(item.candidate.candidate_id == candidate.candidate_id for item in selected)
    assert selected[0].anchor is not None
    assert selected[0].anchor.hide_prim_paths == ("/World/group_north",)
    assert selected[0].zone.optional_inactive_prim_paths == ("/World/prop_north",)
    assert selected[1].composition_yaw_deg == pytest.approx(90.0)
    assert excluded == {
        "scientific_environment_3fo4k5c9jd44__blocked_corner": (
            "clearance intersects loose source props"
        )
    }

    spec = module.load_scenario_spec(BASE_SPEC)
    variant = module.make_variant_spec(
        spec,
        candidate.candidate_id,
        scenario_suffix="3fo4k5c9jd44_zone_north_island",
        inactive_prim_paths=selected[0].anchor.hide_prim_paths,
    )
    assert variant.scene.asset_id == candidate.candidate_id
    assert variant.scenario_id == (
        "scientific_workbench_bimanual_pour_env_3fo4k5c9jd44_zone_north_island"
    )
    assert variant.objects == spec.objects
    assert variant.robot == spec.robot
    assert variant.steps == spec.steps


def test_external_room_facade_and_zone_profile_v02_are_consumed_separately(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep the raw intake binding distinct from ConvertAsset's facade binding.

    The producer-owned facade is the source of the package, while the original
    multi-root room remains the source bound by restricted intake and zone
    profiles.  A consumer must verify both rather than pretending their hashes
    are interchangeable.
    """

    module = _load_module()
    asset_id = "scientific_environment_3fo4k5c9jd44"
    delivery_root = tmp_path / "external_room"
    raw_source = delivery_root / "source" / "3FO4K5C9JD44" / "world.usda"
    facade_source = delivery_root / "facade" / "facade.usda"
    raw_source.parent.mkdir(parents=True)
    facade_source.parent.mkdir(parents=True)
    raw_source.write_text("#usda 1.0\n# raw multi-root room\n", encoding="utf-8")
    facade_source.write_text("#usda 1.0\n# producer-owned facade\n", encoding="utf-8")
    raw_sha = module.file_sha256(raw_source).removeprefix("sha256:")
    facade_sha = module.file_sha256(facade_source).removeprefix("sha256:")

    package = delivery_root / "package"
    (package / "evidence").mkdir(parents=True)
    (package / "asset.usd").write_text("#usda 1.0\n", encoding="utf-8")
    (package / "evidence" / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "asset_application_normalizer.v1",
                "package_id": f"{asset_id}_scenario-forge_isaac41",
                "asset_id": asset_id,
                "asset_role": "visual_static_environment",
                "overall_status": "pass",
                "blocked_reasons": [],
                "source": {"sha256": facade_sha},
                "entrypoints": {
                    "root_usd": "asset.usd",
                    "default_prim": "World",
                    "asset_entry_prim": "/World",
                    "asset_scope_prims": ["/World"],
                    "consumer_profile": "scenario-forge",
                },
                "physics_closure": {
                    "physical_frame": {
                        "package": {"meters_per_unit": 1.0},
                        "scope_bounds": [
                            {
                                "package_world_bound_m": {
                                    "min": [-6.0, -7.0, -0.2],
                                    "max": [10.0, 4.0, 3.5],
                                }
                            }
                        ],
                    }
                },
                "visual_preservation_fingerprint": {
                    "package_after_role": {
                        "scope_world_transforms": {
                            "/World": [
                                [1.0, 0.0, 0.0, 0.0],
                                [0.0, 1.0, 0.0, 0.0],
                                [0.0, 0.0, 1.0, 0.0],
                                [0.0, 0.0, 0.0, 1.0],
                            ]
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (package / "evidence" / "facade_provenance.json").write_text(
        json.dumps(
            {
                "raw_source_default_prim": "/world",
                "raw_source_namespaces": ["/world", "/Root", "/Render"],
                "facade_default_prim": "World",
                "facade_scope": "/World",
                "namespace_mapping": {
                    "/world": "/World/world",
                    "/Root": "/World/Root",
                    "/Render": "/World/Render",
                },
                "raw_source_usd_relative_path": "world.usda",
                "raw_source_usd_sha256": raw_sha,
            }
        ),
        encoding="utf-8",
    )
    admission = delivery_root / "consumer_admission.yaml"
    admission.write_text(
        yaml.safe_dump(
            {
                "request_id": "external-room-facade-consumer-test",
                "target": {
                    "runtime_profile": "isaac41",
                    "asset_role": "visual_static_environment",
                },
                "producer_source_updates": {"revision": "facade-r1"},
                "items": [
                    {
                        "candidate_id": asset_id,
                        "source_usd": "source/3FO4K5C9JD44/world.usda",
                        "source_sha256": raw_sha,
                        "package_source_usd": "facade/facade.usda",
                        "package_source_sha256": facade_sha,
                        "package_dir": "package",
                        "source_scope": "/World",
                        "required_return": {"overall_status": "pass"},
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    candidates = module.load_admitted_backgrounds(admission, delivery_root)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.source_usd == raw_source
    assert candidate.source_sha256 == raw_sha
    assert candidate.package_source_usd == facade_source
    assert candidate.package_source_sha256 == facade_sha
    assert candidate.facade_provenance_path == package / "evidence" / "facade_provenance.json"

    zone_root = delivery_root / "zone_profiles"
    zone_root.mkdir()
    profile_path = zone_root / f"{asset_id}__north_bench_workspace_zone.yaml"
    profile_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "scenario-forge-convertasset-workspace-zone-profile/v0.2",
                "background_asset_id": asset_id,
                "zone_id": "north_bench",
                "status": "profiled",
                "source": {
                    "source_usd_sha256": raw_sha,
                    "consumer_facade_scope": "/World",
                    "package_manifest": "../package/evidence/manifest.json",
                    "facade_provenance": "../package/evidence/facade_provenance.json",
                },
                "producer": {
                    "repo": "ConvertAsset",
                    "revision": "zone-r1",
                    "git_commit": "a" * 40,
                },
                "coordinate_mapping": {
                    "frame": "source_composed",
                    "source_composed_meters_per_unit": 1.0,
                },
                "assembly": {
                    "replaceable_assembly_roots": ["/World/Root/bench"],
                    "anchor_prim": "/World/Root/bench",
                    "anchor_xyz_m": [0.1, 2.6, 0.9],
                },
                "inactivation": {
                    "inactive_prim_root_paths": ["/World/Root/bench"],
                },
                "workspace": {
                    "clearance_aabb_m": {
                        "min": [-1.2, 1.2, 0.0],
                        "max": [1.3, 4.0, 2.2],
                    }
                },
                "yaw": {
                    "reviewed_yaw_deg": 90.0,
                    "rotation_convention": "usd_z_up_right_handed_ccw",
                },
                "evidence_camera": {
                    "position_xyz": [0.1, 1.1, 1.5],
                    "target_xyz": [0.1, 2.6, 0.85],
                    "frame_convention": "usd_z_up_right_handed_ccw",
                    "sight_line_validation": "camera and target are clear",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    zone_manifest = zone_root / "zone_profile_manifest.json"
    zone_manifest.write_text(
        json.dumps(
            {
                "schema_version": "scenario-forge-convertasset-workspace-zone-profile-manifest/v0.2",
                "background_asset_id": asset_id,
                "source": {
                    "source_usd_sha256": raw_sha,
                    "consumer_facade_scope": "/World",
                    "package_manifest": "../package/evidence/manifest.json",
                },
                "producer": {"repo": "ConvertAsset", "revision": "zone-r1", "git_commit": "a" * 40},
                "zones": {
                    "north_bench": {"status": "profiled", "profile": profile_path.name},
                    "east_bench": {
                        "status": "not_applicable",
                        "reason": "clearance intersects retained complete furniture",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    zones = module.load_workspace_zone_profiles(zone_manifest, candidates)
    selected, excluded = module.select_workspace_zone_variants(candidates, zones)
    assert [item.variant_id for item in selected] == [f"{asset_id}__north_bench"]
    assert selected[0].anchor is not None
    assert selected[0].anchor.source_anchor_xyz_m == pytest.approx((0.1, 2.6, 0.9))
    assert selected[0].composition_yaw_deg == pytest.approx(90.0)
    assert selected[0].zone.evidence_camera_position_xyz_su == pytest.approx(
        (0.1, 1.1, 1.5)
    )
    assert selected[0].zone.evidence_camera_target_xyz_su == pytest.approx(
        (0.1, 2.6, 0.85)
    )
    assert excluded == {
        f"{asset_id}__east_bench": "clearance intersects retained complete furniture"
    }

    captured: dict[str, Path] = {}

    class _Handoff:
        def to_local_usd_asset_source(self, **_: object) -> object:
            return object()

    def _fake_load_handoff(
        _package_dir: Path,
        _manifest_path: Path,
        source_usd: Path,
        **_: object,
    ) -> _Handoff:
        captured["source_usd"] = source_usd
        return _Handoff()

    monkeypatch.setattr(module, "load_convert_asset_package_handoff", _fake_load_handoff)
    module._load_background_source(candidate)
    assert captured["source_usd"] == facade_source


def test_external_room_facade_provenance_must_bind_raw_source_hash(tmp_path: Path) -> None:
    module = _load_module()
    asset_id = "scientific_environment_3fo4k5c9jd44"
    root = tmp_path / "delivery"
    source = root / "source.usda"
    facade = root / "facade.usda"
    source.parent.mkdir()
    source.write_text("raw", encoding="utf-8")
    facade.write_text("facade", encoding="utf-8")
    package = root / "package"
    (package / "evidence").mkdir(parents=True)
    (package / "asset.usd").write_text("#usda 1.0\n", encoding="utf-8")
    facade_sha = module.file_sha256(facade).removeprefix("sha256:")
    (package / "evidence" / "manifest.json").write_text(
        json.dumps(
            {
                "asset_id": asset_id,
                "asset_role": "visual_static_environment",
                "overall_status": "pass",
                "blocked_reasons": [],
                "source": {"sha256": facade_sha},
                "entrypoints": {
                    "root_usd": "asset.usd",
                    "default_prim": "World",
                    "asset_entry_prim": "/World",
                    "asset_scope_prims": ["/World"],
                    "consumer_profile": "scenario-forge",
                },
                "physics_closure": {
                    "physical_frame": {
                        "package": {"meters_per_unit": 1.0},
                        "scope_bounds": [
                            {"package_world_bound_m": {"min": [-1, -1, 0], "max": [1, 1, 2]}}
                        ],
                    }
                },
                "visual_preservation_fingerprint": {
                    "package_after_role": {
                        "scope_world_transforms": {
                            "/World": [
                                [1.0, 0.0, 0.0, 0.0],
                                [0.0, 1.0, 0.0, 0.0],
                                [0.0, 0.0, 1.0, 0.0],
                                [0.0, 0.0, 0.0, 1.0],
                            ]
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (package / "evidence" / "facade_provenance.json").write_text(
        json.dumps(
            {
                "facade_default_prim": "World",
                "facade_scope": "/World",
                "raw_source_usd_sha256": "b" * 64,
            }
        ),
        encoding="utf-8",
    )
    admission = root / "admission.yaml"
    admission.write_text(
        yaml.safe_dump(
            {
                "target": {
                    "runtime_profile": "isaac41",
                    "asset_role": "visual_static_environment",
                },
                "producer_source_updates": {"revision": "r1"},
                "items": [
                    {
                        "candidate_id": asset_id,
                        "source_usd": "source.usda",
                        "source_sha256": module.file_sha256(source).removeprefix("sha256:"),
                        "package_source_usd": "facade.usda",
                        "package_source_sha256": facade_sha,
                        "package_dir": "package",
                        "source_scope": "/World",
                        "required_return": {"overall_status": "pass"},
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="facade provenance raw source hash disagrees"):
        module.load_admitted_backgrounds(admission, root)


def test_zone_selection_rejects_conflicting_asset_and_variant_filters(
    tmp_path: Path,
) -> None:
    module = _load_module()
    candidate = _workspace_profile_candidate("scientific_environment_901")
    other_candidate = _workspace_profile_candidate("scientific_environment_902")
    manifest_path = _write_workspace_zone_profile_handoff(
        tmp_path,
        candidate,
        zones={
            "north_island": {
                "status": "profiled",
                "anchor_xyz_su": (12.0, -3.0, 1.2),
                "inactive_roots": ("/World/group_north",),
                "yaw_deg": 0.0,
            },
        },
    )
    zones = module.load_workspace_zone_profiles(manifest_path, (candidate, other_candidate))

    with pytest.raises(ValueError, match="does not belong to background asset"):
        module.select_workspace_zone_variants(
            (candidate, other_candidate),
            zones,
            background_asset_id=other_candidate.candidate_id,
            variant_id="scientific_environment_901__north_island",
        )


def test_explicit_zone_asset_selection_rejects_no_eligible_zones(tmp_path: Path) -> None:
    module = _load_module()
    candidate = _workspace_profile_candidate("scientific_environment_901")
    manifest_path = _write_workspace_zone_profile_handoff(
        tmp_path,
        candidate,
        zones={
            "blocked_corner": {
                "status": "not_applicable",
                "not_applicable_reason": "clearance intersects retained source furniture",
            },
        },
    )
    zones = module.load_workspace_zone_profiles(manifest_path, (candidate,))

    with pytest.raises(ValueError, match="has no eligible workspace zones"):
        module.select_workspace_zone_variants(
            (candidate,),
            zones,
            background_asset_id=candidate.candidate_id,
        )


def test_workspace_zone_quarantines_ambiguous_nonzero_v02_yaw(tmp_path: Path) -> None:
    module = _load_module()
    candidate = _workspace_profile_candidate("scientific_environment_901")
    manifest_path = _write_workspace_zone_profile_handoff(
        tmp_path,
        candidate,
        zones={
            "north_bench": {
                "status": "profiled",
                "anchor_xyz_su": (1.0, 2.0, 0.9),
                "inactive_roots": ("/World/north_bench",),
                "yaw_deg": 90.0,
            },
        },
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    profile_path = manifest_path.parent / manifest["zones"]["north_bench"]["profile"]
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile.pop("composition")
    profile["yaw"] = {"reviewed_yaw_deg": 90.0}
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")

    zones = module.load_workspace_zone_profiles(manifest_path, (candidate,))
    selected, excluded = module.select_workspace_zone_variants((candidate,), zones)

    assert selected == ()
    assert excluded == {
        "scientific_environment_901__north_bench": (
            "non-zero reviewed yaw lacks explicit USD +Z right-handed convention"
        )
    }


@pytest.mark.parametrize(
    ("candidate_id", "expected"),
    [
        ("scientific_environment_084", True),
        ("scientific_environment_3fo4k5c9jd44", True),
        ("scientific_environment_room-a", False),
        ("scientific_environment_3fo4k5c9jd44__north_island", False),
        ("scientific_environment_", False),
    ],
)
def test_background_asset_id_validation_allows_safe_external_room_ids(
    candidate_id: str,
    expected: bool,
) -> None:
    module = _load_module()

    assert module.is_background_asset_id(candidate_id) is expected


def test_external_intake_replaces_legacy_background_provenance(tmp_path: Path) -> None:
    module = _load_module()
    candidate = _workspace_profile_candidate("scientific_environment_3fo4k5c9jd44")
    intake_path = tmp_path / "intake.yaml"
    intake_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "scenario-forge-external-environment-intake/v0.1",
                "asset_id": candidate.candidate_id,
                "asset_role": "visual_static_environment",
                "license": "LicenseRef-Internal-Restricted",
                "redistributable": False,
                "attribution": ["Restricted external environment source."],
                "source": {
                    "usd_sha256": candidate.source_sha256,
                    "tree_sha256": "b" * 64,
                },
                "archive": {"sha256": "c" * 64},
                "provenance": {
                    "visibility": "restricted",
                    "internal_reference": "restricted/room/3FO4K5C9JD44",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    attached = module.apply_external_environment_intake((candidate,), intake_path)

    assert attached[0].candidate_id == candidate.candidate_id
    assert attached[0].license == "LicenseRef-Internal-Restricted"
    assert attached[0].redistributable is False
    assert attached[0].attribution == (
        "Restricted external environment source.",
        "Restricted extracted source tree SHA-256: " + "b" * 64 + ".",
        "Restricted source archive SHA-256: " + "c" * 64 + ".",
    )
    assert attached[0].source_uri == "restricted-environment://restricted/room/3FO4K5C9JD44"
    assert attached[0].external_tree_sha256 == "b" * 64
    assert attached[0].external_archive_sha256 == "c" * 64
    assert attached[0].restricted_provenance_reference == "restricted/room/3FO4K5C9JD44"


def test_generated_intake_binds_code_as_room_background_provenance(
    tmp_path: Path,
) -> None:
    module = _load_module()
    candidate = _workspace_profile_candidate(
        "scientific_environment_code_room_example4_v1"
    )
    intake_path = tmp_path / "generated_intake.yaml"
    intake_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": (
                    "scenario-forge-generated-environment-intake/v0.1"
                ),
                "asset_id": candidate.candidate_id,
                "asset_role": "visual_static_environment",
                "license": "LicenseRef-Internal-Generated",
                "redistributable": False,
                "attribution": ["Code-as-Room generated environment."],
                "producer": {
                    "repo": "Code-as-Room",
                    "revision": "a" * 40,
                    "run_id": "run_example4",
                    "manifest_sha256": "b" * 64,
                },
                "source": {
                    "usd_sha256": candidate.source_sha256,
                    "declared_closure_sha256": "c" * 64,
                },
                "provenance": {
                    "kind": "generated_blender_room",
                    "visibility": "internal",
                    "source_uri": (
                        "generated-environment://code-as-room/"
                        + "a" * 40
                        + "/run_example4"
                    ),
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    attached = module.apply_generated_environment_intake(
        (candidate,),
        intake_path,
    )

    assert attached[0].license == "LicenseRef-Internal-Generated"
    assert attached[0].redistributable is False
    assert attached[0].source_uri.startswith(
        "generated-environment://code-as-room/"
    )
    assert attached[0].generated_closure_sha256 == "c" * 64
    assert attached[0].generated_manifest_sha256 == "b" * 64
    assert attached[0].generated_producer_revision == "a" * 40
    assert attached[0].generated_run_id == "run_example4"
    module.validate_generation_background_provenance(attached)


def test_nonlegacy_background_requires_restricted_intake_before_generation() -> None:
    module = _load_module()
    candidate = _workspace_profile_candidate("scientific_environment_3fo4k5c9jd44")

    with pytest.raises(ValueError, match="external or generated intake"):
        module.validate_generation_background_provenance((candidate,))

    module.validate_generation_background_provenance(
        (
            module.replace(
                candidate,
                license="LicenseRef-Internal-Restricted",
                attribution=("Restricted external environment source.",),
                redistributable=False,
                source_uri="restricted-environment://restricted/room/3FO4K5C9JD44",
                external_tree_sha256="b" * 64,
                external_archive_sha256="c" * 64,
                restricted_provenance_reference="restricted/room/3FO4K5C9JD44",
            ),
        )
    )


def test_main_generates_independent_packages_for_profiled_zones(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    candidate = _workspace_profile_candidate("scientific_environment_901")
    zone_manifest = _write_workspace_zone_profile_handoff(
        tmp_path / "profiles",
        candidate,
        zones={
            "north_island": {
                "status": "profiled",
                "anchor_xyz_su": (12.0, -3.0, 1.2),
                "inactive_roots": ("/World/group_north",),
                "optional_inactive_paths": ("/World/prop_north",),
                "yaw_deg": 0.0,
            },
            "south_bench": {
                "status": "profiled",
                "anchor_xyz_su": (-8.0, 4.0, 1.2),
                "inactive_roots": ("/World/group_south",),
                "optional_inactive_paths": ("/World/prop_south_a", "/World/prop_south_b"),
                "yaw_deg": 90.0,
            },
            "blocked_corner": {
                "status": "not_applicable",
                "not_applicable_reason": "clearance intersects loose source props",
            },
        },
    )
    compiled_specs = []

    def fake_compile(spec, sources, package_root):
        del sources
        package_root.mkdir(parents=True)
        compiled_specs.append(spec)
        return SimpleNamespace(package_root=package_root)

    monkeypatch.setattr(module, "load_admitted_backgrounds", lambda *_: (candidate,))
    monkeypatch.setattr(module, "load_existing_package_sources", lambda *_: {})
    monkeypatch.setattr(module, "_validate_base_inputs", lambda *_: None)
    monkeypatch.setattr(module, "_load_background_source", lambda *_: object())
    monkeypatch.setattr(module, "compile_scenario_package", fake_compile)
    monkeypatch.setattr(
        module,
        "export_genmanip_collected_package",
        lambda package_root: SimpleNamespace(output_dir=package_root),
    )
    monkeypatch.setattr(module, "_configure_background_preview", lambda *_args, **_kwargs: None)

    output_root = tmp_path / "variants"
    assert (
        module.main(
            [
                "--base-package",
                str(tmp_path / "base"),
                "--admission",
                str(tmp_path / "admission.yaml"),
                "--background-root",
                str(tmp_path / "packages"),
                "--workspace-zone-profiles",
                str(zone_manifest),
                "--out",
                str(output_root),
            ]
        )
        == 0
    )

    generated = json.loads((output_root / "background_variants_manifest.json").read_text())
    assert generated["schema_version"] == (
        "scenario-forge-scientific-workbench-background-variants/v0.2"
    )
    assert generated["variant_count"] == 2
    assert generated["candidate_count"] == 1
    assert [entry["variant_id"] for entry in generated["variants"]] == [
        "scientific_environment_901__north_island",
        "scientific_environment_901__south_bench",
    ]
    assert generated["excluded_workspace_variants"] == {
        "scientific_environment_901__blocked_corner": (
            "clearance intersects loose source props"
        )
    }
    assert [spec.scene.asset_id for spec in compiled_specs] == [candidate.candidate_id] * 2
    assert [spec.scene.inactive_prim_paths for spec in compiled_specs] == [
        ("/World/group_north", "/World/prop_north"),
        ("/World/group_south", "/World/prop_south_a", "/World/prop_south_b"),
    ]
    assert [spec.scenario_id for spec in compiled_specs] == [
        "scientific_workbench_bimanual_pour_env_901_zone_north_island",
        "scientific_workbench_bimanual_pour_env_901_zone_south_bench",
    ]


def test_workspace_profiles_override_legacy_anchor_and_exclude_not_applicable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    candidate_059 = _workspace_profile_candidate("scientific_environment_059")
    candidate_081 = _workspace_profile_candidate("scientific_environment_081")
    manifest_059 = _write_workspace_profile_handoff(
        tmp_path / "profile_059",
        candidate_059,
        status="profiled",
        anchor_xyz_m=(42.59, -5.92, 28.466),
        inactive_roots=(
            "/World/group_063",
            "/World/group_064",
            "/World/group_073",
            "/World/group_241",
        ),
    )
    _write_workspace_profile_handoff(
        tmp_path / "profile_081",
        candidate_081,
        status="not_applicable",
        not_applicable_reason="no complete source island is available",
    )
    combined_root = tmp_path / "combined"
    combined_root.mkdir()
    for handoff in (manifest_059, tmp_path / "profile_081" / "workspace_profiles_manifest.json"):
        payload = json.loads(handoff.read_text(encoding="utf-8"))
        candidate_id = next(iter(payload["candidates"]))
        source_profile = handoff.parent / payload["candidates"][candidate_id]["profile"]
        target_profile = combined_root / source_profile.name
        target_profile.write_text(source_profile.read_text(encoding="utf-8"), encoding="utf-8")
        payload["candidates"][candidate_id]["profile"] = target_profile.name
        if (combined_root / "workspace_profiles_manifest.json").is_file():
            combined = json.loads(
                (combined_root / "workspace_profiles_manifest.json").read_text(encoding="utf-8")
            )
            combined["candidates"].update(payload["candidates"])
            payload = combined
        (combined_root / "workspace_profiles_manifest.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    profiles = module.load_workspace_profiles(
        combined_root / "workspace_profiles_manifest.json",
        (candidate_059, candidate_081),
    )

    anchor = module.workspace_anchor_for(candidate_059, profiles)
    assert anchor is not None
    assert anchor.source_anchor_xyz_m == pytest.approx((42.59, -5.92, 28.466))
    assert anchor.hide_prim_paths == (
        "/World/group_063",
        "/World/group_064",
        "/World/group_073",
        "/World/group_241",
    )

    selected, excluded = module.select_workspace_candidates(
        (candidate_059, candidate_081),
        profiles,
    )
    assert [candidate.candidate_id for candidate in selected] == ["scientific_environment_059"]
    assert excluded == {"scientific_environment_081": "no complete source island is available"}
    with pytest.raises(ValueError, match="no complete source island"):
        module.select_workspace_candidates(
            (candidate_059, candidate_081),
            profiles,
            candidate_id="scientific_environment_081",
        )


def test_workspace_profile_rejects_source_hash_mismatch(tmp_path: Path) -> None:
    module = _load_module()
    candidate = _workspace_profile_candidate("scientific_environment_066")
    manifest_path = _write_workspace_profile_handoff(
        tmp_path,
        candidate,
        status="profiled",
        anchor_xyz_m=(-18.96, 4.23, 18.194),
        inactive_roots=("/World/group_111",),
    )
    profile_path = tmp_path / "scientific_environment_066_workspace_profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile["source"]["source_sha256"] = "b" * 64
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="source hash"):
        module.load_workspace_profiles(manifest_path, (candidate,))


def test_workspace_focus_preview_uses_post_reset_runtime_workspace_bounds(
    tmp_path: Path,
) -> None:
    module = _load_module()
    collected_root = tmp_path / "collected"
    request_path = collected_root / "evidence" / "render_request.yaml"
    request_path.parent.mkdir(parents=True)
    request_path.write_text(
        yaml.safe_dump(
            {
                "views": {
                    "scene_overview": {
                        "anchor_runtime_ids": [
                            "scene_room",
                            "lift2",
                            "00000000000000000000000000000000",
                            "obj_conical_bottle03",
                            "obj_graduated_cylinder_03",
                        ],
                        "azimuth_deg": -125.0,
                        "elevation_deg": 38.0,
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    candidate = module.BackgroundCandidate(
        candidate_id="scientific_environment_084",
        package_dir=Path("/tmp/package"),
        manifest_path=Path("/tmp/manifest.json"),
        source_usd=Path("/tmp/source.usd"),
        source_sha256="a" * 64,
        source_scope="/World",
        producer_revision="r1",
        meters_per_unit=1.0,
        root_scale_xyz=(0.001, 0.001, 0.001),
        root_translate_xyz=(0.0, 0.0, 0.0),
        physical_bounds_m=((-1.0, -1.0, 0.0), (1.0, 1.0, 2.0)),
        authored_camera=None,
    )

    module._configure_background_preview(
        collected_root,
        {"camera_origin_xyz": [0.0, 0.0, 0.0], "effective_scale": 1.0},
        candidate,
    )

    configured = yaml.safe_load(request_path.read_text(encoding="utf-8"))
    overview = configured["views"]["scene_overview"]
    assert configured["camera_policy_version"] == ("scenario-forge/runtime-workspace-context-v7")
    assert overview["anchor_runtime_ids"] == [
        "lift2_end_effectors",
        "obj_conical_bottle03",
        "obj_graduated_cylinder_03",
    ]
    assert overview["camera_source"] == "GenManip post-reset runtime workspace bounds"
    assert overview["runtime_target_direction_xyz"] == pytest.approx(
        [-0.679108, -0.475516, 0.559193]
    )
    assert overview["runtime_target_distance_m"] == pytest.approx(2.8)
    assert "target_xyz" not in overview
    assert "position_xyz" not in overview


def test_workspace_focus_preview_retargets_authored_room_direction_to_workspace(
    tmp_path: Path,
) -> None:
    module = _load_module()
    collected_root = tmp_path / "collected"
    request_path = collected_root / "evidence" / "render_request.yaml"
    request_path.parent.mkdir(parents=True)
    request_path.write_text(
        yaml.safe_dump(
            {
                "views": {
                    "scene_overview": {
                        "anchor_runtime_ids": ["lift2"],
                        "runtime_target_direction_xyz": [1.0, 0.0, 0.0],
                        "runtime_target_distance_m": 2.8,
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    candidate = module.BackgroundCandidate(
        candidate_id="scientific_environment_083",
        package_dir=Path("/tmp/package"),
        manifest_path=Path("/tmp/manifest.json"),
        source_usd=Path("/tmp/source.usd"),
        source_sha256="a" * 64,
        source_scope="/World",
        producer_revision="r1",
        meters_per_unit=1.0,
        root_scale_xyz=(1.0, 1.0, 1.0),
        root_translate_xyz=(0.0, 0.0, 0.0),
        physical_bounds_m=((-1.0, -1.0, 0.0), (1.0, 1.0, 2.0)),
        authored_camera=((0.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    )

    module._configure_background_preview(
        collected_root,
        {"camera_origin_xyz": [0.0, 0.0, 0.0], "effective_scale": 1.0},
        candidate,
        anchor=module.WorkspaceAnchor(
            source_prim_path="/World/group_026",
            source_anchor_xyz_m=(0.0, 0.0, 0.0),
            camera_mode="workspace_focus",
        ),
    )

    configured = yaml.safe_load(request_path.read_text(encoding="utf-8"))
    overview = configured["views"]["scene_overview"]
    target = module.EBENCH_WORKSPACE_TARGET_XYZ
    assert configured["camera_policy_version"] == (
        "scenario-forge/runtime-workspace-context-v8"
    )
    assert overview["target_xyz"] == pytest.approx(list(target))
    assert overview["position_xyz"] == pytest.approx(
        [target[0], target[1] - module.AUTHORED_CONTEXT_CAMERA_DISTANCE_M, target[2]]
    )
    assert overview["camera_source"].startswith(
        "scenario-forge source authored Perspective direction"
    )
    assert "runtime_target_direction_xyz" not in overview


def test_workspace_zone_preview_reuses_post_reset_workspace_camera(
    tmp_path: Path,
) -> None:
    module = _load_module()
    collected_root = tmp_path / "collected"
    request_path = collected_root / "evidence" / "render_request.yaml"
    request_path.parent.mkdir(parents=True)
    request_path.write_text(
        yaml.safe_dump(
            {
                "views": {
                    "scene_overview": {
                        "anchor_runtime_ids": ["lift2"],
                        "runtime_target_direction_xyz": [1.0, 0.0, 0.0],
                        "runtime_target_distance_m": 2.8,
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    candidate = module.BackgroundCandidate(
        candidate_id="scientific_environment_3fo4k5c9jd44",
        package_dir=Path("/tmp/package"),
        manifest_path=Path("/tmp/manifest.json"),
        source_usd=Path("/tmp/source.usd"),
        source_sha256="a" * 64,
        source_scope="/World",
        producer_revision="r1",
        meters_per_unit=1.0,
        root_scale_xyz=(1.0, 1.0, 1.0),
        root_translate_xyz=(0.0, 0.0, 0.0),
        physical_bounds_m=((-6.0, -7.0, 0.0), (10.0, 4.0, 3.3)),
        authored_camera=None,
    )
    anchor = module.WorkspaceAnchor(
        source_prim_path="/World/Root/Meshes/Assets/Table/Actor_0002",
        source_anchor_xyz_m=(-0.351, -4.275, 0.77),
        source_composed_meters_per_unit=1.0,
        preserve_workspace_metric=True,
        camera_mode="workspace_focus",
    )
    zone = module.WorkspaceZoneProfile(
        background_asset_id=candidate.candidate_id,
        zone_id="south_table_b",
        status="profiled",
        profile_path=Path("/tmp/south_table_b.yaml"),
        producer_revision="r1",
        producer_git_commit="a" * 40,
        anchor=anchor,
        raw_anchor_xyz_su=(-0.351, -4.275, 0.77),
        source_composed_meters_per_unit=1.0,
        raw_clearance_aabb_su=((-1.58, -5.65, 0.0), (0.87, -2.9, 2.2)),
        composition_yaw_deg=0.0,
    )

    module._configure_background_preview(
        collected_root,
        {
            "scene_pose": {"xyz": [0.5966705, 4.2680945, 0.002761]},
            "fit_factor": 1.0,
            "effective_scale": 1.0,
            "composition_yaw_deg": 0.0,
        },
        candidate,
        anchor=anchor,
        workspace_zone=zone,
    )

    configured = yaml.safe_load(request_path.read_text(encoding="utf-8"))
    overview = configured["views"]["scene_overview"]
    assert configured["camera_policy_version"] == (
        "scenario-forge/runtime-workspace-camera-reference-v10"
    )
    assert overview["camera_reference_view"] == "workspace_closeup"
    assert overview["camera_distance_multiplier"] == pytest.approx(1.15)
    assert overview["camera_source"] == (
        "GenManip post-reset workspace camera with room context"
    )
    assert "position_xyz" not in overview
    assert "target_xyz" not in overview
    assert "runtime_target_direction_xyz" not in overview


def test_workspace_zone_preview_reuses_post_reset_workspace_camera_when_source_camera_is_recorded(
    tmp_path: Path,
) -> None:
    module = _load_module()
    collected_root = tmp_path / "collected"
    request_path = collected_root / "evidence" / "render_request.yaml"
    request_path.parent.mkdir(parents=True)
    request_path.write_text(
        yaml.safe_dump(
            {
                "views": {
                    "scene_overview": {
                        "anchor_runtime_ids": ["lift2"],
                        "runtime_target_direction_xyz": [1.0, 0.0, 0.0],
                        "runtime_target_distance_m": 2.8,
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    candidate = module.BackgroundCandidate(
        candidate_id="scientific_environment_3fo4k5c9jd44",
        package_dir=Path("/tmp/package"),
        manifest_path=Path("/tmp/manifest.json"),
        source_usd=Path("/tmp/source.usd"),
        source_sha256="a" * 64,
        source_scope="/World",
        producer_revision="r1",
        meters_per_unit=1.0,
        root_scale_xyz=(1.0, 1.0, 1.0),
        root_translate_xyz=(0.0, 0.0, 0.0),
        physical_bounds_m=((-6.0, -7.0, 0.0), (10.0, 4.0, 3.3)),
        authored_camera=None,
    )
    anchor = module.WorkspaceAnchor(
        source_prim_path="/World/Root/Meshes/Assets/LaboratoryEquipment/Actor_0003",
        source_anchor_xyz_m=(0.0, 2.6, 0.9),
        source_composed_meters_per_unit=1.0,
        preserve_workspace_metric=True,
        camera_mode="workspace_focus",
    )
    zone = module.WorkspaceZoneProfile(
        background_asset_id=candidate.candidate_id,
        zone_id="north_bench_pair_east",
        status="profiled",
        profile_path=Path("/tmp/north_bench_pair_east.yaml"),
        producer_revision="r3",
        producer_git_commit="a" * 40,
        anchor=anchor,
        raw_anchor_xyz_su=(0.0, 2.6, 0.9),
        source_composed_meters_per_unit=1.0,
        raw_clearance_aabb_su=((-1.2, 1.2, 0.0), (1.3, 4.0, 2.2)),
        composition_yaw_deg=-90.0,
        evidence_camera_position_xyz_su=(0.0, 2.0, 1.5),
        evidence_camera_target_xyz_su=(0.0, 3.0, 0.85),
    )

    module._configure_background_preview(
        collected_root,
        {
            "scene_pose": {"xyz": [0.2456705, -0.0069055, 0.772761]},
            "fit_factor": 1.0,
            "effective_scale": 1.0,
            "composition_yaw_deg": -90.0,
        },
        candidate,
        anchor=anchor,
        workspace_zone=zone,
    )

    configured = yaml.safe_load(request_path.read_text(encoding="utf-8"))
    overview = configured["views"]["scene_overview"]
    assert configured["camera_policy_version"] == (
        "scenario-forge/runtime-workspace-camera-reference-v10"
    )
    assert overview["camera_reference_view"] == "workspace_closeup"
    assert overview["camera_distance_multiplier"] == pytest.approx(1.15)
    assert overview["camera_source"] == (
        "GenManip post-reset workspace camera with room context"
    )
    assert "position_xyz" not in overview
    assert "target_xyz" not in overview
    assert "runtime_target_direction_xyz" not in overview
    assert "runtime_target_distance_m" not in overview


def test_source_root_camera_is_consumed_for_scene_overview(tmp_path: Path) -> None:
    module = _load_module()
    package_dir = tmp_path / "package"
    source_root = package_dir / "deps" / "usd"
    source_root.mkdir(parents=True)
    (source_root / "source_root.usd").write_text(
        "#usda 1.0\n"
        "customLayerData = {\n"
        "dictionary cameraSettings = {\n"
        "dictionary Perspective = {\n"
        "double3 position = (1, 2, 3)\n"
        "double3 target = (4, 5, 6)\n"
        "}\n}\n}\n",
        encoding="utf-8",
    )

    assert module._source_authored_camera(package_dir) == (
        (1.0, 2.0, 3.0),
        (4.0, 5.0, 6.0),
    )


def test_candidate_regeneration_can_preserve_existing_variant_records(
    tmp_path: Path,
) -> None:
    module = _load_module()
    manifest_path = tmp_path / "background_variants_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "variants": [
                    {
                        "candidate_id": "scientific_environment_059",
                        "preview": {"status": "passed"},
                    },
                    {
                        "candidate_id": "scientific_environment_081",
                        "preview": {"status": "passed"},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    records = module._load_existing_variants(manifest_path)

    assert sorted(records) == [
        "scientific_environment_059",
        "scientific_environment_081",
    ]
    assert records["scientific_environment_059"]["preview"]["status"] == "passed"


def test_load_admitted_backgrounds_rejects_dynamic_claim(tmp_path: Path) -> None:
    module = _load_module()
    request_path = tmp_path / "request.yaml"
    request_path.write_text(
        yaml.safe_dump(
            {
                "target": {
                    "runtime_profile": "isaac41",
                    "asset_role": "rigid_object",
                },
                "producer_source_updates": {"revision": "r1"},
                "items": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="visual_static_environment"):
        module.load_admitted_backgrounds(request_path, tmp_path / "packages")


def _load_module():
    spec = importlib.util.spec_from_file_location("background_variants", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _workspace_profile_candidate(
    candidate_id: str,
    *,
    meters_per_unit: float = 1.0,
    root_scale_xyz: tuple[float, float, float] = (1.0, 1.0, 1.0),
    source_scope: str = "/World",
    physical_bounds_m: tuple[tuple[float, float, float], tuple[float, float, float]] = (
        (-100.0, -100.0, -10.0),
        (100.0, 100.0, 100.0),
    ),
):
    module = _load_module()
    return module.BackgroundCandidate(
        candidate_id=candidate_id,
        package_dir=Path("/tmp/package"),
        manifest_path=Path("/tmp/manifest.json"),
        source_usd=Path(f"/tmp/{candidate_id}.usd"),
        source_sha256="a" * 64,
        source_scope=source_scope,
        producer_revision="r1",
        meters_per_unit=meters_per_unit,
        root_scale_xyz=root_scale_xyz,
        root_translate_xyz=(0.0, 0.0, 0.0),
        physical_bounds_m=physical_bounds_m,
        authored_camera=None,
    )


def _write_workspace_profile_handoff(
    root: Path,
    candidate,
    *,
    status: str,
    anchor_xyz_m: tuple[float, float, float] | None = None,
    inactive_roots: tuple[str, ...] = (),
    optional_inactive_paths: tuple[str, ...] = (),
    not_applicable_reason: str | None = None,
    source_composed_meters_per_unit: float | None = 1.0,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    profile_name = f"{candidate.candidate_id}_workspace_profile.yaml"
    profile_path = root / profile_name
    profile = {
        "schema_version": "scenario-forge-convertasset-workspace-integration-profile/v0.1",
        "candidate_id": candidate.candidate_id,
        "status": status,
        "source": {
            "source_usd": str(candidate.source_usd),
            "source_sha256": candidate.source_sha256,
            "scope": candidate.source_scope,
        },
        "producer": {
            "repo": "ConvertAsset",
            "git_commit": "a" * 40,
            "revision": "profile-r1",
        },
    }
    if status == "profiled":
        assert anchor_xyz_m is not None
        coordinate_mapping = (
            {}
            if source_composed_meters_per_unit is None
            else {
                "coordinate_mapping": {
                    "frame": "source_composed",
                    "source_composed_meters_per_unit": (source_composed_meters_per_unit),
                }
            }
        )
        profile.update(
            {
                **coordinate_mapping,
                "assembly": {
                    "replaceable_assembly_roots": list(inactive_roots),
                    "anchor_prim": inactive_roots[0],
                    "anchor_xyz_m": list(anchor_xyz_m),
                },
                "inactivation": {
                    "inactive_prim_root_paths": list(inactive_roots),
                    "optional_inactive_prim_paths": list(optional_inactive_paths),
                },
                "workspace": {
                    "clearance_aabb_m": {
                        "min": [-1.0, -1.0, -1.0],
                        "max": [1.0, 1.0, 1.0],
                    }
                },
            }
        )
    else:
        profile["not_applicable_reason"] = not_applicable_reason
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    manifest_path = root / "workspace_profiles_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "scenario-forge-convertasset-workspace-integration-profile-manifest/v0.1",
                "producer": {"repo": "ConvertAsset", "revision": "profile-r1"},
                "candidates": {
                    candidate.candidate_id: {
                        "status": status,
                        "profile": profile_name,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


def _write_workspace_zone_profile_handoff(
    root: Path,
    candidate,
    *,
    zones: dict[str, dict[str, object]],
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    manifest_zones: dict[str, dict[str, str]] = {}
    for zone_id, zone in zones.items():
        profile_name = f"{candidate.candidate_id}__{zone_id}_workspace_zone.yaml"
        profile_path = root / profile_name
        status = str(zone["status"])
        profile: dict[str, object] = {
            "schema_version": "scenario-forge-convertasset-workspace-zone-profile/v0.2",
            "background_asset_id": candidate.candidate_id,
            "zone_id": zone_id,
            "status": status,
            "source": {
                "source_usd": str(candidate.source_usd),
                "source_sha256": candidate.source_sha256,
                "scope": candidate.source_scope,
            },
            "producer": {
                "repo": "ConvertAsset",
                "git_commit": "a" * 40,
                "revision": "zone-profile-r1",
            },
        }
        if status == "profiled":
            inactive_roots = tuple(zone["inactive_roots"])
            anchor_xyz_su = tuple(zone["anchor_xyz_su"])
            workspace_mode = str(zone.get("workspace_mode", "replace_assembly"))
            anchor_prim = str(
                zone.get(
                    "anchor_prim",
                    inactive_roots[0] if inactive_roots else "/World/Floor",
                )
            )
            profile.update(
                {
                    "coordinate_mapping": {
                        "frame": "source_composed",
                        "source_composed_meters_per_unit": 1.0,
                    },
                    "assembly": {
                        "replaceable_assembly_roots": list(inactive_roots),
                        "anchor_prim": anchor_prim,
                        "anchor_xyz_su": list(anchor_xyz_su),
                    },
                    "inactivation": {
                        "inactive_prim_root_paths": list(inactive_roots),
                        "optional_inactive_prim_paths": list(
                            zone.get("optional_inactive_paths", ())
                        ),
                    },
                    "workspace": {
                        "mode": workspace_mode,
                        "clearance_aabb_su": {
                            "min": [-20.0, -20.0, -2.0],
                            "max": [20.0, 20.0, 4.0],
                        }
                    },
                    "composition": {"yaw_deg": float(zone["yaw_deg"])},
                }
            )
        else:
            profile["not_applicable_reason"] = zone["not_applicable_reason"]
        profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
        manifest_zones[zone_id] = {"status": status, "profile": profile_name}

    manifest_path = root / "workspace_zone_profiles_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": (
                    "scenario-forge-convertasset-workspace-zone-profile-manifest/v0.2"
                ),
                "background_asset_id": candidate.candidate_id,
                "producer": {"repo": "ConvertAsset", "revision": "zone-profile-r1"},
                "zones": manifest_zones,
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


def test_workspace_zone_profile_supports_open_floor_without_inactivation(
    tmp_path: Path,
) -> None:
    module = _load_module()
    candidate = _workspace_profile_candidate(
        "scientific_environment_code_room_example4_v1"
    )
    manifest = _write_workspace_zone_profile_handoff(
        tmp_path / "profiles",
        candidate,
        zones={
            "center_open_floor": {
                "status": "profiled",
                "workspace_mode": "open_floor",
                "anchor_prim": "/World/Floor",
                "anchor_xyz_su": (0.0, -0.3, 0.772761),
                "inactive_roots": (),
                "yaw_deg": 0.0,
            }
        },
    )

    profiles = module.load_workspace_zone_profiles(manifest, (candidate,))
    profile = profiles[
        "scientific_environment_code_room_example4_v1__center_open_floor"
    ]

    assert profile.status == "profiled"
    assert profile.anchor is not None
    assert profile.anchor.hide_prim_paths == ()

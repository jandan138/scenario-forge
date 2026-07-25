from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import sys

import pytest
import yaml


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
            "raw_source": {
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
    mapped = [
        placement["scene_pose"]["xyz"][index]
        + placement["scene_pose"]["scale_xyz"][index]
        * raw_anchor[index]
        / candidate.root_scale_xyz[index]
        for index in range(3)
    ]
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
        "lift2",
        "00000000000000000000000000000000",
        "obj_conical_bottle03",
        "obj_graduated_cylinder_03",
    ]
    assert overview["camera_source"] == "GenManip post-reset runtime workspace bounds"
    assert overview["runtime_target_direction_xyz"] == pytest.approx(
        [0.679108, -0.475516, 0.559193]
    )
    assert overview["runtime_target_distance_m"] == pytest.approx(2.8)
    assert "target_xyz" not in overview
    assert "position_xyz" not in overview


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
        source_scope="/World",
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

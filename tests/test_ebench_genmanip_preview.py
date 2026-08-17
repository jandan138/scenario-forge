from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
import struct
from types import SimpleNamespace
import zlib

import pytest
import yaml

from scripts.ebench.render_genmanip_initial_preview import (
    _entrance_side_from_wall_coverage,
    _opposite_room_corner_azimuths,
    _preview_timing,
    _room_cutaway_sides,
    _runtime_prim,
    _task_data_with_preserved_articulation_parts,
)
from scenario_forge.adapters.ebench.genmanip import export_genmanip_collected_package
from scenario_forge.adapters.ebench.preview import (
    GenManipPreviewError,
    _initial_fixture_support_relations,
    _validate_runtime_geometry,
    compute_preview_input_digest,
    run_genmanip_initial_preview,
    validate_genmanip_preview_evidence,
    write_genmanip_preview_request,
)
from tests.test_ebench_genmanip_export import (
    _build_articulated_object_package,
    _build_package,
    _build_qualified_object_package,
)


_TABLE_RUNTIME_ID = "00000000000000000000000000000000"
_TASK_RUNTIME_IDS = ["obj_conical_bottle03", "obj_graduated_cylinder_03"]


def test_preview_derives_initial_fixture_support_from_pick_step() -> None:
    contract = {
        "objects": [
            {
                "scenario_object_id": "obj_rod",
                "runtime_uid": "obj_rod",
                "named_frames": {},
            },
            {
                "scenario_object_id": "obj_rack",
                "runtime_uid": "obj_rack",
                "named_frames": {
                    "middle_socket_04_inserted_bottom": {
                        "xyz": [0.0, 0.0, 0.01743],
                        "wxyz": [1.0, 0.0, 0.0, 0.0],
                    }
                },
            },
        ],
        "steps": [
            {
                "id": "pick_rod",
                "parameters": {
                    "object": "obj_rod",
                    "source_fixture": "obj_rack",
                    "source_frame": "obj_rack.middle_socket_04_inserted_bottom",
                    "source_support_offset_xyz_m": [0.0, 0.0, -0.004],
                },
            }
        ],
    }

    assert _initial_fixture_support_relations(contract) == {
        "obj_rod": {
            "kind": "fixture_frame_support_height",
            "target_runtime_id": "obj_rack",
            "target_frame": "obj_rack.middle_socket_04_inserted_bottom",
            "target_frame_local_xyz": [0.0, 0.0, 0.01343],
        }
    }


def test_preview_timing_accepts_explicit_zero_action_smoke_steps() -> None:
    assert _preview_timing({"zero_action_warmup_steps": 960}) == (960, True)


def test_preview_recovery_keeps_genmanip_articulation_parts_active() -> None:
    task_data = {
        "initial_layout": {
            "centrifuge": {"type": "articulation"},
            "test_tube": {"type": "object"},
        }
    }

    recovered = _task_data_with_preserved_articulation_parts(
        task_data,
        ("centrifuge_lid", "centrifuge_rotor", "centrifuge_start_button"),
    )

    assert task_data["initial_layout"] == {
        "centrifuge": {"type": "articulation"},
        "test_tube": {"type": "object"},
    }
    assert recovered["initial_layout"]["centrifuge_lid"] == {"type": "articulation_part"}
    assert recovered["initial_layout"]["centrifuge_rotor"] == {"type": "articulation_part"}
    assert recovered["initial_layout"]["centrifuge_start_button"] == {"type": "articulation_part"}


def test_preview_runtime_prim_resolves_articulation_root() -> None:
    articulation_prim = object()
    scene = SimpleNamespace(
        uuid="scene",
        object_list={},
        articulation_list={
            "centrifuge": SimpleNamespace(prim=articulation_prim),
        },
    )

    assert _runtime_prim(None, scene, "centrifuge") is articulation_prim


def test_export_writes_evidence_only_preview_request_without_changing_policy_cameras(
    tmp_path: Path,
) -> None:
    collected_package = export_genmanip_collected_package(_build_package(tmp_path)).output_dir

    request_path = collected_package / "evidence" / "render_request.yaml"
    request = yaml.safe_load(request_path.read_text(encoding="utf-8"))

    assert request["schema_version"] == "scenario-forge-genmanip-preview-request/v0.2"
    assert request["package_id"] == "scientific_workbench_bimanual_pour"
    assert request["purpose"] == "evidence_only"
    assert request["affects_policy_observation"] is False
    assert request["moment"] == "post_reset_pre_action"
    assert request["camera_policy_version"] == "scenario-forge/task-anchor-fit-v6"
    assert request["input_digest"] == compute_preview_input_digest(collected_package)
    assert request["expected_runtime_ids"] == {
        "robot": "lift2",
        "table": _TABLE_RUNTIME_ID,
        "task_objects": _TASK_RUNTIME_IDS,
    }

    expected_inputs = {
        "package_manifest",
        "task_config",
        "episode_metadata",
        "scene_usd",
        "evaluation_camera",
        "source_bundle",
    }
    assert set(request["inputs"]) == expected_inputs
    for role, item in request["inputs"].items():
        relative_path = Path(item["path"])
        assert not relative_path.is_absolute()
        assert ".." not in relative_path.parts
        input_path = collected_package / relative_path
        if role == "source_bundle":
            assert input_path.is_dir()
            assert item["sha256"] == _tree_sha256(input_path)
        else:
            assert item["sha256"] == _file_sha256(input_path)

    assert set(request["views"]) == {
        "workspace_closeup",
        "scene_overview",
        "task_object_closeup",
    }
    assert request["views"]["task_object_closeup"]["required_runtime_ids"] == (_TASK_RUNTIME_IDS)
    assert request["views"]["workspace_closeup"]["required_runtime_ids"] == [
        "lift2",
        _TABLE_RUNTIME_ID,
        *_TASK_RUNTIME_IDS,
    ]
    assert request["views"]["workspace_closeup"]["anchor_runtime_ids"] == [
        "lift2_end_effectors",
        *_TASK_RUNTIME_IDS,
    ]
    assert request["views"]["workspace_closeup"]["azimuth_deg"] == -35.0
    assert request["views"]["workspace_closeup"]["elevation_deg"] == 34.0
    assert request["views"]["workspace_closeup"]["minimum_distance"] == 1.0
    assert request["views"]["scene_overview"]["required_runtime_ids"] == [
        "lift2",
        _TABLE_RUNTIME_ID,
        *_TASK_RUNTIME_IDS,
    ]
    assert request["views"]["scene_overview"]["anchor_runtime_ids"] == [
        "lift2",
        _TABLE_RUNTIME_ID,
        *_TASK_RUNTIME_IDS,
    ]
    assert request["views"]["scene_overview"]["azimuth_deg"] == -125.0
    assert request["views"]["scene_overview"]["elevation_deg"] == 38.0
    assert request["views"]["scene_overview"]["framing_margin"] == 1.05
    assert request["views"]["scene_overview"]["minimum_distance"] == 1.6

    camera_path = collected_package / request["inputs"]["evaluation_camera"]["path"]
    camera_bytes = camera_path.read_bytes()
    camera_config = yaml.safe_load(camera_bytes)
    assert set(camera_config) == {"overlook_camera"}
    assert camera_config["overlook_camera"]["prim_path"].endswith("Camera_overlook")
    assert b"workspace_closeup" not in camera_bytes
    assert b"scene_overview" not in camera_bytes
    assert b"qa_camera" not in camera_bytes.lower()


def test_preview_request_can_require_1080p_runtime_evidence(tmp_path: Path) -> None:
    collected_package = export_genmanip_collected_package(_build_package(tmp_path)).output_dir

    write_genmanip_preview_request(collected_package, resolution=(1920, 1080))

    request = _load_yaml(collected_package / "evidence" / "render_request.yaml")
    for view_name in (
        "workspace_closeup",
        "scene_overview",
        "task_object_closeup",
    ):
        assert request["views"][view_name]["resolution"] == [1920, 1080]
    assert "lift2" in request["views"]["workspace_closeup"]["required_runtime_ids"]


def test_full_environment_preview_request_requires_seven_1080p_views(
    tmp_path: Path,
) -> None:
    collected_package = export_genmanip_collected_package(_build_package(tmp_path)).output_dir
    manifest_path = collected_package / "package_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_assets"][0]["upstream_package"] = {
        "metadata": {"producer_asset_role": "visual_static_environment"}
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    write_genmanip_preview_request(collected_package)

    request = _load_yaml(collected_package / "evidence" / "render_request.yaml")
    assert request["schema_version"] == "scenario-forge-genmanip-preview-request/v0.3"
    assert list(request["views"]) == [
        "workspace_closeup",
        "scene_overview",
        "task_object_closeup",
        "room_topdown",
        "room_corner_a",
        "room_corner_b",
        "room_entrance_eye_level",
    ]
    required = ["lift2", _TABLE_RUNTIME_ID, *_TASK_RUNTIME_IDS]
    for name, view in request["views"].items():
        assert view["resolution"] == [1920, 1080], name
    for name in (
        "room_topdown",
        "room_corner_a",
        "room_corner_b",
        "room_entrance_eye_level",
    ):
        assert request["views"][name]["required_runtime_ids"] == required
        assert request["views"][name]["bounds_source"] == "runtime_scene_room"
    assert request["views"]["room_corner_a"]["cutaway_policy"] == (
        "nearest_complete_room_wall_roots"
    )
    assert request["views"]["room_entrance_eye_level"]["cutaway_policy"] == "none"


def test_full_environment_preview_evidence_passes_room_framing_gate(
    tmp_path: Path,
) -> None:
    collected_package = export_genmanip_collected_package(_build_package(tmp_path)).output_dir
    manifest_path = collected_package / "package_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_assets"][0]["upstream_package"] = {
        "metadata": {"producer_asset_role": "visual_static_environment"}
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_genmanip_preview_request(collected_package)
    request = _load_yaml(collected_package / "evidence" / "render_request.yaml")
    _write_passing_evidence(collected_package, request)

    result = validate_genmanip_preview_evidence(collected_package)

    assert result.status == "passed"
    gate = _load_yaml(result.gate_path)
    assert gate["schema_version"] == "scenario-forge-genmanip-preview-gate/v0.3"
    assert set(gate["views"]) == set(request["views"])


def test_room_survey_camera_policy_selects_opposite_corners_and_open_entrance() -> None:
    assert _opposite_room_corner_azimuths() == pytest.approx((45.0, 225.0))
    assert _room_cutaway_sides(45.0) == ("east", "north")
    assert _room_cutaway_sides(225.0) == ("south", "west")
    coverage = {
        "north": [(0.0, 1.0)],
        "east": [(0.0, 0.9)],
        "south": [(0.0, 0.25), (0.75, 1.0)],
        "west": [(0.0, 1.0)],
    }
    assert _entrance_side_from_wall_coverage(coverage) == ("south", pytest.approx(0.5))


def test_preview_request_requires_articulated_task_objects_in_both_views(
    tmp_path: Path,
) -> None:
    collected_package = export_genmanip_collected_package(
        _build_articulated_object_package(tmp_path)
    ).output_dir

    request = _load_yaml(collected_package / "evidence" / "render_request.yaml")
    articulated_id = "obj_graduated_cylinder_03"

    assert articulated_id in request["expected_runtime_ids"]["task_objects"]
    for view_name in (
        "workspace_closeup",
        "scene_overview",
        "task_object_closeup",
    ):
        assert articulated_id in request["views"][view_name]["required_runtime_ids"]
        assert articulated_id in request["views"][view_name]["anchor_runtime_ids"]


def test_preview_request_carries_convertasset_expected_task_geometry(
    tmp_path: Path,
) -> None:
    collected_package = export_genmanip_collected_package(
        _build_qualified_object_package(tmp_path)
    ).output_dir

    request = _load_yaml(collected_package / "evidence" / "render_request.yaml")
    expected = request["expected_runtime_geometry"]

    assert set(expected) == {
        "obj_conical_bottle03",
        "obj_graduated_cylinder_03",
    }
    for runtime_id, item in expected.items():
        assert item["schema_version"] == ("scenario-forge-task-interactive-geometry/v0.1")
        assert item["asset_entry_prim"] in {
            "/World/conical_bottle03",
            "/World/graduated_cylinder_03",
        }
        assert item["extent_m"] == [0.32, 0.35, 0.226]
        assert item["max_extent_relative_error"] == 0.05
        assert item["max_root_tilt_deg"] == 10.0
        assert item["max_support_gap_m"] == 0.01
        assert item["support_frame"] == "support"
        assert item["support_frame_local_matrix"] == [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        assert len(item["support_frame_source_sha256"]) == 64
        assert item["runtime_id"] == runtime_id


def test_preview_evidence_with_matching_digest_writes_visual_ready_gate(
    tmp_path: Path,
) -> None:
    collected_package = export_genmanip_collected_package(_build_package(tmp_path)).output_dir
    request = _load_yaml(collected_package / "evidence" / "render_request.yaml")
    evidence_dir = _write_passing_evidence(collected_package, request)

    validate_genmanip_preview_evidence(collected_package)

    gate_path = evidence_dir / "visual_ready_gate.yaml"
    gate = _load_yaml(gate_path)
    assert gate["schema_version"] == "scenario-forge-genmanip-preview-gate/v0.2"
    assert gate["status"] == "passed"
    assert gate["package_id"] == request["package_id"]
    assert gate["input_digest"] == request["input_digest"]
    assert set(gate["views"]) == {
        "workspace_closeup",
        "scene_overview",
        "task_object_closeup",
    }
    assert gate["next_stage"] == "clean_room_visual_review"
    assert gate["verification_scope"] == (
        "structural_runtime_geometry_and_camera_composition_metadata"
    )
    assert gate["runtime_geometry"]["status"] == "passed"
    assert "on-camera visibility" in gate["claim_boundary"]
    assert "task success" in gate["claim_boundary"]


def test_preview_geometry_gate_uses_qualified_extent_for_each_runtime_sample(
    tmp_path: Path,
) -> None:
    collected_package = export_genmanip_collected_package(
        _build_qualified_object_package(tmp_path)
    ).output_dir
    request_path = collected_package / "evidence" / "render_request.yaml"
    request = _load_yaml(request_path)
    expected = request["expected_runtime_geometry"]
    assert isinstance(expected, dict)
    runtime_id = next(iter(expected))
    expected_item = expected[runtime_id]
    assert isinstance(expected_item, dict)
    expected_item["qualified_extent_m_by_sample"] = {
        "warmup_start": [0.32, 0.35, 0.226],
        "post_warmup": [0.34, 0.36, 0.24],
    }
    evidence_dir = _write_passing_evidence(collected_package, request)
    manifest = json.loads((evidence_dir / "render_manifest.json").read_text(encoding="utf-8"))

    gate = _validate_runtime_geometry(request, manifest)

    assert gate["task_objects"][runtime_id]["expected_extent_m_by_sample"] == {
        "warmup_start": [0.32, 0.35, 0.226],
        "post_warmup": [0.34, 0.36, 0.24],
    }


def test_preview_geometry_gate_allows_rotated_post_warmup_aabb_without_profile(
    tmp_path: Path,
) -> None:
    collected_package = export_genmanip_collected_package(
        _build_qualified_object_package(tmp_path)
    ).output_dir
    request = _load_yaml(collected_package / "evidence" / "render_request.yaml")
    runtime_id = next(iter(request["expected_runtime_geometry"]))
    request["expected_runtime_geometry"][runtime_id].pop("qualified_extent_m_by_sample", None)
    evidence_dir = _write_passing_evidence(collected_package, request)
    manifest = json.loads((evidence_dir / "render_manifest.json").read_text(encoding="utf-8"))
    post = manifest["runtime_geometry"]["task_objects"][runtime_id]["post_warmup"]
    lower = post["world_bound_m"]["min"]
    center = [
        (low + high) / 2.0 for low, high in zip(lower, post["world_bound_m"]["max"], strict=True)
    ]
    rotated_extent = [0.36, 0.31, 0.226]
    post["world_bound_m"] = {
        "min": [c - extent / 2.0 for c, extent in zip(center, rotated_extent, strict=True)],
        "max": [c + extent / 2.0 for c, extent in zip(center, rotated_extent, strict=True)],
    }
    post["extent_m"] = rotated_extent

    gate = _validate_runtime_geometry(request, manifest)

    assert gate["task_objects"][runtime_id]["extent_comparison_by_sample"] == {
        "warmup_start": "sorted_axis_extents",
        "post_warmup": "longest_aabb_axis_rotation_tolerant",
    }


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("oversized", "extent"),
        ("off_table", "tabletop XY"),
        ("floating", "support gap"),
        ("tipped", "root tilt"),
    ],
)
def test_preview_geometry_gate_rejects_bad_runtime_task_placement(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    collected_package = export_genmanip_collected_package(
        _build_qualified_object_package(tmp_path)
    ).output_dir
    request = _load_yaml(collected_package / "evidence" / "render_request.yaml")
    evidence_dir = _write_passing_evidence(collected_package, request)
    manifest_path = evidence_dir / "render_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    runtime_id = sorted(request["expected_runtime_geometry"])[0]
    runtime_item = manifest["runtime_geometry"]["task_objects"][runtime_id]
    runtime_bound = runtime_item["post_warmup"]["world_bound_m"]
    if mutation == "oversized":
        runtime_bound["max"][0] += 1.0
    elif mutation == "off_table":
        runtime_bound["min"][0] += 3.0
        runtime_bound["max"][0] += 3.0
    elif mutation == "floating":
        runtime_item["post_warmup"]["root_pose"]["xyz_m"][2] += 0.2
        runtime_item["post_warmup"]["support_frame_world_point_m"][2] += 0.2
    else:
        runtime_item["post_warmup"]["root_pose"]["wxyz"] = [
            0.7071067811865476,
            0.7071067811865475,
            0.0,
            0.0,
        ]
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(GenManipPreviewError, match=message):
        validate_genmanip_preview_evidence(collected_package)

    assert not (evidence_dir / "visual_ready_gate.yaml").exists()


def test_preview_support_gate_is_not_spoofed_by_matching_overall_bbox(
    tmp_path: Path,
) -> None:
    collected_package = export_genmanip_collected_package(
        _build_qualified_object_package(tmp_path)
    ).output_dir
    request = _load_yaml(collected_package / "evidence" / "render_request.yaml")
    evidence_dir = _write_passing_evidence(collected_package, request)
    manifest_path = evidence_dir / "render_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    runtime_id = sorted(request["expected_runtime_geometry"])[0]
    item = manifest["runtime_geometry"]["task_objects"][runtime_id]

    # The producer-declared support frame, not a collider-inflated overall AABB,
    # is the authoritative tabletop contact witness.
    assert item["post_warmup"]["world_bound_m"]["min"][2] == pytest.approx(0.805)
    item["post_warmup"]["root_pose"]["xyz_m"][2] = 0.8135
    item["post_warmup"]["support_frame_world_point_m"][2] = 0.8135
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(GenManipPreviewError, match="support gap"):
        validate_genmanip_preview_evidence(collected_package)


def test_preview_evidence_requires_room_visibility_and_honors_camera_reference(
    tmp_path: Path,
) -> None:
    collected_package = export_genmanip_collected_package(_build_package(tmp_path)).output_dir
    request_path = collected_package / "evidence" / "render_request.yaml"
    request = _load_yaml(request_path)
    views = request["views"]
    assert isinstance(views, dict)
    overview = views["scene_overview"]
    assert isinstance(overview, dict)
    overview["camera_reference_view"] = "workspace_closeup"
    overview["camera_distance_multiplier"] = 1.15
    request_path.write_text(yaml.safe_dump(request, sort_keys=False), encoding="utf-8")
    evidence_dir = _write_passing_evidence(collected_package, request)

    validate_genmanip_preview_evidence(collected_package)

    manifest_path = evidence_dir / "render_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["views"]["scene_overview"]["scene_visibility"] = (
        "scene_room_invisible_workspace_isolation"
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(GenManipPreviewError, match="scene_room_inherited"):
        validate_genmanip_preview_evidence(collected_package)

    manifest["views"]["scene_overview"]["scene_visibility"] = "scene_room_inherited"
    manifest["views"]["scene_overview"]["camera"]["distance_m"] = 99.0
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(GenManipPreviewError, match="camera reference"):
        validate_genmanip_preview_evidence(collected_package)


def test_preview_evidence_validation_accepts_relative_collected_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collected_package = export_genmanip_collected_package(_build_package(tmp_path)).output_dir
    request = _load_yaml(collected_package / "evidence" / "render_request.yaml")
    _write_passing_evidence(collected_package, request)
    monkeypatch.chdir(collected_package.parent)

    result = validate_genmanip_preview_evidence(Path(collected_package.name))

    assert result.status == "passed"
    assert result.gate_path.is_file()


@pytest.mark.parametrize(
    ("corrupt", "message"),
    [
        ("missing_image", "missing|workspace_closeup"),
        ("stale_input", "digest|sha256|hash"),
        ("stale_source_bundle", "digest|sha256|hash"),
        ("redirected_input", "input|digest|sha256|hash"),
        ("wrong_package_id", "package_id.*package manifest|package manifest.*package_id"),
        ("tampered_runtime_log", "runtime log.*sha256|runtime log.*hash"),
        ("stale_request", "request.*sha256|request.*hash"),
        ("wrong_image_hash", "sha256|hash"),
    ],
)
def test_preview_evidence_rejects_missing_stale_or_mismatched_artifacts(
    tmp_path: Path,
    corrupt: str,
    message: str,
) -> None:
    collected_package = export_genmanip_collected_package(_build_package(tmp_path)).output_dir
    request = _load_yaml(collected_package / "evidence" / "render_request.yaml")
    evidence_dir = _write_passing_evidence(collected_package, request)

    if corrupt == "missing_image":
        (evidence_dir / "workspace_closeup.png").unlink()
    elif corrupt == "stale_input":
        config_path = collected_package / request["inputs"]["task_config"]["path"]
        config_path.write_text(
            config_path.read_text(encoding="utf-8") + "\n# changed after render\n",
            encoding="utf-8",
        )
    elif corrupt == "stale_source_bundle":
        source_bundle = collected_package / (
            "assets/scene_usds/scenario_forge/scientific_workbench_bimanual_pour/"
            "source_bundle/scientific_workbench_environment/scene.usda"
        )
        source_bundle.write_text(
            source_bundle.read_text(encoding="utf-8") + "\n# changed after render\n",
            encoding="utf-8",
        )
    elif corrupt == "redirected_input":
        request_path = collected_package / "evidence" / "render_request.yaml"
        redirected_request = _load_yaml(request_path)
        inputs = redirected_request["inputs"]
        assert isinstance(inputs, dict)
        scene_input = inputs["scene_usd"]
        assert isinstance(scene_input, dict)
        original_scene = collected_package / scene_input["path"]
        alternate_scene = collected_package / "alternate_scene.usda"
        alternate_scene.write_bytes(original_scene.read_bytes())
        scene_input["path"] = alternate_scene.relative_to(collected_package).as_posix()
        scene_input["sha256"] = _file_sha256(alternate_scene)
        request_path.write_text(
            yaml.safe_dump(redirected_request, sort_keys=False), encoding="utf-8"
        )
        manifest_path = evidence_dir / "render_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["request_sha256"] = _file_sha256(request_path)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    elif corrupt == "tampered_runtime_log":
        runtime_log = evidence_dir / "runtime.log"
        runtime_log.write_text(
            runtime_log.read_text(encoding="utf-8") + "tampered after render\n",
            encoding="utf-8",
        )
    elif corrupt == "wrong_package_id":
        request_path = collected_package / "evidence" / "render_request.yaml"
        wrong_request = _load_yaml(request_path)
        wrong_request["package_id"] = "wrong-package"
        wrong_request["input_digest"] = (
            "sha256:"
            + sha256(
                json.dumps(
                    {
                        "package_id": wrong_request["package_id"],
                        "inputs": wrong_request["inputs"],
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
        )
        request_path.write_text(yaml.safe_dump(wrong_request, sort_keys=False), encoding="utf-8")
        manifest_path = evidence_dir / "render_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["package_id"] = wrong_request["package_id"]
        manifest["input_digest"] = wrong_request["input_digest"]
        manifest["request_sha256"] = _file_sha256(request_path)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    elif corrupt == "stale_request":
        request_path = collected_package / "evidence" / "render_request.yaml"
        stale_request = _load_yaml(request_path)
        views = stale_request["views"]
        assert isinstance(views, dict)
        overview = views["scene_overview"]
        assert isinstance(overview, dict)
        overview["elevation_deg"] = 12.0
        request_path.write_text(yaml.safe_dump(stale_request, sort_keys=False), encoding="utf-8")
    else:
        manifest_path = evidence_dir / "render_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["views"]["scene_overview"]["sha256"] = "sha256:" + ("0" * 64)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    with pytest.raises(GenManipPreviewError, match=message):
        validate_genmanip_preview_evidence(collected_package)

    assert not (evidence_dir / "visual_ready_gate.yaml").exists()


@pytest.mark.parametrize("entrypoint", ["run", "validate"])
def test_preview_entrypoints_do_not_unlink_gate_through_external_evidence_symlink(
    tmp_path: Path, entrypoint: str
) -> None:
    collected_package = export_genmanip_collected_package(_build_package(tmp_path)).output_dir
    external = tmp_path / "external-evidence"
    external.mkdir()
    external_gate = external / "visual_ready_gate.yaml"
    external_gate.write_text("owner: external\n", encoding="utf-8")
    (collected_package / "evidence" / "initial_scene").symlink_to(
        external, target_is_directory=True
    )

    with pytest.raises(GenManipPreviewError):
        if entrypoint == "run":
            run_genmanip_initial_preview(
                collected_package,
                tmp_path / "missing-isaac-python",
                tmp_path / "missing-renderer.py",
                tmp_path / "missing-genmanip",
            )
        else:
            validate_genmanip_preview_evidence(collected_package)

    assert external_gate.read_text(encoding="utf-8") == "owner: external\n"


def test_preview_request_writer_rejects_external_evidence_symlink(
    tmp_path: Path,
) -> None:
    collected_package = export_genmanip_collected_package(_build_package(tmp_path)).output_dir
    evidence = collected_package / "evidence"
    evidence.rename(collected_package / "original-evidence")
    external = tmp_path / "external-request-output"
    external.mkdir()
    evidence.symlink_to(external, target_is_directory=True)

    with pytest.raises(GenManipPreviewError, match="escapes"):
        write_genmanip_preview_request(collected_package)

    assert not (external / "render_request.yaml").exists()


def _write_passing_evidence(
    collected_package: Path,
    request: dict[str, object],
) -> Path:
    evidence_dir = collected_package / "evidence" / "initial_scene"
    evidence_dir.mkdir(parents=True)
    image_specs = {
        "workspace_closeup": (34, 89, 144),
        "scene_overview": (91, 117, 74),
        "task_object_closeup": (147, 91, 62),
    }
    views: dict[str, object] = {}
    request_views = request["views"]
    assert isinstance(request_views, dict)
    image_specs.update(
        {
            "room_topdown": (87, 105, 128),
            "room_corner_a": (102, 126, 139),
            "room_corner_b": (113, 136, 147),
            "room_entrance_eye_level": (126, 143, 150),
        }
    )
    for index, view_name in enumerate(request_views):
        color = image_specs[view_name]
        image_path = evidence_dir / f"{view_name}.png"
        view_request = request_views[view_name]
        assert isinstance(view_request, dict)
        width, height = view_request["resolution"]
        _write_rgb_png(image_path, width=width, height=height, color=color)
        distance_m = 1.4 + index
        views[view_name] = {
            "status": "pass",
            "image_path": image_path.name,
            "sha256": _file_sha256(image_path),
            "resolution": [width, height],
            "present_runtime_ids": view_request["required_runtime_ids"],
            "scene_visibility": (
                "scene_room_invisible_workspace_isolation"
                if view_name in {"workspace_closeup", "task_object_closeup"}
                else "scene_room_inherited"
            ),
            "temporary_hidden_prim_paths": (
                [
                    "/World/test/room/Wall_North",
                    "/World/test/room/Wall_East",
                ]
                if view_name in {"room_corner_a", "room_corner_b"}
                else []
            ),
            "camera": {
                "position": [0.3 + index, -0.8, 1.4],
                "look_at": [0.3, 0.0, 0.8],
                "focal_length_mm": 24.0,
                "distance_m": distance_m,
            },
        }
        if view_name.startswith("room_"):
            views[view_name]["framing"] = {
                "status": "pass",
                "room": {
                    "fully_in_frame": view_name != "room_entrance_eye_level",
                    "ndc_bounds": [-0.8, -0.75, 0.8, 0.75],
                    "occupancy_ratio": 0.6,
                },
                "workcell": {
                    "fully_in_frame": True,
                    "ndc_bounds": [-0.4, -0.4, 0.4, 0.4],
                    "occupancy_ratio": 0.16,
                },
                "entrance_side": ("south" if view_name == "room_entrance_eye_level" else None),
            }

    overview_request = request_views["scene_overview"]
    assert isinstance(overview_request, dict)
    reference_view = overview_request.get("camera_reference_view")
    if reference_view is not None:
        assert reference_view == "workspace_closeup"
        multiplier = float(overview_request.get("camera_distance_multiplier", 1.0))
        reference_camera = views[reference_view]["camera"]
        assert isinstance(reference_camera, dict)
        overview_camera = views["scene_overview"]["camera"]
        assert isinstance(overview_camera, dict)
        overview_camera["look_at"] = list(reference_camera["look_at"])
        overview_camera["distance_m"] = multiplier * float(reference_camera["distance_m"])

    runtime_log = evidence_dir / "runtime.log"
    runtime_log.write_text("GenManip initial preview render completed\n", encoding="utf-8")
    table_bound = {
        "min": [-1.0, -1.0, 0.0],
        "max": [1.0, 1.0, 0.8],
    }
    expected_geometry = request.get("expected_runtime_geometry", {})
    assert isinstance(expected_geometry, dict)
    expected_runtime_ids = request["expected_runtime_ids"]
    assert isinstance(expected_runtime_ids, dict)
    task_runtime_ids = expected_runtime_ids["task_objects"]
    assert isinstance(task_runtime_ids, list)
    task_bounds: dict[str, object] = {}
    for index, runtime_id in enumerate(task_runtime_ids):
        expected = expected_geometry.get(runtime_id, {})
        assert isinstance(expected, dict)
        extent = expected.get("extent_m", [0.1, 0.1, 0.1])
        assert isinstance(extent, list) and len(extent) == 3
        qualified_extents = expected.get("qualified_extent_m_by_sample", {})
        assert isinstance(qualified_extents, dict)
        warmup_extent = qualified_extents.get("warmup_start", extent)
        post_extent = qualified_extents.get("post_warmup", extent)
        assert isinstance(warmup_extent, list) and len(warmup_extent) == 3
        assert isinstance(post_extent, list) and len(post_extent) == 3
        lower = [-0.7 + 0.5 * index, -0.2, 0.805]
        support_matrix = expected.get("support_frame_local_matrix")

        def snapshot(sample_extent: list[object]) -> dict[str, object]:
            upper = [
                lower[0] + float(sample_extent[0]),
                lower[1] + float(sample_extent[1]),
                lower[2] + float(sample_extent[2]),
            ]
            value: dict[str, object] = {
                "world_bound_m": {"min": lower, "max": upper},
                "extent_m": [float(component) for component in sample_extent],
            }
            if support_matrix is not None:
                assert isinstance(support_matrix, list) and len(support_matrix) == 4
                support_local_x = float(support_matrix[3][0])
                support_local_y = float(support_matrix[3][1])
                support_local_z = float(support_matrix[3][2])
                root_x = float(lower[0]) - support_local_x
                root_y = float(lower[1]) - support_local_y
                root_z = table_bound["max"][2] - support_local_z
                value.update(
                    {
                        "root_pose": {
                            "xyz_m": [root_x, root_y, root_z],
                            "wxyz": [1.0, 0.0, 0.0, 0.0],
                        },
                        "support_frame_world_point_m": [
                            float(lower[0]),
                            float(lower[1]),
                            table_bound["max"][2],
                        ],
                    }
                )
            return value

        task_bounds[str(runtime_id)] = {
            "runtime_id": str(runtime_id),
            "warmup_start": snapshot(warmup_extent),
            "post_warmup": snapshot(post_extent),
        }
    manifest = {
        "schema_version": (
            "scenario-forge-genmanip-preview-evidence/v0.3"
            if request["schema_version"] == "scenario-forge-genmanip-preview-request/v0.3"
            else "scenario-forge-genmanip-preview-evidence/v0.2"
        ),
        "package_id": request["package_id"],
        "input_digest": request["input_digest"],
        "request_sha256": _file_sha256(collected_package / "evidence" / "render_request.yaml"),
        "purpose": "evidence_only",
        "moment": "post_reset_pre_action",
        "render_status": "pass",
        "runtime": {
            "engine": "Isaac Sim",
            "isaac_sim_version": "test",
            "genmanip_revision": "test",
        },
        "runtime_log_path": runtime_log.name,
        "runtime_log_sha256": _file_sha256(runtime_log),
        "runtime_log_scan": {
            "status": "pass",
            "scope": "known_blocking_material_signals",
            "scanned_streams": ["renderer_runtime_log", "subprocess_stdout", "subprocess_stderr"],
            "blocking_signal_count": 0,
            "blocking_signals": [],
        },
        "runtime_geometry": {
            "status": "pass",
            "sample_moment": "post_reset_zero_action_warmup",
            "table": {
                "runtime_id": expected_runtime_ids["table"],
                "world_bound_m": table_bound,
                "extent_m": [2.0, 2.0, 0.8],
            },
            "task_objects": task_bounds,
        },
        "views": views,
        "claim_boundary": (
            "Initial-scene visual evidence only; not task success, policy success, "
            "physics fidelity, or liquid-transfer evidence."
        ),
    }
    (evidence_dir / "render_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return evidence_dir


def _write_rgb_png(
    path: Path,
    *,
    width: int,
    height: int,
    color: tuple[int, int, int],
) -> None:
    row = bytes(color) * width
    pixels = (b"\x00" + row) * height
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(pixels))
        + _png_chunk(b"IEND", b"")
    )


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)


def _file_sha256(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _tree_sha256(root: Path) -> str:
    digest = sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(_file_sha256(path).removeprefix("sha256:")))
    return "sha256:" + digest.hexdigest()


def _load_yaml(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data

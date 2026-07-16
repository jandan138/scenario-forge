from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts import generate_scientific_workbench_bimanual_pour as generator
from tests.test_convert_asset_adapter import _write_source_bound_handoff
from tests.test_scenario_package_compiler import _write_source_scene


REPO_ROOT = Path(__file__).resolve().parents[1]

_TASK_READY_INACTIVE_PRIMS = [
    "/World/Cube",
    "/World/lounge_booth_table",
    "/World/beaker1",
    "/World/beaker2",
    "/World/beaker3",
    "/World/conical_bottle01",
    "/World/conical_bottle02",
    "/World/conical_bottle04",
    "/World/target_plat",
    "/World/target_plat2",
    "/World/DryingBox_01",
    "/World/DryingBox_02",
    "/World/DryingBox_04",
    "/World/MuffleFurnace",
    "/World/Cabinet_01",
    "/World/Cabinet_02",
]


def _convert_asset_args(
    root: Path,
    source_usd: Path,
    *,
    source_vessel_revision: str = "source-vessel-profile-r1",
    target_vessel_revision: str = "target-vessel-profile-r3",
) -> list[str]:
    _, dryingbox_package, dryingbox_manifest, _ = _write_source_bound_handoff(
        root / "dryingbox_handoff",
        source_usd=source_usd,
    )
    _, source_package, source_manifest, _ = _write_source_bound_handoff(
        root / "source_vessel_handoff",
        source_usd=source_usd,
        with_interaction_contract=True,
        observed_collider_approximation="sdf",
        interaction_root="/World/conical_bottle03",
    )
    _, target_package, target_manifest, _ = _write_source_bound_handoff(
        root / "target_vessel_handoff",
        source_usd=source_usd,
        with_interaction_contract=True,
        interaction_root="/World/graduated_cylinder_03",
    )
    return [
        "--convert-asset-package",
        str(dryingbox_package),
        "--convert-asset-manifest",
        str(dryingbox_manifest),
        "--source-vessel-package",
        str(source_package),
        "--source-vessel-manifest",
        str(source_manifest),
        "--target-vessel-package",
        str(target_package),
        "--target-vessel-manifest",
        str(target_manifest),
        "--dryingbox-revision",
        "324ce6e6d4395ccfda1e59e5ae89de9389cdf225",
        "--source-vessel-revision",
        source_vessel_revision,
        "--target-vessel-revision",
        target_vessel_revision,
    ]


def _write_task_ready_source_scene(root: Path) -> Path:
    source = _write_source_scene(root)
    text = source.read_text(encoding="utf-8")
    insertion = "\n".join(
        f'    def Xform "{name}" {{}}'
        for name in [
            *(Path(path).name for path in _TASK_READY_INACTIVE_PRIMS),
            "DryingBox_03",
            "CylinderLight",
            "GroundPlane",
        ]
    )
    closing_brace = text.rfind("\n}")
    assert closing_brace > 0
    source.write_text(
        text[:closing_brace] + "\n" + insertion + text[closing_brace:],
        encoding="utf-8",
    )
    return source


def test_golden_opening_frames_follow_the_assets_local_positive_y_axis() -> None:
    scenario = yaml.safe_load(generator.DEFAULT_SPEC.read_text(encoding="utf-8"))
    objects = {item["id"]: item for item in scenario["objects"]}

    expected = {
        "obj_conical_bottle03": [0.0, 0.1965674179, 0.0],
        "obj_graduated_cylinder_03": [0.0, 0.2722941904, 0.0],
    }
    for object_id, position in expected.items():
        opening = objects[object_id]["named_frames"]["opening"]
        assert opening["xyz"] == position
        # Opening-frame +Z is the outward normal; the mesh opens along local +Y.
        assert opening["wxyz"] == [
            0.7071067811865476,
            -0.7071067811865475,
            0.0,
            0.0,
        ]


def test_golden_actor_roles_use_same_side_arms_instead_of_crossing_midline() -> None:
    scenario = yaml.safe_load(generator.DEFAULT_SPEC.read_text(encoding="utf-8"))
    actors = {item["id"]: item for item in scenario["robot"]["actors"]}

    # Lift2's left arm is on +Y beside the +Y source; its right arm is beside
    # the -Y target. The role assignment should not force both arms to cross.
    assert actors["operating_arm"]["end_effector"] == "left"
    assert actors["auxiliary_arm"]["end_effector"] == "right"


def test_golden_generator_static_only_skips_runtime_and_excludes_upstream_reports(
    tmp_path: Path,
) -> None:
    source_usd = _write_source_scene(tmp_path)
    reports = source_usd.parent / "_reports"
    reports.mkdir()
    (reports / "old.png").write_bytes(b"old render")
    output = tmp_path / "output"

    result = generator.main(
        [
            "--source-usd",
            str(source_usd),
            *_convert_asset_args(tmp_path, source_usd),
            "--out",
            str(output),
            "--static-only",
        ]
    )

    assert result == 0
    collected = output / "adapters/ebench/genmanip"
    assert (collected / "evidence/render_request.yaml").is_file()
    assert not (output / "assets/scientific_workbench_environment/_reports").exists()
    overlay_root = output / "assets/scientific_workbench_dryingbox_03_dynamic"
    assert (overlay_root / "physics/profile.json").is_file()
    assert (overlay_root / "overlays/physics_profile.usda").is_file()
    assert not (overlay_root / "evidence").exists()
    for asset_id in (
        "scientific_workbench_conical_bottle03_dynamic",
        "scientific_workbench_graduated_cylinder_03_dynamic",
    ):
        assert (
            output
            / "assets"
            / asset_id
            / "evidence/interaction_runtime_qualification/report.json"
        ).is_file()
    assert not (collected / "evidence/initial_scene/visual_ready_gate.yaml").exists()
    assets = yaml.safe_load(
        (output / "provenance/provenance.yaml").read_text(encoding="utf-8")
    )["assets"]
    upstream_by_asset = {
        item["asset_id"]: item["upstream_package"]
        for item in assets
        if "upstream_package" in item
    }
    upstream = upstream_by_asset["scientific_workbench_dryingbox_03_dynamic"]
    assert upstream["producer"] == "ConvertAsset"
    assert upstream["revision"] == "324ce6e6d4395ccfda1e59e5ae89de9389cdf225"
    assert upstream["metadata"]["quality_tier"] == "provisional_geometry"
    expected_vessel_revisions = {
        "scientific_workbench_conical_bottle03_dynamic": "source-vessel-profile-r1",
        "scientific_workbench_graduated_cylinder_03_dynamic": "target-vessel-profile-r3",
    }
    assert {
        asset_id: upstream_by_asset[asset_id]["revision"]
        for asset_id in expected_vessel_revisions
    } == expected_vessel_revisions

    asset_manifest = yaml.safe_load(
        (output / "assets/asset_manifest.yaml").read_text(encoding="utf-8")
    )
    asset_manifest_upstream = {
        item["asset_id"]: item["upstream_package"]["revision"]
        for item in asset_manifest["assets"]
        if "upstream_package" in item
    }
    assert {
        asset_id: asset_manifest_upstream[asset_id]
        for asset_id in expected_vessel_revisions
    } == expected_vessel_revisions

    collected_manifest = json.loads(
        (collected / "package_manifest.json").read_text(encoding="utf-8")
    )
    collected_upstream = {
        item["asset_id"]: item["upstream_package"]["revision"]
        for item in collected_manifest["source_assets"]
        if "upstream_package" in item
    }
    assert {
        asset_id: collected_upstream[asset_id]
        for asset_id in expected_vessel_revisions
    } == expected_vessel_revisions

    task_config = yaml.safe_load(
        (collected / "tasks/config.yaml").read_text(encoding="utf-8")
    )
    assert task_config["evaluation_configs"][0]["physics_scene_config"] == {
        "EnableGPUDynamics": True
    }
    assert task_config["evaluation_configs"][0]["robots"] == [
        {"type": "manip/lift2/R5a", "position": [-1.02, 0.0, 0.31]}
    ]
    episode = json.loads(
        (
            collected
            / "tasks/scenario_forge/scientific_workbench_bimanual_pour/000/episode_metadata.json"
        ).read_text(encoding="utf-8")
    )
    assert episode["task_data"]["initial_layout"]["lift2"]["position"] == [
        -1.02,
        0.0,
        0.31,
    ]
    initial_layout = episode["task_data"]["initial_layout"]
    assert initial_layout["00000000000000000000000000000000"]["scale"] == [
        0.003,
        0.0035,
        0.004,
    ]
    assert initial_layout["obj_conical_bottle03"]["position"] == [-0.25, 0.16, 0.81]
    assert initial_layout["obj_graduated_cylinder_03"]["position"] == [
        -0.25,
        -0.16,
        0.81,
    ]
    contract = episode["task_data"]["scenario_forge_runtime_contract"]
    assert contract["contract_status"] == "transport_only"
    contract_objects = {
        item["scenario_object_id"]: item for item in contract["objects"]
    }
    assert contract_objects["obj_conical_bottle03"]["named_frames"]["opening"] == {
        "xyz": [0.0, 0.1965674179, 0.0],
        "wxyz": [0.7071067811865476, -0.7071067811865475, 0.0, 0.0],
    }
    assert contract_objects["obj_graduated_cylinder_03"]["named_frames"][
        "opening"
    ] == {
        "xyz": [0.0, 0.2722941904, 0.0],
        "wxyz": [0.7071067811865476, -0.7071067811865475, 0.0, 0.0],
    }
    assert contract["schema_version"] == (
        "scenario-forge-genmanip-runtime-contract/v0.3"
    )
    assert [predicate["sequence_index"] for predicate in contract["success"]["predicates"]] == [
        0,
        1,
        2,
    ]
    assert [predicate["type"] for predicate in contract["success"]["predicates"][:2]] == [
        "named_frames_relative_pose_reached",
        "named_frames_relative_pose_reached",
    ]
    for object_id in ("obj_conical_bottle03", "obj_graduated_cylinder_03"):
        assert initial_layout[object_id]["add_colliders"] is False
        assert initial_layout[object_id]["add_rigid_body"] is False
        assert contract_objects[object_id]["physics_authoring"] == {
            "local_colliders": False,
            "local_mass": False,
            "local_rigid_body": False,
            "owner": "convert_asset_package",
        }
    actors = {item["id"]: item for item in contract["robot"]["actors"]}
    assert actors["operating_arm"]["end_effector"] == "left"
    assert actors["auxiliary_arm"]["end_effector"] == "right"
    scene_text = (
        collected
        / "assets/scene_usds/scenario_forge/scientific_workbench_bimanual_pour/scene.usda"
    ).read_text(encoding="utf-8")
    assert 'over "Cube" (' in scene_text
    assert "active = false" in scene_text
    assert "double3 xformOp:translate = (-9.5, -43.3, 0)" in scene_text
    assert "quatd xformOp:orient = (0.7933533, 0, 0, 0.6087614)" in scene_text
    assert 'over "Cabinet_02" (' in scene_text
    assert 'over "CylinderLight"' in scene_text
    assert 'over "GroundPlane"' in scene_text
    for local_physics_token in (
        "__aan_collision_proxy",
        "physics:mass",
        "physics:diagonalInertia",
        "physics:centerOfMass",
        "physics:principalAxes",
        "PhysicsMassAPI",
    ):
        assert local_physics_token not in scene_text


def test_golden_generator_default_build_runs_genmanip_preview(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_usd = _write_source_scene(tmp_path)
    output = tmp_path / "output"
    isaac_python = tmp_path / "isaac python"
    renderer_script = tmp_path / "renderer.py"
    genmanip_root = tmp_path / "GenManip"
    isaac_python.write_text("", encoding="utf-8")
    renderer_script.write_text("", encoding="utf-8")
    genmanip_root.mkdir()
    calls: list[tuple[Path, Path, Path, Path, float]] = []

    def fake_run(
        collected_root: Path,
        runtime_python: Path,
        runtime_script: Path,
        runtime_root: Path,
        *,
        timeout_seconds: float,
    ) -> object:
        calls.append(
            (
                collected_root,
                runtime_python,
                runtime_script,
                runtime_root,
                timeout_seconds,
            )
        )
        return object()

    monkeypatch.setattr(generator, "run_genmanip_initial_preview", fake_run)

    result = generator.main(
        [
            "--source-usd",
            str(source_usd),
            *_convert_asset_args(tmp_path, source_usd),
            "--out",
            str(output),
            "--isaac-python",
            str(isaac_python),
            "--renderer-script",
            str(renderer_script),
            "--genmanip-root",
            str(genmanip_root),
            "--preview-timeout",
            "321",
        ]
    )

    assert result == 0
    assert calls == [
        (
            output / "adapters/ebench/genmanip",
            isaac_python,
            renderer_script,
            genmanip_root,
            321.0,
        )
    ]


def test_golden_task_ready_overlay_removes_unrelated_dynamic_context_in_both_scenes(
    tmp_path: Path,
) -> None:
    Usd = pytest.importorskip("pxr.Usd")
    source_usd = _write_task_ready_source_scene(tmp_path)
    output = tmp_path / "output"

    result = generator.main(
        [
            "--source-usd",
            str(source_usd),
            *_convert_asset_args(tmp_path, source_usd),
            "--out",
            str(output),
            "--static-only",
        ]
    )

    assert result == 0
    scenario = yaml.safe_load((output / "scenario.yaml").read_text(encoding="utf-8"))
    assert scenario["scene"]["inactive_prim_paths"] == _TASK_READY_INACTIVE_PRIMS

    portable = Usd.Stage.Open(str(output / "scene/main.usda"))
    assert portable
    for path in _TASK_READY_INACTIVE_PRIMS:
        assert not portable.GetPrimAtPath(path).IsActive(), path
    for path in [
        "/World/table",
        "/World/conical_bottle03",
        "/World/graduated_cylinder_03",
        "/World/DryingBox_03",
        "/World/CylinderLight",
        "/World/GroundPlane",
    ]:
        assert portable.GetPrimAtPath(path).IsActive(), path

    collected = Usd.Stage.Open(
        str(
            output
            / "adapters/ebench/genmanip/assets/scene_usds/scenario_forge/"
            "scientific_workbench_bimanual_pour/scene.usda"
        )
    )
    assert collected
    room = "/World/scientific_workbench_bimanual_pour/room"
    for path in _TASK_READY_INACTIVE_PRIMS:
        assert not collected.GetPrimAtPath(room + path.removeprefix("/World")).IsActive(), path
    for path in [
        f"{room}/DryingBox_03",
        f"{room}/CylinderLight",
        f"{room}/GroundPlane",
        "/World/scientific_workbench_bimanual_pour/obj_table",
        "/World/scientific_workbench_bimanual_pour/obj_obj_conical_bottle03",
        "/World/scientific_workbench_bimanual_pour/obj_obj_graduated_cylinder_03",
    ]:
        assert collected.GetPrimAtPath(path).IsActive(), path
    active_physics_scenes = [
        prim.GetPath().pathString
        for prim in collected.Traverse()
        if prim.IsActive() and prim.GetTypeName() == "PhysicsScene"
    ]
    assert active_physics_scenes == ["/physicsScene"]

    portable_mass = portable.GetPrimAtPath(
        "/World/DryingBox_03/body"
    ).GetAttribute("physics:mass")
    assert portable_mass.Get() == pytest.approx(12.0)
    assert portable_mass.GetPropertyStack()[0].layer.realPath.endswith(
        "/assets/scientific_workbench_dryingbox_03_dynamic/"
        "overlays/physics_profile.usda"
    )
    collected_mass = collected.GetPrimAtPath(
        f"{room}/DryingBox_03/body"
    ).GetAttribute("physics:mass")
    assert collected_mass.Get() == pytest.approx(12.0)
    assert collected_mass.GetPropertyStack()[0].layer.realPath.endswith(
        "/source_bundle/scientific_workbench_dryingbox_03_dynamic/"
        "overlays/physics_profile.usda"
    )


def test_golden_generator_validates_handoff_before_replacing_output(
    tmp_path: Path,
) -> None:
    source_usd = _write_source_scene(tmp_path)
    handoff_args = _convert_asset_args(tmp_path, source_usd)
    source_usd.write_text(
        source_usd.read_text(encoding="utf-8") + "\n# changed after handoff\n",
        encoding="utf-8",
    )
    output = tmp_path / "output"
    output.mkdir()
    marker = output / "keep.txt"
    marker.write_text("existing output", encoding="utf-8")

    with pytest.raises(ValueError, match="source SHA-256"):
        generator.main(
            [
                "--source-usd",
                str(source_usd),
                *handoff_args,
                "--out",
                str(output),
                "--static-only",
            ]
        )

    assert marker.read_text(encoding="utf-8") == "existing output"


def test_runbook_stages_canary_in_a_private_genmanip_workspace() -> None:
    runbook = (
        REPO_ROOT / "docs/operations/generate-bimanual-pour-package.md"
    ).read_text(encoding="utf-8")

    assert "LABUTOPIA_ROOT=" in runbook
    assert "GENMANIP_SOURCE=" in runbook
    assert "CANARY_ROOT=" in runbook
    assert "CANDIDATE=" in runbook
    assert "CANONICAL=" in runbook
    assert "BACKUP=" in runbook
    assert '--out "$CANDIDATE"' in runbook
    assert 'mv "$CANDIDATE" "$CANONICAL"' in runbook
    assert 'package check "$CANDIDATE" --require-asset-lock' in runbook
    assert 'git clone --no-hardlinks "$GENMANIP_SOURCE" "$CANARY_ROOT"' in runbook
    assert 'git -C "$CANARY_ROOT" checkout --detach "$GENMANIP_REVISION"' in runbook
    assert "GENMANIP_REVISION=014bf5435a373df9b3bcf5a69aa7fe22d17f613d" in runbook
    assert 'git -C "$GENMANIP_SOURCE" archive HEAD' not in runbook
    assert 'rm -rf "$target"' not in runbook
    assert "shared EBench asset directory" in runbook
    assert "--source-vessel-revision" in runbook
    assert "--target-vessel-revision" in runbook
    assert (
        "SOURCE_VESSEL_REVISION=ba4ac8ccbf3c32f257abdbb68a554a74a90003f1"
        in runbook
    )
    assert (
        "TARGET_VESSEL_REVISION=4bb541161a652cc4e5dd63253adffba018f17137"
        in runbook
    )
    assert "2026-07-15-aan-graduated-cylinder-r3-grasp-section" in runbook
    assert 'VESSEL_REVISION="$(git -C "$CONVERT_ASSET_ROOT" rev-parse HEAD)"' not in runbook

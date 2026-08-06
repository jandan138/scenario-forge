from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from scripts import generate_scientific_workbench_bimanual_pour as generator
from tests.test_convert_asset_adapter import (
    _write_source_bound_handoff,
    _write_static_support_handoff,
    _write_visual_static_handoff,
)
from tests.test_scenario_package_compiler import _write_source_scene


REPO_ROOT = Path(__file__).resolve().parents[1]

# The package must retain Scene1_hard's parent-layer placement, units, and
# rotation for the lab_015 payload; ConvertAsset extracts this exact scope.
_SCENE1_ENVIRONMENT_SCOPE = "/World/lab_015"
_EBENCH_TABLE_SCOPE = "/World/table"


@pytest.fixture(autouse=True)
def _stub_tabletop_policy_for_non_tabletop_fixture_packages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep these source-handoff tests independent from tabletop geometry fixtures."""

    monkeypatch.setattr(
        generator,
        "validate_scientific_workbench_tabletop_placement",
        lambda package_root: SimpleNamespace(
            evidence_path=Path(package_root) / "evidence/tabletop_placement_policy.yaml",
            overall_status="pass",
        ),
    )


def _convert_asset_args(
    root: Path,
    scene1_source_usd: Path,
    source_vessel_source_usd: Path,
    target_vessel_source_usd: Path | None = None,
    *,
    scene1_environment_revision: str = "54ff5660937c08cf3784c44a3f500757ab4eed78",
    table_revision: str = "54ff5660937c08cf3784c44a3f500757ab4eed78",
    source_vessel_revision: str = "source-vessel-profile-r1",
    target_vessel_revision: str = "target-vessel-profile-r3",
) -> list[str]:
    target_vessel_source_usd = target_vessel_source_usd or source_vessel_source_usd
    _, environment_package, environment_manifest, _ = _write_visual_static_handoff(
        root / "scene1_environment_handoff",
        source_usd=scene1_source_usd,
        scope=_SCENE1_ENVIRONMENT_SCOPE,
    )
    table_source_usd, table_package, table_manifest, _ = (
        _write_static_support_handoff(root / "table_handoff")
    )
    _, source_package, source_manifest, _ = _write_source_bound_handoff(
        root / "source_vessel_handoff",
        source_usd=source_vessel_source_usd,
        with_interaction_contract=True,
        observed_collider_approximation="sdf",
        interaction_root="/World/conical_bottle03",
        identity_facade_frames=True,
    )
    _, target_package, target_manifest, _ = _write_source_bound_handoff(
        root / "target_vessel_handoff",
        source_usd=target_vessel_source_usd,
        with_interaction_contract=True,
        interaction_root="/World/graduated_cylinder_03",
        identity_facade_frames=True,
    )
    return [
        "--scene1-source-usd",
        str(scene1_source_usd),
        "--table-source-usd",
        str(table_source_usd),
        "--source-vessel-source-usd",
        str(source_vessel_source_usd),
        "--target-vessel-source-usd",
        str(target_vessel_source_usd),
        "--scene1-environment-package",
        str(environment_package),
        "--scene1-environment-manifest",
        str(environment_manifest),
        "--table-package",
        str(table_package),
        "--table-manifest",
        str(table_manifest),
        "--source-vessel-package",
        str(source_package),
        "--source-vessel-manifest",
        str(source_manifest),
        "--target-vessel-package",
        str(target_package),
        "--target-vessel-manifest",
        str(target_manifest),
        "--scene1-environment-revision",
        scene1_environment_revision,
        "--table-revision",
        table_revision,
        "--source-vessel-revision",
        source_vessel_revision,
        "--target-vessel-revision",
        target_vessel_revision,
    ]


def _write_scene1_hard_environment_source(root: Path) -> Path:
    source = root / "scene1-hard" / "Scene1_hard.usda"
    source.parent.mkdir(parents=True)
    source.write_text(
        """#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)
def Xform "World"
{
    def Xform "lab_015" {}
    def Xform "table_hard" {}
}
""",
        encoding="utf-8",
    )
    return source


def test_golden_opening_frames_follow_the_identity_facades_local_positive_z_axis() -> None:
    scenario = yaml.safe_load(generator.DEFAULT_SPEC.read_text(encoding="utf-8"))
    objects = {item["id"]: item for item in scenario["objects"]}

    expected = {
        "obj_conical_bottle03": [0.0, 0.0, 0.1965674179],
        "obj_graduated_cylinder_03": [0.0, 0.0, 0.2722941904],
    }
    for object_id, position in expected.items():
        opening = objects[object_id]["named_frames"]["opening"]
        assert opening["xyz"] == position
        assert opening["wxyz"] == [1.0, 0.0, 0.0, 0.0]


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
    pytest.importorskip("pxr.Usd", reason="IK request generation requires OpenUSD")
    scene1_source_usd = _write_scene1_hard_environment_source(tmp_path)
    source_vessel_source_usd = _write_source_scene(tmp_path / "source-vessel-source")
    target_vessel_source_usd = _write_source_scene(tmp_path / "target-vessel-source")
    output = tmp_path / "output"

    result = generator.main(
        [
            *_convert_asset_args(
                tmp_path,
                scene1_source_usd,
                source_vessel_source_usd,
                target_vessel_source_usd,
            ),
            "--out",
            str(output),
            "--static-only",
        ]
    )

    assert result == 0
    collected = output / "adapters/ebench/genmanip"
    assert (collected / "evidence/render_request.yaml").is_file()
    for asset_id in (
        "scientific_workbench_scene1_hard_environment",
        "scientific_workbench_ebench_table",
    ):
        assert (output / "assets" / asset_id / "asset.usd").is_file()
        assert not (output / "assets" / asset_id / "evidence").exists()
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
    expected_revisions = {
        "scientific_workbench_scene1_hard_environment": (
            "54ff5660937c08cf3784c44a3f500757ab4eed78"
        ),
        "scientific_workbench_ebench_table": (
            "54ff5660937c08cf3784c44a3f500757ab4eed78"
        ),
        "scientific_workbench_conical_bottle03_dynamic": "source-vessel-profile-r1",
        "scientific_workbench_graduated_cylinder_03_dynamic": "target-vessel-profile-r3",
    }
    assert {
        asset_id: upstream_by_asset[asset_id]["revision"]
        for asset_id in expected_revisions
    } == expected_revisions
    assert upstream_by_asset["scientific_workbench_scene1_hard_environment"][
        "metadata"
    ]["consumer_usage"] == "visual_static_environment"
    assert upstream_by_asset["scientific_workbench_ebench_table"][
        "metadata"
    ]["consumer_usage"] == "static_support_object"

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
        for asset_id in expected_revisions
    } == expected_revisions

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
        for asset_id in expected_revisions
    } == expected_revisions

    task_config = yaml.safe_load(
        (collected / "tasks/config.yaml").read_text(encoding="utf-8")
    )
    assert task_config["evaluation_configs"][0]["physics_scene_config"][
        "SolverType"
    ] == "TGS"
    assert task_config["evaluation_configs"][0]["physics_scene_config"][
        "TimeStepsPerSecond"
    ] == 60
    assert len(task_config["evaluation_configs"][0]["preprocess_config"]) == 3
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
    table_layout = initial_layout["00000000000000000000000000000000"]
    assert table_layout["position"] == [0.242788066, 0.0, 0.0]
    assert table_layout["scale"] == [0.003, 0.0035, 0.004]
    assert table_layout["path"] == (
        "collected_packages/scientific_workbench_bimanual_pour/"
        "assets/scene_usds/scenario_forge/scientific_workbench_bimanual_pour/"
        "source_bundle/scenario_forge_runtime/table.usd"
    )
    assert table_layout["add_colliders"] is False
    assert table_layout["add_rigid_body"] is False
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
        "xyz": [0.0, 0.0, 0.1965674179],
        "wxyz": [1.0, 0.0, 0.0, 0.0],
    }
    assert contract_objects["obj_graduated_cylinder_03"]["named_frames"][
        "opening"
    ] == {
        "xyz": [0.0, 0.0, 0.2722941904],
        "wxyz": [1.0, 0.0, 0.0, 0.0],
    }
    assert contract["schema_version"] == (
        "scenario-forge-genmanip-runtime-contract/v0.4"
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
    assert "scientific_workbench_scene1_hard_environment" in scene_text
    assert "scientific_workbench_ebench_table" not in scene_text
    assert 'def Xform "obj_table"' not in scene_text
    assert 'over "table" (' in scene_text
    assert "double3 xformOp:translate = (0.621309, 0.462547, 0.061353)" in scene_text
    assert "scientific_workbench_dryingbox_03_dynamic" not in scene_text
    for local_physics_token in (
        "__aan_collision_proxy",
        "physics:mass",
        "physics:diagonalInertia",
        "physics:centerOfMass",
        "physics:principalAxes",
        "PhysicsMassAPI",
    ):
        assert local_physics_token not in scene_text

    runtime_table_path = (
        collected
        / "assets/scene_usds/scenario_forge/scientific_workbench_bimanual_pour/"
        "source_bundle/scenario_forge_runtime/table.usd"
    )
    runtime_table_text = runtime_table_path.read_text(encoding="utf-8")
    assert 'defaultPrim = "Asset"' in runtime_table_text
    assert (
        "prepend references = "
        "@../scientific_workbench_ebench_table/asset.usd@</World>"
    ) in runtime_table_text
    assert runtime_table_text.count("uniform token[] xformOpOrder = []") == 2
    for forbidden_token in (
        "PhysicsCollisionAPI",
        "PhysicsRigidBodyAPI",
        "PhysicsMassAPI",
        "physics:mass",
        "physics:diagonalInertia",
    ):
        assert forbidden_token not in runtime_table_text

    Usd = pytest.importorskip("pxr.Usd")
    runtime_table_stage = Usd.Stage.Open(str(runtime_table_path))
    assert runtime_table_stage
    assert runtime_table_stage.GetDefaultPrim().GetPath().pathString == "/Asset"
    assert runtime_table_stage.GetPrimAtPath("/Asset/table").IsActive()
    assert (
        runtime_table_stage.GetPrimAtPath("/Asset/table")
        .GetAttribute("xformOpOrder")
        .Get()
        == []
    )


def test_golden_generator_default_build_runs_genmanip_preview(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pytest.importorskip("pxr.Usd", reason="IK request generation requires OpenUSD")
    scene1_source_usd = _write_scene1_hard_environment_source(tmp_path)
    vessel_source_usd = _write_source_scene(tmp_path / "vessel-source")
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
            *_convert_asset_args(tmp_path, scene1_source_usd, vessel_source_usd),
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


def test_scene1_environment_and_table_scopes_are_composed_in_both_scenes(
    tmp_path: Path,
) -> None:
    Usd = pytest.importorskip("pxr.Usd")
    scene1_source_usd = _write_scene1_hard_environment_source(tmp_path)
    vessel_source_usd = _write_source_scene(tmp_path / "vessel-source")
    output = tmp_path / "output"

    result = generator.main(
        [
            *_convert_asset_args(tmp_path, scene1_source_usd, vessel_source_usd),
            "--out",
            str(output),
            "--static-only",
        ]
    )

    assert result == 0
    scenario = yaml.safe_load((output / "scenario.yaml").read_text(encoding="utf-8"))
    assert scenario["scene"]["asset_id"] == "scientific_workbench_scene1_hard_environment"
    assert "overlay_asset_ids" not in scenario["scene"]
    table = next(item for item in scenario["objects"] if item["id"] == "table")
    assert table["asset_id"] == "scientific_workbench_ebench_table"
    assert table["source_prim_path"] == _EBENCH_TABLE_SCOPE

    portable = Usd.Stage.Open(str(output / "scene/main.usda"))
    assert portable
    for path in [
        _SCENE1_ENVIRONMENT_SCOPE,
        _EBENCH_TABLE_SCOPE,
        "/World/conical_bottle03",
        "/World/graduated_cylinder_03",
    ]:
        assert portable.GetPrimAtPath(path).IsActive(), path
    assert not portable.GetPrimAtPath("/World/DryingBox_03").IsValid()

    collected = Usd.Stage.Open(
        str(
            output
            / "adapters/ebench/genmanip/assets/scene_usds/scenario_forge/"
            "scientific_workbench_bimanual_pour/scene.usda"
        )
    )
    assert collected
    room = "/World/_scene/room"
    assert collected.GetPrimAtPath(f"{room}/lab_015").IsActive()
    assert not collected.GetPrimAtPath(f"{room}/table").IsActive()
    assert not collected.GetPrimAtPath(
        "/World/_scene/obj_table"
    ).IsValid()
    for path in [
        "/World/_scene/obj_obj_conical_bottle03",
        "/World/_scene/obj_obj_graduated_cylinder_03",
    ]:
        assert collected.GetPrimAtPath(path).IsActive(), path
    active_physics_scenes = [
        prim.GetPath().pathString
        for prim in collected.Traverse()
        if prim.IsActive() and prim.GetTypeName() == "PhysicsScene"
    ]
    assert active_physics_scenes == ["/physicsScene"]


def test_golden_generator_validates_handoff_before_replacing_output(
    tmp_path: Path,
) -> None:
    scene1_source_usd = _write_scene1_hard_environment_source(tmp_path)
    vessel_source_usd = _write_source_scene(tmp_path / "vessel-source")
    handoff_args = _convert_asset_args(tmp_path, scene1_source_usd, vessel_source_usd)
    scene1_source_usd.write_text(
        scene1_source_usd.read_text(encoding="utf-8") + "\n# changed after handoff\n",
        encoding="utf-8",
    )
    output = tmp_path / "output"
    output.mkdir()
    marker = output / "keep.txt"
    marker.write_text("existing output", encoding="utf-8")

    with pytest.raises(ValueError, match="source SHA-256"):
        generator.main(
            [
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
    assert "--scene1-environment-revision" in runbook
    assert "--table-revision" in runbook
    assert "--source-vessel-revision" in runbook
    assert "--target-vessel-revision" in runbook
    assert "TABLE_REVISION=77600fc529446eeea0a6abc8de04da4c484dbae8" in runbook
    assert "VESSEL_REVISION=db71fde4e97fa2698926b23a2a86af663eda6177" in runbook
    assert "Scene1_hard.usd" in runbook
    assert "Scene1_hard.usd:/World/lab_015" in runbook
    assert "/World/table" in runbook
    assert "graduated_cylinder_identity/package" in runbook
    assert 'VESSEL_REVISION="$(git -C "$CONVERT_ASSET_ROOT" rev-parse HEAD)"' not in runbook

from __future__ import annotations

import json
import pickle
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from scenario_forge.adapters.ebench.genmanip import (
    GenManipExportError,
    export_genmanip_collected_package,
)
from scenario_forge.assets.source import LocalUSDAssetSource
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.package_compiler import compile_scenario_package
from tests.test_scenario_package_compiler import _write_source_scene
from tests.test_scenario_spec import _scenario_mapping


_OVERLAY_ASSET_ID = "dryingbox_03_dynamic"


def _build_package(tmp_path: Path) -> Path:
    source_usd = _write_source_scene(tmp_path)
    package_root = tmp_path / "package"
    compile_scenario_package(
        ScenarioSpec.from_mapping(_scenario_mapping()),
        {
            "scientific_workbench_environment": LocalUSDAssetSource(
                asset_id="scientific_workbench_environment",
                source_usd=source_usd,
                role="environment",
                license="CC-BY-NC-4.0",
                source_uri="example://scientific-workbench-scene",
                attribution=("Example scientific workbench asset",),
                redistributable=False,
            )
        },
        package_root,
    )
    return package_root


def _write_overlay_base_scene(root: Path) -> Path:
    source_usd = _write_source_scene(root)
    source_text = source_usd.read_text(encoding="utf-8")
    closing_world = source_text.rfind("\n}")
    assert closing_world >= 0
    source_usd.write_text(
        source_text[:closing_world]
        + """
    def Xform "DryingBox_03"
    {
        custom string scenarioForge:compositionWinner = "base"
    }
"""
        + source_text[closing_world:],
        encoding="utf-8",
    )
    return source_usd


def _write_scene_overlay(root: Path) -> Path:
    overlay_usd = root / "overlay-source" / "asset.usda"
    overlay_usd.parent.mkdir(parents=True)
    overlay_usd.write_text(
        """#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{
    def Xform "DryingBox_03"
    {
        custom string scenarioForge:compositionWinner = "overlay"
        float physics:mass = 1
        float3 physics:diagonalInertia = (1, 1, 1)
        point3f physics:centerOfMass = (0, 0, 0)
        quatf physics:principalAxes = (1, 0, 0, 0)
    }
}
""",
        encoding="utf-8",
    )
    return overlay_usd


def _overlay_scenario_mapping() -> dict[str, object]:
    scenario = _scenario_mapping()
    scenario["schema_version"] = "scenario-spec/v0.2"
    scene = dict(scenario["scene"])  # type: ignore[arg-type]
    scene["overlay_asset_ids"] = [_OVERLAY_ASSET_ID]
    scenario["scene"] = scene
    return scenario


def _build_overlay_package(tmp_path: Path) -> Path:
    source_usd = _write_overlay_base_scene(tmp_path)
    overlay_usd = _write_scene_overlay(tmp_path)
    package_root = tmp_path / "package"
    compile_scenario_package(
        ScenarioSpec.from_mapping(_overlay_scenario_mapping()),
        {
            "scientific_workbench_environment": LocalUSDAssetSource(
                asset_id="scientific_workbench_environment",
                source_usd=source_usd,
                role="environment",
                license="CC-BY-NC-4.0",
                source_uri="example://scientific-workbench-scene",
                attribution=("Example scientific workbench asset",),
                redistributable=False,
            ),
            _OVERLAY_ASSET_ID: LocalUSDAssetSource(
                asset_id=_OVERLAY_ASSET_ID,
                source_usd=overlay_usd,
                role="scene_overlay",
                license="CC-BY-NC-4.0",
                source_uri="example://dryingbox-03-dynamic",
                attribution=("Example source-bound dynamic package",),
                redistributable=False,
                root_prim_path="/World",
            ),
        },
        package_root,
    )
    return package_root


def _room_references(scene_path: Path) -> list[object]:
    Sdf = pytest.importorskip("pxr.Sdf")
    layer = Sdf.Layer.FindOrOpen(str(scene_path))
    assert layer
    room = layer.GetPrimAtPath(
        "/World/scientific_workbench_bimanual_pour/room"
    )
    assert room
    return list(room.referenceList.GetAddedOrExplicitItems())


def _tree_hash(root: Path) -> str:
    digest = sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_genmanip_export_writes_discoverable_scene_config_and_metadata(tmp_path: Path) -> None:
    package_root = _build_package(tmp_path)

    result = export_genmanip_collected_package(package_root)

    output = result.output_dir
    config = yaml.safe_load((output / "tasks" / "config.yaml").read_text(encoding="utf-8"))
    evaluation = config["evaluation_configs"][0]
    assert config["demonstration_configs"] == []
    assert evaluation["table_uid"] == "table"
    assert evaluation["robots"] == [{"type": "manip/lift2/R5a", "position": [0.0, 0.0, 0.0]}]
    assert evaluation["action_contract"]["action_shape"] == [16]
    assert evaluation["action_contract"]["base_motion_shape"] == [3]
    assert evaluation["usd_name"] == (
        "collected_packages/scientific_workbench_bimanual_pour/"
        "assets/scene_usds/scenario_forge/scientific_workbench_bimanual_pour/scene"
    )
    metric_types = {
        metric["type"]
        for stage in evaluation["generation_config"]["goal"]
        for alternative in stage
        for metric in alternative
    }
    assert metric_types == {
        "manip/default/sr_based_genmanip_range",
        "manip/default/sr_based_genmanip_axis_align",
    }
    axis_metrics = [
        metric
        for stage in evaluation["generation_config"]["goal"]
        for alternative in stage
        for metric in alternative
        if metric["type"] == "manip/default/sr_based_genmanip_axis_align"
    ]
    assert [(metric["obj1_axis"], metric["obj2_axis"]) for metric in axis_metrics] == [
        ("y", "y"),
        ("y", "y"),
    ]

    scene_path = output / "assets/scene_usds/scenario_forge/scientific_workbench_bimanual_pour/scene.usda"
    scene_text = scene_path.read_text(encoding="utf-8")
    assert 'defaultPrim = "World"' in scene_text
    assert 'def Xform "scientific_workbench_bimanual_pour"' in scene_text
    assert 'def Xform "obj_obj_conical_bottle03"' in scene_text
    assert 'def Xform "obj_obj_graduated_cylinder_03"' in scene_text
    assert 'def Xform "obj_table"' in scene_text
    assert 'def Xform "lift2"' not in scene_text
    assert 'def Xform "franka"' not in scene_text

    Usd = pytest.importorskip("pxr.Usd")
    stage = Usd.Stage.Open(str(scene_path))
    world_children = list(stage.GetPrimAtPath("/World").GetChildren())
    assert [prim.GetName() for prim in world_children] == ["scientific_workbench_bimanual_pour"]
    scene_uid = "/World/scientific_workbench_bimanual_pour"
    assert stage.GetPrimAtPath(f"{scene_uid}/obj_obj_conical_bottle03")
    assert stage.GetPrimAtPath(f"{scene_uid}/obj_obj_graduated_cylinder_03")
    assert stage.GetPrimAtPath(f"{scene_uid}/obj_table")
    assert not stage.GetPrimAtPath(f"{scene_uid}/room/conical_bottle03").IsActive()
    assert not stage.GetPrimAtPath(f"{scene_uid}/room/Cube").IsActive()
    room = stage.GetPrimAtPath(f"{scene_uid}/room")
    assert tuple(room.GetAttribute("xformOp:translate").Get()) == (-1.0, 2.0, 0.0)
    assert tuple(room.GetAttribute("xformOp:orient").Get().GetImaginary()) == (
        0.0,
        0.0,
        0.0,
    )
    background_fixture = stage.GetPrimAtPath(f"{scene_uid}/room/background_fixture")
    assert list(background_fixture.GetAttribute("xformOpOrder").Get())[0] == (
        "!resetXformStack!"
    )
    expected_materials = {
        f"{scene_uid}/obj_table/surface": f"{scene_uid}/room/Looks/TableMat",
        f"{scene_uid}/obj_obj_conical_bottle03/mesh": (
            f"{scene_uid}/room/Looks/GlassFlask"
        ),
        f"{scene_uid}/obj_obj_graduated_cylinder_03/mesh": (
            f"{scene_uid}/room/Looks/GlassCylinder"
        ),
    }
    for prim_path, material_path in expected_materials.items():
        relationship = stage.GetPrimAtPath(prim_path).GetRelationship("material:binding")
        assert [str(target) for target in relationship.GetTargets()] == [material_path]
        assert stage.GetPrimAtPath(material_path)
    active_physics_scenes = [
        prim
        for prim in stage.Traverse()
        if prim.IsActive() and prim.GetTypeName() == "PhysicsScene"
    ]
    assert len(active_physics_scenes) == 1
    assert active_physics_scenes[0].GetPath().pathString == "/physicsScene"

    task_name = evaluation["task_name"]
    episode_dir = output / "tasks" / task_name / "000"
    episode_json = json.loads((episode_dir / "episode_metadata.json").read_text(encoding="utf-8"))
    with (episode_dir / "meta_info.pkl").open("rb") as handle:
        episode_pickle = pickle.load(handle)
    assert episode_pickle == episode_json
    assert episode_json["task_name"] == task_name
    assert episode_json["episode_name"] == "000"
    assert episode_json["task_data"]["goal"] == evaluation["generation_config"]["goal"]
    initial_layout = episode_json["task_data"]["initial_layout"]
    assert set(initial_layout) == {
        "00000000000000000000000000000000",
        "obj_conical_bottle03",
        "obj_graduated_cylinder_03",
        "lift2",
    }
    assert initial_layout["lift2"]["type"] == "robot"
    assert len(initial_layout["lift2"]["joint_positions"]) == 16

    manifest = json.loads((output / "package_manifest.json").read_text(encoding="utf-8"))
    assert manifest["claim_scope"] == "kinematic_proxy"
    assert "liquid_transfer_claim_allowed" not in manifest
    assert manifest["validation_scope"]["liquid_transfer"] is False
    assert manifest["runtime_requirements"]["robot_profile"] == "manip/lift2/R5a"


def test_genmanip_export_composes_scene_overlay_before_base_without_local_physics(
    tmp_path: Path,
) -> None:
    package_root = _build_overlay_package(tmp_path)

    result = export_genmanip_collected_package(package_root)

    scene_path = (
        result.output_dir
        / "assets/scene_usds/scenario_forge/scientific_workbench_bimanual_pour/scene.usda"
    )
    references = _room_references(scene_path)
    assert [reference.assetPath for reference in references] == [
        f"source_bundle/{_OVERLAY_ASSET_ID}/asset.usda",
        "source_bundle/scientific_workbench_environment/scene.usda",
    ]
    assert [str(reference.primPath) for reference in references] == [
        "/World",
        "/World",
    ]

    Usd = pytest.importorskip("pxr.Usd")
    stage = Usd.Stage.Open(str(scene_path))
    assert stage
    drying_box_path = (
        "/World/scientific_workbench_bimanual_pour/room/DryingBox_03"
    )
    drying_box = stage.GetPrimAtPath(drying_box_path)
    assert drying_box and drying_box.IsActive()
    assert [
        prim.GetPath().pathString
        for prim in stage.Traverse()
        if prim.IsActive() and prim.GetName() == "DryingBox_03"
    ] == [drying_box_path]

    winner = drying_box.GetAttribute("scenarioForge:compositionWinner")
    assert winner.Get() == "overlay"
    property_stack = winner.GetPropertyStack()
    assert len(property_stack) == 2
    assert Path(property_stack[0].layer.realPath).as_posix().endswith(
        f"/source_bundle/{_OVERLAY_ASSET_ID}/asset.usda"
    )
    assert Path(property_stack[1].layer.realPath).as_posix().endswith(
        "/source_bundle/scientific_workbench_environment/scene.usda"
    )
    assert drying_box.GetAttribute("physics:mass").Get() == pytest.approx(1.0)

    scene_text = scene_path.read_text(encoding="utf-8")
    for locally_forbidden_physics_token in (
        "physics:mass",
        "physics:diagonalInertia",
        "physics:centerOfMass",
        "physics:principalAxes",
        "PhysicsMassAPI",
    ):
        assert locally_forbidden_physics_token not in scene_text


def test_genmanip_export_rejects_overlay_missing_from_asset_manifest(
    tmp_path: Path,
) -> None:
    package_root = _build_package(tmp_path)
    scenario_path = package_root / "scenario.yaml"
    scenario = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
    scenario["schema_version"] = "scenario-spec/v0.2"
    scenario["scene"]["overlay_asset_ids"] = [_OVERLAY_ASSET_ID]
    scenario_path.write_text(
        yaml.safe_dump(scenario, sort_keys=False),
        encoding="utf-8",
    )
    output_dir = tmp_path / "collected"

    with pytest.raises(
        GenManipExportError,
        match=rf"asset manifest.*{_OVERLAY_ASSET_ID}|overlay.*{_OVERLAY_ASSET_ID}",
    ):
        export_genmanip_collected_package(package_root, output_dir)

    assert not output_dir.exists()


def test_genmanip_export_rejects_v01_scenario_with_overlay(tmp_path: Path) -> None:
    package_root = _build_overlay_package(tmp_path)
    scenario_path = package_root / "scenario.yaml"
    scenario = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
    scenario["schema_version"] = "scenario-spec/v0.1"
    scenario_path.write_text(yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8")

    with pytest.raises(GenManipExportError, match="scenario-spec/v0.2"):
        export_genmanip_collected_package(package_root, tmp_path / "collected")


def test_genmanip_export_rejects_overlay_asset_with_wrong_role(tmp_path: Path) -> None:
    package_root = _build_overlay_package(tmp_path)
    manifest_path = package_root / "assets/asset_manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    overlay = next(
        item for item in manifest["assets"] if item["asset_id"] == _OVERLAY_ASSET_ID
    )
    overlay["role"] = "object"
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(GenManipExportError, match="role.*scene_overlay"):
        export_genmanip_collected_package(package_root, tmp_path / "collected")


def test_genmanip_export_rejects_overlay_reused_as_object_asset(tmp_path: Path) -> None:
    package_root = _build_overlay_package(tmp_path)
    scenario_path = package_root / "scenario.yaml"
    scenario = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
    scenario["objects"][0]["asset_id"] = _OVERLAY_ASSET_ID
    scenario_path.write_text(yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8")

    with pytest.raises(GenManipExportError, match="overlay.*object"):
        export_genmanip_collected_package(package_root, tmp_path / "collected")


def test_genmanip_export_without_overlays_keeps_single_base_reference(
    tmp_path: Path,
) -> None:
    package_root = _build_package(tmp_path)

    result = export_genmanip_collected_package(package_root)

    scene_path = (
        result.output_dir
        / "assets/scene_usds/scenario_forge/scientific_workbench_bimanual_pour/scene.usda"
    )
    references = _room_references(scene_path)
    assert [reference.assetPath for reference in references] == [
        "source_bundle/scientific_workbench_environment/scene.usda"
    ]
    assert [str(reference.primPath) for reference in references] == ["/World"]


def test_genmanip_export_is_deterministic_and_removes_stale_files(tmp_path: Path) -> None:
    package_root = _build_package(tmp_path)
    first = export_genmanip_collected_package(package_root)
    first_hash = _tree_hash(first.output_dir)
    (first.output_dir / "stale.txt").write_text("old", encoding="utf-8")

    second = export_genmanip_collected_package(package_root)

    assert not (second.output_dir / "stale.txt").exists()
    assert _tree_hash(second.output_dir) == first_hash


@pytest.mark.parametrize("output_kind", ["package", "package_parent"])
def test_genmanip_export_rejects_output_that_contains_package_input(
    tmp_path: Path, output_kind: str
) -> None:
    package_root = _build_package(tmp_path)
    output_dir = package_root if output_kind == "package" else package_root.parent

    with pytest.raises(GenManipExportError, match="must not contain package_dir"):
        export_genmanip_collected_package(package_root, output_dir)


@pytest.mark.parametrize("relative_output", ["assets", "scene", "task"])
def test_genmanip_export_rejects_non_adapter_output_inside_package_without_writing(
    tmp_path: Path, relative_output: str
) -> None:
    package_root = _build_package(tmp_path)
    before = _tree_hash(package_root)

    with pytest.raises(GenManipExportError, match="default adapter path"):
        export_genmanip_collected_package(package_root, package_root / relative_output)

    assert _tree_hash(package_root) == before


def test_genmanip_export_does_not_delete_preexisting_sibling_staging_directory(
    tmp_path: Path,
) -> None:
    package_root = _build_package(tmp_path)
    output_dir = tmp_path / "collected"
    previous_staging = tmp_path / ".collected.staging"
    previous_staging.mkdir()
    marker = previous_staging / "belongs-to-user.txt"
    marker.write_text("keep", encoding="utf-8")

    export_genmanip_collected_package(package_root, output_dir)

    assert marker.read_text(encoding="utf-8") == "keep"


@pytest.mark.parametrize("explicit_default", [False, True])
def test_genmanip_export_rejects_default_adapter_parent_symlink_escape(
    tmp_path: Path, explicit_default: bool
) -> None:
    package_root = _build_package(tmp_path)
    external = tmp_path / "external-adapters"
    external.mkdir()
    marker = external / "belongs-to-user.txt"
    marker.write_text("keep", encoding="utf-8")
    (package_root / "adapters").symlink_to(external, target_is_directory=True)
    output = package_root / "adapters" / "ebench" / "genmanip"

    with pytest.raises(GenManipExportError, match="default adapter path.*symlink|symlink"):
        export_genmanip_collected_package(
            package_root,
            output if explicit_default else None,
        )

    assert marker.read_text(encoding="utf-8") == "keep"
    assert not (external / "ebench").exists()


def test_genmanip_export_rejects_aliased_default_path_through_parent_symlink(
    tmp_path: Path,
) -> None:
    package_root = _build_package(tmp_path)
    external = tmp_path / "external-adapters"
    existing_output = external / "ebench" / "genmanip"
    existing_output.mkdir(parents=True)
    marker = existing_output / "belongs-to-user.txt"
    marker.write_text("keep", encoding="utf-8")
    (package_root / "adapters").symlink_to(external, target_is_directory=True)
    aliased_default = (
        package_root / "adapters" / "ebench" / ".." / "ebench" / "genmanip"
    )

    with pytest.raises(GenManipExportError, match="default adapter path.*symlink|symlink"):
        export_genmanip_collected_package(package_root, aliased_default)

    assert marker.read_text(encoding="utf-8") == "keep"


def test_genmanip_export_rejects_any_success_operator_instead_of_changing_semantics(
    tmp_path: Path,
) -> None:
    source_usd = _write_source_scene(tmp_path)
    scenario = _scenario_mapping()
    success = dict(scenario["success"])  # type: ignore[arg-type]
    success["operator"] = "any"
    scenario["success"] = success
    package_root = tmp_path / "package"
    compile_scenario_package(
        ScenarioSpec.from_mapping(scenario),
        {
            "scientific_workbench_environment": LocalUSDAssetSource(
                asset_id="scientific_workbench_environment",
                source_usd=source_usd,
                role="environment",
                license="CC-BY-NC-4.0",
                source_uri="example://scientific-workbench-scene",
                redistributable=False,
            )
        },
        package_root,
    )

    with pytest.raises(GenManipExportError, match="success.operator.*all"):
        export_genmanip_collected_package(package_root, tmp_path / "collected")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("canonical_usd", "assets/../../outside.usd", "canonical|lock"),
        ("license", "Apache-2.0", "license|lock"),
        ("redistributable", True, "redistributable|provenance"),
    ],
)
def test_genmanip_export_rejects_tampered_asset_manifest_before_writing(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    package_root = _build_package(tmp_path)
    manifest_path = package_root / "assets" / "asset_manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"][0][field] = value
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    output_dir = tmp_path / "collected"

    with pytest.raises(GenManipExportError, match=message):
        export_genmanip_collected_package(package_root, output_dir)

    assert not output_dir.exists()


@pytest.mark.parametrize("unsafe_field", ["scenario_id", "seed"])
def test_genmanip_export_rejects_unsafe_path_segments_before_writing(
    tmp_path: Path, unsafe_field: str
) -> None:
    package_root = _build_package(tmp_path)
    escaped = tmp_path / f"escaped-{unsafe_field}"
    scenario_path = package_root / "scenario.yaml"
    scenario = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
    scenario[unsafe_field] = str(escaped)
    scenario_path.write_text(yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8")
    if unsafe_field == "scenario_id":
        manifest_path = package_root / "manifest.yaml"
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest["package_id"] = str(escaped)
        manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    with pytest.raises(GenManipExportError, match=unsafe_field):
        export_genmanip_collected_package(package_root, tmp_path / "collected")

    assert not escaped.exists()

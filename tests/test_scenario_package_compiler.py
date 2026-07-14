from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from scenario_forge.assets.source import LocalUSDAssetSource
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.package_compiler import compile_scenario_package
from scenario_forge.package import validate_package
from tests.test_scenario_spec import _scenario_mapping


def _write_source_scene(root: Path) -> Path:
    source = root / "source" / "scene.usda"
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
    def Scope "Looks"
    {
        def Material "TableMat" {}
        def Material "GlassFlask" {}
        def Material "GlassCylinder" {}
    }
    def PhysicsScene "PhysicsScene" {}
    def Xform "table"
    {
        def Cube "surface" (
            prepend apiSchemas = ["MaterialBindingAPI"]
        )
        {
            rel material:binding = </World/Looks/TableMat>
        }
    }
    def Xform "conical_bottle03"
    {
        def Cylinder "mesh" (
            prepend apiSchemas = ["MaterialBindingAPI", "PhysicsCollisionAPI", "PhysicsRigidBodyAPI"]
        )
        {
            rel material:binding = </World/Looks/GlassFlask>
        }
    }
    def Xform "graduated_cylinder_03"
    {
        def Cylinder "mesh" (
            prepend apiSchemas = ["MaterialBindingAPI", "PhysicsCollisionAPI", "PhysicsRigidBodyAPI"]
        )
        {
            rel material:binding = </World/Looks/GlassCylinder>
        }
    }
    def Xform "background_fixture"
    {
        double3 xformOp:translate = (3, 4, 5)
        quatd xformOp:orient = (1, 0, 0, 0)
        double3 xformOp:scale = (1, 1, 1)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient", "xformOp:scale"]
    }
}
""",
        encoding="utf-8",
    )
    return source


def _asset_source(
    source_usd: Path,
    *,
    exclude_relative_paths: tuple[str, ...] | None = None,
) -> LocalUSDAssetSource:
    if exclude_relative_paths is not None:
        return LocalUSDAssetSource(
            asset_id="scientific_workbench_environment",
            source_usd=source_usd,
            role="environment",
            license="CC-BY-NC-4.0",
            source_uri="example://scientific-workbench-scene",
            attribution=("Example scientific workbench asset",),
            redistributable=False,
            exclude_relative_paths=exclude_relative_paths,
        )
    return LocalUSDAssetSource(
        asset_id="scientific_workbench_environment",
        source_usd=source_usd,
        role="environment",
        license="CC-BY-NC-4.0",
        source_uri="example://scientific-workbench-scene",
        attribution=("Example scientific workbench asset",),
        redistributable=False,
    )


def _tree_hash(root: Path) -> str:
    digest = sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _scenario_with_overlays(*overlay_asset_ids: str) -> ScenarioSpec:
    scenario = _scenario_mapping()
    scenario["schema_version"] = "scenario-spec/v0.2"
    scene = dict(scenario["scene"])  # type: ignore[arg-type]
    scene["overlay_asset_ids"] = list(overlay_asset_ids)
    scenario["scene"] = scene
    return ScenarioSpec.from_mapping(scenario)


def _write_scene_overlay(
    root: Path,
    *,
    root_prim_name: str = "World",
    marker_value: str = "overlay",
) -> Path:
    overlay = root / "overlay" / "overlay.usda"
    overlay.parent.mkdir(parents=True)
    overlay.write_text(
        f'''#usda 1.0
(
    defaultPrim = "{root_prim_name}"
    metersPerUnit = 1
    upAxis = "Z"
)

over "{root_prim_name}"
{{
    over "background_fixture"
    {{
        string scenarioForge:layerOrigin = "{marker_value}"
    }}
}}
''',
        encoding="utf-8",
    )
    return overlay


def _write_object_only_asset(root: Path) -> Path:
    source = root / "object" / "standalone_flask.usda"
    source.parent.mkdir(parents=True)
    source.write_text(
        '''#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{
    def Xform "conical_bottle03"
    {
        string scenarioForge:assetOrigin = "object-only"
    }
}
''',
        encoding="utf-8",
    )
    return source


def test_package_compiler_builds_portable_v02_package_from_scenario_spec(tmp_path: Path) -> None:
    source_usd = _write_source_scene(tmp_path)
    spec = ScenarioSpec.from_mapping(_scenario_mapping())
    package_root = tmp_path / "package"

    result = compile_scenario_package(
        spec,
        {"scientific_workbench_environment": _asset_source(source_usd)},
        package_root,
    )

    report = validate_package(package_root, require_asset_lock=True)
    assert report.ok, report.messages
    assert result.package_root == package_root
    scenario_data = yaml.safe_load((package_root / "scenario.yaml").read_text(encoding="utf-8"))
    assert scenario_data == _scenario_mapping()
    scene = (package_root / "scene" / "main.usda").read_text(encoding="utf-8")
    assert "subLayers" in scene
    assert "@../assets/scientific_workbench_environment/scene.usda@" in scene
    assert 'over "conical_bottle03"' in scene
    assert "obj_obj_conical_bottle03" not in scene
    assert "double3 xformOp:translate = (-1, 2, 0)" in scene
    assert 'over "Cube" (' in scene
    assert "active = false" in scene
    assert scene.count('"!resetXformStack!"') >= 4
    task = yaml.safe_load((package_root / "task" / "task.yaml").read_text(encoding="utf-8"))
    assert task["invariants"][0]["type"] == "maintain_grasp"
    assert task["success"]["claim_scope"] == "kinematic_proxy"
    validation = yaml.safe_load(
        (package_root / "evidence" / "validation_report.yaml").read_text(encoding="utf-8")
    )
    assert validation["schema_version"] == "validation-report/v0.2"
    assert validation["overall_level"] == "asset_locked"
    asset = yaml.safe_load(
        (package_root / "assets" / "asset_manifest.yaml").read_text(encoding="utf-8")
    )["assets"][0]
    assert asset["redistributable"] is False
    assert not Path(asset["source_uri"]).is_absolute()


def test_portable_scene_is_valid_usd_and_world_anchor_keeps_standard_trs(
    tmp_path: Path,
) -> None:
    Usd = pytest.importorskip("pxr.Usd")
    UsdGeom = pytest.importorskip("pxr.UsdGeom")
    source_usd = _write_source_scene(tmp_path)
    package_root = tmp_path / "package"

    compile_scenario_package(
        ScenarioSpec.from_mapping(_scenario_mapping()),
        {"scientific_workbench_environment": _asset_source(source_usd)},
        package_root,
    )

    stage = Usd.Stage.Open(str(package_root / "scene" / "main.usda"))
    assert stage
    root = stage.GetPrimAtPath("/World")
    assert tuple(root.GetAttribute("xformOp:translate").Get()) == (-1.0, 2.0, 0.0)
    anchored = stage.GetPrimAtPath("/World/background_fixture")
    assert list(anchored.GetAttribute("xformOpOrder").Get()) == [
        "!resetXformStack!",
        "xformOp:translate",
        "xformOp:orient",
        "xformOp:scale",
    ]
    world_translation = (
        UsdGeom.XformCache().GetLocalToWorldTransform(anchored).ExtractTranslation()
    )
    assert tuple(world_translation) == pytest.approx((3.0, 4.0, 5.0))


def test_package_compiler_rejects_output_containing_symlinked_source_target(
    tmp_path: Path,
) -> None:
    package_root = tmp_path / "package"
    real_source = package_root / "scene.usda"
    real_source.parent.mkdir()
    real_source.write_text("#usda 1.0\n", encoding="utf-8")
    link = tmp_path / "source-link" / "scene.usda"
    link.parent.mkdir()
    link.symlink_to(real_source)
    source = LocalUSDAssetSource(
        asset_id="scientific_workbench_environment",
        source_usd=link,
        role="environment",
        license="CC-BY-NC-4.0",
        source_uri="example://symlinked-scene",
        redistributable=False,
    )

    with pytest.raises(ValueError, match="must not overlap"):
        compile_scenario_package(
            ScenarioSpec.from_mapping(_scenario_mapping()),
            {"scientific_workbench_environment": source},
            package_root,
        )

    assert real_source.read_text(encoding="utf-8") == "#usda 1.0\n"


def test_package_compiler_replaces_output_deterministically(tmp_path: Path) -> None:
    source_usd = _write_source_scene(tmp_path)
    spec = ScenarioSpec.from_mapping(_scenario_mapping())
    sources = {"scientific_workbench_environment": _asset_source(source_usd)}
    package_root = tmp_path / "package"

    compile_scenario_package(spec, sources, package_root)
    first_hash = _tree_hash(package_root)
    (package_root / "stale.txt").write_text("old", encoding="utf-8")
    compile_scenario_package(spec, sources, package_root)

    assert not (package_root / "stale.txt").exists()
    assert _tree_hash(package_root) == first_hash


def test_package_compiler_excludes_declared_top_level_source_artifacts(tmp_path: Path) -> None:
    source_usd = _write_source_scene(tmp_path)
    reports_dir = source_usd.parent / "_reports"
    reports_dir.mkdir()
    (reports_dir / "old.png").write_bytes(b"old upstream render")
    runtime_assets_dir = source_usd.parent / "reports_assets"
    runtime_assets_dir.mkdir()
    (runtime_assets_dir / "keep.txt").write_text("runtime dependency", encoding="utf-8")
    spec = ScenarioSpec.from_mapping(_scenario_mapping())
    package_root = tmp_path / "package"

    compile_scenario_package(
        spec,
        {
            "scientific_workbench_environment": _asset_source(
                source_usd,
                exclude_relative_paths=("_reports",),
            )
        },
        package_root,
    )

    copied_source = package_root / "assets" / "scientific_workbench_environment"
    assert not (copied_source / "_reports").exists()
    assert (copied_source / "reports_assets" / "keep.txt").read_text(encoding="utf-8") == (
        "runtime dependency"
    )

    asset_manifest = yaml.safe_load(
        (package_root / "assets" / "asset_manifest.yaml").read_text(encoding="utf-8")
    )
    assert asset_manifest["assets"][0]["excluded_relative_paths"] == ["_reports"]

    provenance = yaml.safe_load(
        (package_root / "provenance" / "provenance.yaml").read_text(encoding="utf-8")
    )
    assert provenance["assets"][0]["excluded_relative_paths"] == ["_reports"]

    generation_plan = yaml.safe_load(
        (package_root / "generation" / "plan.yaml").read_text(encoding="utf-8")
    )
    copy_operation = next(
        operation
        for operation in generation_plan["operations"]
        if operation["type"] == "copy_usd_closure"
    )
    assert copy_operation["excluded_relative_paths"] == ["_reports"]


@pytest.mark.parametrize(
    "exclude_relative_paths",
    [
        ("/absolute/reports",),
        ("../_reports",),
        ("_reports/*",),
        ("scene.usda",),
    ],
    ids=["absolute", "parent-traversal", "glob", "canonical-usd"],
)
def test_local_usd_asset_source_rejects_unsafe_or_canonical_exclusions(
    tmp_path: Path,
    exclude_relative_paths: tuple[str, ...],
) -> None:
    source_usd = _write_source_scene(tmp_path)

    with pytest.raises(ValueError):
        _asset_source(
            source_usd,
            exclude_relative_paths=exclude_relative_paths,
        )


def test_scene_overlays_compose_strongest_first_and_win_conflicting_opinions(
    tmp_path: Path,
) -> None:
    Usd = pytest.importorskip("pxr.Usd")
    base_usd = _write_source_scene(tmp_path / "base")
    base_usd.write_text(
        base_usd.read_text(encoding="utf-8").replace(
            '    def Xform "background_fixture"\n    {',
            (
                '    def Xform "background_fixture"\n'
                "    {\n"
                '        string scenarioForge:layerOrigin = "base"\n'
            ),
        ),
        encoding="utf-8",
    )
    overlay_usd = _write_scene_overlay(tmp_path)
    spec = _scenario_with_overlays("scientific_workbench_dryingbox_overlay")
    package_root = tmp_path / "package"

    compile_scenario_package(
        spec,
        {
            "scientific_workbench_environment": _asset_source(base_usd),
            "scientific_workbench_dryingbox_overlay": LocalUSDAssetSource(
                asset_id="scientific_workbench_dryingbox_overlay",
                source_usd=overlay_usd,
                root_prim_path="/World",
                role="scene_overlay",
                license="CC-BY-NC-4.0",
                source_uri="convert-asset://dryingbox-03/profile-r1",
                redistributable=False,
            ),
        },
        package_root,
    )

    scene_path = package_root / "scene" / "main.usda"
    scene_text = scene_path.read_text(encoding="utf-8")
    overlay_reference = (
        "@../assets/scientific_workbench_dryingbox_overlay/overlay.usda@"
    )
    base_reference = (
        "@../assets/scientific_workbench_environment/scene.usda@"
    )
    assert scene_text.index(overlay_reference) < scene_text.index(base_reference)

    stage = Usd.Stage.Open(str(scene_path))
    assert stage
    marker = stage.GetPrimAtPath("/World/background_fixture").GetAttribute(
        "scenarioForge:layerOrigin"
    )
    assert marker.Get() == "overlay"
    property_stack = marker.GetPropertyStack()
    assert property_stack
    strongest_layer = Path(property_stack[0].layer.realPath)
    copied_overlay = (
        package_root
        / "assets"
        / "scientific_workbench_dryingbox_overlay"
        / "overlay.usda"
    )
    assert strongest_layer.resolve() == copied_overlay.resolve()


def test_scene_overlay_root_prim_must_match_scene_root(tmp_path: Path) -> None:
    base_usd = _write_source_scene(tmp_path / "base")
    overlay_usd = _write_scene_overlay(
        tmp_path,
        root_prim_name="Asset",
    )
    spec = _scenario_with_overlays("mismatched_overlay")

    with pytest.raises(
        ValueError,
        match=r"overlay.*root_prim_path|root_prim_path.*scene\.root_prim_path",
    ):
        compile_scenario_package(
            spec,
            {
                "scientific_workbench_environment": _asset_source(base_usd),
                "mismatched_overlay": LocalUSDAssetSource(
                    asset_id="mismatched_overlay",
                    source_usd=overlay_usd,
                    root_prim_path="/Asset",
                    role="scene_overlay",
                    license="CC-BY-NC-4.0",
                    source_uri="convert-asset://mismatched-overlay",
                    redistributable=False,
                ),
            },
            tmp_path / "package",
        )


def test_scene_overlay_source_must_use_scene_overlay_role(tmp_path: Path) -> None:
    base_usd = _write_source_scene(tmp_path / "base")
    overlay_usd = _write_scene_overlay(tmp_path)
    spec = _scenario_with_overlays("wrong_role_overlay")

    with pytest.raises(ValueError, match="role.*scene_overlay"):
        compile_scenario_package(
            spec,
            {
                "scientific_workbench_environment": _asset_source(base_usd),
                "wrong_role_overlay": LocalUSDAssetSource(
                    asset_id="wrong_role_overlay",
                    source_usd=overlay_usd,
                    root_prim_path="/World",
                    role="object",
                    license="CC-BY-NC-4.0",
                    source_uri="convert-asset://wrong-role-overlay",
                    redistributable=False,
                ),
            },
            tmp_path / "package",
        )


def test_package_compiler_rejects_missing_scene_overlay_source(tmp_path: Path) -> None:
    base_usd = _write_source_scene(tmp_path)
    spec = _scenario_with_overlays("missing_overlay")

    with pytest.raises(
        ValueError,
        match=r"missing local USD asset source.*missing_overlay",
    ):
        compile_scenario_package(
            spec,
            {"scientific_workbench_environment": _asset_source(base_usd)},
            tmp_path / "package",
        )


def test_object_only_asset_preserves_legacy_sublayer_composition(
    tmp_path: Path,
) -> None:
    base_usd = _write_source_scene(tmp_path / "base")
    object_usd = _write_object_only_asset(tmp_path)
    scenario = _scenario_mapping()
    objects = list(scenario["objects"])  # type: ignore[arg-type]
    standalone_object = dict(objects[1])  # type: ignore[arg-type]
    standalone_object["asset_id"] = "standalone_conical_flask"
    objects[1] = standalone_object
    scenario["objects"] = objects
    package_root = tmp_path / "package"

    compile_scenario_package(
        ScenarioSpec.from_mapping(scenario),
        {
            "scientific_workbench_environment": _asset_source(base_usd),
            "standalone_conical_flask": LocalUSDAssetSource(
                asset_id="standalone_conical_flask",
                source_usd=object_usd,
                role="object",
                license="CC-BY-NC-4.0",
                source_uri="example://standalone-conical-flask",
                redistributable=False,
            ),
        },
        package_root,
    )

    scene_text = (package_root / "scene" / "main.usda").read_text(
        encoding="utf-8"
    )
    sublayer_block = scene_text.split("]", maxsplit=1)[0]
    object_reference = (
        "../assets/standalone_conical_flask/standalone_flask.usda"
    )
    assert f"@{object_reference}@" in sublayer_block
    assert f"prepend references = @{object_reference}@" not in scene_text

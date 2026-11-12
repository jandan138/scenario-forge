"""Portable colleague-layout export without changing task semantics."""
import pytest

from scripts.export_task09_colleague_layout import export_layout, check_layout, make_validation_fixture


@pytest.fixture
def source(tmp_path):
    pytest.importorskip('pxr')
    from pxr import Usd, UsdGeom, UsdPhysics, Sdf
    root = tmp_path/'source'
    (root/'scene').mkdir(parents=True)
    texture = root/'assets/composed/SubUSDs/textures/salt.png'
    texture.parent.mkdir(parents=True)
    texture.write_bytes(b'unchanged texture')
    for version in ('41', '45'):
        mdl = root/f'assets/material_closure/isaac{version}/task09/deps/mdl'
        mdl.mkdir(parents=True)
        (mdl/'root.mdl').write_text('import ::helper::*;')
        (mdl/'helper.mdl').write_text('retained sibling dependency '+version)
    stage = Usd.Stage.CreateNew(str(root/'scene/main.usda'))
    w = stage.DefinePrim('/World', 'Xform')
    stage.SetDefaultPrim(w)
    UsdGeom.SetStageMetersPerUnit(stage, 1.)
    UsdGeom.SetStageUpAxis(stage, 'Z')
    obj = UsdGeom.Cube.Define(stage, '/World/Sample').GetPrim()
    UsdPhysics.RigidBodyAPI.Apply(obj)
    UsdPhysics.MassAPI.Apply(obj).CreateMassAttr(.001)
    obj.CreateAttribute('texture', Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(str(texture)))
    obj.CreateAttribute('script', Sdf.ValueTypeNames.String).Set('original controller')
    stage.GetRootLayer().Save()
    for version in ('41', '45'):
        stage = Usd.Stage.CreateNew(str(root/f'scene/runtime{version}.usda'))
        stage.GetRootLayer().subLayerPaths = ['./main.usda']
        p = stage.OverridePrim('/World/Sample')
        p.CreateAttribute('node:type', Sdf.ValueTypeNames.Token).Set('node'+version)
        p.CreateAttribute('info:mdl:sourceAsset', Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(
            str(root/f'assets/material_closure/isaac{version}/task09/deps/mdl/root.mdl')))
        stage.GetRootLayer().Save()
        stage = Usd.Stage.CreateNew(str(root/f'scene/demo{version}.usda'))
        stage.GetRootLayer().subLayerPaths = [f'./runtime{version}.usda']
        UsdPhysics.Scene.Define(stage, '/World/PhysicsScene')
        stage.GetRootLayer().Save()
    return root


def test_export_preserves_values_and_localizes_both_runtime_dependencies(source, tmp_path):
    from pxr import Usd, UsdGeom
    out = tmp_path/'export'
    report = export_layout(source, out)
    assert report['status'] == 'pass'
    assert {p.name for p in out.iterdir()} == {'scene.usd', 'scene_isaac45.usda', 'SubUSDs'}
    for version, entry in [('41', 'scene.usd'), ('45', 'scene_isaac45.usda')]:
        stage = Usd.Stage.Open(str(out/entry))
        assert UsdGeom.GetStageMetersPerUnit(stage) == 1.
        assert UsdGeom.GetStageUpAxis(stage) == 'Z'
        assert stage.GetDefaultPrim().GetPath().pathString == '/World'
        assert stage.GetPrimAtPath('/World/Sample').GetAttribute('node:type').Get() == 'node'+version
        assert (out/f'SubUSDs/materials/isaac{version}/task09/helper.mdl').is_file()
    assert not Usd.Stage.Open(str(out/'scene.usd')).GetRootLayer().subLayerPaths
    check_layout(out, source)


def test_rejects_existing_destination_without_touching_it(source, tmp_path):
    out = tmp_path/'occupied'
    out.mkdir()
    marker = out/'keep'
    marker.write_text('do not overwrite')
    with pytest.raises(FileExistsError):
        export_layout(source, out)
    assert marker.read_text() == 'do not overwrite'


def test_validation_environment_stays_outside_export(source, tmp_path):
    from pxr import Usd, UsdPhysics
    out = tmp_path/'export'
    export_layout(source, out)
    fixture = make_validation_fixture(out, source, tmp_path/'fixture')
    clean = Usd.Stage.Open(str(out/'scene.usd'))
    assert not any(p.IsA(UsdPhysics.Scene) for p in clean.Traverse())
    stage = Usd.Stage.Open(str(fixture/'scene/demo41.usda'))
    assert stage.GetPrimAtPath('/World/PhysicsScene').IsA(UsdPhysics.Scene)

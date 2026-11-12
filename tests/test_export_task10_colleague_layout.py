"""Task10 shared layout must be self contained and preserve USD semantics."""
from pxr import Usd, UsdGeom, Sdf

from scripts.export_task10_colleague_layout import export_layout


def test_export_localizes_texture_without_changing_bytes(tmp_path):
    package = tmp_path/'package'
    (package/'scene').mkdir(parents=True)
    texture = package/'assets/composed/producer/source/SubUSDs/textures/label.png'
    texture.parent.mkdir(parents=True)
    texture.write_bytes(b'unchanged-test-resource')
    for name in ('main','isaac45'):
        stage = Usd.Stage.CreateNew(str(package/f'scene/{name}.usda'))
        root = UsdGeom.Xform.Define(stage,'/World').GetPrim()
        stage.SetDefaultPrim(root)
        UsdGeom.SetStageMetersPerUnit(stage,1.)
        UsdGeom.SetStageUpAxis(stage,'Z')
        root.CreateAttribute('test:texture',Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(str(texture)))
        blocked = root.CreateAttribute('primvars:blocked_test',Sdf.ValueTypeNames.BoolArray,custom=True)
        blocked.Block()
        stage.GetRootLayer().Save()
    out = tmp_path/'shared'
    report = export_layout(package,out)
    assert report['status'] == 'pass'
    assert (out/'SubUSDs/textures/label.png').read_bytes() == texture.read_bytes()
    assert sorted(p.name for p in out.iterdir()) == ['SubUSDs','scene.usd','scene_isaac45.usda']

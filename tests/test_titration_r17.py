import json
from pathlib import Path

import pytest
from pxr import Usd,UsdGeom

from scripts.generate_traditional_titration_vr_r17 import build, SOURCE, STATION, pose_reference, audit_changes

pytestmark = pytest.mark.local_artifacts


@pytest.fixture(scope='module')
def package(tmp_path_factory):
    return build(output=tmp_path_factory.mktemp('r17'))


def test_reference_poses_and_allowed_structure_changes(package):
    old=Usd.Stage.Open(str(SOURCE/'scene.usd'))
    new=Usd.Stage.Open(str(package/'scene.usd'))
    proof=pose_reference()
    audit=audit_changes(old,new,proof['poses'])
    assert audit['status']=='pass'
    assert audit['prim_paths_identical']
    assert audit['changed_types']==[STATION+'/Instance/Burette/body_link/Visual/delivery_tip']
    cache=UsdGeom.XformCache()
    for path,matrix in proof['poses'].items():
        actual=cache.GetLocalToWorldTransform(new.GetPrimAtPath(path))
        assert max(abs(actual[i][j]-matrix[i][j]) for i in range(4) for j in range(4))<1e-8
    script='/Instance/Runtime/TitrationFlowGraph/FlowController'
    assert old.GetPrimAtPath(STATION+script).GetAttribute('inputs:script').Get()==new.GetPrimAtPath(STATION+script).GetAttribute('inputs:script').Get()
    assert new.GetPrimAtPath(STATION+'/Instance/Burette/body_link/Visual/delivery_tip').GetTypeName()=='Mesh'


def test_pose_audit_rejects_extra_physics_change(package):
    old=Usd.Stage.Open(str(SOURCE/'scene.usd'))
    new=Usd.Stage.Open(str(package/'scene.usd'))
    new.SetEditTarget(new.GetSessionLayer())
    prim=next(p for p in new.Traverse() if p.GetAttribute('physics:mass'))
    prim.GetAttribute('physics:mass').Set(123.0)
    with pytest.raises(ValueError):
        audit_changes(old,new,pose_reference()['poses'])


def test_package_metadata_and_guide(package):
    manifest=json.loads((package/'manifest.json').read_text())
    assert manifest['package_id'].endswith('r1_7')
    assert manifest['status']=='runtime_pending'
    assert manifest['assets']['titration_station_package_id']=='traditional_titration_station_r4'
    assert 'runtime_evidence' not in manifest
    assert (package/'COLOR_GUIDE_CN.md').is_file()
    assert json.loads((package/'evidence/initial_pose_reference.json').read_text())['zip_sha256']=='a68ab0cefeec96cee73e4f511c6ee3199027e753ad6a4f3f6cdaf2e893cb63a9'
    assert not list(Path(package).glob('*.zip'))

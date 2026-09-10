"""Checks requiring the locally generated colleague-task handoff."""
from pathlib import Path
import runpy

import pytest

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'outputs/scientific_workbench_solid_sample_weighing_vr_r1_20260909/handoff/scientific_workbench_solid_sample_weighing_vr_r1'
B='/World/obj_analytical_balance'


@pytest.mark.local_artifacts
def test_force_pan_has_its_own_rigid_link_and_valid_joint_targets():
    from pxr import Usd, UsdPhysics
    stage=Usd.Stage.Open(str(PACKAGE/'scene.usd'))
    assert stage.GetPrimAtPath(B+'/Instance/WeighingPan').HasAPI(UsdPhysics.RigidBodyAPI)
    assert stage.GetPrimAtPath(B+'/Instance/Body').GetAttribute('physics:mass').Get()==pytest.approx(6.8)
    assert not stage.GetPrimAtPath(B+'/Instance/Joints/BaseFixed')
    assert not stage.GetPrimAtPath(B+'/Instance/Chassis')
    for p in stage.Traverse():
        if p.IsA(UsdPhysics.Joint):
            for name in ('physics:body0','physics:body1'):
                assert all(stage.GetPrimAtPath(t) for t in p.GetRelationship(name).GetTargets())
    script=stage.GetPrimAtPath(B+'/BalanceRuntime/Graph/FlowController').GetAttribute('inputs:script').Get()
    assert 'get_link_incoming_joint_force' in script
    assert 'from scripts.' not in script and '/cpfs/' not in script
    assert stage.GetPrimAtPath(B).GetAttribute('balance:revision').Get()=='force_weighing_r1'


@pytest.mark.local_artifacts
def test_dual_runtime_config_registers_device_root_and_all_three_links():
    from pxr import Usd
    for version,name in [('45','task_config.py'),('41','task_config_isaac41.py')]:
        cfg=next(iter(runpy.run_path(str(PACKAGE/name))['TASKS'].values()))
        stage=Usd.Stage.Open(cfg['scene_usd_file_path']['scene1'])
        expected='isaacsim.core.nodes.OnPhysicsStep' if version=='45' else 'omni.isaac.core_nodes.OnPhysicsStep'
        assert stage.GetPrimAtPath(B+'/BalanceRuntime/Graph/OnPhysicsStep').GetAttribute('node:type').Get()==expected
        for suffix in ['', '/Instance/Body','/Instance/WeighingPan','/Instance/RightTare']:
            assert (B+suffix).replace('/World/','/World/_scene/',1) in cfg['obj_prim_list']
        assert cfg['physx_scene_cfg']['EnableGPUDynamics'] is True
        assert cfg['weighing']['target_g']==30
        assert cfg['weighing']['resolution_g']==.1

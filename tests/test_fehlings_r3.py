import math

import pytest

from scripts.fehlings_r3_contact import bath_contact,frustum_overlap
from scripts.fehlings_r2_state import initial_state,advance

WATER=[(.003,.035),(.09,.036)]
SAMPLE=[(.004,.0014),(.02,.006),(.033,.0074)]


def test_shallow_tilted_and_partial_contacts_do_not_require_full_immersion():
    assert bath_contact(SAMPLE,.033,(0,0,.084),(0,0,1),WATER)
    axis=(math.sin(math.radians(55)),0,math.cos(math.radians(55)))
    assert bath_contact(SAMPLE,.033,(-.012,0,.07),axis,WATER)
    assert bath_contact(SAMPLE,.033,(.037,0,.05),(0,0,1),WATER)
    assert bath_contact(SAMPLE,.033,(0,0,.04),(1,0,0),WATER)


def test_above_outside_wall_only_and_upper_tube_only_do_not_heat():
    assert not bath_contact(SAMPLE,.033,(0,0,.091),(0,0,1),WATER)
    assert not bath_contact(SAMPLE,.033,(.05,0,.04),(0,0,1),WATER)
    # Overlapping rectangular bounds at the circular corner are not contact.
    assert not bath_contact(SAMPLE,.033,(.035,.035,.04),(0,0,1),WATER)
    # Tube inverted: its upper part could enter the bath, but the sample stays above it.
    assert not bath_contact(SAMPLE,.033,(0,0,.14),(0,0,-1),WATER)
    assert not bath_contact(SAMPLE,.033,(0,0,-.05),(0,0,1),WATER)


def test_narrowphase_distinguishes_radial_graze_and_gap():
    water=((0,0,0),(0,0,.1),.035,.035)
    hit=((.0399,0,.04),(.0399,0,.07),.005,.005)
    miss=((.0401,0,.04),(.0401,0,.07),.005,.005)
    assert frustum_overlap(hit,water)
    assert not frustum_overlap(miss,water)


def test_contact_time_pauses_and_keeps_r2_timing():
    state=advance(initial_state(),25,True,False,(0,0,0))
    state=advance(state,100,False,False,(0,0,0))
    assert state['heated_s']==25
    state=advance(state,35,True,False,(0,0,0))
    assert state['heated_s']==60 and not state['success']
    assert advance(state,3,False,True,(0,0,0))['success']


def test_narrowphase_matches_analytic_parallel_frusta():
    import random
    rng=random.Random(73)
    water=((0,0,0),(0,0,.1),.035,.036)
    for _ in range(400):
        x,y,z=rng.uniform(-.05,.05),rng.uniform(-.05,.05),rng.uniform(-.04,.12)
        tube=((x,y,z),(x,y,z+.033),.0014,.0074)
        low,high=max(0,z),min(.1,z+.033)
        expected=False
        if low<=high:
            reach=max(.035+.001*t/.1+.0014+.006*(t-z)/.033 for t in (low,high))
            expected=math.hypot(x,y)<=reach
        assert frustum_overlap(tube,water)==expected,(tube,expected)


@pytest.fixture(scope='module')
def package(tmp_path_factory):
    from scripts.generate_fehlings_water_bath_r3 import build
    return build(output=tmp_path_factory.mktemp('bath-r3'))


@pytest.mark.local_artifacts
def test_package_has_collision_free_water_and_retained_cup_colliders(package):
    import json
    import runpy
    from pxr import Usd,UsdPhysics
    from scripts.generate_fehlings_water_bath_r3 import WATER,BEAKER
    stage=Usd.Stage.Open(str(package/'scene.usd'))
    assert not stage.GetPrimAtPath('/World/fluid_runtime')
    assert not stage.GetPrimAtPath(BEAKER+'/__aan_pbd_collision_proxy')
    assert not any('Particle' in p.GetTypeName() for p in stage.TraverseAll())
    for p in Usd.PrimRange(stage.GetPrimAtPath(WATER)):
        assert not any('Physics' in x or 'Physx' in x for x in p.GetAppliedSchemas())
    active=[p for p in Usd.PrimRange(stage.GetPrimAtPath(BEAKER)) if p.HasAPI(UsdPhysics.CollisionAPI) and p.GetAttribute('physics:collisionEnabled').Get()]
    assert len(active)==3
    assert stage.GetPrimAtPath(BEAKER).GetAttribute('physics:mass').Get()==pytest.approx(.18)
    recipe=json.loads((package/'evidence/water_recipe.json').read_text())
    low,high=recipe['profile_m'][0][0],recipe['profile_m'][-1][0]
    assert (high-low)/(recipe['usable_rim_m']-low)==pytest.approx(.8)
    assert high+.8267>.91
    cfg=next(iter(runpy.run_path(str(package/'task_config.py'))['TASKS'].values()))
    assert 'pbd_particle_count' not in cfg['water_bath']
    assert 'immersion_depth_range_m' not in cfg['water_bath']
    assert all('fluid_runtime' not in g['objs'] for g in cfg['layout_randomization']['objects'])


@pytest.mark.local_artifacts
def test_finalization_preserves_r3_contact_contract(package):
    import runpy
    import yaml
    from scripts.finalize_fehlings_water_bath import write_versioned_task_documents
    write_versioned_task_documents(package)
    task=yaml.safe_load((package/'task.yaml').read_text())
    assert task['reaction_policy']['version']=='visual_water_contact_v3'
    assert task['immersion_hold_seconds']==60
    cfg=next(iter(runpy.run_path(str(package/'task_config.py'))['TASKS'].values()))
    assert cfg['water_bath']['water_representation']=='visual_mesh'
    assert 'pbd_particle_count' not in cfg['water_bath']

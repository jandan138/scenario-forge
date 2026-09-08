import pytest

from scripts.fehlings_r2_state import initial_state, advance, appearance, geometry, mesh_topology

PROFILE = [(0.004, 0.0014), (0.020, 0.0065), (0.040, 0.0074)]
TOP = 0.0326


def test_reaction_boundaries_are_continuous_and_finish_at_sixty():
    assert appearance(0) == appearance(29.9) == appearance(30)
    assert appearance(30)['progress'] == 0
    assert appearance(45)['color'] == pytest.approx((.65,.30,.14))
    assert appearance(60)['color'] == pytest.approx((.94,.97,1))
    assert appearance(60)['opacity'] == .25
    assert appearance(90) == appearance(60)
    for t in (30,45,60):
        a,b=appearance(t-1e-7),appearance(t+1e-7)
        assert max(abs(x-y) for x,y in zip(a['color'],b['color'])) < 1e-6
        assert abs(a['opacity']-b['opacity']) < 1e-6
    state=advance(initial_state(),59.9,True,False,(0,0,0))
    assert not advance(state,3,False,True,(0,0,0))['success']
    state=advance(state,.1,True,False,(0,0,0))
    assert state['stage']=='ready_to_withdraw'
    assert advance(state,3,False,True,(0,0,0))['success']


def test_pause_observation_interrupt_latch_and_reset():
    state=advance(initial_state(),40,True,False,(0,0,0))
    assert advance(state,100,False,True,(0,0,0))['heated_s']==40
    assert advance(state,0,True,False,(0,0,0))==state
    state=advance(state,20,True,False,(0,0,0))
    state=advance(state,2,False,True,(0,0,0))
    state=advance(state,.5,False,True,(.03,0,0))
    assert state['observe_s']==0
    state=advance(state,3,False,True,(.03,0,0))
    assert state['success']
    assert advance(state,100,True,False,(0,0,0))==state
    assert initial_state()['heated_s']==0


def test_geometry_grows_from_fixed_floor_without_overlap_or_top_drift():
    from scripts.fehlings_r2_state import radius_at
    import math
    sizes=[]
    heights=[]
    for p in (0,.001,.25,.5,.75,1):
        result=geometry(PROFILE,TOP,p)
        bed=result['Sediment']
        sample=result['Sample']
        heights.append(result['sediment_height_m'])
        assert min(v[2] for v in bed['body'])==pytest.approx(PROFILE[0][0])
        assert max(v[2] for v in sample['surface'])==pytest.approx(TOP)
        if p>0:
            assert min(v[2] for v in sample['body']) > max(v[2] for v in bed['surface'])
        sizes.append(tuple(len(result[n][part]) for n in ('Sample','Sediment') for part in ('body','surface')))
        for n in ('Sample','Sediment'):
            for part in ('body','surface'):
                assert all(math.hypot(v[0],v[1]) <= radius_at(PROFILE,v[2])+1e-9 for v in result[n][part])
                counts,indices=mesh_topology(part)
                assert sum(counts)==len(indices)
                assert max(indices)<len(result[n][part])
    assert all(a<b for a,b in zip(heights,heights[1:]))
    assert len(set(sizes))==1


def test_package_relations_and_physical_invariance(tmp_path):
    import json
    from pxr import Usd, UsdGeom
    from scripts.generate_fehlings_water_bath_r2 import build, SOURCE, TUBE
    from scripts.finalize_traditional_titration_vr_r14 import physical_state
    root=build(output=tmp_path)
    old=Usd.Stage.Open(str(SOURCE/'scene.usd'))
    stage=Usd.Stage.Open(str(root/'scene.usd'))
    assert physical_state(old)==physical_state(stage)
    tube=stage.GetPrimAtPath(TUBE)
    for name in ('sampleShader','sedimentShader','sampleBody','sampleSurface','sedimentBody','sedimentSurface'):
        paths=tube.GetRelationship('fehlings:'+name).GetTargets()
        assert len(paths)==1 and stage.GetPrimAtPath(paths[0])
    for label in ('Sample','Sediment'):
        for part in ('body','surface'):
            mesh=UsdGeom.Mesh(stage.GetPrimAtPath(TUBE+'/VisualLiquid/'+label+'/'+part))
            assert mesh.ValidateTopology(mesh.GetFaceVertexIndicesAttr().Get(),mesh.GetFaceVertexCountsAttr().Get(),len(mesh.GetPointsAttr().Get()))[0]
    manifest=json.loads((root/'manifest.json').read_text())
    assert manifest['status']=='runtime_pending'
    assert manifest['reaction_policy']['heating_complete_seconds']==60
    assert 'runtime_reports' not in manifest
    assert (root/'COLOR_GUIDE_CN.md').is_file()


def test_reset_applies_without_pose_and_does_not_heat_same_step(tmp_path):
    import ast
    from types import SimpleNamespace as NS
    from pxr import Usd,Gf,UsdGeom
    from scripts import fehlings_r2_state as policy
    from scripts.fehlings_state import geometry_flags
    from scripts.generate_fehlings_water_bath_r2 import build,TUBE,GRAPH
    root=build(output=tmp_path)
    stage=Usd.Stage.Open(str(root/'scene.usd'))
    stage.SetEditTarget(stage.GetSessionLayer())
    tube=stage.GetPrimAtPath(TUBE)
    script=stage.GetPrimAtPath(GRAPH+'/FlowController').GetAttribute('inputs:script').Get()
    names={'_target','_apply_state','compute'}
    nodes=[n for n in ast.parse(script).body if isinstance(n,ast.FunctionDef) and n.name in names]
    ns={name:getattr(policy,name) for name in ('initial_state','appearance','advance','geometry')}
    ns.update(Gf=Gf,UsdGeom=UsdGeom,geometry_flags=geometry_flags,
              omni=NS(usd=NS(get_context=lambda:NS(get_stage=lambda:stage))),
              _dynamic_control=NS(acquire_dynamic_control_interface=lambda:NS(get_rigid_body=lambda _:0)),
              _state=advance(initial_state(),45,True,False,(0,0,0)),_last_geometry_progress=None)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<r2 reset bridge>','exec'),ns)
    ns['_apply_state'](stage,tube)
    db=NS(node=NS(get_prim_path=lambda:GRAPH+'/FlowController'),inputs=NS(deltaSeconds=1))
    ns['compute'](db)
    assert tube.GetAttribute('fehlings:heated_seconds').Get()==45
    tube.GetAttribute('fehlings:reset_requested').Set(True)
    ns['compute'](db)
    assert tube.GetAttribute('fehlings:heated_seconds').Get()==0
    assert tube.GetAttribute('fehlings:sediment_height_m').Get()==0
    assert tuple(stage.GetPrimAtPath(TUBE+'/VisualLiquid/Looks/Sample/Shader').GetAttribute('inputs:diffuseColor').Get())==pytest.approx((.4,.72,.95))
    assert not tube.GetAttribute('fehlings:reset_requested').Get()

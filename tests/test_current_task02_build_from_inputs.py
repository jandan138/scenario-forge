from pathlib import Path

import pytest

from scripts.build_task02_current import build_variant


@pytest.mark.local_artifacts
def test_current_fill20_builds_from_inputs_with_effective_collision_apis(tmp_path: Path):
    from pxr import Usd, UsdPhysics

    output = build_variant('fill20', tmp_path / 'fill20')
    stage = Usd.Stage.Open(str(output / 'vr/scene.usd'))
    assert stage.GetDefaultPrim().GetPath().pathString == '/World'
    assert not stage.GetPrimAtPath('/World/_scene')
    assert len(stage.GetPrimAtPath('/World/fluid_runtime/ParticleSet').GetAttribute('points').Get()) == 290
    for name, component, mesh in (
        ('beaker', 'Beaker_Hollow_Body', 'Beaker_Hollow_Body_Mesh'),
        ('graduated_cylinder', 'Hollow_Body', 'Hollow_Body_Mesh_002'),
    ):
        vessel = stage.GetPrimAtPath(f'/World/obj_{name}/Visual/Source/{component}/{mesh}')
        assert vessel.HasAPI(UsdPhysics.CollisionAPI)
        assert vessel.GetAttribute('physics:approximation').Get() == 'sdf'
        proxy = stage.GetPrimAtPath(f'/World/obj_{name}/__aan_pbd_collision_proxy/PBD_Unified_Vessel_Mesh')
        assert proxy.GetAttribute('physics:collisionEnabled').Get() is False

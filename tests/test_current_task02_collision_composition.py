from pxr import Sdf, Usd, UsdGeom, UsdPhysics

from scripts import generate_scientific_workbench_task02_r10_3_colleague_collision as generator


def test_materialized_root_keeps_legacy_proxy_disabled(tmp_path):
    path = tmp_path / 'scene.usd'
    stage = Usd.Stage.CreateNew(str(path))
    for name in ('beaker', 'graduated_cylinder'):
        prim = UsdGeom.Mesh.Define(stage, f'/World/obj_{name}/__aan_pbd_collision_proxy/PBD_Unified_Vessel_Mesh').GetPrim()
        prim.CreateAttribute('physics:collisionEnabled', Sdf.ValueTypeNames.Bool).Set(True)
        for component, mesh in (*generator.SDF_MESHES[name], *generator.HULL_MESHES[name]):
            UsdGeom.Mesh.Define(stage, f'/World/obj_{name}/Visual/Source/{component}/{mesh}')
    stage.GetRootLayer().Save()
    generator.finalize_collision_opinions(path)
    reopened = Usd.Stage.Open(str(path))
    for name in ('beaker', 'graduated_cylinder'):
        prim = reopened.GetPrimAtPath(f'/World/obj_{name}/__aan_pbd_collision_proxy/PBD_Unified_Vessel_Mesh')
        assert prim.GetAttribute('physics:collisionEnabled').Get() is False
        for component, mesh in (*generator.SDF_MESHES[name], *generator.HULL_MESHES[name]):
            collider = reopened.GetPrimAtPath(f'/World/obj_{name}/Visual/Source/{component}/{mesh}')
            assert collider.HasAPI(UsdPhysics.CollisionAPI)
            assert collider.HasAPI(UsdPhysics.MeshCollisionAPI)

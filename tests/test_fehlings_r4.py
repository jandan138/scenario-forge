from pathlib import Path

import pytest

R3 = Path(
    "outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r3_20260909/"
    "handoff/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r3"
)
RACK_MESH = "/World/obj_tube_rack/Cube_015"
TUBE_MESH = (
    "/World/obj_sample_tube/Visual/Source/centrifuge_tube_15ml_red_cap_ROOT"
    "/Tube_Body_Hollow/Tube_Body_Hollow_Mesh"
)
TUBE_CYL = "/World/obj_sample_tube/CpuContactCylinder"
WATER = "/World/obj_beaker/VisualWater"


def _world_translations(stage):
    from pxr import UsdGeom

    cache = UsdGeom.XformCache()
    poses = {}
    for child in stage.GetPrimAtPath("/World").GetChildren():
        name = child.GetName()
        if name.startswith("obj_") or name in ("table", "background"):
            poses[str(child.GetPath())] = tuple(
                round(v, 6) for v in cache.GetLocalToWorldTransform(child).ExtractTranslation()
            )
    return poses


@pytest.mark.local_artifacts
def test_r4_keeps_r3_placements_and_switches_cpu_colliders(tmp_path):
    from pxr import Usd, UsdPhysics

    from scripts.generate_fehlings_water_bath_r3 import BEAKER
    from scripts.generate_fehlings_water_bath_r4 import TUBE, build

    assert R3.exists()
    r3 = Usd.Stage.Open(str(R3 / "scene.usd"))
    r3_poses = _world_translations(r3)
    r3_approx = r3.GetPrimAtPath(RACK_MESH).GetAttribute("physics:approximation").Get()
    del r3
    root = build(output=tmp_path / "bath-r4")
    r4 = Usd.Stage.Open(str(root / "scene.usd"))
    assert r3_poses == _world_translations(r4)

    rack = r4.GetPrimAtPath(RACK_MESH)
    assert not rack.HasAPI(UsdPhysics.CollisionAPI)
    assert not rack.HasAPI(UsdPhysics.MeshCollisionAPI)
    slots = [
        prim
        for prim in Usd.PrimRange(r4.GetPrimAtPath("/World/obj_tube_rack"))
        if prim.GetName().startswith("slot_15ml")
        and prim.HasAPI(UsdPhysics.CollisionAPI)
        and prim.GetAttribute("physics:collisionEnabled").Get()
    ]
    assert len(slots) == 18
    assert r3_approx == "sdf"

    tube_mesh = r4.GetPrimAtPath(TUBE_MESH)
    assert not tube_mesh.HasAPI(UsdPhysics.CollisionAPI)
    assert not tube_mesh.HasAPI(UsdPhysics.MeshCollisionAPI)
    assert "PhysxSDFMeshCollisionAPI" not in tube_mesh.GetAppliedSchemas()
    assert "PhysxSDFMeshCollisionAPI" not in tube_mesh.GetMetadata('apiSchemas').GetAppliedItems()
    assert "PhysxSDFMeshCollisionAPI" not in rack.GetMetadata('apiSchemas').GetAppliedItems()
    cyl = r4.GetPrimAtPath(TUBE_CYL)
    assert cyl.IsValid()
    assert cyl.HasAPI(UsdPhysics.CollisionAPI)
    assert cyl.GetAttribute("physics:collisionEnabled").Get() is True
    assert cyl.GetAttribute("radius").Get() == pytest.approx(0.00861, abs=1e-6)
    assert cyl.GetAttribute("height").Get() == pytest.approx(0.101, abs=1e-6)
    enabled_tube = [
        str(prim.GetPath())
        for prim in Usd.PrimRange(r4.GetPrimAtPath(TUBE))
        if prim.HasAPI(UsdPhysics.CollisionAPI)
        and prim.GetAttribute("physics:collisionEnabled").Get()
    ]
    assert enabled_tube == [TUBE_CYL]

    for prim in Usd.PrimRange(r4.GetPrimAtPath(WATER)):
        assert not any("Physics" in x or "Physx" in x for x in prim.GetAppliedSchemas())
    active = [
        prim
        for prim in Usd.PrimRange(r4.GetPrimAtPath(BEAKER))
        if prim.HasAPI(UsdPhysics.CollisionAPI)
        and prim.GetAttribute("physics:collisionEnabled").Get()
    ]
    assert len(active) == 3
    for prim in active:
        approx = prim.GetAttribute("physics:approximation").Get()
        assert approx in (None, "none", "convexHull")
        assert approx != "sdf"
    assert r4.GetPrimAtPath(TUBE).GetAttribute("physics:kinematicEnabled").Get() is False
    assert r4.GetPrimAtPath(BEAKER).GetAttribute("physics:kinematicEnabled").Get() is True
    assert r4.GetDefaultPrim().GetCustomDataByKey("scenario_forge:taskId").endswith("_r4")


def test_collision_removal_strips_authored_physx_tokens_without_schema_plugin(monkeypatch):
    import builtins
    from pxr import Sdf, Usd, UsdGeom
    from scripts.generate_fehlings_water_bath_r4 import _strip_collision_apis

    stage = Usd.Stage.CreateInMemory()
    prim = UsdGeom.Mesh.Define(stage, '/Mesh').GetPrim()
    prim.SetMetadata('apiSchemas', Sdf.TokenListOp.CreateExplicit([
        'PhysicsCollisionAPI', 'PhysicsMeshCollisionAPI', 'PhysxSDFMeshCollisionAPI',
        'PhysxCollisionAPI', 'MaterialBindingAPI']))
    original = builtins.__import__

    def no_physx(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'pxr' and 'PhysxSchema' in fromlist:
            raise ImportError('schema plugin deliberately unavailable')
        return original(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, '__import__', no_physx)
    _strip_collision_apis(prim)
    assert prim.GetMetadata('apiSchemas').GetAppliedItems() == ['MaterialBindingAPI']

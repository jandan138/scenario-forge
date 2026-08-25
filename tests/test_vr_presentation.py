from __future__ import annotations

from pathlib import Path

import pytest

from scenario_forge.adapters.vr_presentation import (
    STANDARD_WORKBENCH_ASSET_ID,
    VRPresentationPolicyError,
    apply_standard_workbench_vr_presentation,
)


def _write_table_scene(path: Path, *, legacy_wrapper: bool) -> tuple[Path, str]:
    from pxr import Gf, Usd, UsdGeom, UsdPhysics

    stage = Usd.Stage.CreateNew(str(path))
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    prefix = "/World/table/table" if legacy_wrapper else "/World/table"
    mesh_path = f"{prefix}/Surface/Source/mesh"
    mesh = UsdGeom.Cube.Define(stage, mesh_path)
    mesh.AddTranslateOp().Set(Gf.Vec3d(0.1, 0.2, 0.3))
    UsdPhysics.CollisionAPI.Apply(mesh.GetPrim()).CreateCollisionEnabledAttr(True)
    stage.GetRootLayer().Save()
    return path, mesh_path


@pytest.mark.parametrize("legacy_wrapper", [False, True])
def test_hides_only_standard_workbench_surface_and_preserves_collision(
    tmp_path: Path, legacy_wrapper: bool
) -> None:
    from pxr import Usd, UsdGeom

    scene, mesh_path = _write_table_scene(
        tmp_path / "scene.usda", legacy_wrapper=legacy_wrapper
    )

    report = apply_standard_workbench_vr_presentation(
        scene, table_asset_id=STANDARD_WORKBENCH_ASSET_ID
    )

    stage = Usd.Stage.Open(str(scene), Usd.Stage.LoadAll)
    prim = stage.GetPrimAtPath(mesh_path)
    assert report == {
        "policy": "standard_workbench_surface_hidden",
        "status": "applied",
        "table_asset_id": STANDARD_WORKBENCH_ASSET_ID,
        "prim_path": mesh_path,
        "visibility": "invisible",
        "collision_preserved": True,
    }
    assert UsdGeom.Imageable(prim).ComputeVisibility() == UsdGeom.Tokens.invisible
    assert prim.IsActive()
    assert prim.GetAttribute("physics:collisionEnabled").Get() is True
    assert tuple(prim.GetAttribute("xformOp:translate").Get()) == (0.1, 0.2, 0.3)


def test_standard_workbench_missing_surface_fails_generation(tmp_path: Path) -> None:
    from pxr import Usd, UsdGeom

    scene = tmp_path / "scene.usda"
    stage = Usd.Stage.CreateNew(str(scene))
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, "/World").GetPrim())
    stage.GetRootLayer().Save()

    with pytest.raises(VRPresentationPolicyError, match="surface mesh"):
        apply_standard_workbench_vr_presentation(
            scene, table_asset_id=STANDARD_WORKBENCH_ASSET_ID
        )


def test_nonstandard_table_is_not_modified(tmp_path: Path) -> None:
    from pxr import Usd, UsdGeom

    scene, mesh_path = _write_table_scene(
        tmp_path / "scene.usda", legacy_wrapper=False
    )

    report = apply_standard_workbench_vr_presentation(
        scene, table_asset_id="another_table"
    )

    stage = Usd.Stage.Open(str(scene), Usd.Stage.LoadAll)
    assert report["status"] == "not_applicable"
    assert UsdGeom.Imageable(stage.GetPrimAtPath(mesh_path)).ComputeVisibility() == (
        UsdGeom.Tokens.inherited
    )

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

from scripts.generate_scientific_workbench_neutral_background_vr import (
    BACKGROUND_LAYOUT,
    build,
)


def _write_base(root: Path) -> Path:
    from pxr import Usd, UsdGeom, UsdLux, UsdPhysics

    vr = root / "vr"
    runtime = vr / "deps/r7_scene/source_bundle/scenario_forge_runtime"
    runtime.mkdir(parents=True)
    room_stage = Usd.Stage.CreateNew(str(vr / "deps/r7_scene/scene.usda"))
    UsdGeom.Xform.Define(room_stage, "/World/_scene/room")
    room_stage.GetRootLayer().Save()
    table_stage = Usd.Stage.CreateNew(str(runtime / "table.usd"))
    asset = UsdGeom.Xform.Define(table_stage, "/Asset").GetPrim()
    table_stage.SetDefaultPrim(asset)
    UsdGeom.Xform.Define(table_stage, "/Asset/table/Surface/Source")
    table_mesh = UsdGeom.Cube.Define(
        table_stage, "/Asset/table/Surface/Source/mesh"
    )
    UsdPhysics.CollisionAPI.Apply(
        table_mesh.GetPrim()
    ).CreateCollisionEnabledAttr(True)
    table_stage.GetRootLayer().Save()
    for name in ("scene.usd", "legacy_scene.usd"):
        stage = Usd.Stage.CreateNew(str(vr / name))
        world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
        stage.SetDefaultPrim(world)
        if name == "scene.usd":
            UsdGeom.Xform.Define(stage, "/World/background")
            UsdGeom.Xform.Define(stage, "/World/table/table/Surface/Source")
            mesh = UsdGeom.Cube.Define(
                stage, "/World/table/table/Surface/Source/mesh"
            )
            UsdPhysics.CollisionAPI.Apply(mesh.GetPrim()).CreateCollisionEnabledAttr(
                True
            )
            UsdLux.DomeLight.Define(stage, "/World/vr_direct_open_light")
            UsdPhysics.Scene.Define(stage, "/World/physicsScene")
            for object_name in (*BACKGROUND_LAYOUT, "obj_beaker", "obj_stir_bar"):
                UsdGeom.Xform.Define(stage, f"/World/{object_name}")
            UsdGeom.Xform.Define(stage, "/World/fluid_runtime")
        stage.GetRootLayer().Save()
    return root


def test_neutral_background_contains_only_rear_context_props(tmp_path: Path) -> None:
    from pxr import Usd, UsdGeom

    output = build(_write_base(tmp_path / "base"), tmp_path / "out")
    scene = output / "vr/scene.usd"
    stage = Usd.Stage.Open(str(scene), Usd.Stage.LoadAll)
    children = {prim.GetName() for prim in stage.GetPrimAtPath("/World").GetChildren()}
    assert children == {
        "background",
        "table",
        "vr_direct_open_light",
        "physicsScene",
        *BACKGROUND_LAYOUT,
    }
    for name, xyz in BACKGROUND_LAYOUT.items():
        assert tuple(
            stage.GetPrimAtPath(f"/World/{name}")
            .GetAttribute("xformOp:translate")
            .Get()
        ) == xyz
    table_mesh = stage.GetPrimAtPath(
        "/World/table/table/Surface/Source/mesh"
    )
    assert UsdGeom.Imageable(table_mesh).ComputeVisibility() == (
        UsdGeom.Tokens.invisible
    )
    assert table_mesh.GetAttribute("physics:collisionEnabled").Get() is True

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["task_objective"] == "none"
    assert manifest["background_objects"] == list(BACKGROUND_LAYOUT)
    archive = output / "handoff/scientific_workbench_neutral_background_vr.zip"
    with ZipFile(archive) as bundle:
        assert "vr/scene.usd" in bundle.namelist()
        assert "scene_config.yaml" in bundle.namelist()
        assert "task_config.py" not in bundle.namelist()

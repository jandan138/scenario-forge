from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from pxr import Usd, UsdPhysics

from scripts.generate_scientific_workbench_task08_vr_r12 import build


def test_task08_r12_builds_three_interactive_tubes_caps_and_visual_liquids(
    tmp_path: Path,
) -> None:
    output = build(tmp_path / "task08")
    scene = output / "vr/scene.usd"
    stage = Usd.Stage.Open(str(scene))
    assert stage.GetDefaultPrim().GetPath() == "/World"
    assert not stage.GetPrimAtPath("/World/_scene")
    rack = stage.GetPrimAtPath("/World/obj_tube_rack")
    assert tuple(rack.GetAttribute("xformOp:scale").Get()) == (1.0, 1.0, 1.0)
    assert not rack.HasAPI(UsdPhysics.RigidBodyAPI)
    for index in range(3):
        tube = stage.GetPrimAtPath(f"/World/obj_tube_{index:02d}")
        cap = stage.GetPrimAtPath(f"/World/obj_cap_{index:02d}")
        liquid = stage.GetPrimAtPath(f"/World/obj_tube_{index:02d}/VisualLiquid")
        assert tube.HasAPI(UsdPhysics.RigidBodyAPI)
        assert cap.HasAPI(UsdPhysics.RigidBodyAPI)
        assert liquid.GetAttribute("scenarioForge:interactive").Get() is False
        assert liquid.GetAttribute("scenarioForge:fillFraction").Get() == pytest.approx(0.8)
        assert not liquid.HasAPI(UsdPhysics.RigidBodyAPI)
        assert not any(
            prim.HasAPI(UsdPhysics.CollisionAPI) for prim in Usd.PrimRange(liquid)
        )


def test_task08_r12_vr_config_lists_every_object_without_robot_physics_patch(
    tmp_path: Path,
) -> None:
    output = build(tmp_path / "task08")
    config_path = output / "vr/task_config.py"
    source = config_path.read_text(encoding="utf-8")
    ast.parse(source)
    assert "set_robot_physics_material" not in source
    assert "set_robot_contact_offset" not in source
    assert "set_robot_rest_offset" not in source
    for name in (
        "obj_tube_rack",
        "obj_steel_plate",
        "obj_tube_00",
        "obj_tube_01",
        "obj_tube_02",
        "obj_cap_00",
        "obj_cap_01",
        "obj_cap_02",
    ):
        assert f"/World/_scene/{name}" in source
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["claims"]["vr_action_collection_layout_ready"] is False
    assert manifest["claims"]["thread_interaction_ready"] is False
    assert manifest["claims"]["task08_success"] is False

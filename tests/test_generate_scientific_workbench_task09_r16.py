from __future__ import annotations

import json

import pytest
from pxr import Usd, UsdGeom, UsdPhysics

from scripts.generate_scientific_workbench_task09_r16 import build_handoff


pytestmark = pytest.mark.local_artifacts


def test_r16_scene_uses_fixed_base_articulation_and_short_cart(tmp_path) -> None:
    result = build_handoff(tmp_path / "handoff")
    stage = Usd.Stage.Open(str(result.root / "scene.usd"))
    root = stage.GetPrimAtPath("/World/obj_oven")
    instance = stage.GetPrimAtPath("/World/obj_oven/Instance")
    body = stage.GetPrimAtPath("/World/obj_oven/Instance/Body")
    fixed = stage.GetPrimAtPath("/World/obj_oven/Instance/Joints/BaseFixed")
    cart = stage.GetPrimAtPath("/World/obj_oven_cart")

    assert root.HasAPI(UsdPhysics.ArticulationRootAPI)
    assert root.GetAttribute("physxArticulation:articulationEnabled").Get() is True
    assert instance.IsA(UsdGeom.Xform)
    assert body.GetAttribute("physics:kinematicEnabled").Get() is False
    assert fixed.GetRelationship("physics:body0").GetTargets() == [root.GetPath()]
    assert fixed.GetRelationship("physics:body1").GetTargets() == [body.GetPath()]
    assert list(cart.GetAttribute("xformOp:scale").Get()) == [1.0, 1.0, 0.7]
    assert list(root.GetAttribute("xformOp:translate").Get()) == [1.51, 0.0, 0.5285]


def test_r16_manifest_publishes_v2_contract_without_robot_claim(tmp_path) -> None:
    result = build_handoff(tmp_path / "handoff")
    manifest = json.loads(result.manifest.read_text())
    assert manifest["claims"]["articulated_instance_layout_v2"] is True
    assert manifest["claims"]["fixed_base_articulation"] is True
    assert manifest["claims"]["instance_identity_xform"] is True
    assert manifest["claims"]["robot_policy_success"] is False
    assert manifest["status"] == "static_built_runtime_pending"

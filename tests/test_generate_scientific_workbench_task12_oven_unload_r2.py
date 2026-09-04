from __future__ import annotations

import json

import pytest
from pxr import Usd, UsdGeom, UsdPhysics

from scripts.generate_scientific_workbench_task09_r16 import (
    build_handoff as build_task09,
)
from scripts.generate_scientific_workbench_task12_oven_unload_r2 import build_handoff


pytestmark = pytest.mark.local_artifacts


def test_task12_r2_keeps_layout_and_upgrades_oven_articulation(tmp_path) -> None:
    base = build_task09(tmp_path / "task09")
    result = build_handoff(tmp_path / "handoff", base_root=base.root)
    stage = Usd.Stage.Open(str(result.root / "scene.usd"))
    root = stage.GetPrimAtPath("/World/obj_oven")
    instance = stage.GetPrimAtPath("/World/obj_oven/Instance")
    body = stage.GetPrimAtPath("/World/obj_oven/Instance/Body")
    assert root.HasAPI(UsdPhysics.ArticulationRootAPI)
    assert instance.IsA(UsdGeom.Xform)
    assert body.GetAttribute("physics:kinematicEnabled").Get() is False
    assert list(
        stage.GetPrimAtPath("/World/obj_oven_cart").GetAttribute("xformOp:scale").Get()
    ) == [1.0, 1.0, 0.7]
    assert list(root.GetAttribute("xformOp:translate").Get()) == [1.51, 0.0, 0.5285]
    assert stage.GetPrimAtPath("/World/obj_sample_beaker")
    assert stage.GetPrimAtPath("/World/obj_sample_conical_flask")


def test_task12_r2_manifest_has_r16_lineage(tmp_path) -> None:
    base = build_task09(tmp_path / "task09")
    result = build_handoff(tmp_path / "handoff", base_root=base.root)
    manifest = json.loads(result.manifest.read_text())
    assert manifest["lineage"]["base_handoff"] == "scientific_workbench_task09_r16_vr"
    assert manifest["claims"]["articulated_instance_layout_v2"] is True
    assert manifest["claims"]["fixed_base_articulation"] is True
    assert manifest["claims"]["robot_policy_success"] is False

from __future__ import annotations

import json

import pytest
from pxr import Usd

from scripts.generate_scientific_workbench_task09_r14 import build_handoff


pytestmark = pytest.mark.local_artifacts


def test_r14_scene_exposes_two_roots_with_full_gui_trs(tmp_path) -> None:
    result = build_handoff(tmp_path / "handoff")
    stage = Usd.Stage.Open(str(result.root / "scene.usd"))
    assert stage
    for path in ("/World/obj_oven", "/World/obj_oven_cart"):
        prim = stage.GetPrimAtPath(path)
        assert prim.GetAttribute("xformOpOrder").Get() == [
            "xformOp:translate",
            "xformOp:orient",
            "xformOp:scale",
        ]
        assert list(prim.GetAttribute("xformOp:scale").Get()) == [1.0, 1.0, 1.0]
    assert stage.GetPrimAtPath(
        "/World/obj_oven/ControlPanel/AuxControlKnob"
    ).IsValid()
    door = stage.GetPrimAtPath("/World/obj_oven/Joints/DoorHinge")
    assert door.GetAttribute("drive:angular:physics:damping").Get() == 9.0
    assert door.GetAttribute("physics:upperLimit").Get() == 60.0


def test_r14_task_defaults_to_aux_knob_and_documents_gui_contract(tmp_path) -> None:
    result = build_handoff(tmp_path / "handoff")
    task = json.loads((result.root / "task_r14.json").read_text(encoding="utf-8"))
    assert task["temperature_control"] == "obj_oven.ControlPanel.AuxControlKnob"
    assert task["start_control"] == "obj_oven.ControlPanel.AuxControlKnob"
    assert task["uniform_scale_range"] == [0.85, 1.15]
    readme = (result.root / "README_CN.md").read_text(encoding="utf-8")
    assert "DoorHinge" in readme
    assert "Damping = 9.0" in readme
    assert "Upper Limit = 60" in readme
    manifest = json.loads((result.root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["claims"]["dual_physical_knobs"] is True
    assert manifest["claims"]["gui_independent_root_trs"] is True

from __future__ import annotations

import json

from pxr import Usd, UsdGeom, UsdPhysics

from scripts.generate_scientific_workbench_task09_r15 import build_handoff


def test_r15_scene_preserves_obj_root_and_places_all_links_under_instance(tmp_path) -> None:
    result = build_handoff(tmp_path / "handoff")
    stage = Usd.Stage.Open(str(result.root / "scene.usd"))
    root = stage.GetPrimAtPath("/World/obj_oven")
    assert root
    assert list(UsdGeom.Xformable(root).GetLocalTransformation().ExtractTranslation()) == [
        1.51,
        0.0,
        0.755,
    ]
    instance = stage.GetPrimAtPath("/World/obj_oven/Instance")
    assert instance.IsA(UsdGeom.Scope)
    links = [
        str(prim.GetPath())
        for prim in Usd.PrimRange(root)
        if prim.HasAPI(UsdPhysics.RigidBodyAPI)
    ]
    assert links and all(path.startswith("/World/obj_oven/Instance/") for path in links)
    assert not stage.GetPrimAtPath("/World/obj_oven/Body")


def test_r15_paths_and_manifest_publish_instance_contract(tmp_path) -> None:
    result = build_handoff(tmp_path / "handoff")
    task = json.loads((result.root / "task_r15.json").read_text())
    assert task["temperature_control"] == (
        "obj_oven.Instance.ControlPanel.AuxControlKnob"
    )
    assert task["door_joint"] == "obj_oven.Instance.Joints.DoorHinge"
    config = (result.root / "task_config.py").read_text()
    assert "/World/_scene/obj_oven" in config
    assert "/World/_scene/obj_oven/Instance" not in config
    manifest = json.loads(result.manifest.read_text())
    assert manifest["claims"]["articulated_instance_layout_v1"] is True
    assert manifest["claims"]["all_links_under_instance"] is True
    assert manifest["status"] == "static_built_runtime_pending"

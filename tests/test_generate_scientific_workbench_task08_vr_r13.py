from __future__ import annotations

import ast
import json
from pathlib import Path
import runpy
import sys
import types

import pytest
from pxr import Usd, UsdPhysics

from scripts.generate_scientific_workbench_task08_vr_r13 import (
    ASSISTED_CAP_ENTRY,
    ASSISTED_TUBE_ENTRY,
    build,
)


def test_task08_controller_resolves_direct_and_nested_instance_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    omni = types.ModuleType("omni")
    omni.__path__ = []
    omni_usd = types.ModuleType("omni.usd")
    omni_isaac = types.ModuleType("omni.isaac")
    omni_isaac.__path__ = []
    dynamic_control = types.ModuleType("omni.isaac.dynamic_control")
    dynamic_control._dynamic_control = types.SimpleNamespace(INVALID_HANDLE=-1)
    monkeypatch.setitem(sys.modules, "omni", omni)
    monkeypatch.setitem(sys.modules, "omni.usd", omni_usd)
    monkeypatch.setitem(sys.modules, "omni.isaac", omni_isaac)
    monkeypatch.setitem(sys.modules, "omni.isaac.dynamic_control", dynamic_control)
    namespace = runpy.run_path(
        str(Path("scripts/task08_assisted_thread_controller.py").resolve())
    )
    resolver = namespace["_instance_root_from_node_path"]
    assert (
        resolver("/World/TaskRuntime/AssistedThreadGraph/Controller") == "/World"
    )
    assert (
        resolver(
            "/World/_scene/TaskRuntime/AssistedThreadGraph/Controller"
        )
        == "/World/_scene"
    )
    with pytest.raises(ValueError):
        resolver("/World/Unexpected/Controller")


@pytest.mark.local_artifacts
def test_task08_r13_embeds_one_turn_assisted_thread_contract(tmp_path: Path) -> None:
    output = build(tmp_path / "task08_r13")
    stage = Usd.Stage.Open(str(output / "vr/scene.usd"))
    graph = stage.GetPrimAtPath("/World/TaskRuntime/AssistedThreadGraph")
    controller = stage.GetPrimAtPath(
        "/World/TaskRuntime/AssistedThreadGraph/Controller"
    )
    contract = stage.GetPrimAtPath("/World/TaskRuntime/AssistedThreadContract")
    assert graph.GetTypeName() == "OmniGraph"
    assert controller.GetAttribute("node:type").Get() == "omni.graph.scriptnode.ScriptNode"
    script = controller.GetAttribute("inputs:script").Get()
    assert "free" in script and "engaged" in script and "closed" in script
    assert "__aan_collision_proxy/grasp_box" in script
    assert contract.GetAttribute("assistedThread:effectiveLeadMPerTurn").Get() == pytest.approx(
        0.0076
    )
    assert contract.GetAttribute("assistedThread:closeAngleDegrees").Get() == pytest.approx(
        350.0
    )
    assert contract.GetAttribute("assistedThread:state").Get() == "free"
    assert [
        str(path)
        for path in contract.GetRelationship("assistedThread:targetTube").GetTargets()
    ] == ["/World/obj_tube_01"]
    assert [
        str(path)
        for path in contract.GetRelationship("assistedThread:targetCap").GetTargets()
    ] == ["/World/obj_cap_01"]


@pytest.mark.local_artifacts
def test_task08_r13_consumes_smooth_proxy_assets_and_keeps_visual_threads(
    tmp_path: Path,
) -> None:
    output = build(tmp_path / "task08_r13")
    stage = Usd.Stage.Open(str(output / "vr/scene.usd"))
    tube = stage.GetPrimAtPath("/World/obj_tube_01")
    cap = stage.GetPrimAtPath("/World/obj_cap_01")
    assert tube.HasAPI(UsdPhysics.RigidBodyAPI)
    assert cap.HasAPI(UsdPhysics.RigidBodyAPI)
    assert ASSISTED_TUBE_ENTRY.endswith("Tube15LongNeckThreadedBody")
    assert ASSISTED_CAP_ENTRY.endswith("Tube15LongNeckThreadedClosedCap")
    assert stage.GetPrimAtPath("/World/obj_tube_01/__aan_collision_proxy")
    assert stage.GetPrimAtPath("/World/obj_cap_01/__aan_collision_proxy")
    assert stage.GetPrimAtPath(
        "/World/obj_tube_01/node_/mesh_"
    ).GetAttribute("physics:collisionEnabled").Get() is False
    assert stage.GetPrimAtPath(
        "/World/obj_cap_01/node_/mesh_"
    ).GetAttribute("physics:collisionEnabled").Get() is False


@pytest.mark.local_artifacts
def test_task08_r13_config_and_manifest_keep_claim_boundaries(tmp_path: Path) -> None:
    output = build(tmp_path / "task08_r13")
    config = (output / "vr/task_config.py").read_text()
    ast.parse(config)
    assert "set_robot_physics_material" not in config
    assert "set_robot_contact_offset" not in config
    assert "set_robot_rest_offset" not in config
    assert "assisted_thread" in config
    assert "effective_lead_m_per_turn': 0.0076" in config
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["release_id"] == "r13"
    assert manifest["claims"]["assisted_thread"] is True
    assert manifest["claims"]["physical_thread_contact"] is False
    assert manifest["claims"]["thread_interaction_ready"] is False
    assert manifest["claims"]["robot_policy_success"] is False

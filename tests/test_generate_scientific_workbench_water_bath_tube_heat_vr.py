from __future__ import annotations

import json

import pytest
import yaml
from pxr import Usd, UsdGeom, UsdPhysics

from scripts.generate_scientific_workbench_water_bath_tube_heat_vr import (
    build_handoff,
)


@pytest.fixture(scope="module")
def water_bath(tmp_path_factory):
    return build_handoff(tmp_path_factory.mktemp("water_bath") / "package")


def test_water_bath_places_beaker_on_stirrer_and_one_tube_in_outer_slot(
    water_bath,
) -> None:
    stage = Usd.Stage.Open(str(water_bath.root / "vr/scene.usd"))
    assert stage and stage.GetDefaultPrim().GetPath() == "/World"

    beaker = stage.GetPrimAtPath("/World/obj_beaker")
    assert list(beaker.GetAttribute("xformOp:translate").Get()) == [
        0.37,
        -0.028,
        0.8267,
    ]
    stirrer = stage.GetPrimAtPath("/World/obj_magnetic_stirrer")
    assert stirrer.GetAttribute("scenarioForge:heatingState").Get() == "preheated"
    assert stirrer.GetAttribute("scenarioForge:temperatureSetpointC").Get() == 60.0
    assert stirrer.GetAttribute("scenarioForge:stirringEnabled").Get() is False

    tube = stage.GetPrimAtPath("/World/obj_sample_tube")
    assert tube.IsValid()
    assert list(tube.GetAttribute("xformOp:translate").Get()) == pytest.approx([
        0.1215,
        -0.1461325,
        0.7784,
    ])
    assert not stage.GetPrimAtPath("/World/obj_tube_01").IsValid()
    assert not stage.GetPrimAtPath("/World/obj_sample_cap").IsValid()

    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy],
    )
    rack = cache.ComputeWorldBound(
        stage.GetPrimAtPath("/World/obj_tube_rack")
    ).ComputeAlignedRange()
    tube_bound = cache.ComputeWorldBound(tube).ComputeAlignedRange()
    assert tube_bound.GetMax()[2] - rack.GetMax()[2] >= 0.045


def test_water_bath_reuses_pbd_water_and_adds_physics_free_amber_sample(
    water_bath,
) -> None:
    stage = Usd.Stage.Open(str(water_bath.root / "vr/scene.usd"))
    points = stage.GetPrimAtPath("/World/fluid_runtime/ParticleSets/beaker_liquid")
    assert len(points.GetAttribute("points").Get()) == 969
    assert stage.GetPrimAtPath("/World/fluid_runtime").GetAttribute(
        "xformOpOrder"
    ).Get() in (None, [])
    water = stage.GetPrimAtPath("/World/fluid_runtime/LiquidMaterial/PreviewSurface")
    assert list(water.GetAttribute("inputs:diffuseColor").Get()) == pytest.approx([
        0.32,
        0.72,
        0.95,
    ])
    assert abs(float(water.GetAttribute("inputs:opacity").Get()) - 0.34) < 1e-6

    visual_liquid = stage.GetPrimAtPath("/World/obj_sample_tube/VisualLiquid")
    assert visual_liquid.GetAttribute("scenarioForge:role").Get() == (
        "visual_static_liquid"
    )
    assert visual_liquid.GetAttribute("scenarioForge:interactive").Get() is False
    for prim in Usd.PrimRange(visual_liquid):
        assert not prim.HasAPI(UsdPhysics.RigidBodyAPI)
        assert not prim.HasAPI(UsdPhysics.CollisionAPI)


def test_water_bath_vr_config_and_task_contract(water_bath) -> None:
    config = (water_bath.root / "vr/task_config.py").read_text()
    for name in (
        "obj_magnetic_stirrer",
        "obj_beaker",
        "obj_tube_rack",
        "obj_sample_tube",
    ):
        assert f"/World/_scene/{name}" in config
        assert name in config
    assert "['obj_magnetic_stirrer', 'obj_beaker', 'fluid_runtime']" in config
    assert "['obj_tube_rack', 'obj_sample_tube']" in config

    task = yaml.safe_load((water_bath.root / "task.yaml").read_text())
    assert task["task_id"] == "scientific_workbench_water_bath_heat_centrifuge_tube"
    assert task["temperature_setpoint_c"] == 60.0
    assert task["immersion_hold_seconds"] == 5.0
    assert [step["id"] for step in task["steps"]] == [
        "pick_tube_from_rack",
        "align_over_water_bath",
        "immerse_tube",
        "hold_in_water_bath",
        "withdraw_tube",
        "return_tube_to_rack",
    ]
    manifest = json.loads(water_bath.manifest.read_text())
    assert manifest["claims"]["pbd_water"] is True
    assert manifest["claims"]["tube_visual_static_liquid"] is True
    assert manifest["claims"]["thermal_transfer_simulated"] is False
    assert manifest["claims"]["robot_policy_success"] is False

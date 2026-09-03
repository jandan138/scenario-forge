from __future__ import annotations

import json

import pytest
import yaml
from pxr import Usd, UsdGeom

from scripts.generate_scientific_workbench_task12_oven_unload import build_handoff
from scripts.validate_scientific_workbench_task12_oven_unload import evaluate_report


@pytest.mark.local_artifacts
def test_task12_places_dual_glassware_on_lower_shelf_and_shortens_cart(
    tmp_path,
) -> None:
    result = build_handoff(tmp_path / "handoff")
    stage = Usd.Stage.Open(str(result.root / "scene.usd"))
    assert stage

    cart = stage.GetPrimAtPath("/World/obj_oven_cart")
    oven = stage.GetPrimAtPath("/World/obj_oven")
    assert list(cart.GetAttribute("xformOp:scale").Get()) == [1.0, 1.0, 0.7]
    assert list(oven.GetAttribute("xformOp:translate").Get()) == [
        1.51,
        0.0,
        0.5285,
    ]
    assert stage.GetPrimAtPath("/World/obj_oven/Instance").IsValid()

    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy],
    )
    shelf = cache.ComputeWorldBound(
        stage.GetPrimAtPath(
            "/World/obj_oven/Instance/Shelves/Shelf_0/CollisionProxy"
        )
    ).ComputeAlignedRange()
    for path in (
        "/World/obj_sample_beaker",
        "/World/obj_sample_conical_flask",
    ):
        vessel = cache.ComputeWorldBound(stage.GetPrimAtPath(path)).ComputeAlignedRange()
        assert vessel.GetMin()[0] >= shelf.GetMin()[0]
        assert vessel.GetMax()[0] <= shelf.GetMax()[0]
        assert vessel.GetMin()[1] >= shelf.GetMin()[1]
        assert vessel.GetMax()[1] <= shelf.GetMax()[1]
        assert 0.0 <= vessel.GetMin()[2] - shelf.GetMax()[2] <= 0.002


@pytest.mark.local_artifacts
def test_task12_authors_completed_panel_and_dual_unload_contract(tmp_path) -> None:
    result = build_handoff(tmp_path / "handoff")
    stage = Usd.Stage.Open(str(result.root / "scene.usd"))
    control = stage.GetPrimAtPath("/World/obj_oven/Instance/ControlPanel")
    assert control.GetAttribute("oven:mainsPower").Get() is True
    assert control.GetAttribute("oven:operatingState").Get() == "complete"
    assert control.GetAttribute("oven:heatingEnabled").Get() is False
    assert control.GetAttribute("oven:heaterActive").Get() is False
    assert control.GetAttribute("oven:chamberLightEnabled").Get() is True
    assert control.GetAttribute("oven:actualTemperatureC").Get() == 65.0
    assert control.GetAttribute("oven:temperatureSetpointC").Get() == 65.0

    task = yaml.safe_load((result.root / "task.yaml").read_text())
    assert task["task_id"] == "scientific_workbench_oven_unload_shutdown_dual_glassware"
    assert task["target_vessels"] == [
        "obj_sample_beaker",
        "obj_sample_conical_flask",
    ]
    assert [step["id"] for step in task["steps"]] == [
        "open_door",
        "remove_beaker",
        "place_beaker_on_table",
        "remove_conical_flask",
        "place_conical_flask_on_table",
        "close_door",
        "power_off",
    ]

    config = (result.root / "task_config.py").read_text()
    for name in (
        "obj_oven_cart",
        "obj_oven",
        "obj_sample_beaker",
        "obj_sample_conical_flask",
    ):
        assert f'"/World/_scene/{name}"' in config
        assert f'"{name}"' in config
    assert '"x_offset_range": [-0.01, 0.01]' in config
    assert '"y_offset_range": [-0.01, 0.01]' in config

    manifest = json.loads(result.manifest.read_text())
    assert manifest["claims"]["articulated_instance_layout_v1"] is True
    assert manifest["claims"]["initial_process_state"] == "complete"
    assert manifest["claims"]["robot_policy_success"] is False


def test_task12_runtime_report_requires_both_vessels_and_device_completion() -> None:
    report = {
        "runtime": {"name": "isaac41", "kit_version": "4.1.0-rc.7"},
        "objects": {
            "obj_oven_cart": {"translation_drift_m": 0.0},
            "obj_oven": {"translation_drift_m": 0.0},
            "obj_sample_beaker": {
                "translation_drift_m": 0.001,
                "inside_shelf_xy": True,
                "bottom_gap_to_shelf_m": 0.0,
            },
            "obj_sample_conical_flask": {
                "translation_drift_m": 0.001,
                "inside_shelf_xy": True,
                "bottom_gap_to_shelf_m": 0.0,
            },
        },
        "control_before_shutdown": {
            "mains_power": True,
            "heating_enabled": False,
            "operating_state": "complete",
            "chamber_light_enabled": True,
            "temperature_setpoint_c": 65.0,
        },
        "device": {
            "door_open_rotation_delta_deg": 60.0,
            "door_closed_residual_deg": 1.0,
        },
        "control_after_shutdown": {
            "mains_power": False,
            "operating_state": "off",
            "chamber_light_enabled": False,
        },
    }
    assert evaluate_report(report)["status"] == "pass"
    report["objects"]["obj_sample_conical_flask"]["inside_shelf_xy"] = False
    assert evaluate_report(report)["status"] == "blocked"

#!/usr/bin/env python3
"""Run the Isaac 4.1 static and device smoke for Task 12 oven unload."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import traceback
from typing import Any


def evaluate_report(report: dict[str, Any]) -> dict[str, Any]:
    objects = report.get("objects", {})
    checks = {
        "isaac41_runtime": str(
            report.get("runtime", {}).get("kit_version", "")
        ).startswith("4.1"),
        "cart_stable": objects.get("obj_oven_cart", {}).get("translation_drift_m", 1.0)
        <= 0.002,
        "oven_stable": objects.get("obj_oven", {}).get("translation_drift_m", 1.0)
        <= 0.002,
        "beaker_supported_on_lower_shelf": bool(
            objects.get("obj_sample_beaker", {}).get("translation_drift_m", 1.0)
            <= 0.02
            and objects.get("obj_sample_beaker", {}).get("inside_shelf_xy", False)
            and -0.003
            <= objects.get("obj_sample_beaker", {}).get("bottom_gap_to_shelf_m", 1.0)
            <= 0.005
        ),
        "flask_supported_on_lower_shelf": bool(
            objects.get("obj_sample_conical_flask", {}).get(
                "translation_drift_m", 1.0
            )
            <= 0.02
            and objects.get("obj_sample_conical_flask", {}).get(
                "inside_shelf_xy", False
            )
            and -0.003
            <= objects.get("obj_sample_conical_flask", {}).get(
                "bottom_gap_to_shelf_m", 1.0
            )
            <= 0.005
        ),
        "initial_panel_complete_65c": bool(
            report.get("control_before_shutdown", {}).get("mains_power") is True
            and report.get("control_before_shutdown", {}).get("heating_enabled")
            is False
            and report.get("control_before_shutdown", {}).get("operating_state")
            == "complete"
            and report.get("control_before_shutdown", {}).get("chamber_light_enabled")
            is True
            and abs(
                float(
                    report.get("control_before_shutdown", {}).get(
                        "temperature_setpoint_c", math.nan
                    )
                )
                - 65.0
            )
            <= 0.5
        ),
        "door_opened_and_closed": bool(
            report.get("device", {}).get("door_open_rotation_delta_deg", 0.0)
            >= 35.0
            and report.get("device", {}).get("door_closed_residual_deg", 180.0)
            <= 10.0
        ),
        "mains_rocker_shutdown": bool(
            report.get("control_after_shutdown", {}).get("mains_power") is False
            and report.get("control_after_shutdown", {}).get("operating_state")
            == "off"
            and report.get("control_after_shutdown", {}).get("chamber_light_enabled")
            is False
        ),
    }
    return {"status": "pass" if all(checks.values()) else "blocked", "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    original = sys.argv
    sys.argv = [sys.argv[0]]
    try:
        from isaacsim import SimulationApp
    except ImportError:
        from omni.isaac.kit import SimulationApp

    app = SimulationApp(
        {"headless": True, "renderer": "RayTracedLighting", "sync_loads": True}
    )
    sys.argv = original
    try:
        import carb.settings
        import omni.kit.app
        import omni.timeline
        import omni.usd
        from pxr import Usd, UsdGeom

        settings = carb.settings.get_settings()
        settings.set_bool("/app/omni.graph.scriptnode/enable_opt_in", False)
        settings.set_bool("/app/omni.graph.scriptnode/opt_in", True)
        settings.set_bool("/app/scripting/ignoreWarningDialog", True)
        manager = omni.kit.app.get_app().get_extension_manager()
        kit_version = str(omni.kit.app.get_app().get_app_version())
        for extension in ("omni.graph.action_nodes", "omni.graph.scriptnode"):
            manager.set_extension_enabled_immediate(extension, True)
        context = omni.usd.get_context()
        scene = root / "scene.usd"
        if not context.open_stage(str(scene)):
            raise RuntimeError(f"cannot open {scene}")
        while context.get_stage_loading_status()[2] > 0:
            app.update()
        for _ in range(16):
            app.update()
        stage = context.get_stage()
        names = (
            "obj_oven_cart",
            "obj_oven",
            "obj_sample_beaker",
            "obj_sample_conical_flask",
        )

        def matrix(path: str):
            return UsdGeom.Xformable(stage.GetPrimAtPath(path)).ComputeLocalToWorldTransform(0)

        def xyz(name: str) -> list[float]:
            value = matrix("/World/" + name).ExtractTranslation()
            return [float(value[index]) for index in range(3)]

        def rotation_delta_deg(first, second) -> float:
            relative = first.GetInverse() * second
            return abs(float(relative.ExtractRotation().GetAngle()))

        def control_state() -> dict[str, Any]:
            control = stage.GetPrimAtPath("/World/obj_oven/Instance/ControlPanel")
            return {
                "mains_power": bool(control.GetAttribute("oven:mainsPower").Get()),
                "heating_enabled": bool(
                    control.GetAttribute("oven:heatingEnabled").Get()
                ),
                "heater_active": bool(control.GetAttribute("oven:heaterActive").Get()),
                "chamber_light_enabled": bool(
                    control.GetAttribute("oven:chamberLightEnabled").Get()
                ),
                "temperature_setpoint_c": float(
                    control.GetAttribute("oven:temperatureSetpointC").Get()
                ),
                "actual_temperature_c": float(
                    control.GetAttribute("oven:actualTemperatureC").Get()
                ),
                "operating_state": str(
                    control.GetAttribute("oven:operatingState").Get()
                ),
            }

        initial = {name: xyz(name) for name in names}
        door_path = "/World/obj_oven/Instance/Door"
        door_initial = matrix(door_path)
        timeline = omni.timeline.get_timeline_interface()
        timeline.play()
        for _ in range(300):
            app.update()
        settled = {name: xyz(name) for name in names}
        control_before_shutdown = control_state()

        door_joint = stage.GetPrimAtPath("/World/obj_oven/Instance/Joints/DoorHinge")
        velocity = door_joint.GetAttribute("drive:angular:physics:targetVelocity")
        velocity.Set(45.0)
        for _ in range(180):
            app.update()
        door_open = matrix(door_path)
        velocity.Set(-45.0)
        for _ in range(220):
            app.update()
        velocity.Set(0.0)
        door_closed = matrix(door_path)

        rocker = stage.GetPrimAtPath(
            "/World/obj_oven/Instance/Joints/MainsRocker"
        ).GetAttribute("drive:angular:physics:targetPosition")
        rocker.Set(-8.0)
        for _ in range(180):
            app.update()
        control_after_shutdown = control_state()
        timeline.stop()

        cache = UsdGeom.BBoxCache(
            Usd.TimeCode.Default(),
            [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy],
        )
        shelf = cache.ComputeWorldBound(
            stage.GetPrimAtPath(
                "/World/obj_oven/Instance/Shelves/Shelf_0/CollisionProxy"
            )
        ).ComputeAlignedRange()
        object_reports = {}
        for name in names:
            final = settled[name]
            item = {
                "initial_xyz_m": initial[name],
                "settled_xyz_m": final,
                "translation_drift_m": math.sqrt(
                    sum((final[index] - initial[name][index]) ** 2 for index in range(3))
                ),
            }
            if name.startswith("obj_sample_"):
                bound = cache.ComputeWorldBound(
                    stage.GetPrimAtPath("/World/" + name)
                ).ComputeAlignedRange()
                item.update(
                    {
                        "inside_shelf_xy": bool(
                            bound.GetMin()[0] >= shelf.GetMin()[0]
                            and bound.GetMax()[0] <= shelf.GetMax()[0]
                            and bound.GetMin()[1] >= shelf.GetMin()[1]
                            and bound.GetMax()[1] <= shelf.GetMax()[1]
                        ),
                        "bottom_gap_to_shelf_m": float(
                            bound.GetMin()[2] - shelf.GetMax()[2]
                        ),
                    }
                )
            object_reports[name] = item
        report = {
            "schema_version": "scenario-forge-task12-oven-unload-smoke/v0.1",
            "runtime": {"name": "isaac41", "kit_version": kit_version},
            "objects": object_reports,
            "control_before_shutdown": control_before_shutdown,
            "control_after_shutdown": control_after_shutdown,
            "device": {
                "door_open_rotation_delta_deg": rotation_delta_deg(
                    door_initial, door_open
                ),
                "door_closed_residual_deg": rotation_delta_deg(
                    door_initial, door_closed
                ),
                "door_target_velocity_deg_s": 45.0,
                "shutdown_rocker_target_deg": -8.0,
            },
        }
        report.update(evaluate_report(report))
        destination = root / "evidence/runtime/static_device_smoke.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(destination)
        return 0 if report["status"] == "pass" else 5
    except BaseException:
        traceback.print_exc()
        raise
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())

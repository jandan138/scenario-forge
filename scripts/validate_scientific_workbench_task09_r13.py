#!/usr/bin/env python3
"""Run an Isaac 4.1 static Play gate for the Task 09 r13 final scene."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any


def evaluate_report(report: dict[str, Any]) -> dict[str, Any]:
    objects = report.get("objects", {})
    checks = {
        "cart_stable": objects.get("obj_oven_cart", {}).get("translation_drift_m", 1.0)
        <= 0.002,
        "oven_stable": objects.get("obj_oven", {}).get("translation_drift_m", 1.0)
        <= 0.002,
        "beaker_stable_on_table": (
            objects.get("obj_sample_beaker", {}).get("translation_drift_m", 1.0)
            <= 0.02
            and 0.74
            <= objects.get("obj_sample_beaker", {}).get("final_z_m", 0.0)
            <= 0.80
        ),
        "flask_stable_on_table": (
            objects.get("obj_context_conical_flask", {}).get(
                "translation_drift_m", 1.0
            )
            <= 0.02
            and 0.74
            <= objects.get("obj_context_conical_flask", {}).get("final_z_m", 0.0)
            <= 0.80
        ),
        "powered_idle_60c": bool(
            report.get("control", {}).get("mains_power") is True
            and report.get("control", {}).get("heating_enabled") is False
            and abs(
                float(report.get("control", {}).get("temperature_setpoint_c", math.nan))
                - 60.0
            )
            <= 0.5
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
        from pxr import UsdGeom

        settings = carb.settings.get_settings()
        settings.set_bool("/app/omni.graph.scriptnode/enable_opt_in", False)
        settings.set_bool("/app/omni.graph.scriptnode/opt_in", True)
        settings.set_bool("/app/scripting/ignoreWarningDialog", True)
        manager = omni.kit.app.get_app().get_extension_manager()
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
            "obj_context_conical_flask",
        )

        def xyz(name: str) -> list[float]:
            value = (
                UsdGeom.Xformable(stage.GetPrimAtPath("/World/" + name))
                .ComputeLocalToWorldTransform(0)
                .ExtractTranslation()
            )
            return [float(value[index]) for index in range(3)]

        initial = {name: xyz(name) for name in names}
        timeline = omni.timeline.get_timeline_interface()
        timeline.play()
        for _ in range(300):
            app.update()
        final = {name: xyz(name) for name in names}
        timeline.stop()
        control = stage.GetPrimAtPath("/World/obj_oven/ControlPanel")
        report = {
            "schema_version": "scenario-forge-task09-r13-static-play/v0.1",
            "runtime": "isaac41",
            "objects": {
                name: {
                    "initial_xyz_m": initial[name],
                    "final_xyz_m": final[name],
                    "final_z_m": final[name][2],
                    "translation_drift_m": math.sqrt(
                        sum((final[name][index] - initial[name][index]) ** 2 for index in range(3))
                    ),
                }
                for name in names
            },
            "control": {
                "mains_power": bool(control.GetAttribute("oven:mainsPower").Get()),
                "heating_enabled": bool(
                    control.GetAttribute("oven:heatingEnabled").Get()
                ),
                "temperature_setpoint_c": float(
                    control.GetAttribute("oven:temperatureSetpointC").Get()
                ),
                "operating_state": str(
                    control.GetAttribute("oven:operatingState").Get()
                ),
            },
        }
        report.update(evaluate_report(report))
        destination = root / "evidence/runtime/static_play_report.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(destination)
        return 0 if report["status"] == "pass" else 5
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate the materialized titration VR scene without a robot policy."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
from typing import Any


OBJECT_DRIFT_LIMITS = {
    "obj_magnetic_stirrer": 0.005,
    "obj_receiver_flask": 0.02,
    "obj_sample_beaker": 0.02,
    "obj_context_conical_flask": 0.02,
}


def evaluate_burette(states):
    names = ('pre_run', 'running_initial', 'mid', 'end_scale', 'reset')
    checks = {'all_liquid_states_recorded': all(n in states for n in names),
              'precharge_always_visible': bool(states) and all(s['precharge_visible'] for s in states.values())}
    for name in names:
        state = states.get(name, {})
        remaining = float(state.get('remaining_ml', -100))
        checks['burette_'+name] = (
            abs(float(state.get('surface_z', 100)) - (-0.09+0.32*remaining/25)) < 1e-5
            and abs(float(state.get('column_bottom_z', 100))+0.09) < 1e-5
            and state.get('column_visible') == (remaining > 0.01))
    checks['burette_mid_reached'] = 10 < states.get('mid', {}).get('remaining_ml', -1) < 15
    checks['burette_reset_full'] = abs(states.get('reset', {}).get('remaining_ml', -100)-25) < 1e-5
    checks['burette_exhausted'] = abs(states.get('end_scale', {}).get('remaining_ml', -100)) < 1e-5
    return checks


def evaluate_report(report: dict[str, Any]) -> dict[str, Any]:
    objects = report.get("objects", {})
    state = report.get("state_machine", {})
    layout = report.get("layout", {})
    checks = {
        "objects_stable": all(
            float(objects.get(name, {}).get("translation_drift_m", 1.0)) <= limit
            for name, limit in OBJECT_DRIFT_LIMITS.items()
        ),
        "tip_above_receiver": 0.005
        <= float(layout.get("tip_to_receiver_vertical_clearance_m", -1.0))
        <= 0.03,
        "tip_xy_aligned": float(layout.get("tip_receiver_xy_error_m", 1.0)) <= 0.005,
        "ordered_success_path": state.get("success") is True
        and state.get("visited") == {"open": True, "fine": True, "drip": True},
        "endpoint_in_window": 14.7 <= float(state.get("endpoint_dispensed_ml", -1.0)) <= 15.3,
        "closed_hold_three_seconds": float(state.get("hold_seconds", 0.0)) >= 3.0,
        "actual_receiver_pale_pink": state.get("indicator_phase") == "endpoint_pale_pink"
        and state.get("pale_visual_visible") is True,
        "reset_restored": state.get("reset_dispensed_ml") == 0.0,
        "one_dof_station": report.get("dof_count") == 1,
    }
    if "liquid_material" in report:
        material = report['liquid_material']
        def matches(colors, expected):
            return bool(colors) and all(
                len(color) == 3 and all(abs(a-b) < 1e-5 for a, b in zip(color, expected))
                for color in colors
            )
        checks['liquid_material_initial'] = matches(material.get('initial', []), (0.97, 0.99, 1.0))
        checks['liquid_material_endpoint'] = matches(material.get('endpoint', []), (1.0, 0.80, 0.88))
        checks['liquid_material_reset'] = matches(material.get('reset', []), (0.97, 0.99, 1.0))
    if 'burette_states' in report:
        checks.update(evaluate_burette(report['burette_states']))
    return {"status": "pass" if all(checks.values()) else "blocked", "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    original = sys.argv
    sys.argv = [sys.argv[0]]
    try:
        from isaacsim import SimulationApp
    except ImportError:
        from omni.isaac.kit import SimulationApp
    app = SimulationApp({"headless": True, "renderer": "RayTracedLighting", "sync_loads": True})
    sys.argv = original
    report: dict[str, Any] = {
        "schema_version": "scenario-forge-titration-vr-runtime/v0.1",
        "status": "blocked",
        "scene": str(root / "scene.usd"),
        "scene_sha256": sha256((root / "scene.usd").read_bytes()).hexdigest(),
    }
    try:
        import carb.settings
        import numpy as np
        import omni.kit.app
        import omni.usd
        from pxr import Usd, UsdGeom

        settings = carb.settings.get_settings()
        settings.set_bool("/app/omni.graph.scriptnode/enable_opt_in", False)
        settings.set_bool("/app/omni.graph.scriptnode/opt_in", True)
        settings.set_bool("/app/scripting/ignoreWarningDialog", True)
        manager = omni.kit.app.get_app().get_extension_manager()
        for extension in (
            "isaacsim.core.nodes",
            "omni.graph.action_nodes",
            "omni.graph.scriptnode",
        ):
            manager.set_extension_enabled_immediate(extension, True)

        context = omni.usd.get_context()
        if context.open_stage(str(root / "scene.usd")) is False:
            raise RuntimeError("Isaac could not open the titration scene")
        while context.get_stage_loading_status()[2] > 0:
            app.update()
        for _ in range(20):
            app.update()
        stage = context.get_stage()
        stage.SetEditTarget(Usd.EditTarget(stage.GetSessionLayer()))

        base = '/World/obj_titration_station/Instance/Burette/body_link/Visual/'
        has_precharge = bool(stage.GetPrimAtPath(base+'liquid_precharge'))

        def burette_state():
            col = stage.GetPrimAtPath(base+'liquid_column')
            men = stage.GetPrimAtPath(base+'liquid_meniscus')
            st = stage.GetPrimAtPath('/World/obj_titration_station')
            remaining = float(st.GetAttribute('titration:burette_liquid_volume_ml').Get())
            return {'remaining_ml': remaining,
                    'surface_z': float(men.GetAttribute('xformOp:translate').Get()[2]),
                    'column_bottom_z': float(col.GetAttribute('xformOp:translate').Get()[2])-float(col.GetAttribute('height').Get())/2,
                    'column_visible': UsdGeom.Imageable(col).ComputeVisibility() != 'invisible',
                    'precharge_visible': UsdGeom.Imageable(stage.GetPrimAtPath(base+'liquid_precharge')).ComputeVisibility() != 'invisible'}

        if has_precharge:
            report['burette_states'] = {'pre_run': burette_state()}

        try:
            from isaacsim.core.api import World
            from isaacsim.core.prims import SingleArticulation, SingleRigidPrim
        except ImportError:
            from omni.isaac.core import World
            from omni.isaac.core.articulations import Articulation as SingleArticulation
            from omni.isaac.core.prims import RigidPrim as SingleRigidPrim

        world = World(stage_units_in_meters=1.0, physics_dt=1.0 / 60.0)
        articulation = world.scene.add(
            SingleArticulation("/World/obj_titration_station", name="titration_station")
        )
        rigid_prims = {
            name: world.scene.add(SingleRigidPrim("/World/" + name, name=name))
            for name in OBJECT_DRIFT_LIMITS
        }
        world.reset()
        world.play()

        def step(count: int) -> None:
            for _ in range(count):
                world.step(render=False)

        def positions() -> dict[str, list[float]]:
            return {
                name: [float(value) for value in prim.get_world_pose()[0]]
                for name, prim in rigid_prims.items()
            }

        initial_positions = positions()
        station = stage.GetPrimAtPath("/World/obj_titration_station")

        def value(name: str):
            return station.GetAttribute(name).Get()

        def liquid_colors():
            result = []
            for path in station.GetRelationship('titration:receiverLiquidShader').GetTargets():
                attr = stage.GetPrimAtPath(path).GetAttribute('inputs:glass_color')
                if attr:
                    result.append(list(attr.Get()))
            return result

        step(3)
        if has_precharge:
            report['burette_states']['running_initial'] = burette_state()
        if liquid_colors():
            report['liquid_material'] = {'initial': liquid_colors()}

        def set_angle(degrees: float) -> None:
            articulation.set_joint_positions(np.asarray([math.radians(degrees)]))
            step(3)

        def until(threshold: float, max_steps: int) -> None:
            for _ in range(max_steps):
                world.step(render=False)
                if float(value("titration:dispensed_volume_ml")) >= threshold:
                    return
            raise RuntimeError(f"dispensed volume did not reach {threshold}")

        set_angle(90.0)
        if has_precharge:
            until(12.5, 600)
            report['burette_states']['mid'] = burette_state()
        until(14.4, 600)
        set_angle(25.0)
        until(14.7, 180)
        set_angle(10.0)
        until(15.0, 600)
        set_angle(0.0)
        step(190)
        success_state = {
            "success": bool(value("titration:task_success")),
            "endpoint_dispensed_ml": float(value("titration:dispensed_volume_ml")),
            "hold_seconds": float(value("titration:endpoint_hold_seconds")),
            "indicator_phase": str(value("titration:indicator_phase")),
            "visited": {
                "open": bool(value("titration:visited_open")),
                "fine": bool(value("titration:visited_fine")),
                "drip": bool(value("titration:visited_drip")),
            },
            "pale_visual_visible": (
                stage.GetPrimAtPath(
                    "/World/obj_receiver_flask/VisualLiquid/SolutionEndpointPalePink"
                )
                .GetAttribute("visibility")
                .Get()
                == "inherited"
            ),
        }
        if 'liquid_material' in report:
            report['liquid_material']['endpoint'] = liquid_colors()
        if has_precharge:
            set_angle(90.0)
            until(25.0, 900)
            set_angle(0.0)
            report['burette_states']['end_scale'] = burette_state()
        station.GetAttribute("titration:reset_requested").Set(True)
        step(3)
        success_state["reset_dispensed_ml"] = float(value("titration:dispensed_volume_ml"))
        if 'liquid_material' in report:
            report['liquid_material']['reset'] = liquid_colors()
        if has_precharge:
            report['burette_states']['reset'] = burette_state()
        set_angle(0.0)
        step(300)
        final_positions = positions()

        cache = UsdGeom.BBoxCache(
            Usd.TimeCode.Default(),
            [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy],
        )
        tip_box = cache.ComputeWorldBound(
            stage.GetPrimAtPath(
                "/World/obj_titration_station/Instance/Burette/body_link/Visual/delivery_tip"
            )
        ).ComputeAlignedBox()
        flask_box = cache.ComputeWorldBound(
            stage.GetPrimAtPath("/World/obj_receiver_flask")
        ).ComputeAlignedBox()
        tip_center = (tip_box.GetMin() + tip_box.GetMax()) * 0.5
        flask_center = (flask_box.GetMin() + flask_box.GetMax()) * 0.5
        layout = {
            "tip_to_receiver_vertical_clearance_m": float(
                tip_box.GetMin()[2] - flask_box.GetMax()[2]
            ),
            "tip_receiver_xy_error_m": math.hypot(
                float(tip_center[0] - flask_center[0]),
                float(tip_center[1] - flask_center[1]),
            ),
        }
        report.update(
            {
                "runtime_version": app.app.get_app_version(),
                "dof_count": int(articulation.num_dof),
                "objects": {
                    name: {
                        "initial_xyz_m": initial_positions[name],
                        "final_xyz_m": final_positions[name],
                        "translation_drift_m": math.sqrt(
                            sum(
                                (final_positions[name][index] - initial_positions[name][index]) ** 2
                                for index in range(3)
                            )
                        ),
                    }
                    for name in OBJECT_DRIFT_LIMITS
                },
                "state_machine": success_state,
                "layout": layout,
            }
        )
        report.update(evaluate_report(report))
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        app.close()
    print(args.output)
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())

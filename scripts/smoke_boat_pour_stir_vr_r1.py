#!/usr/bin/env python3
"""Isaac 4.5 short physics smoke for boat-pour-then-stir VR r1."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import traceback


GRAIN_COUNT = 30
PARTICLE_SET = "/World/ParticleSet"
BOAT = "/World/obj_weighing_boat"
CYLINDER = "/World/obj_graduated_cylinder"
BALANCE = "/World/obj_analytical_balance"
HARD_MARKERS = (
    "Unrecognized primvar 'displayColor'",
    "Unrecognized primvar 'displayOpacity'",
    "CUDA error",
    "illegal memory access",
    "Non-GPU-compatible convex mesh",
    "Failed to cook",
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _parse_lcd(text: object) -> float | None:
    if not isinstance(text, str):
        return None
    stripped = text.strip().replace("g", "").strip()
    try:
        return float(stripped)
    except ValueError:
        return None


def _box_contains(box: object, point: object, pad: float = 0.006) -> bool:
    low, high = box.GetMin(), box.GetMax()
    return all(
        float(low[i]) - pad <= float(point[i]) <= float(high[i]) + pad for i in range(3)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("outputs/scientific_workbench_boat_pour_stir_vr_r1_20260920"),
    )
    parser.add_argument("--seconds", type=float, default=3.0)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    scene = root / "scene.usd"
    if not scene.is_file():
        raise FileNotFoundError(scene)
    out = (args.out or (root / "evidence/isaac45_runtime_smoke.json")).resolve()
    original = sys.argv
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True, "multi_gpu": False})
    sys.argv = original
    report: dict[str, object] = {
        "schema_version": "scenario-forge.boat-pour-stir-vr-r1-smoke.v1",
        "status": "failed",
        "scene": str(scene),
        "scene_sha256": _sha(scene),
        "requested_seconds": args.seconds,
        "requested_hz": 120,
    }
    try:
        import carb.logging
        import carb.settings
        import omni.kit.app
        import omni.physx
        import omni.physx.bindings._physx as pb
        import omni.usd
        from pxr import Usd, UsdGeom

        try:
            from isaacsim.core.api import World
        except ImportError:
            from omni.isaac.core import World

        fatal_errors: list[str] = []
        log_stream = app.app.get_log_event_stream()

        def on_log(event: object) -> None:
            payload = getattr(event, "payload", {})
            if payload.get("level", 0) >= carb.logging.LEVEL_ERROR:
                fatal_errors.append(str(payload))

        _log_sub = log_stream.create_subscription_to_pop(
            on_log, name="boat_pour_stir physics errors"
        )
        settings = carb.settings.get_settings()
        settings.set_bool("/app/omni.graph.scriptnode/enable_opt_in", False)
        settings.set_bool("/app/omni.graph.scriptnode/opt_in", True)
        settings.set_bool("/app/scripting/ignoreWarningDialog", True)
        settings.set(pb.SETTING_UPDATE_TO_USD, True)
        settings.set(pb.SETTING_UPDATE_PARTICLES_TO_USD, True)
        settings.set(pb.SETTING_UPDATE_VELOCITIES_TO_USD, True)
        settings.set_bool(pb.SETTING_SUPPRESS_READBACK, False)
        settings.set_bool("/physics/suppressReadback", False)
        manager = omni.kit.app.get_app().get_extension_manager()
        for extension in (
            "isaacsim.core.nodes",
            "omni.isaac.core_nodes",
            "omni.graph.action_nodes",
            "omni.graph.scriptnode",
        ):
            manager.set_extension_enabled_immediate(extension, True)
        omni.physx.get_physx_interface().overwrite_gpu_setting(1)
        log_path = Path(str(settings.get("/log/file") or ""))
        log_offset = log_path.stat().st_size if log_path.exists() else 0

        context = omni.usd.get_context()
        if not context.open_stage(str(scene)):
            raise RuntimeError(f"cannot open {scene}")
        while context.get_stage_loading_status()[2]:
            app.update()
        for _ in range(20):
            app.update()
        stage = context.get_stage()
        stage.SetEditTarget(stage.GetSessionLayer())
        step_node = stage.GetPrimAtPath(
            "/World/obj_analytical_balance/BalanceRuntime/Graph/OnPhysicsStep"
        )
        if step_node.IsValid():
            step_node.GetAttribute("node:type").Set("isaacsim.core.nodes.OnPhysicsStep")
        report["runtime"] = {
            "name": "Isaac Sim 4.5.0",
            "kit_version": str(omni.kit.app.get_app().get_app_version()),
        }
        report["on_physics_step_type"] = (
            step_node.GetAttribute("node:type").Get() if step_node.IsValid() else None
        )

        world = World(
            stage_units_in_meters=1.0,
            physics_prim_path="/World/PhysicsScene",
            set_defaults=False,
            physics_dt=1 / 120,
            rendering_dt=1 / 120,
        )
        physics = world.get_physics_context()
        physics.enable_gpu_dynamics(True)
        physics.set_broadphase_type("GPU")
        physics.set_solver_type("TGS")
        physics.set_physics_dt(1 / 120)
        world.reset()
        world.get_physics_context().set_physics_dt(1 / 120)
        log_stream.pump()
        if fatal_errors:
            raise RuntimeError("Physics initialization error: " + fatal_errors[0])

        steps = max(1, round(args.seconds * 120))
        rendered_steps = min(60, steps)
        for step in range(steps):
            world.step(render=step < rendered_steps)
        log_stream.pump()
        _ = _log_sub

        cache = UsdGeom.BBoxCache(
            Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]
        )
        boat_prim = stage.GetPrimAtPath(BOAT)
        boat_box = cache.ComputeWorldBound(boat_prim).ComputeAlignedBox()
        cylinder_box = cache.ComputeWorldBound(
            stage.GetPrimAtPath(CYLINDER)
        ).ComputeAlignedBox()
        boat_mid = boat_box.GetMidpoint()
        boat_xf = UsdGeom.Xformable(boat_prim).ComputeLocalToWorldTransform(
            Usd.TimeCode.Default()
        ).ExtractTranslation()
        report["boat_live_xyz"] = [float(boat_mid[0]), float(boat_mid[1]), float(boat_mid[2])]
        report["boat_xform_xyz"] = [float(boat_xf[0]), float(boat_xf[1]), float(boat_xf[2])]
        grain_inside = 0
        grain_points: list[list[float]] = []
        for index in range(GRAIN_COUNT):
            prim = stage.GetPrimAtPath(f"/World/obj_powder_grain_{index:05d}")
            xform = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(
                Usd.TimeCode.Default()
            )
            point = xform.ExtractTranslation()
            grain_points.append([float(point[0]), float(point[1]), float(point[2])])
            if _box_contains(boat_box, point, pad=0.008):
                grain_inside += 1

        particle_set = stage.GetPrimAtPath(PARTICLE_SET)
        live = particle_set.GetAttribute("physxParticle:simulationPoints").Get()
        points = live or particle_set.GetAttribute("points").Get() or []
        pbd_inside = sum(1 for point in points if _box_contains(cylinder_box, point))
        pbd_below = sum(1 for point in points if float(point[2]) < 0.70)

        balance = stage.GetPrimAtPath(BALANCE)
        def _bal(name: str) -> object:
            return balance.GetAttribute(f"balance:{name}").Get()

        lcd = _bal("lcd_readout")
        net_g = _bal("net_g")
        tare_g = _bal("tare_g")
        tared = _bal("tared")
        lcd_g = _parse_lcd(lcd)
        log_text = (
            log_path.read_text(encoding="utf-8", errors="replace")[log_offset:]
            if log_path.exists()
            else ""
        )
        hard_errors = [
            line.strip()
            for line in log_text.splitlines()
            if any(marker in line for marker in HARD_MARKERS)
        ]
        hard_errors.extend(fatal_errors)
        lcd_ok = lcd_g is not None and 0.04 <= lcd_g <= 0.08
        net_ok = isinstance(net_g, (int, float)) and 0.04 <= float(net_g) <= 0.08
        gross_g = _bal("gross_g")
        untared_load_ok = (
            isinstance(gross_g, (int, float))
            and 10.04 <= float(gross_g) <= 10.12
            and lcd not in (None, "------")
        )
        passed = (
            not hard_errors
            and grain_inside >= 28
            and len(points) >= 900
            and pbd_inside >= 900
            and pbd_below == 0
            and (lcd_ok or net_ok or untared_load_ok)
        )
        report.update(
            {
                "status": "pass" if passed else "blocked",
                "physics_steps": steps,
                "rendered_steps": rendered_steps,
                "world_physics_dt": world.get_physics_dt(),
                "grains": {
                    "count": GRAIN_COUNT,
                    "inside_boat": grain_inside,
                    "sample_xyz": grain_points[:3],
                },
                "pbd": {
                    "live_count": len(points),
                    "inside_cylinder": pbd_inside,
                    "below_table": pbd_below,
                    "used_simulation_points": bool(live),
                },
                "balance": {
                    "lcd_readout": lcd,
                    "lcd_g": lcd_g,
                    "net_g": net_g,
                    "tare_g": tare_g,
                    "tared": tared,
                    "gross_g": _bal("gross_g"),
                    "status": _bal("status"),
                    "valid": _bal("valid"),
                    "stable": _bal("stable"),
                    "error": _bal("error"),
                    "target_g": _bal("target_g"),
                },
                "hard_errors": hard_errors,
                "claims": {
                    "isaac45_cold_start_ran": True,
                    "engine_crash": False,
                    "lcd_near_0_06_g": bool(lcd_ok or net_ok),
                    "untared_boat_plus_grains": bool(untared_load_ok),
                    "grains_retained_in_boat": grain_inside >= 28,
                    "pbd_retained_in_cylinder": pbd_inside >= 900,
                    "robot_policy_success": False,
                    "liquid_transfer_verified": False,
                    "dissolve_verified": False,
                    "scene_fixture_verified": False,
                },
            }
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if passed else 1
    except BaseException:
        report["status"] = "failed"
        report["traceback"] = traceback.format_exc()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        traceback.print_exc()
        return 2
    finally:
        app.close()


if __name__ == "__main__":
    try:
        code = main()
    except BaseException:
        traceback.print_exc()
        code = 2
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)

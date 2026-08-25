#!/usr/bin/env python3
"""Render and step both r5 liquid entrypoints on Isaac Sim 4.1 or 4.5."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
import traceback


PARTICLE_SET = "/World/fluid_runtime/ParticleSets/beaker_liquid"
SAMPLER = "/World/fluid_runtime/Samplers/beaker_liquid/Volume"
HYDRA_MARKERS = (
    "Unrecognized primvar 'displayColor'",
    "Unrecognized primvar 'displayOpacity'",
)
HARD_MARKERS = HYDRA_MARKERS + (
    "CUDA error",
    "illegal memory access",
    "Non-GPU-compatible convex mesh",
    "Failed to cook",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--runtime-label", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=3.0)
    args = parser.parse_args()
    root = args.root.resolve()
    original = sys.argv
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp

    app = SimulationApp(
        {"headless": True, "multi_gpu": False, "renderer": "RayTracedLighting"}
    )
    sys.argv = original
    try:
        import carb
        import omni.kit.app
        import omni.physx
        import omni.physx.bindings._physx as pb
        import omni.usd
        try:
            from isaacsim.core.api import World
        except ImportError:
            from omni.isaac.core import World
        from pxr import Usd, UsdGeom, UsdShade

        settings = carb.settings.get_settings()
        settings.set(pb.SETTING_UPDATE_TO_USD, True)
        settings.set(pb.SETTING_UPDATE_PARTICLES_TO_USD, True)
        settings.set(pb.SETTING_UPDATE_VELOCITIES_TO_USD, True)
        settings.set_bool(pb.SETTING_SUPPRESS_READBACK, False)
        settings.set_bool("/physics/suppressReadback", False)
        omni.physx.get_physx_interface().overwrite_gpu_setting(1)
        log_path = Path(str(settings.get("/log/file")))
        context = omni.usd.get_context()
        entries = {}
        all_errors = []

        for scene_name in ("scene.usd", "scene_liquid_edit.usd"):
            if hasattr(World, "clear_instance"):
                World.clear_instance()
            scene_path = root / "vr" / scene_name
            log_offset = log_path.stat().st_size if log_path.exists() else 0
            if not context.open_stage(str(scene_path)):
                raise RuntimeError(f"cannot open {scene_path}")
            for _ in range(50):
                app.update()
            stage = context.get_stage()
            physics_scenes = [
                str(prim.GetPath())
                for prim in stage.Traverse()
                if prim.IsActive() and prim.GetTypeName() == "PhysicsScene"
            ]
            particles = stage.GetPrimAtPath(PARTICLE_SET)
            authored_display = {
                name: particles.GetAttribute(name).HasAuthoredValueOpinion()
                for name in ("primvars:displayColor", "primvars:displayOpacity")
            }
            material, _ = UsdShade.MaterialBindingAPI(particles).ComputeBoundMaterial()
            shader = UsdShade.Shader(
                stage.GetPrimAtPath(str(material.GetPath()) + "/PreviewSurface")
            )
            authored_count = len(particles.GetAttribute("points").Get() or [])
            world = World(
                stage_units_in_meters=1.0,
                physics_prim_path="/World/physicsScene",
                set_defaults=False,
                physics_dt=1 / 120,
                rendering_dt=1 / 120,
            )
            world.reset()
            steps = max(1, round(args.seconds * 120))
            rendered_steps = min(60, steps)
            for step in range(steps):
                world.step(render=step < rendered_steps)
            values = particles.GetAttribute("points").Get() or []
            beaker_box = UsdGeom.BBoxCache(
                Usd.TimeCode.Default(),
                [UsdGeom.Tokens.default_, UsdGeom.Tokens.render],
            ).ComputeWorldBound(stage.GetPrimAtPath("/World/obj_beaker")).ComputeAlignedBox()
            low, high = beaker_box.GetMin(), beaker_box.GetMax()
            inside = sum(
                all(float(low[i]) - 0.006 <= float(point[i]) <= float(high[i]) + 0.006 for i in range(3))
                for point in values
            )
            below = sum(float(point[2]) < float(low[2]) - 0.006 for point in values)
            text = log_path.read_text(encoding="utf-8", errors="replace")[log_offset:] if log_path.exists() else ""
            errors = [
                line.strip()
                for line in text.splitlines()
                if any(marker in line for marker in HARD_MARKERS)
            ]
            all_errors.extend(errors)
            sampler_targets = []
            if scene_name == "scene_liquid_edit.usd":
                sampler = stage.GetPrimAtPath(SAMPLER)
                sampler_targets = [
                    str(path)
                    for path in sampler.GetRelationship(
                        "physxParticleSampling:particles"
                    ).GetTargets()
                ] if sampler else []
            entries[scene_name] = {
                "active_physics_scenes": physics_scenes,
                "authored_particle_count": authored_count,
                "live_particle_count": len(values),
                "retention_ratio": inside / len(values) if values else 0.0,
                "below_floor_count": below,
                "display_primvars_authored": authored_display,
                "material_path": str(material.GetPath()) if material else None,
                "diffuse_color": list(shader.GetInput("diffuseColor").Get()),
                "opacity": float(shader.GetInput("opacity").Get()),
                "sampler_targets": sampler_targets,
                "rendered_steps": rendered_steps,
                "hard_errors": errors,
            }
        frozen = entries["scene.usd"]
        editable = entries["scene_liquid_edit.usd"]
        passed = (
            not all_errors
            and all(
                item["active_physics_scenes"] == ["/World/physicsScene"]
                and not any(item["display_primvars_authored"].values())
                and item["live_particle_count"] > 0
                and item["retention_ratio"] >= 0.99
                and item["below_floor_count"] == 0
                and item["material_path"] is not None
                for item in entries.values()
            )
            and frozen["authored_particle_count"] == 969
            and editable["sampler_targets"] == [PARTICLE_SET]
            and math.isclose(frozen["opacity"], 0.34, abs_tol=1e-6)
        )
        report = {
            "schema_version": "scenario-forge.stir-bar-vr-r5-render-gate.v1",
            "status": "pass" if passed else "blocked",
            "runtime": {
                "name": args.runtime_label,
                "kit_version": str(omni.kit.app.get_app().get_app_version()),
            },
            "entries": entries,
            "hydra_primvar_error_count": sum(
                any(marker in line for marker in HYDRA_MARKERS)
                for line in all_errors
            ),
            "hard_errors": all_errors,
            "claims": {
                "shared_particle_system_material": True,
                "particle_display_primvars_authored": False,
                "render_compatibility": passed,
                "robot_policy_success": False,
                "benchmark_success": False,
            },
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if passed else 1
    except BaseException:
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

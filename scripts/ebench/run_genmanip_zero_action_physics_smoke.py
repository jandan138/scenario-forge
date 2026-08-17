#!/usr/bin/env python3
"""Run one fail-closed, zero-action GenManip physics smoke.

This is package validation evidence, not an episode runner: it constructs the
collected scene, performs GenManip reset/recovery, advances exactly 960 physics
steps without an action, records finite task-object transforms and particle
counts, then exits.
"""

from __future__ import annotations

import argparse
import gc
import importlib.metadata
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


STEPS = 960
SCHEMA = "scenario-forge-genmanip-zero-action-physics-smoke/v0.1"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collected-root", type=Path, required=True)
    parser.add_argument("--genmanip-root", type=Path, required=True)
    parser.add_argument(
        "--request", type=Path, default=Path("evidence/render_request.yaml")
    )
    return parser


def _translation(stage: Any, path: str, UsdGeom: Any, Usd: Any) -> list[float]:
    prim = stage.GetPrimAtPath(path)
    if not prim or not prim.IsValid():
        raise RuntimeError(f"runtime prim is missing: {path}")
    matrix = UsdGeom.XformCache(Usd.TimeCode.Default()).GetLocalToWorldTransform(prim)
    value = matrix.ExtractTranslation()
    result = [float(value[0]), float(value[1]), float(value[2])]
    if not all(math.isfinite(item) for item in result):
        raise RuntimeError(f"runtime prim has a non-finite transform: {path}")
    return result


def _particle_counts(stage: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for prim in stage.Traverse():
        attribute = prim.GetAttribute("physxParticle:simulationPoints")
        if not attribute or not attribute.IsValid():
            continue
        points = attribute.Get()
        counts[str(prim.GetPath())] = 0 if points is None else len(points)
    if not counts:
        raise RuntimeError("no PhysX particle simulationPoints were found")
    return counts


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _write_report(root: Path, report: Mapping[str, Any]) -> Path:
    destination = root / "evidence/product_smoke/report.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return destination


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    collected_root = args.collected_root.resolve()
    genmanip_root = args.genmanip_root.resolve()
    if str(genmanip_root) not in sys.path:
        sys.path.insert(0, str(genmanip_root))

    # Import the helper module before SimulationApp only for its pure parsing
    # helpers. Simulator imports remain below the process boundary.
    import render_genmanip_initial_preview as preview
    from isaacsim import SimulationApp

    simulation_app = SimulationApp(
        {
            "headless": True,
            "renderer": "RayTracedLighting",
            "multi_gpu": False,
            "width": 320,
            "height": 240,
        }
    )
    scene = None
    try:
        from pxr import Usd, UsdGeom
        from genmanip.core.scene.scene import Scene
        from genmanip.core.scene.scene_config import SceneConfig
        from genmanip.utils.loader.domain_randomization import reset_scene
        from genmanip.utils.loader.scene import recovery_scene
        from genmanip.utils.standalone.file_utils import load_default_config

        request = preview._load_mapping(
            (collected_root / args.request).resolve(), "render request"
        )
        inputs = preview._required_mapping(request, "inputs", "render request")
        task_config_path = preview._input_path(collected_root, inputs, "task_config")
        episode_path = preview._input_path(collected_root, inputs, "episode_metadata")
        scene_path = preview._input_path(collected_root, inputs, "scene_usd")
        evaluation_camera_path = preview._input_path(
            collected_root, inputs, "evaluation_camera"
        )
        task_config = preview._load_mapping(task_config_path, "task config")
        episode = preview._load_json_mapping(episode_path, "episode metadata")
        task_name = preview._required_string(request, "task_name", "render request")
        package_id = preview._required_string(request, "package_id", "render request")
        task_data = preview._required_mapping(episode, "task_data", "episode metadata")
        preview._resolve_collected_asset_paths_for_preview(
            task_data, collected_root, package_id
        )
        evaluation = preview._select_evaluation(task_config, task_name)
        evaluation["usd_name"] = str(scene_path.with_suffix(""))
        domain = preview._required_mapping(
            evaluation, "domain_randomization", "evaluation"
        )
        cameras = preview._required_mapping(
            domain, "cameras", "evaluation domain_randomization"
        )
        cameras["config_path"] = str(evaluation_camera_path)
        domain["cameras"] = cameras
        evaluation["domain_randomization"] = domain

        default_config = load_default_config(
            str(genmanip_root), "__scenario_forge_physics_smoke__.json", "local"
        )
        scene = Scene(SceneConfig(**evaluation))
        scene.initialize(
            default_config,
            physics_dt=float(evaluation.get("physics_dt", 1.0 / 120.0)),
            rendering_dt=float(evaluation.get("rendering_dt", 1.0 / 60.0)),
            is_render=False,
            only_color_rep_for_camera=True,
        )
        scene.post_initialize()
        reset_scene(scene)
        preserved = tuple(scene.articulation_part_list)
        recovery_scene(
            scene,
            preview._task_data_with_preserved_articulation_parts(task_data, preserved),
            task_name,
            default_config,
        )
        stage = scene.world.stage
        expected = preview._required_mapping(
            request, "expected_runtime_ids", "render request"
        )
        task_ids = preview._string_list(
            expected.get("task_objects"), "expected_runtime_ids.task_objects"
        )
        runtime_paths = {
            runtime_id: f"/World/{scene.uuid}/obj_{runtime_id}" for runtime_id in task_ids
        }
        before_translations = {
            runtime_id: _translation(stage, path, UsdGeom, Usd)
            for runtime_id, path in runtime_paths.items()
        }
        before_particles = _particle_counts(stage)
        for _ in range(STEPS):
            scene.world.step(render=False)
        after_translations = {
            runtime_id: _translation(stage, path, UsdGeom, Usd)
            for runtime_id, path in runtime_paths.items()
        }
        after_particles = _particle_counts(stage)
        if before_particles != after_particles:
            raise RuntimeError(
                f"particle count changed during zero-action smoke: "
                f"{before_particles} -> {after_particles}"
            )
        drift = {
            runtime_id: math.dist(before_translations[runtime_id], after_translations[runtime_id])
            for runtime_id in task_ids
        }
        report = {
            "schema_version": SCHEMA,
            "status": "pass",
            "package_id": package_id,
            "runtime": {
                "engine": "Isaac Sim",
                "isaac_sim_version": _package_version("isaacsim"),
                "physics_rate_hz": 120,
                "render_without_physics": False,
            },
            "phases": {
                "genmanip_scene_constructed": "pass",
                "physics_initialized": "pass",
                "reset_and_recovery": "pass",
                "zero_action_physics": "pass",
            },
            "physics_steps": STEPS,
            "physics_duration_s": 8.0,
            "action_count": 0,
            "task_object_translation_before_m": before_translations,
            "task_object_translation_after_m": after_translations,
            "task_object_drift_m": drift,
            "particle_counts": after_particles,
            "claim_boundary": (
                "GenManip construction, reset/recovery, and 960 zero-action physics "
                "steps only; not robot transfer, liquid metric, policy, or benchmark success."
            ),
        }
        destination = _write_report(collected_root, report)
        print(f"PHYSICS_SMOKE_PASS {destination}", flush=True)
        return 0
    finally:
        if scene is not None:
            try:
                scene.world.stop()
                scene.world.clear_instance()
            except Exception:
                pass
            del scene
            gc.collect()
        simulation_app.close()


if __name__ == "__main__":
    raise SystemExit(main())

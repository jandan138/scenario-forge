#!/usr/bin/env python3
"""Open one VR review USD in Isaac Sim 4.1 and emit a narrow load report."""

from __future__ import annotations

import argparse
import ast
import importlib.metadata
import json
from pathlib import Path
from typing import Any, Sequence


SCHEMA = "scenario-forge-vr-usd-open-smoke/v0.2"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vr-root", type=Path, required=True)
    return parser


def _version() -> str | None:
    try:
        return importlib.metadata.version("isaacsim")
    except importlib.metadata.PackageNotFoundError:
        return None


def _task_ids(config_path: Path) -> list[str]:
    tree = ast.parse(config_path.read_text(encoding="utf-8"), filename=str(config_path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "TASKS" for target in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            raise ValueError("TASKS must be a dictionary literal")
        result = []
        for key in node.value.keys:
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                raise ValueError("TASKS keys must be string literals")
            result.append(key.value)
        if not result:
            raise ValueError("TASKS must contain at least one task")
        return result
    raise ValueError("task_config.py does not define TASKS")


def _task_configs(config_path: Path) -> dict[str, dict[str, Any]]:
    namespace: dict[str, Any] = {"_ASSETS_DIR": Path("/runtime/assets")}
    exec(compile(config_path.read_text(encoding="utf-8"), str(config_path), "exec"), namespace)
    tasks = namespace.get("TASKS")
    if not isinstance(tasks, dict) or not tasks:
        raise ValueError("task_config.py must define a non-empty TASKS dictionary")
    if not all(isinstance(key, str) and isinstance(value, dict) for key, value in tasks.items()):
        raise ValueError("TASKS must map string ids to dictionaries")
    return tasks


def _stage_contract(stage: Any) -> dict[str, Any]:
    default_prim = stage.GetDefaultPrim()
    if not default_prim or not default_prim.IsValid():
        raise RuntimeError("VR scene has no valid default prim")
    if str(default_prim.GetPath()) != "/World":
        raise RuntimeError("VR source defaultPrim must resolve to /World")
    if stage.GetPrimAtPath("/World/_scene").IsValid():
        raise RuntimeError("VR source must not author /World/_scene; runtime owns that mount")
    children = {child.GetName(): child for child in default_prim.GetChildren()}
    missing_roots = [name for name in ("background", "table", "vr_direct_open_light") if name not in children]
    if missing_roots:
        raise RuntimeError("VR source is missing direct /World children: " + ", ".join(missing_roots))
    object_names = sorted(name for name in children if name.startswith("obj_"))
    if not object_names:
        raise RuntimeError("VR source has no direct obj_* children")
    light = children["vr_direct_open_light"]
    if light.GetTypeName() != "DomeLight":
        raise RuntimeError("/World/vr_direct_open_light must be a DomeLight")
    intensity = light.GetAttribute("inputs:intensity").Get()
    if intensity is None or abs(float(intensity) - 750.0) > 1e-6:
        raise RuntimeError("VR direct-open DomeLight intensity must be 750")
    fluid_required: list[str] = []
    fluid = stage.GetPrimAtPath("/World/fluid_runtime")
    if fluid.IsValid():
        fluid_required = [
            "/World/fluid_runtime/Source",
            "/World/fluid_runtime/Target",
            "/World/fluid_runtime/ParticleSet",
        ]
        missing = [path for path in fluid_required if not stage.GetPrimAtPath(path).IsValid()]
        if missing:
            raise RuntimeError("VR fluid scene is missing required prims: " + ", ".join(missing))
    return {
        "default_prim": "/World",
        "direct_children": sorted(children),
        "object_names": object_names,
        "fluid_required_prims": fluid_required,
        "light": {"prim": "/World/vr_direct_open_light", "type": "DomeLight", "intensity": 750.0},
    }


def _config_contract(tasks: dict[str, dict[str, Any]], stage_contract: dict[str, Any]) -> dict[str, Any]:
    object_names = stage_contract["object_names"]
    expected_paths = {f"/World/_scene/{name}" for name in object_names}
    fluid_expected = bool(stage_contract["fluid_required_prims"])
    summaries = []
    for task_id, task in tasks.items():
        obj_paths = task.get("obj_prim_list")
        if not isinstance(obj_paths, list) or set(obj_paths) != expected_paths:
            raise RuntimeError(f"{task_id} obj_prim_list does not exactly cover direct obj_* children")
        layout = task.get("layout_randomization")
        if not isinstance(layout, dict) or layout.get("table") != "table":
            raise RuntimeError(f"{task_id} layout_randomization.table must be table")
        groups = layout.get("objects")
        if not isinstance(groups, list):
            raise RuntimeError(f"{task_id} layout_randomization.objects must be a list")
        randomized: list[str] = []
        for group in groups:
            if not isinstance(group, dict):
                raise RuntimeError(f"{task_id} randomization group must be a dictionary")
            if group.get("mode") != "local":
                raise RuntimeError(f"{task_id} randomization groups must use local mode")
            if group.get("x_offset_range") != [-0.01, 0.01] or group.get("y_offset_range") != [-0.01, 0.01]:
                raise RuntimeError(f"{task_id} randomization groups must use +/- 0.01 m x/y")
            if group.get("yaw_range_degrees") != [0.0, 0.0]:
                raise RuntimeError(f"{task_id} randomization groups must keep yaw fixed")
            names = group.get("objs")
            if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
                raise RuntimeError(f"{task_id} randomization group objs must be strings")
            randomized.extend(names)
        expected_randomized = set(object_names)
        if fluid_expected:
            expected_randomized.add("fluid_runtime")
        if set(randomized) != expected_randomized or len(randomized) != len(expected_randomized):
            raise RuntimeError(f"{task_id} randomization groups do not exactly cover movable content")
        summaries.append({"task_id": task_id, "obj_prim_count": len(obj_paths), "randomized_names": randomized})
    return {"tasks": summaries}


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.vr_root.resolve()
    scene_path = root / "scene.usd"
    config_path = root / "task_config.py"
    task_ids = _task_ids(config_path)
    task_configs = _task_configs(config_path)

    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True, "renderer": "RayTracedLighting"})
    try:
        import omni.usd

        context = omni.usd.get_context()
        if not context.open_stage(str(scene_path)):
            raise RuntimeError(f"Isaac Sim could not open {scene_path}")
        for _ in range(20):
            app.update()
        stage = context.get_stage()
        if stage is None:
            raise RuntimeError("Isaac Sim returned no stage after open")
        stage_contract = _stage_contract(stage)
        config_contract = _config_contract(task_configs, stage_contract)
        report: dict[str, Any] = {
            "schema_version": SCHEMA,
            "status": "pass",
            "runtime": {"engine": "Isaac Sim", "isaac_sim_version": _version()},
            "scene_usd": "scene.usd",
            "task_config": "task_config.py",
            "task_ids": task_ids,
            "default_prim": stage_contract["default_prim"],
            "direct_root_contract": stage_contract,
            "config_contract": config_contract,
            "physics_steps": 0,
            "claim_boundary": (
                "Isaac Sim USD open and static VR config syntax only; not teleoperation, "
                "robot insertion, physics, liquid metric, or task success."
            ),
        }
        destination = root / "evidence/open_smoke/report.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(f"VR_OPEN_PASS {destination}", flush=True)
        return 0
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())

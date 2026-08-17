#!/usr/bin/env python3
"""Open one VR review USD in Isaac Sim 4.1 and emit a narrow load report."""

from __future__ import annotations

import argparse
import ast
import importlib.metadata
import json
from pathlib import Path
from typing import Any, Sequence


SCHEMA = "scenario-forge-vr-usd-open-smoke/v0.1"


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


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.vr_root.resolve()
    scene_path = root / "scene.usd"
    config_path = root / "task_config.py"
    task_ids = _task_ids(config_path)

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
        default_prim = stage.GetDefaultPrim()
        if not default_prim or not default_prim.IsValid():
            raise RuntimeError("VR scene has no valid default prim")
        required = (
            "/World/_scene/fluid_runtime/Source",
            "/World/_scene/fluid_runtime/Target",
            "/World/_scene/fluid_runtime/ParticleSet",
        )
        missing = [path for path in required if not stage.GetPrimAtPath(path).IsValid()]
        if missing:
            raise RuntimeError("VR scene is missing required prims: " + ", ".join(missing))
        report: dict[str, Any] = {
            "schema_version": SCHEMA,
            "status": "pass",
            "runtime": {"engine": "Isaac Sim", "isaac_sim_version": _version()},
            "scene_usd": "scene.usd",
            "task_config": "task_config.py",
            "task_ids": task_ids,
            "default_prim": str(default_prim.GetPath()),
            "required_prims": list(required),
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

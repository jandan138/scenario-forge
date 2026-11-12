#!/usr/bin/env python3
"""Add a VR collection entry beside the task_09 weighing scene.

The clean main scene stays without a room, light, or PhysicsScene. This entry
sublayers that scene, references the admitted modern-wet-chemistry room, and
adds the texture-free direct-open DomeLight used by earlier VR handoffs.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "scientific_workbench_solid_weighing_task09_r1"
ROOM_ID = "scientific_environment_code_room_wet_chemistry_v2"
ROOM_SOURCE = (
    REPO_ROOT
    / "external_artifacts/build_inputs/v1/environment-0c45bdf06b0d2b2c/source_bundle"
    / ROOM_ID
)
DEFAULT_PACKAGE = (
    REPO_ROOT
    / "outputs/task09_solid_weighing_r1_20261008/handoff"
    / TASK_ID
)


def build(package: Path, output: Path) -> Path:
    """Write ``vr/scene.usd`` and ``vr/task_config.py`` under ``output``."""

    package = package.resolve()
    output = output.resolve()
    main = package / "scene/main.usda"
    if not main.is_file():
        raise FileNotFoundError(main)
    if not (ROOM_SOURCE / "asset.usd").is_file():
        raise FileNotFoundError(ROOM_SOURCE / "asset.usd")
    if any(path.is_symlink() for path in ROOM_SOURCE.rglob("*")):
        raise ValueError(f"room input contains a symlink: {ROOM_SOURCE}")

    output.mkdir(parents=True, exist_ok=True)
    room_dest = output / "deps/environment" / ROOM_ID
    if room_dest.exists():
        shutil.rmtree(room_dest)
    shutil.copytree(ROOM_SOURCE, room_dest)
    main_rel = Path(os.path.relpath(main, output)).as_posix()
    (output / "scene.usd").write_text(_scene_text(main_rel), encoding="utf-8")
    (output / "task_config.py").write_text(_task_config(_registration(output / "scene.usd")), encoding="utf-8")
    return output


def _scene_text(main_rel: str) -> str:
    room = f"deps/environment/{ROOM_ID}/asset.usd"
    return f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
    subLayers = [@{main_rel}@]
)

over "World"
{{
    def Xform "background" (
        prepend references = @{room}@</World>
    )
    {{
        double3 xformOp:translate = (0.002882434, -0.0069055, 0)
        quatd xformOp:orient = (0, 0, 0, 1)
        double3 xformOp:scale = (1, 1, 1)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient", "xformOp:scale"]
        over "Beaker325ml" (
            active = false
        )
        {{
        }}
        over "GraduatedCylinder250ml" (
            active = false
        )
        {{
        }}
        over "PhysicsScene" (
            active = false
        )
        {{
        }}
        over "table" (
            active = false
        )
        {{
        }}
    }}

    def DomeLight "vr_direct_open_light"
    {{
        color3f inputs:color = (1, 1, 1)
        float inputs:exposure = 0
        float inputs:intensity = 750
    }}
}}
"""


def _registration(scene_path: Path) -> tuple[list[str], list[str]]:
    from pxr import Usd, UsdPhysics

    stage = Usd.Stage.Open(str(scene_path))
    world = stage.GetPrimAtPath("/World")
    roots = [child.GetName() for child in world.GetChildren() if child.GetName().startswith("obj_")]
    balance = stage.GetPrimAtPath("/World/obj_analytical_balance")
    links = [
        str(prim.GetPath()).replace("/World/", "/World/_scene/", 1)
        for prim in Usd.PrimRange(balance)
        if prim.HasAPI(UsdPhysics.RigidBodyAPI)
    ]
    return roots, links


def _task_config(registration: tuple[list[str], list[str]]) -> str:
    roots, links = registration
    objects = [f'"/World/_scene/{name}"' for name in roots] + [f'"{path}"' for path in links]
    groups = ",\n".join(_group(name) for name in roots)
    object_lines = ",\n        ".join(objects)
    return f"""# Merge this TASKS entry into the VR plugin mapping.
# Deploy this directory at _ASSETS_DIR/scenes/{TASK_ID}/.
# The robot keys configure the collector-spawned robot. This USD does not contain one.
from pathlib import Path

_ASSETS_DIR = Path(__file__).resolve().parents[2]
TASKS = {{
    "{TASK_ID}": {{
        "scene_usd_file_path": {{
            "scene1": str(_ASSETS_DIR / "scenes/{TASK_ID}/scene.usd"),
        }},
        "obj_prim_list": [
        {object_lines},
        ],
        "layout_randomization": {{
            "table": "table",
            "objects": [
{groups}
            ],
        }},
        "robot_cfg": {{
            "position": [0.0, -1.02, 0.31],
            "orientation": [0.7071067812, 0.0, 0.0, 0.7071067812],
        }},
        "physx_scene_cfg": {{
            "BroadphaseType": "GPU",
            "EnableGPUDynamics": True,
            "SolverType": "TGS",
            "TimeStepsPerSecond": 120,
        }},
        "set_robot_physics_material": {{
            "Restitution": 0.0,
            "DynamicFriction": 0.5,
            "StaticFriction": 0.5,
            "FrictionCombineMode": "max",
            "RestitutionCombineMode": "multiply",
            "ImprovePatchFriction": True,
        }},
        "set_robot_contact_offset": 0.05,
        "set_robot_rest_offset": 0.001,
    }},
}}
"""


def _group(name: str) -> str:
    return f"""                {{
                    "objs": ["{name}"],
                    "mode": "local",
                    "yaw_range_degrees": [0.0, 0.0],
                    "x_offset_range": [-0.01, 0.01],
                    "y_offset_range": [-0.01, 0.01],
                }}"""


def main() -> None:
    build(DEFAULT_PACKAGE, DEFAULT_PACKAGE / "vr")


if __name__ == "__main__":
    main()

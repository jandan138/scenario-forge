"""Simulator-neutral USD fixture authoring for glass material A/B evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


REAGENT_BOTTLE_CLEAR_OMNIGLASS_INPUTS: dict[str, dict[str, Any]] = {
    "glass_color": {"type": "color3f", "value": [0.99, 0.998, 1.0]},
    "reflection_color": {"type": "color3f", "value": [1.0, 1.0, 1.0]},
    "frosting_roughness": {"type": "float", "value": 0.035},
    "glass_ior": {"type": "float", "value": 1.47},
    "thin_walled": {"type": "bool", "value": False},
    "depth": {"type": "float", "value": 0.002},
}


def build_evidence_scene(
    *,
    output_path: Path,
    room_usd: Path,
    table_usd: Path,
    asset_usd: Path,
    asset_prim_path: str,
    object_height_m: float,
    mdl_inputs: Mapping[str, Mapping[str, Any]] | None = None,
    mdl_material_name: str = "OmniGlassRenderChangeV1",
) -> Path:
    """Write one fixed-layout evidence scene; rendering stays in an adapter process."""

    for path in (room_usd, table_usd, asset_usd):
        if not Path(path).is_file():
            raise FileNotFoundError(path)
    if (
        not asset_prim_path.startswith("/")
        or asset_prim_path == "/"
        or "//" in asset_prim_path
    ):
        raise ValueError("asset_prim_path must be an absolute USD prim path")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    overlay = ""
    if mdl_inputs:
        overlay = "\n" + _omniglass_input_overlay(
            mdl_inputs, material_name=mdl_material_name
        )
    scene = f'''#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{{
    def Xform "_scene"
    {{
        def Xform "room" (
            prepend references = @{Path(room_usd).resolve()}@</World>
        )
        {{
            double3 xformOp:translate = (0.002882434, -0.0069055, 0)
            uniform token[] xformOpOrder = ["xformOp:translate"]
            over "table" (active = false) {{}}
            over "PhysicsScene" (active = false) {{}}
        }}

        def Xform "table" (
            prepend references = @{Path(table_usd).resolve()}@</World>
        )
        {{
            double3 xformOp:translate = (0, 0, 0)
            uniform token[] xformOpOrder = ["xformOp:translate"]
        }}

        def Xform "obj_glass" (
            prepend references = @{Path(asset_usd).resolve()}@<{asset_prim_path}>
        )
        {{
            double3 xformOp:translate = (0, -0.17, {float(object_height_m):.9g})
            uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate"]{overlay}
        }}
    }}

    def DomeLight "EvidenceDome"
    {{
        float inputs:intensity = 620
        color3f inputs:color = (0.86, 0.92, 1.0)
    }}

    def DistantLight "EvidenceKey"
    {{
        float inputs:angle = 2.5
        color3f inputs:color = (1.0, 0.94, 0.84)
        float inputs:intensity = 1100
        double3 xformOp:rotateXYZ = (-42, 18, -28)
        uniform token[] xformOpOrder = ["xformOp:rotateXYZ"]
    }}
}}
'''
    output_path.write_text(scene, encoding="utf-8")
    return output_path


def _omniglass_input_overlay(
    mdl_inputs: Mapping[str, Mapping[str, Any]],
    *,
    material_name: str,
) -> str:
    lines = [
        '            over "__aan_visual_materials"',
        "            {",
        f'                over "{material_name}"',
        "                {",
        '                    over "Shader"',
        "                    {",
    ]
    for name, spec in mdl_inputs.items():
        lines.append(f"                        {_format_mdl_input(name, spec)}")
    lines.extend(
        [
            "                    }",
            "                }",
            "            }",
        ]
    )
    return "\n".join(lines)


def _format_mdl_input(name: str, spec: Mapping[str, Any]) -> str:
    input_type = spec["type"]
    value = spec["value"]
    if input_type == "bool":
        rendered = "true" if value else "false"
    elif input_type == "color3f":
        rendered = "(" + ", ".join(repr(component) for component in value) + ")"
    else:
        rendered = repr(value)
    return f"{input_type} inputs:{name} = {rendered}"

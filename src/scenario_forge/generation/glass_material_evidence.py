"""Simulator-neutral USD fixture authoring for glass material A/B evidence."""

from __future__ import annotations

from pathlib import Path


def build_evidence_scene(
    *,
    output_path: Path,
    room_usd: Path,
    table_usd: Path,
    asset_usd: Path,
    asset_prim_path: str,
    object_height_m: float,
) -> Path:
    """Write one fixed-layout evidence scene; rendering stays in an adapter process."""

    for path in (room_usd, table_usd, asset_usd):
        if not Path(path).is_file():
            raise FileNotFoundError(path)
    if not asset_prim_path.startswith("/World/"):
        raise ValueError("asset_prim_path must be under /World")
    output_path.parent.mkdir(parents=True, exist_ok=True)
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
            uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate"]
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

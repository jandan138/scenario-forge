#!/usr/bin/env python3
"""Author an evidence-only Task 02 r8 layer; it never advances physics."""

from __future__ import annotations

import argparse
from pathlib import Path


def preview_usda(scene: str, robot: str, table: str) -> str:
    return f'''#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
    subLayers = [@{scene}@]
)

over "World"
{{
    over "_scene"
    {{
        over "fluid_runtime" (active = false) {{}}
        def Xform "obj_table" (
            prepend references = @{table}@</Asset>
        )
        {{
            double3 xformOp:translate = (0, 0, 0)
            uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate"]
        }}
        def Xform "lift2" (
            prepend references = @{robot}@</Root/lift2>
        )
        {{
            double3 xformOp:translate = (0, -1.02, 0.31)
            quatd xformOp:orient = (0.7071067812, 0, 0, 0.7071067812)
            uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
        }}
    }}

    def Camera "Task02R8PreviewCamera"
    {{
        float focalLength = 34
        float horizontalAperture = 36
        double3 xformOp:translate = (2.45, -2.70, 2.35)
        double3 xformOp:rotateXYZ = (65.0, 0.0, 42.0)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
    }}

    def DomeLight "Task02R8PreviewLight"
    {{
        float intensity = 650
    }}
}}
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--robot", type=Path, required=True)
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        preview_usda(
            str(args.scene.resolve()),
            str(args.robot.resolve()),
            str(args.table.resolve()),
        ),
        encoding="utf-8",
    )
    print(args.out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

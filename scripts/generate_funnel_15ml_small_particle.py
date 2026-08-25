#!/usr/bin/env python3
"""Emit the 15 mL small-particle funnel mesh.

Prefers the AI3DGen Blender generator when ``bpy`` is importable. Otherwise
writes the same lathe (no bevel) as a USDA using pxr. Collision/SDF stays in
ConvertAsset.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

MM_TO_M = 0.001
REPO = Path(__file__).resolve().parents[1]


def _ring(radius: float, z_value: float, segments: int) -> list[tuple[float, float, float]]:
    return [
        (
            radius * math.cos(2.0 * math.pi * index / segments),
            radius * math.sin(2.0 * math.pi * index / segments),
            z_value,
        )
        for index in range(segments)
    ]


def _connect_outer(
    faces: list[list[int]], upper: int, lower: int, segments: int
) -> None:
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.append([upper + index, lower + index, lower + nxt, upper + nxt])


def _connect_inner(
    faces: list[list[int]], upper: int, lower: int, segments: int
) -> None:
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.append([upper + index, upper + nxt, lower + nxt, lower + index])


def lathe_funnel(geometry: dict) -> tuple[list[tuple[float, float, float]], list[list[int]]]:
    segments = int(geometry["radial_segments"])
    top_radius = geometry["top_diameter_mm"] * 0.5 * MM_TO_M
    neck_radius = geometry["neck_diameter_mm"] * 0.5 * MM_TO_M
    wall = geometry["wall_thickness_mm"] * MM_TO_M
    inner_top = top_radius - wall
    inner_neck = neck_radius - wall
    stem = geometry["stem_length_mm"] * MM_TO_M
    top_z = (geometry["stem_length_mm"] + geometry["frustum_height_mm"]) * MM_TO_M
    ring_data = (
        (top_radius, top_z),
        (neck_radius, stem),
        (neck_radius, 0.0),
        (inner_top, top_z),
        (inner_neck, stem),
        (inner_neck, 0.0),
    )
    vertices: list[tuple[float, float, float]] = []
    starts: list[int] = []
    for radius, z_value in ring_data:
        starts.append(len(vertices))
        vertices.extend(_ring(radius, z_value, segments))
    outer_top, outer_neck, outer_bottom, inner_top_i, inner_neck_i, inner_bottom = starts
    faces: list[list[int]] = []
    _connect_outer(faces, outer_top, outer_neck, segments)
    _connect_outer(faces, outer_neck, outer_bottom, segments)
    _connect_inner(faces, inner_top_i, inner_neck_i, segments)
    _connect_inner(faces, inner_neck_i, inner_bottom, segments)
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.append(
            [outer_top + index, outer_top + nxt, inner_top_i + nxt, inner_top_i + index]
        )
        faces.append(
            [
                outer_bottom + index,
                inner_bottom + index,
                inner_bottom + nxt,
                outer_bottom + nxt,
            ]
        )
    return vertices, faces


def write_usda(path: Path, vertices: list[tuple[float, float, float]], faces: list[list[int]]) -> None:
    from pxr import Usd, UsdGeom, Gf, Vt, Sdf

    path.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/World/Funnel")
    stage.SetDefaultPrim(root.GetPrim())
    mesh = UsdGeom.Mesh.Define(stage, "/World/Funnel/Visual")
    mesh.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*p) for p in vertices]))
    mesh.CreateFaceVertexCountsAttr([len(face) for face in faces])
    mesh.CreateFaceVertexIndicesAttr([i for face in faces for i in face])
    mesh.CreateSubdivisionSchemeAttr("none")
    mesh.GetPrim().CreateAttribute("userProperties:shape", Sdf.ValueTypeNames.String).Set(
        "hollow_frustum_plus_hollow_cylinder"
    )
    stage.GetRootLayer().Save()


def main() -> int:
    sys.path.insert(0, str(REPO / "src"))
    from scenario_forge.generation.funnel_15ml_small_particle import (
        load_funnel_15ml_small_particle_contract,
        to_ai3dgen_funnel_config,
        check_funnel_15ml_small_particle_contract,
    )

    contract_path = REPO / "configs/prototypes/funnel_15ml_small_particle_v1.yaml"
    contract = load_funnel_15ml_small_particle_contract(contract_path)
    checked = check_funnel_15ml_small_particle_contract(contract)
    config = to_ai3dgen_funnel_config(contract)
    out_dir = REPO / "outputs/funnel_15ml_small_particle_20260824"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ai3dgen.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    (out_dir / "contract_check.json").write_text(json.dumps(checked, indent=2) + "\n", encoding="utf-8")

    try:
        sys.path.insert(0, "/tmp/ai3dgen_share/ai3dgen")
        from glass_funnel_generator import load_spec, generate_funnel_artifacts

        generate_funnel_artifacts(
            load_spec(REPO / "configs/prototypes/funnel_15ml_small_particle_ai3dgen.json"),
            out_dir / "ai3dgen",
            render_images=False,
            save_blend=False,
        )
        print("generated with AI3DGen bpy", out_dir / "ai3dgen")
        return 0
    except Exception as exc:
        print("bpy generator unavailable:", exc)

    vertices, faces = lathe_funnel(config["geometry"])
    usd_path = out_dir / "funnel_15ml_small_particle.usda"
    write_usda(usd_path, vertices, faces)
    print("wrote lathe USDA", usd_path)
    print("throat_inner_diameter_mm", checked["throat_inner_diameter_mm"])
    print("radial_insertion_clearance_after_collision_mm", checked["radial_insertion_clearance_after_collision_mm"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

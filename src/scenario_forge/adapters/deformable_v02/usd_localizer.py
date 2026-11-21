"""Self-contained USD, URDF, MJCF, and M1 deformable asset localization helpers."""

from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path
from typing import Any


_BROKEN_PATH_MARKERS = ("@source_bundle/", "/cpfs/", "AppData\\Local\\Temp", "AppData/Local/Temp")

_DEFAULT_PANDA_URDF_CANDIDATES = (
    Path(
        r"C:\Users\Administrator\Miniconda3\envs\sim-genesis-py312"
        r"\Lib\site-packages\genesis\assets\urdf\panda_bullet"
    ),
    Path("/home/user/miniconda3/envs/sim-genesis-py312/lib/python3.12/site-packages/genesis/assets/urdf/panda_bullet"),
)


def find_local_panda_urdf_dir() -> Path:
    """Locate the local Franka Panda URDF directory."""
    for candidate in _DEFAULT_PANDA_URDF_CANDIDATES:
        if (candidate / "panda.urdf").is_file():
            return candidate
    raise FileNotFoundError(
        "Could not locate Franka Panda URDF directory in standard conda locations."
    )


def _format_vec3_list(points: list[tuple[float, float, float]]) -> str:
    return ", ".join(f"({x:.6f}, {y:.6f}, {z:.6f})" for x, y, z in points)


def _format_int3_list(tris: list[tuple[int, int, int]]) -> str:
    return ", ".join(f"({a}, {b}, {c})" for a, b, c in tris)


def _format_int4_list(tets: list[tuple[int, int, int, int]]) -> str:
    return ", ".join(f"({a}, {b}, {c}, {d})" for a, b, c, d in tets)


def _parse_usda_point3f_array(text: str, attr_name: str) -> list[tuple[float, float, float]]:
    pattern = rf"{re.escape(attr_name)}\s*=\s*\[(.*?)\]"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return []
    body = match.group(1)
    triples = re.findall(
        r"\(\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*\)",
        body,
    )
    return [(float(a), float(b), float(c)) for a, b, c in triples]


def _parse_usda_tuple_int_array(text: str, attr_name: str, width: int) -> list[tuple[int, ...]]:
    pattern = rf"{re.escape(attr_name)}\s*=\s*\[(.*?)\]"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return []
    body = match.group(1)
    num_pat = r"\s*,\s*".join([r"([-+]?\d+)"] * width)
    matches = re.findall(rf"\(\s*{num_pat}\s*\)", body)
    return [tuple(int(v) for v in row) for row in matches]


def _parse_usda_flat_int_array(text: str, attr_name: str) -> list[int]:
    pattern = rf"{re.escape(attr_name)}\s*=\s*\[(.*?)\]"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return []
    return [int(x) for x in re.findall(r"[-+]?\d+", match.group(1))]


def _parse_obj_mesh(obj_path: Path) -> tuple[list[tuple[float, float, float]], list[int], list[int]]:
    """Parse vertices and fan-triangulated face indices from an OBJ file."""
    vertices: list[tuple[float, float, float]] = []
    face_counts: list[int] = []
    face_indices: list[int] = []
    for raw_line in obj_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if parts[0] == "v" and len(parts) >= 4:
            vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif parts[0] == "f" and len(parts) >= 4:
            idxs = []
            for tok in parts[1:]:
                v_str = tok.split("/")[0]
                v_idx = int(v_str)
                idxs.append(v_idx - 1 if v_idx > 0 else len(vertices) + v_idx)
            for k in range(1, len(idxs) - 1):
                face_counts.append(3)
                face_indices.extend((idxs[0], idxs[k], idxs[k + 1]))
    return vertices, face_counts, face_indices


def _rpy_to_wxyz(roll: float, pitch: float, yaw: float) -> tuple[float, float, float, float]:
    cr, sr = math.cos(roll * 0.5), math.sin(roll * 0.5)
    cp, sp = math.cos(pitch * 0.5), math.sin(pitch * 0.5)
    cy, sy = math.cos(yaw * 0.5), math.sin(yaw * 0.5)
    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy
    return (w, x, y, z)


def _write_obj_file(
    path: Path,
    vertices: list[tuple[float, float, float]],
    triangles: list[tuple[int, int, int]],
) -> None:
    lines = ["# Self-contained mesh exported by scenario_forge.adapters.deformable_v02"]
    for x, y, z in vertices:
        lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")
    for a, b, c in triangles:
        lines.append(f"f {a + 1} {b + 1} {c + 1}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _wrap_usd_asset(asset_dir: Path, scoped_source_content: str, overlay_paths: tuple[str, ...] = ()) -> Path:
    deps_usd = asset_dir / "deps" / "usd" / "scoped_source.usda"
    deps_usd.parent.mkdir(parents=True, exist_ok=True)
    deps_usd.write_text(scoped_source_content, encoding="utf-8")

    layers = [f"@{p}@" for p in overlay_paths] + ["@deps/usd/scoped_source.usda@"]
    sublayers_block = ",\n        ".join(layers)
    asset_usd = asset_dir / "asset.usd"
    asset_usd.write_text(
        f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    kilogramsPerUnit = 1
    upAxis = "Z"
    timeCodesPerSecond = 24
    framesPerSecond = 24
    startTimeCode = 0
    endTimeCode = 0
    subLayers = [
        {sublayers_block},
    ]
)
""",
        encoding="utf-8",
    )
    return asset_usd


def localize_usd_asset_closures(
    source_assets_root: Path,
    dest_assets_root: Path,
    asset_ids: tuple[str, ...],
) -> list[str]:
    """Copy existing local USD asset closures and check for broken external links."""
    broken: list[str] = []
    dest_assets_root.mkdir(parents=True, exist_ok=True)
    for asset_id in asset_ids:
        src = source_assets_root / asset_id
        if not src.is_dir():
            raise FileNotFoundError(f"Source USD closure missing: {src}")
        dst = dest_assets_root / asset_id
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        for usd_file in dst.rglob("*.usd*"):
            if usd_file.suffix.lower() not in {".usd", ".usda"}:
                continue
            text = usd_file.read_text(encoding="utf-8", errors="ignore")
            for marker in _BROKEN_PATH_MARKERS:
                if marker in text:
                    broken.append(f"{usd_file}: contains {marker}")
    return broken


def _usd_box_mesh(
    name: str,
    hx: float,
    hy: float,
    hz: float,
    center: tuple[float, float, float],
    material_rel: str,
    *,
    rigid: bool = False,
    collision: bool = True,
    mass: float | None = None,
    static_friction: float = 0.65,
    dynamic_friction: float = 0.55,
) -> str:
    cx, cy, cz = center
    pts = [
        (cx - hx, cy - hy, cz - hz),
        (cx + hx, cy - hy, cz - hz),
        (cx + hx, cy + hy, cz - hz),
        (cx - hx, cy + hy, cz - hz),
        (cx - hx, cy - hy, cz + hz),
        (cx + hx, cy - hy, cz + hz),
        (cx + hx, cy + hy, cz + hz),
        (cx - hx, cy + hy, cz + hz),
    ]
    tris = [
        (0, 2, 1), (0, 3, 2),
        (4, 5, 6), (4, 6, 7),
        (0, 1, 5), (0, 5, 4),
        (1, 2, 6), (1, 6, 5),
        (2, 3, 7), (2, 7, 6),
        (3, 0, 4), (3, 4, 7),
    ]
    counts = ", ".join(["3"] * len(tris))
    indices = ", ".join(str(i) for t in tris for i in t)
    schemas = ['"MaterialBindingAPI"']
    if collision:
        schemas.extend(['"PhysicsCollisionAPI"', '"PhysxCollisionAPI"'])
    if rigid:
        schemas.append('"PhysicsRigidBodyAPI"')
    if mass is not None:
        schemas.append('"PhysicsMassAPI"')
    api_str = ", ".join(schemas)
    mass_line = f"\n            float physics:mass = {mass:.4f}" if mass is not None else ""
    return f"""        def Mesh "{name}" (
            apiSchemas = [{api_str}]
        )
        {{
            uniform bool doubleSided = 1
            int[] faceVertexCounts = [{counts}]
            int[] faceVertexIndices = [{indices}]
            rel material:binding = <{material_rel}>
            point3f[] points = [{_format_vec3_list(pts)}]
            float physxCollision:contactOffset = 0.002
            float physxCollision:restOffset = 0.0005{mass_line}
            float physics:staticFriction = {static_friction:.3f}
            float physics:dynamicFriction = {dynamic_friction:.3f}
        }}"""


def _usd_cylinder_mesh(
    name: str,
    radius_bottom: float,
    radius_top: float,
    z0: float,
    z1: float,
    segments: int,
    material_rel: str,
    *,
    collision: bool = True,
) -> str:
    pts: list[tuple[float, float, float]] = [(0.0, 0.0, z0), (0.0, 0.0, z1)]
    for i in range(segments):
        ang = 2.0 * math.pi * i / segments
        ca, sa = math.cos(ang), math.sin(ang)
        pts.append((radius_bottom * ca, radius_bottom * sa, z0))
        pts.append((radius_top * ca, radius_top * sa, z1))
    tris: list[tuple[int, int, int]] = []
    for i in range(segments):
        j = (i + 1) % segments
        b0, t0 = 2 + 2 * i, 3 + 2 * i
        b1, t1 = 2 + 2 * j, 3 + 2 * j
        tris.append((0, b1, b0))
        tris.append((1, t0, t1))
        tris.append((b0, b1, t1))
        tris.append((b0, t1, t0))
    counts = ", ".join(["3"] * len(tris))
    indices = ", ".join(str(i) for t in tris for i in t)
    schemas = ['"MaterialBindingAPI"']
    if collision:
        schemas.extend(['"PhysicsCollisionAPI"', '"PhysxCollisionAPI"'])
    api_str = ", ".join(schemas)
    return f"""        def Mesh "{name}" (
            apiSchemas = [{api_str}]
        )
        {{
            uniform bool doubleSided = 1
            int[] faceVertexCounts = [{counts}]
            int[] faceVertexIndices = [{indices}]
            rel material:binding = <{material_rel}>
            point3f[] points = [{_format_vec3_list(pts)}]
            float physxCollision:contactOffset = 0.002
            float physxCollision:restOffset = 0.0005
        }}"""


def create_robot_pedestal_usd(dest_dir: Path) -> Path:
    """Create a grounded dark brushed-steel robot pedestal (height 0.755m)."""
    mesh_str = _usd_box_mesh(
        "PedestalColumn",
        0.13,
        0.13,
        0.3775,
        (0.0, 0.0, 0.3775),
        "/World/robot_pedestal/Materials/BrushedSteel",
        collision=True,
    )
    cap_str = _usd_box_mesh(
        "MountingFlange",
        0.145,
        0.145,
        0.008,
        (0.0, 0.0, 0.747),
        "/World/robot_pedestal/Materials/AnodizedAluminum",
        collision=True,
    )
    usda = f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{{
    def Xform "robot_pedestal" (
        kind = "component"
    )
    {{
        def Scope "Materials"
        {{
            def Material "BrushedSteel"
            {{
                token outputs:surface.connect = </World/robot_pedestal/Materials/BrushedSteel/Shader.outputs:surface>
                def Shader "Shader"
                {{
                    uniform token info:id = "UsdPreviewSurface"
                    color3f inputs:diffuseColor = (0.16, 0.17, 0.19)
                    float inputs:metallic = 0.85
                    float inputs:roughness = 0.32
                    token outputs:surface
                }}
            }}
            def Material "AnodizedAluminum"
            {{
                token outputs:surface.connect = </World/robot_pedestal/Materials/AnodizedAluminum/Shader.outputs:surface>
                def Shader "Shader"
                {{
                    uniform token info:id = "UsdPreviewSurface"
                    color3f inputs:diffuseColor = (0.58, 0.60, 0.63)
                    float inputs:metallic = 0.90
                    float inputs:roughness = 0.25
                    token outputs:surface
                }}
            }}
        }}
{mesh_str}
{cap_str}
    }}
}}
"""
    return _wrap_usd_asset(dest_dir, usda)


def create_pastry_box_hinged_usd(dest_dir: Path) -> Path:
    """Create articulated walnut & clear-acrylic pastry display box with revolute lid."""
    base_floor = _usd_box_mesh(
        "TrayBase", 0.068, 0.068, 0.005, (0.0, 0.0, 0.005),
        "/World/pastry_box_hinged/Materials/WalnutWood", collision=True
    )
    back_wall = _usd_box_mesh(
        "BackWall", 0.068, 0.004, 0.020, (0.0, 0.064, 0.022),
        "/World/pastry_box_hinged/Materials/WalnutWood", collision=True
    )
    left_wall = _usd_box_mesh(
        "LeftWall", 0.004, 0.060, 0.007, (-0.064, 0.0, 0.017),
        "/World/pastry_box_hinged/Materials/WalnutWood", collision=True
    )
    right_wall = _usd_box_mesh(
        "RightWall", 0.004, 0.060, 0.007, (0.064, 0.0, 0.017),
        "/World/pastry_box_hinged/Materials/WalnutWood", collision=True
    )
    lid_plate = _usd_box_mesh(
        "LidPlate", 0.066, 0.064, 0.003, (0.0, -0.064, 0.0),
        "/World/pastry_box_hinged/Materials/AcrylicAmber", collision=True, rigid=False
    )
    lid_tab = _usd_box_mesh(
        "LidHandleTab", 0.022, 0.010, 0.004, (0.0, -0.130, 0.004),
        "/World/pastry_box_hinged/Materials/BrassAccent", collision=True, rigid=False
    )
    usda = f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{{
    def Xform "pastry_box_hinged" (
        apiSchemas = ["PhysicsArticulationRootAPI", "PhysxArticulationAPI"]
        kind = "component"
    )
    {{
        def Scope "Materials"
        {{
            def Material "WalnutWood"
            {{
                token outputs:surface.connect = </World/pastry_box_hinged/Materials/WalnutWood/Shader.outputs:surface>
                def Shader "Shader"
                {{
                    uniform token info:id = "UsdPreviewSurface"
                    color3f inputs:diffuseColor = (0.28, 0.17, 0.10)
                    float inputs:metallic = 0.05
                    float inputs:roughness = 0.42
                    token outputs:surface
                }}
            }}
            def Material "AcrylicAmber"
            {{
                token outputs:surface.connect = </World/pastry_box_hinged/Materials/AcrylicAmber/Shader.outputs:surface>
                def Shader "Shader"
                {{
                    uniform token info:id = "UsdPreviewSurface"
                    color3f inputs:diffuseColor = (0.86, 0.78, 0.65)
                    float inputs:opacity = 0.62
                    float inputs:roughness = 0.14
                    token outputs:surface
                }}
            }}
            def Material "BrassAccent"
            {{
                token outputs:surface.connect = </World/pastry_box_hinged/Materials/BrassAccent/Shader.outputs:surface>
                def Shader "Shader"
                {{
                    uniform token info:id = "UsdPreviewSurface"
                    color3f inputs:diffuseColor = (0.78, 0.60, 0.25)
                    float inputs:metallic = 0.90
                    float inputs:roughness = 0.20
                    token outputs:surface
                }}
            }}
        }}

        def Xform "BaseLink" (
            apiSchemas = ["PhysicsRigidBodyAPI", "PhysicsMassAPI"]
        )
        {{
            bool physics:kinematicEnabled = 1
            float physics:mass = 0.45
{base_floor}
{back_wall}
{left_wall}
{right_wall}
        }}

        def Xform "LidLink" (
            apiSchemas = ["PhysicsRigidBodyAPI", "PhysicsMassAPI"]
        )
        {{
            double3 xformOp:translate = (0, 0.064, 0.044)
            uniform token[] xformOpOrder = ["xformOp:translate"]
            float physics:mass = 0.08
{lid_plate}
{lid_tab}
        }}

        def PhysicsRevoluteJoint "lid_hinge"
        {{
            uniform token physics:axis = "X"
            float physics:lowerLimit = 0.0
            float physics:upperLimit = 95.0
            rel physics:body0 = </World/pastry_box_hinged/BaseLink>
            rel physics:body1 = </World/pastry_box_hinged/LidLink>
            point3f physics:localPos0 = (0, 0.064, 0.044)
            point3f physics:localPos1 = (0, 0, 0)
            quatf physics:localRot0 = (1, 0, 0, 0)
            quatf physics:localRot1 = (1, 0, 0, 0)
        }}
    }}
}}
"""
    return _wrap_usd_asset(dest_dir, usda)


def create_serving_plate_usd(dest_dir: Path) -> Path:
    """Create a glazed ceramic dessert serving plate USD asset."""
    plate_inner = _usd_cylinder_mesh(
        "PlateWell", 0.072, 0.092, 0.000, 0.008, 32,
        "/World/serving_plate/Materials/CeramicGlaze", collision=True
    )
    plate_rim = _usd_cylinder_mesh(
        "PlateRim", 0.090, 0.098, 0.006, 0.013, 32,
        "/World/serving_plate/Materials/PorcelainTrim", collision=True
    )
    usda = f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{{
    def Xform "serving_plate" (
        kind = "component"
    )
    {{
        def Scope "Materials"
        {{
            def Material "CeramicGlaze"
            {{
                token outputs:surface.connect = </World/serving_plate/Materials/CeramicGlaze/Shader.outputs:surface>
                def Shader "Shader"
                {{
                    uniform token info:id = "UsdPreviewSurface"
                    color3f inputs:diffuseColor = (0.94, 0.93, 0.90)
                    float inputs:metallic = 0.0
                    float inputs:roughness = 0.18
                    token outputs:surface
                }}
            }}
            def Material "PorcelainTrim"
            {{
                token outputs:surface.connect = </World/serving_plate/Materials/PorcelainTrim/Shader.outputs:surface>
                def Shader "Shader"
                {{
                    uniform token info:id = "UsdPreviewSurface"
                    color3f inputs:diffuseColor = (0.76, 0.64, 0.42)
                    float inputs:metallic = 0.45
                    float inputs:roughness = 0.25
                    token outputs:surface
                }}
            }}
        }}
{plate_inner}
{plate_rim}
    }}
}}
"""
    return _wrap_usd_asset(dest_dir, usda)


def create_wipe_zone_mat_usd(dest_dir: Path) -> Path:
    """Create a thin desk blotter mat with 3 tabletop wipe target zones."""
    mat = _usd_box_mesh(
        "BlotterPad", 0.24, 0.16, 0.001, (0.0, 0.0, 0.001),
        "/World/wipe_zone_mat/Materials/SlateBlotter", collision=True
    )
    m1 = _usd_cylinder_mesh(
        "WipeTarget1", 0.022, 0.022, 0.002, 0.0025, 24,
        "/World/wipe_zone_mat/Materials/TargetRing", collision=False
    )
    m2 = _usd_cylinder_mesh(
        "WipeTarget2", 0.022, 0.022, 0.002, 0.0025, 24,
        "/World/wipe_zone_mat/Materials/TargetRing", collision=False
    )
    m3 = _usd_cylinder_mesh(
        "WipeTarget3", 0.022, 0.022, 0.002, 0.0025, 24,
        "/World/wipe_zone_mat/Materials/TargetRing", collision=False
    )
    usda = f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{{
    def Xform "wipe_zone_mat" (
        kind = "component"
    )
    {{
        def Scope "Materials"
        {{
            def Material "SlateBlotter"
            {{
                token outputs:surface.connect = </World/wipe_zone_mat/Materials/SlateBlotter/Shader.outputs:surface>
                def Shader "Shader"
                {{
                    uniform token info:id = "UsdPreviewSurface"
                    color3f inputs:diffuseColor = (0.20, 0.23, 0.27)
                    float inputs:roughness = 0.72
                    token outputs:surface
                }}
            }}
            def Material "TargetRing"
            {{
                token outputs:surface.connect = </World/wipe_zone_mat/Materials/TargetRing/Shader.outputs:surface>
                def Shader "Shader"
                {{
                    uniform token info:id = "UsdPreviewSurface"
                    color3f inputs:diffuseColor = (0.22, 0.56, 0.76)
                    float inputs:roughness = 0.40
                    token outputs:surface
                }}
            }}
        }}
{mat}
        def Xform "TargetMarker1"
        {{
            double3 xformOp:translate = (-0.09, 0.02, 0.0)
            uniform token[] xformOpOrder = ["xformOp:translate"]
{m1}
        }}
        def Xform "TargetMarker2"
        {{
            double3 xformOp:translate = (0.00, 0.05, 0.0)
            uniform token[] xformOpOrder = ["xformOp:translate"]
{m2}
        }}
        def Xform "TargetMarker3"
        {{
            double3 xformOp:translate = (0.09, 0.02, 0.0)
            uniform token[] xformOpOrder = ["xformOp:translate"]
{m3}
        }}
    }}
}}
"""
    return _wrap_usd_asset(dest_dir, usda)


def create_cloth_caddy_tray_usd(dest_dir: Path) -> Path:
    """Create a birch & slate office caddy tray for parking the folded wiping cloth."""
    base = _usd_box_mesh(
        "CaddyBase", 0.095, 0.095, 0.004, (0.0, 0.0, 0.004),
        "/World/cloth_caddy_tray/Materials/NordicBirch", collision=True
    )
    lip_back = _usd_box_mesh(
        "LipBack", 0.095, 0.004, 0.011, (0.0, 0.091, 0.015),
        "/World/cloth_caddy_tray/Materials/NordicBirch", collision=True
    )
    lip_left = _usd_box_mesh(
        "LipLeft", 0.004, 0.091, 0.011, (-0.091, 0.0, 0.015),
        "/World/cloth_caddy_tray/Materials/NordicBirch", collision=True
    )
    lip_right = _usd_box_mesh(
        "LipRight", 0.004, 0.091, 0.011, (0.091, 0.0, 0.015),
        "/World/cloth_caddy_tray/Materials/NordicBirch", collision=True
    )
    lip_front = _usd_box_mesh(
        "LipFront", 0.095, 0.004, 0.006, (0.0, -0.091, 0.010),
        "/World/cloth_caddy_tray/Materials/SlateTrim", collision=True
    )
    usda = f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{{
    def Xform "cloth_caddy_tray" (
        kind = "component"
    )
    {{
        def Scope "Materials"
        {{
            def Material "NordicBirch"
            {{
                token outputs:surface.connect = </World/cloth_caddy_tray/Materials/NordicBirch/Shader.outputs:surface>
                def Shader "Shader"
                {{
                    uniform token info:id = "UsdPreviewSurface"
                    color3f inputs:diffuseColor = (0.76, 0.67, 0.54)
                    float inputs:roughness = 0.50
                    token outputs:surface
                }}
            }}
            def Material "SlateTrim"
            {{
                token outputs:surface.connect = </World/cloth_caddy_tray/Materials/SlateTrim/Shader.outputs:surface>
                def Shader "Shader"
                {{
                    uniform token info:id = "UsdPreviewSurface"
                    color3f inputs:diffuseColor = (0.28, 0.31, 0.35)
                    float inputs:roughness = 0.38
                    token outputs:surface
                }}
            }}
        }}
{base}
{lip_back}
{lip_left}
{lip_right}
{lip_front}
    }}
}}
"""
    return _wrap_usd_asset(dest_dir, usda)


def _write_panda_usd(dest_dir: Path, meshes_dir: Path) -> Path:
    """Build a visual + kinematic OpenUSD representation of Franka Panda from OBJ meshes."""
    links_spec = [
        ("panda_link0", meshes_dir / "collision" / "link0.obj", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), "PandaWhite"),
        ("panda_link1", meshes_dir / "visual" / "link1.obj", (0.0, 0.0, 0.333), (0.0, 0.0, 0.0), "PandaWhite"),
        ("panda_link2", meshes_dir / "visual" / "link2.obj", (0.0, 0.0, 0.0), (-math.pi / 2, 0.0, 0.0), "PandaCharcoal"),
        ("panda_link3", meshes_dir / "visual" / "link3.obj", (0.0, -0.316, 0.0), (math.pi / 2, 0.0, 0.0), "PandaWhite"),
        ("panda_link4", meshes_dir / "visual" / "link4.obj", (0.0825, 0.0, 0.0), (math.pi / 2, 0.0, 0.0), "PandaCharcoal"),
        ("panda_link5", meshes_dir / "visual" / "link5.obj", (-0.0825, 0.384, 0.0), (-math.pi / 2, 0.0, 0.0), "PandaWhite"),
        ("panda_link6", meshes_dir / "visual" / "link6.obj", (0.0, 0.0, 0.0), (math.pi / 2, 0.0, 0.0), "PandaCharcoal"),
        ("panda_link7", meshes_dir / "collision" / "link7.obj", (0.088, 0.0, 0.0), (math.pi / 2, 0.0, 0.0), "PandaWhite"),
    ]
    indent = "        "
    blocks: list[str] = []
    closing: list[str] = []

    for idx, (link_name, obj_file, xyz, rpy, mat_name) in enumerate(links_spec):
        verts, fcounts, findices = _parse_obj_mesh(obj_file)
        qw, qx, qy, qz = _rpy_to_wxyz(*rpy)
        cur_indent = indent + ("    " * idx)
        counts_str = ", ".join(str(c) for c in fcounts)
        idx_str = ", ".join(str(i) for i in findices)
        blocks.append(
            f"""{cur_indent}def Xform "{link_name}"
{cur_indent}{{
{cur_indent}    double3 xformOp:translate = ({xyz[0]:.6f}, {xyz[1]:.6f}, {xyz[2]:.6f})
{cur_indent}    quatd xformOp:orient = ({qw:.6f}, {qx:.6f}, {qy:.6f}, {qz:.6f})
{cur_indent}    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient"]
{cur_indent}    def Mesh "{link_name}_mesh" (
{cur_indent}        apiSchemas = ["MaterialBindingAPI"]
{cur_indent}    )
{cur_indent}    {{
{cur_indent}        int[] faceVertexCounts = [{counts_str}]
{cur_indent}        int[] faceVertexIndices = [{idx_str}]
{cur_indent}        rel material:binding = </World/franka_panda/Materials/{mat_name}>
{cur_indent}        point3f[] points = [{_format_vec3_list(verts)}]
{cur_indent}    }}"""
        )
        closing.append(f"{cur_indent}}}")

    hand_indent = indent + ("    " * len(links_spec))
    hand_verts, hand_counts, hand_indices = _parse_obj_mesh(meshes_dir / "visual" / "hand.obj")
    finger_verts, finger_counts, finger_indices = _parse_obj_mesh(meshes_dir / "visual" / "finger.obj")
    qw_h, qx_h, qy_h, qz_h = _rpy_to_wxyz(0.0, 0.0, -math.pi / 4)
    hand_block = f"""{hand_indent}def Xform "panda_hand"
{hand_indent}{{
{hand_indent}    double3 xformOp:translate = (0.0, 0.0, 0.107)
{hand_indent}    quatd xformOp:orient = ({qw_h:.6f}, {qx_h:.6f}, {qy_h:.6f}, {qz_h:.6f})
{hand_indent}    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient"]
{hand_indent}    def Mesh "panda_hand_mesh" (apiSchemas = ["MaterialBindingAPI"])
{hand_indent}    {{
{hand_indent}        int[] faceVertexCounts = [{", ".join(str(c) for c in hand_counts)}]
{hand_indent}        int[] faceVertexIndices = [{", ".join(str(i) for i in hand_indices)}]
{hand_indent}        rel material:binding = </World/franka_panda/Materials/PandaCharcoal>
{hand_indent}        point3f[] points = [{_format_vec3_list(hand_verts)}]
{hand_indent}    }}
{hand_indent}    def Xform "panda_leftfinger"
{hand_indent}    {{
{hand_indent}        double3 xformOp:translate = (0.0, 0.04, 0.0584)
{hand_indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{hand_indent}        def Mesh "leftfinger_mesh" (apiSchemas = ["MaterialBindingAPI"])
{hand_indent}        {{
{hand_indent}            int[] faceVertexCounts = [{", ".join(str(c) for c in finger_counts)}]
{hand_indent}            int[] faceVertexIndices = [{", ".join(str(i) for i in finger_indices)}]
{hand_indent}            rel material:binding = </World/franka_panda/Materials/PandaMetal>
{hand_indent}            point3f[] points = [{_format_vec3_list(finger_verts)}]
{hand_indent}        }}
{hand_indent}    }}
{hand_indent}    def Xform "panda_rightfinger"
{hand_indent}    {{
{hand_indent}        double3 xformOp:translate = (0.0, -0.04, 0.0584)
{hand_indent}        quatd xformOp:orient = (0.0, 0.0, 0.0, 1.0)
{hand_indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient"]
{hand_indent}        def Mesh "rightfinger_mesh" (apiSchemas = ["MaterialBindingAPI"])
{hand_indent}        {{
{hand_indent}            int[] faceVertexCounts = [{", ".join(str(c) for c in finger_counts)}]
{hand_indent}            int[] faceVertexIndices = [{", ".join(str(i) for i in finger_indices)}]
{hand_indent}            rel material:binding = </World/franka_panda/Materials/PandaMetal>
{hand_indent}            point3f[] points = [{_format_vec3_list(finger_verts)}]
{hand_indent}        }}
{hand_indent}    }}
{hand_indent}}}"""

    body = "\n".join(blocks) + "\n" + hand_block + "\n" + "\n".join(reversed(closing))
    usda = f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{{
    def Xform "franka_panda" (
        kind = "component"
    )
    {{
        def Scope "Materials"
        {{
            def Material "PandaWhite"
            {{
                token outputs:surface.connect = </World/franka_panda/Materials/PandaWhite/Shader.outputs:surface>
                def Shader "Shader"
                {{
                    uniform token info:id = "UsdPreviewSurface"
                    color3f inputs:diffuseColor = (0.92, 0.93, 0.95)
                    float inputs:metallic = 0.10
                    float inputs:roughness = 0.25
                    token outputs:surface
                }}
            }}
            def Material "PandaCharcoal"
            {{
                token outputs:surface.connect = </World/franka_panda/Materials/PandaCharcoal/Shader.outputs:surface>
                def Shader "Shader"
                {{
                    uniform token info:id = "UsdPreviewSurface"
                    color3f inputs:diffuseColor = (0.15, 0.16, 0.18)
                    float inputs:metallic = 0.35
                    float inputs:roughness = 0.35
                    token outputs:surface
                }}
            }}
            def Material "PandaMetal"
            {{
                token outputs:surface.connect = </World/franka_panda/Materials/PandaMetal/Shader.outputs:surface>
                def Shader "Shader"
                {{
                    uniform token info:id = "UsdPreviewSurface"
                    color3f inputs:diffuseColor = (0.68, 0.70, 0.74)
                    float inputs:metallic = 0.88
                    float inputs:roughness = 0.22
                    token outputs:surface
                }}
            }}
        }}
{body}
    }}
}}
"""
    return _wrap_usd_asset(dest_dir, usda)


def _write_panda_mjcf(xml_path: Path) -> None:
    """Emit a self-contained MuJoCo 4 MJCF model matching panda.urdf kinematics."""
    mjcf = """<mujoco model="franka_panda_tabletop">
  <compiler angle="radian" meshdir="meshes" autolimits="true"/>
  <option integrator="implicitfast"/>
  <asset>
    <mesh name="link0_m" file="collision/link0.obj"/>
    <mesh name="link1_m" file="visual/link1.obj"/>
    <mesh name="link2_m" file="visual/link2.obj"/>
    <mesh name="link3_m" file="visual/link3.obj"/>
    <mesh name="link4_m" file="visual/link4.obj"/>
    <mesh name="link5_m" file="visual/link5.obj"/>
    <mesh name="link6_m" file="visual/link6.obj"/>
    <mesh name="link7_m" file="collision/link7.obj"/>
    <mesh name="hand_m" file="visual/hand.obj"/>
    <mesh name="finger_m" file="visual/finger.obj"/>
  </asset>
  <default>
    <joint armature="0.08" damping="1.5"/>
    <geom friction="1.0 0.02 0.002"/>
  </default>
  <worldbody>
    <body name="panda_link0" pos="0 0 0">
      <geom type="mesh" mesh="link0_m" rgba="0.93 0.94 0.95 1" contype="0" conaffinity="0"/>
      <body name="panda_link1" pos="0 0 0.333">
        <inertial pos="0 -0.04 -0.05" mass="2.7" diaginertia="0.1 0.1 0.1"/>
        <joint name="panda_joint1" type="hinge" axis="0 0 1" range="-2.9671 2.9671"/>
        <geom type="mesh" mesh="link1_m" rgba="0.93 0.94 0.95 1" contype="0" conaffinity="0"/>
        <body name="panda_link2" pos="0 0 0" euler="-1.57079632679 0 0">
          <inertial pos="0 -0.04 0.06" mass="2.73" diaginertia="0.1 0.1 0.1"/>
          <joint name="panda_joint2" type="hinge" axis="0 0 1" range="-1.8326 1.8326"/>
          <geom type="mesh" mesh="link2_m" rgba="0.2 0.22 0.24 1" contype="0" conaffinity="0"/>
          <body name="panda_link3" pos="0 -0.316 0" euler="1.57079632679 0 0">
            <inertial pos="0.01 0.01 -0.05" mass="2.04" diaginertia="0.1 0.1 0.1"/>
            <joint name="panda_joint3" type="hinge" axis="0 0 1" range="-2.9671 2.9671"/>
            <geom type="mesh" mesh="link3_m" rgba="0.93 0.94 0.95 1" contype="0" conaffinity="0"/>
            <body name="panda_link4" pos="0.0825 0 0" euler="1.57079632679 0 0">
              <inertial pos="-0.03 0.03 0.02" mass="2.08" diaginertia="0.1 0.1 0.1"/>
              <joint name="panda_joint4" type="hinge" axis="0 0 1" range="-3.1416 0.0"/>
              <geom type="mesh" mesh="link4_m" rgba="0.2 0.22 0.24 1" contype="0" conaffinity="0"/>
              <body name="panda_link5" pos="-0.0825 0.384 0" euler="-1.57079632679 0 0">
                <inertial pos="0 0.04 -0.12" mass="3.0" diaginertia="0.1 0.1 0.1"/>
                <joint name="panda_joint5" type="hinge" axis="0 0 1" range="-2.9671 2.9671"/>
                <geom type="mesh" mesh="link5_m" rgba="0.93 0.94 0.95 1" contype="0" conaffinity="0"/>
                <body name="panda_link6" pos="0 0 0" euler="1.57079632679 0 0">
                  <inertial pos="0.04 0 0" mass="1.3" diaginertia="0.1 0.1 0.1"/>
                  <joint name="panda_joint6" type="hinge" axis="0 0 1" range="-0.0873 3.8223"/>
                  <geom type="mesh" mesh="link6_m" rgba="0.2 0.22 0.24 1" contype="0" conaffinity="0"/>
                  <body name="panda_link7" pos="0.088 0 0" euler="1.57079632679 0 0">
                    <inertial pos="0 0 0.08" mass="0.2" diaginertia="0.1 0.1 0.1"/>
                    <joint name="panda_joint7" type="hinge" axis="0 0 1" range="-2.9671 2.9671"/>
                    <geom type="mesh" mesh="link7_m" rgba="0.93 0.94 0.95 1" contype="0" conaffinity="0"/>
                    <body name="panda_hand" pos="0 0 0.107" euler="0 0 -0.785398163397">
                      <inertial pos="0 0 0.04" mass="0.81" diaginertia="0.1 0.1 0.1"/>
                      <geom type="mesh" mesh="hand_m" rgba="0.2 0.22 0.24 1" contype="0" conaffinity="0"/>
                      <site name="panda_grasptarget" pos="0 0 0.105" size="0.004"/>
                      <body name="panda_leftfinger" pos="0 0 0.0584">
                        <inertial pos="0 0.01 0.02" mass="0.1" diaginertia="0.01 0.01 0.01"/>
                        <joint name="panda_finger_joint1" type="slide" axis="0 1 0" range="0.0 0.04" damping="10.0"/>
                        <geom name="left_finger_pad" type="box" pos="0 0.008 0.036" size="0.010 0.008 0.018" rgba="0.72 0.74 0.76 1" solref="0.004 1"/>
                      </body>
                      <body name="panda_rightfinger" pos="0 0 0.0584">
                        <inertial pos="0 -0.01 0.02" mass="0.1" diaginertia="0.01 0.01 0.01"/>
                        <joint name="panda_finger_joint2" type="slide" axis="0 -1 0" range="0.0 0.04" damping="10.0"/>
                        <geom name="right_finger_pad" type="box" pos="0 -0.008 0.036" size="0.010 0.008 0.018" rgba="0.72 0.74 0.76 1" solref="0.004 1"/>
                      </body>
                    </body>
                  </body>
                </body>
              </body>
            </body>
          </body>
        </body>
      </body>
    </body>
  </worldbody>
  <actuator>
    <position name="act_j1" joint="panda_joint1" kp="300" kv="30" ctrlrange="-2.9671 2.9671"/>
    <position name="act_j2" joint="panda_joint2" kp="300" kv="30" ctrlrange="-1.8326 1.8326"/>
    <position name="act_j3" joint="panda_joint3" kp="300" kv="30" ctrlrange="-2.9671 2.9671"/>
    <position name="act_j4" joint="panda_joint4" kp="300" kv="30" ctrlrange="-3.1416 0.0"/>
    <position name="act_j5" joint="panda_joint5" kp="180" kv="18" ctrlrange="-2.9671 2.9671"/>
    <position name="act_j6" joint="panda_joint6" kp="180" kv="18" ctrlrange="-0.0873 3.8223"/>
    <position name="act_j7" joint="panda_joint7" kp="140" kv="14" ctrlrange="-2.9671 2.9671"/>
    <position name="act_f1" joint="panda_finger_joint1" kp="120" kv="12" ctrlrange="0.0 0.04"/>
    <position name="act_f2" joint="panda_finger_joint2" kp="120" kv="12" ctrlrange="0.0 0.04"/>
  </actuator>
</mujoco>
"""
    xml_path.write_text(mjcf, encoding="utf-8")


def vendor_franka_panda_assets(dest_dir: Path, source_urdf_dir: Path | None = None) -> dict[str, Path]:
    """Copy and rewrite Franka Panda URDF, meshes, MJCF, and OpenUSD into dest_dir."""
    src = source_urdf_dir or find_local_panda_urdf_dir()
    meshes_dst = dest_dir / "meshes"
    meshes_dst.mkdir(parents=True, exist_ok=True)
    for sub in ("visual", "collision"):
        src_sub = src / "meshes" / sub
        dst_sub = meshes_dst / sub
        if dst_sub.exists():
            shutil.rmtree(dst_sub)
        shutil.copytree(src_sub, dst_sub)

    urdf_text = (src / "panda.urdf").read_text(encoding="utf-8")
    urdf_text = urdf_text.replace("package://meshes/", "meshes/")
    urdf_dst = dest_dir / "panda.urdf"
    urdf_dst.write_text(urdf_text, encoding="utf-8")

    xml_dst = dest_dir / "panda.xml"
    _write_panda_mjcf(xml_dst)

    asset_usd = _write_panda_usd(dest_dir, meshes_dst)
    return {
        "urdf": urdf_dst,
        "xml": xml_dst,
        "usd": asset_usd,
    }


def localize_deformable_asset_from_m1(
    m1_dir: Path,
    dest_dir: Path,
    *,
    prim_name: str = "DeformableAsset",
) -> dict[str, Any]:
    """Localize calibrated M1 ConvertAsset bundle into a scenario-forge v0.2 asset dir."""
    manifest_path = m1_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    asset_id = str(manifest["asset_id"])
    source_meta = manifest["source"]
    family = str(source_meta["structural_family"])
    budget = manifest["integrity_budget"]
    engines_meta = manifest.get("engines", {})

    dest_dir.mkdir(parents=True, exist_ok=True)
    src_base = (m1_dir / "base.usda").read_text(encoding="utf-8")
    src_isaac = (m1_dir / "engines" / "isaac_physx" / "isaac_physx.usda").read_text(encoding="utf-8")
    src_newton = (m1_dir / "engines" / "newton18" / "newton_overlay.usda").read_text(encoding="utf-8")
    genesis_cfg = json.loads((m1_dir / "engines" / "genesis" / "genesis_config.json").read_text(encoding="utf-8"))

    # Slice to DeformableAsset prim block so GroundPlane CollisionMesh is never matched.
    deform_section = src_isaac[src_isaac.index('"DeformableAsset"'):] if '"DeformableAsset"' in src_isaac else src_isaac
    pts = _parse_usda_point3f_array(deform_section, "omniphysics:restShapePoints")
    if not pts:
        pts = _parse_usda_point3f_array(deform_section, "points")
    min_z = min(z for _, _, z in pts)
    pts_zeroed = [(x, y, z - min_z) for x, y, z in pts]
    if family == "soft_solid":
        surf_tris = _parse_usda_tuple_int_array(deform_section, "surfaceFaceVertexIndices", 3)
        tris = [(a, b, c) for a, b, c in surf_tris]
    else:
        tri_tuples = _parse_usda_tuple_int_array(deform_section, "omniphysics:restTriVtxIndices", 3)
        if tri_tuples:
            tris = [(a, b, c) for a, b, c in tri_tuples]
        else:
            mesh_tris = _parse_usda_flat_int_array(deform_section, "faceVertexIndices")
            tris = [(mesh_tris[i], mesh_tris[i + 1], mesh_tris[i + 2]) for i in range(0, len(mesh_tris), 3)]

    base_pts = _parse_usda_point3f_array(src_base, "points")
    base_min_z = min(z for _, _, z in base_pts) if base_pts else 0.0
    base_pts_zeroed = [(x, y, z - base_min_z) for x, y, z in base_pts]
    base_fcounts = _parse_usda_flat_int_array(src_base, "faceVertexCounts")
    base_findices = _parse_usda_flat_int_array(src_base, "faceVertexIndices")

    diffuse = (0.76, 0.56, 0.36) if family == "soft_solid" else (0.32, 0.62, 0.78)
    roughness = 0.55 if family == "soft_solid" else 0.85
    base_usda = f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{{
    def Mesh "{prim_name}" (
        apiSchemas = ["MaterialBindingAPI"]
    )
    {{
        def Scope "Materials"
        {{
            def Material "VisualMat"
            {{
                token outputs:surface.connect = </World/{prim_name}/Materials/VisualMat/Shader.outputs:surface>
                def Shader "Shader"
                {{
                    uniform token info:id = "UsdPreviewSurface"
                    color3f inputs:diffuseColor = ({diffuse[0]}, {diffuse[1]}, {diffuse[2]})
                    float inputs:roughness = {roughness}
                    token outputs:surface
                }}
            }}
        }}

        rel material:binding = </World/{prim_name}/Materials/VisualMat>
        custom string deformable:assetId = "{asset_id}"
        custom string deformable:structuralFamily = "{family}"
        custom double deformable:youngsModulusPa = {float(source_meta.get("youngs_modulus_pa", 28000.0)):.2f}
        custom double deformable:poissonsRatio = {float(source_meta.get("poissons_ratio", 0.30)):.4f}
        custom string deformable:strainMetric = "{budget.get("strain_metric", "polar_stretch_frobenius_q95")}"
        custom double deformable:strainOnsetA = {float(budget.get("strain_onset_a", 0.15)):.4f}
        custom double deformable:strainFailureB = {float(budget.get("strain_failure_b", 0.45)):.4f}
        custom double deformable:damageThreshold = {float(budget.get("damage_threshold", 0.25)):.4f}
        custom double deformable:maxNormalForceN = {float(budget.get("max_normal_force_n", 60.0)):.4f}
        int[] faceVertexCounts = [{", ".join(str(x) for x in base_fcounts)}]
        int[] faceVertexIndices = [{", ".join(str(x) for x in base_findices)}]
        point3f[] points = [{_format_vec3_list(base_pts_zeroed)}]
    }}
}}
"""
    (dest_dir / "deps" / "usd").mkdir(parents=True, exist_ok=True)
    (dest_dir / "deps" / "usd" / "scoped_source.usda").write_text(base_usda, encoding="utf-8")

    # Build dual-schema overlays (OmniPhysicsDeformable* + PhysxDeformable* + Newton custom attrs)
    isaac_params = engines_meta.get("isaac_physx", {}).get("effective_params", {})
    newton_params = engines_meta.get("newton18", {}).get("effective_params", {})
    mj4_params = engines_meta.get("mujoco4", {}).get("effective_params", {})

    if family == "soft_solid":
        tets = _parse_usda_tuple_int_array(deform_section, "tetVertexIndices", 4)
        tet_tuples = [(a, b, c, d) for a, b, c, d in tets]
        surf_tuples = [(a, b, c) for a, b, c in _parse_usda_tuple_int_array(deform_section, "surfaceFaceVertexIndices", 3)]
        young_pa = float(isaac_params.get("youngs_modulus_pa", 17360.0))
        damping = float(isaac_params.get("elasticity_damping", 0.10))
        omni_overlay = f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

over "World"
{{
    over "{prim_name}"
    {{
        def Scope "DeformableMaterials"
        {{
            def Material "DeformableMat" (
                apiSchemas = ["OmniPhysicsDeformableMaterialAPI", "PhysxDeformableMaterialAPI"]
            )
            {{
                float omniphysics:density = 950
                float omniphysics:dynamicFriction = 0.65
                float omniphysics:poissonsRatio = 0.32
                float omniphysics:staticFriction = 0.80
                float omniphysics:youngsModulus = {young_pa:.3f}
                float physxDeformableMaterial:elasticityDamping = {damping:.4f}
            }}
        }}

        def TetMesh "CollisionVolume" (
            apiSchemas = ["OmniPhysicsDeformableBodyAPI", "OmniPhysicsVolumeDeformableSimAPI", "PhysicsCollisionAPI", "PhysxCollisionAPI", "MaterialBindingAPI"]
        )
        {{
            uniform token purpose = "guide"
            rel material:binding:physics = </World/{prim_name}/DeformableMaterials/DeformableMat>
            point3f[] omniphysics:restShapePoints = [{_format_vec3_list(pts_zeroed)}]
            int4[] omniphysics:restTetVtxIndices = [{_format_int4_list(tet_tuples)}]
            point3f[] points = [{_format_vec3_list(pts_zeroed)}]
            int3[] surfaceFaceVertexIndices = [{_format_int3_list(surf_tuples)}]
            int4[] tetVertexIndices = [{_format_int4_list(tet_tuples)}]
            float physxCollision:contactOffset = 0.004
            float physxCollision:restOffset = 0.001
        }}
    }}
}}
"""
    else:
        young_pa = float(isaac_params.get("youngs_modulus_pa", 180000.0))
        damping = float(isaac_params.get("damping", 0.12))
        omni_overlay = f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

over "World"
{{
    over "{prim_name}" (
        apiSchemas = ["OmniPhysicsDeformableBodyAPI", "OmniPhysicsSurfaceDeformableSimAPI", "PhysicsCollisionAPI", "PhysxCollisionAPI", "MaterialBindingAPI"]
    )
    {{
        def Scope "DeformableMaterials"
        {{
            def Material "DeformableMat" (
                apiSchemas = ["OmniPhysicsDeformableMaterialAPI", "OmniPhysicsSurfaceDeformableMaterialAPI", "PhysxDeformableMaterialAPI"]
            )
            {{
                float omniphysics:density = 173.6111
                float omniphysics:dynamicFriction = 0.45
                float omniphysics:poissonsRatio = 0.30
                float omniphysics:staticFriction = 0.55
                float omniphysics:surfaceBendStiffness = {float(isaac_params.get("bend_stiffness", 100.0)):.2f}
                float omniphysics:surfaceShearStiffness = {float(isaac_params.get("shear_stiffness", 600.0)):.2f}
                float omniphysics:surfaceStretchStiffness = {float(isaac_params.get("stretch_stiffness", 1500.0)):.2f}
                float omniphysics:surfaceThickness = 0.008
                float omniphysics:youngsModulus = {young_pa:.2f}
                float physxDeformableMaterial:elasticityDamping = {damping:.4f}
            }}
        }}

        rel material:binding:physics = </World/{prim_name}/DeformableMaterials/DeformableMat>
        point3f[] omniphysics:restShapePoints = [{_format_vec3_list(pts_zeroed)}]
        int3[] omniphysics:restTriVtxIndices = [{_format_int3_list(tris)}]
        float physxCollision:contactOffset = 0.004
        float physxCollision:restOffset = 0.001
    }}
}}
"""

    newton_attrs = "\n".join(
        f'        custom double newton:{k} = {float(v):.6f}'
        if isinstance(v, (int, float))
        else f'        custom string newton:{k} = "{v}"'
        for k, v in sorted(newton_params.items())
    )
    newton_overlay = f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

over "World"
{{
    over "{prim_name}"
    {{
        custom string newton:engineVersion = "newton-1.8.0"
        custom string newton:solver = "SolverVBD"
{newton_attrs}
    }}
}}
"""

    overlays_dir = dest_dir / "overlays"
    overlays_dir.mkdir(parents=True, exist_ok=True)
    (overlays_dir / "omniphysics_deformable.usda").write_text(omni_overlay, encoding="utf-8")
    (overlays_dir / "newton_overlay.usda").write_text(newton_overlay, encoding="utf-8")

    # Save clean self-contained per-engine manifests & geometry (zero temp paths)
    eng_dir = dest_dir / "engines"
    (eng_dir / "genesis").mkdir(parents=True, exist_ok=True)
    (eng_dir / "genesis" / "genesis_config.json").write_text(
        json.dumps(genesis_cfg, indent=2), encoding="utf-8"
    )
    (eng_dir / "newton18").mkdir(parents=True, exist_ok=True)
    (eng_dir / "newton18" / "newton_config.json").write_text(
        json.dumps(
            {
                "engine_id": "newton18",
                "solver": "SolverVBD",
                "asset_id": asset_id,
                "structural_family": family,
                "params": newton_params,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (eng_dir / "mujoco4").mkdir(parents=True, exist_ok=True)
    _write_obj_file(eng_dir / "mujoco4" / "mesh.obj", pts_zeroed, tris)
    (eng_dir / "mujoco4" / "mujoco4_asset.json").write_text(
        json.dumps(
            {
                "engine_id": "mujoco4",
                "asset_id": asset_id,
                "structural_family": family,
                "mesh_obj": "mesh.obj",
                "params": mj4_params,
                "mass_kg": float(source_meta.get("mass_kg", 0.1)),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (eng_dir / "isaac_physx").mkdir(parents=True, exist_ok=True)
    (eng_dir / "isaac_physx" / "isaac_physx_config.json").write_text(
        json.dumps(
            {
                "engine_id": "isaac_physx",
                "asset_id": asset_id,
                "structural_family": family,
                "params": isaac_params,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    shutil.copy2(manifest_path, dest_dir / "m1_manifest.json")
    asset_usd = dest_dir / "asset.usd"
    asset_usd.write_text(
        """#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    kilogramsPerUnit = 1
    upAxis = "Z"
    timeCodesPerSecond = 24
    framesPerSecond = 24
    startTimeCode = 0
    endTimeCode = 0
    subLayers = [
        @overlays/omniphysics_deformable.usda@,
        @overlays/newton_overlay.usda@,
        @deps/usd/scoped_source.usda@,
    ]
)
""",
        encoding="utf-8",
    )

    return {
        "asset_id": asset_id,
        "structural_family": family,
        "asset_usd": asset_usd,
        "m1_manifest": manifest,
        "min_z_shift": min_z,
        "pts_zeroed": pts_zeroed,
        "tris": tris,
    }

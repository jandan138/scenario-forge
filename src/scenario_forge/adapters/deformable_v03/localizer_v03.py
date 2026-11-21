"""Localized v0.3 deformable PBR dual-mesh assets and rigid task fixtures."""

from __future__ import annotations

import json
import math
from pathlib import Path
import shutil
from typing import Any, Sequence

from scenario_forge.adapters.deformable_v02.usd_localizer import (
    _usd_box_mesh,
    _usd_cylinder_mesh,
    _wrap_usd_asset,
)


def create_parametric_fixture_usd(
    dest_dir: Path,
    root_name: str,
    *,
    boxes: Sequence[dict[str, Any]] = (),
    cylinders: Sequence[dict[str, Any]] = (),
    materials: Sequence[dict[str, Any]] = (),
) -> Path:
    """Create a self-contained rigid OpenUSD component fixture from box and cylinder primitives."""
    mat_blocks: list[str] = []
    default_mat = materials[0]["name"] if materials else "DefaultMat"
    mat_list = list(materials) or [
        {"name": "DefaultMat", "color": (0.45, 0.48, 0.52), "metallic": 0.2, "roughness": 0.45}
    ]
    for m in mat_list:
        col = m["color"]
        mat_blocks.append(
            f"""            def Material "{m["name"]}"
            {{
                token outputs:surface.connect = </World/{root_name}/Materials/{m["name"]}/Shader.outputs:surface>
                def Shader "Shader"
                {{
                    uniform token info:id = "UsdPreviewSurface"
                    color3f inputs:diffuseColor = ({col[0]:.3f}, {col[1]:.3f}, {col[2]:.3f})
                    float inputs:metallic = {float(m.get("metallic", 0.1)):.3f}
                    float inputs:roughness = {float(m.get("roughness", 0.45)):.3f}
                    token outputs:surface
                }}
            }}"""
        )

    geom_blocks: list[str] = []
    for idx, b in enumerate(boxes):
        hx, hy, hz = b["half_extents"]
        cx, cy, cz = b["center"]
        m_name = b.get("material", default_mat)
        geom_blocks.append(
            _usd_box_mesh(
                b.get("name", f"BoxPart_{idx}"),
                float(hx),
                float(hy),
                float(hz),
                (float(cx), float(cy), float(cz)),
                f"/World/{root_name}/Materials/{m_name}",
                rigid=bool(b.get("rigid", False)),
                collision=bool(b.get("collision", True)),
                mass=b.get("mass"),
                static_friction=float(b.get("static_friction", 0.65)),
                dynamic_friction=float(b.get("dynamic_friction", 0.55)),
            )
        )
    for idx, c in enumerate(cylinders):
        m_name = c.get("material", default_mat)
        cx, cy = c.get("center_xy", (0.0, 0.0))
        cyl_str = _usd_cylinder_mesh(
            c.get("name", f"CylPart_{idx}"),
            float(c["r_bottom"]),
            float(c["r_top"]),
            float(c["z0"]),
            float(c["z1"]),
            int(c.get("segments", 36)),
            f"/World/{root_name}/Materials/{m_name}",
            collision=bool(c.get("collision", True)),
        )
        if abs(float(cx)) > 1e-6 or abs(float(cy)) > 1e-6:
            cyl_str = f"""        def Xform "{c.get("name", f"CylPart_{idx}")}_XF"
        {{
            double3 xformOp:translate = ({float(cx):.5f}, {float(cy):.5f}, 0)
            uniform token[] xformOpOrder = ["xformOp:translate"]
{cyl_str}
        }}"""
        geom_blocks.append(cyl_str)

    mats_joined = "\n".join(mat_blocks)
    geoms_joined = "\n".join(geom_blocks)
    usda = f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{{
    def Xform "{root_name}" (
        kind = "component"
    )
    {{
        def Scope "Materials"
        {{
{mats_joined}
        }}
{geoms_joined}
    }}
}}
"""
    return _wrap_usd_asset(dest_dir, usda)


def create_v03_fixture_usds(assets_root: Path) -> dict[str, Path]:
    """Generate the reusable library of v0.3 rigid fixtures under assets_root."""
    created: dict[str, Path] = {}
    specs: dict[str, dict[str, Any]] = {
        "baking_sheet_tray": {
            "materials": [
                {"name": "AnodizedTray", "color": (0.28, 0.30, 0.34), "metallic": 0.72, "roughness": 0.32},
                {"name": "ParchmentLiner", "color": (0.86, 0.80, 0.68), "metallic": 0.0, "roughness": 0.75},
            ],
            "boxes": [
                {"name": "TrayPlate", "half_extents": (0.095, 0.085, 0.003), "center": (0.0, 0.0, 0.003), "material": "AnodizedTray"},
                {"name": "LinerPad", "half_extents": (0.084, 0.074, 0.001), "center": (0.0, 0.0, 0.0055), "material": "ParchmentLiner"},
                {"name": "RimN", "half_extents": (0.095, 0.004, 0.007), "center": (0.0, 0.081, 0.007), "material": "AnodizedTray"},
                {"name": "RimS", "half_extents": (0.095, 0.004, 0.007), "center": (0.0, -0.081, 0.007), "material": "AnodizedTray"},
            ],
        },
        "tartlet_pastry_cup": {
            "materials": [
                {"name": "TartCrust", "color": (0.78, 0.56, 0.30), "metallic": 0.0, "roughness": 0.62},
                {"name": "CreamFill", "color": (0.95, 0.91, 0.80), "metallic": 0.0, "roughness": 0.42},
                {"name": "CeramicPlinth", "color": (0.92, 0.92, 0.90), "metallic": 0.0, "roughness": 0.25},
            ],
            "cylinders": [
                {"name": "SaucerBase", "r_bottom": 0.078, "r_top": 0.085, "z0": 0.0, "z1": 0.005, "material": "CeramicPlinth"},
                {"name": "TartShell", "r_bottom": 0.044, "r_top": 0.052, "z0": 0.005, "z1": 0.021, "material": "TartCrust"},
                {"name": "PastryCream", "r_bottom": 0.042, "r_top": 0.044, "z0": 0.019, "z1": 0.023, "material": "CreamFill"},
            ],
        },
        "smooth_folding_mat": {
            "materials": [
                {"name": "DeskMatSlate", "color": (0.24, 0.28, 0.33), "metallic": 0.0, "roughness": 0.72},
                {"name": "FoldGuideTrim", "color": (0.76, 0.64, 0.44), "metallic": 0.05, "roughness": 0.55},
            ],
            "boxes": [
                {"name": "MatSlab", "half_extents": (0.22, 0.16, 0.001), "center": (0.0, 0.0, 0.001), "material": "DeskMatSlate", "static_friction": 0.15, "dynamic_friction": 0.13},
                {"name": "CenterSeam", "half_extents": (0.002, 0.15, 0.0004), "center": (0.0, 0.0, 0.0021), "material": "FoldGuideTrim", "collision": False},
            ],
        },
        "garment_folding_board": {
            "materials": [
                {"name": "BoardSlate", "color": (0.24, 0.29, 0.35), "metallic": 0.05, "roughness": 0.65},
                {"name": "FoldGuideTrim", "color": (0.78, 0.65, 0.44), "metallic": 0.08, "roughness": 0.50},
            ],
            "boxes": [
                {"name": "BoardSlab", "half_extents": (0.095, 0.13, 0.014), "center": (0.045, 0.0, 0.014), "material": "BoardSlate", "static_friction": 0.65, "dynamic_friction": 0.55},
                {"name": "CenterSeam", "half_extents": (0.002, 0.125, 0.0005), "center": (0.01, 0.0, 0.0283), "material": "FoldGuideTrim", "collision": False},
            ],
        },
        "toner_cartridge_box": {
            "materials": [
                {"name": "CartonBody", "color": (0.86, 0.72, 0.52), "metallic": 0.0, "roughness": 0.68},
                {"name": "LabelBand", "color": (0.16, 0.42, 0.68), "metallic": 0.0, "roughness": 0.45},
            ],
            "boxes": [
                {"name": "CartonHull", "half_extents": (0.032, 0.032, 0.022), "center": (0.0, 0.0, 0.022), "material": "CartonBody", "rigid": True, "mass": 0.45, "static_friction": 0.9, "dynamic_friction": 0.8},
                {"name": "TopLabel", "half_extents": (0.028, 0.014, 0.001), "center": (0.0, 0.0, 0.0445), "material": "LabelBand", "collision": False},
            ],
        },
        "delivery_caddy": {
            "materials": [
                {"name": "NordicBirch", "color": (0.78, 0.66, 0.48), "metallic": 0.0, "roughness": 0.58},
                {"name": "SlateTrim", "color": (0.22, 0.25, 0.30), "metallic": 0.1, "roughness": 0.50},
            ],
            "boxes": [
                {"name": "CaddyBase", "half_extents": (0.085, 0.085, 0.003), "center": (0.0, 0.0, 0.003), "material": "NordicBirch"},
                {"name": "RimN", "half_extents": (0.085, 0.004, 0.010), "center": (0.0, 0.081, 0.010), "material": "SlateTrim"},
                {"name": "RimW", "half_extents": (0.004, 0.085, 0.010), "center": (-0.081, 0.0, 0.010), "material": "SlateTrim"},
                {"name": "RimE", "half_extents": (0.004, 0.085, 0.010), "center": (0.081, 0.0, 0.010), "material": "SlateTrim"},
            ],
        },
        "cable_carrier_cradle": {
            "materials": [
                {"name": "ESDBase", "color": (0.20, 0.22, 0.25), "metallic": 0.15, "roughness": 0.55},
                {"name": "CopperRail", "color": (0.72, 0.46, 0.22), "metallic": 0.85, "roughness": 0.28},
            ],
            "boxes": [
                {"name": "BasePlate", "half_extents": (0.105, 0.055, 0.004), "center": (0.0, 0.0, 0.004), "material": "ESDBase"},
                {"name": "LeftStand", "half_extents": (0.012, 0.036, 0.007), "center": (-0.068, 0.0, 0.011), "material": "CopperRail"},
                {"name": "RightStand", "half_extents": (0.012, 0.036, 0.007), "center": (0.068, 0.0, 0.011), "material": "CopperRail"},
            ],
        },
        "smt_u_clip_block": {
            "materials": [
                {"name": "PCBGreen", "color": (0.11, 0.36, 0.22), "metallic": 0.05, "roughness": 0.42},
                {"name": "ClipNylon", "color": (0.86, 0.86, 0.84), "metallic": 0.0, "roughness": 0.38},
            ],
            "boxes": [
                {"name": "ClipFloor", "half_extents": (0.105, 0.048, 0.004), "center": (0.0, 0.0, 0.004), "material": "PCBGreen"},
                {"name": "WallSouth", "half_extents": (0.082, 0.005, 0.012), "center": (0.0, -0.020, 0.014), "material": "ClipNylon"},
                {"name": "WallNorth", "half_extents": (0.082, 0.005, 0.012), "center": (0.0, 0.020, 0.014), "material": "ClipNylon"},
            ],
        },
        "pcba_header_boss": {
            "materials": [
                {"name": "PCBGreen", "color": (0.10, 0.35, 0.20), "metallic": 0.05, "roughness": 0.42},
                {"name": "GoldPins", "color": (0.85, 0.68, 0.24), "metallic": 0.90, "roughness": 0.22},
            ],
            "boxes": [
                {"name": "PCBABase", "half_extents": (0.075, 0.075, 0.003), "center": (0.0, 0.0, 0.003), "material": "PCBGreen"},
                {"name": "HeaderShroud", "half_extents": (0.026, 0.026, 0.002), "center": (0.0, 0.0, 0.007), "material": "GoldPins"},
                {"name": "GuideRailW", "half_extents": (0.004, 0.036, 0.005), "center": (-0.042, 0.0, 0.009), "material": "GoldPins"},
                {"name": "GuideRailE", "half_extents": (0.004, 0.036, 0.005), "center": (0.042, 0.0, 0.009), "material": "GoldPins"},
            ],
        },
        "tube_bench_cradle": {
            "materials": [
                {"name": "DelrinWhite", "color": (0.88, 0.89, 0.91), "metallic": 0.0, "roughness": 0.40},
                {"name": "SteelFoot", "color": (0.50, 0.53, 0.57), "metallic": 0.85, "roughness": 0.28},
            ],
            "boxes": [
                {"name": "BasePlate", "half_extents": (0.105, 0.055, 0.004), "center": (0.0, 0.0, 0.004), "material": "SteelFoot"},
                {"name": "LeftPost", "half_extents": (0.014, 0.032, 0.007), "center": (-0.068, 0.0, 0.011), "material": "DelrinWhite"},
                {"name": "RightPost", "half_extents": (0.014, 0.032, 0.007), "center": (0.068, 0.0, 0.011), "material": "DelrinWhite"},
            ],
        },
        "manifold_fork_saddle": {
            "materials": [
                {"name": "AnodizedBlue", "color": (0.20, 0.42, 0.72), "metallic": 0.75, "roughness": 0.30},
                {"name": "StainlessBase", "color": (0.68, 0.70, 0.73), "metallic": 0.88, "roughness": 0.24},
            ],
            "boxes": [
                {"name": "ManifoldBase", "half_extents": (0.105, 0.055, 0.004), "center": (0.0, 0.0, 0.004), "material": "StainlessBase"},
                {"name": "ForkS", "half_extents": (0.085, 0.005, 0.013), "center": (0.0, -0.022, 0.015), "material": "AnodizedBlue"},
                {"name": "ForkN", "half_extents": (0.085, 0.005, 0.013), "center": (0.0, 0.022, 0.015), "material": "AnodizedBlue"},
            ],
        },
        "bulb_collar_holder": {
            "materials": [
                {"name": "StainlessPlate", "color": (0.68, 0.70, 0.73), "metallic": 0.85, "roughness": 0.25},
                {"name": "GlassCollar", "color": (0.74, 0.86, 0.94), "metallic": 0.15, "roughness": 0.15},
            ],
            "boxes": [
                {"name": "StandBase", "half_extents": (0.065, 0.065, 0.003), "center": (0.0, 0.0, 0.003), "material": "StainlessPlate"},
                {"name": "CollarPostN", "half_extents": (0.018, 0.004, 0.006), "center": (0.0, 0.034, 0.012), "material": "GlassCollar"},
                {"name": "CollarPostS", "half_extents": (0.018, 0.004, 0.006), "center": (0.0, -0.034, 0.012), "material": "GlassCollar"},
                {"name": "CollarPostW", "half_extents": (0.004, 0.018, 0.006), "center": (-0.034, 0.0, 0.012), "material": "GlassCollar"},
                {"name": "CollarPostE", "half_extents": (0.004, 0.018, 0.006), "center": (0.034, 0.0, 0.012), "material": "GlassCollar"},
            ],
        },
    }
    for name, cfg in specs.items():
        created[name] = create_parametric_fixture_usd(assets_root / name, name, **cfg)
    return created


def localize_v03_deformable_asset(
    m1_bundle_dir: Path,
    dest_dir: Path,
    *,
    prim_name: str,
) -> dict[str, Any]:
    """Copy M1 v0.3 dual-mesh PBR bundle into scenario-forge asset closure with renamed USD prims."""
    manifest = json.loads((m1_bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    asset_id = str(manifest["asset_id"])
    source_meta = manifest["source"]
    budget = manifest["integrity_budget"]

    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(m1_bundle_dir / "manifest.json", dest_dir / "m1_manifest.json")
    shutil.copy2(m1_bundle_dir / "physics_proxy.npz", dest_dir / "physics_proxy.npz")
    shutil.copy2(m1_bundle_dir / "skinning.npz", dest_dir / "skinning.npz")
    shutil.copytree(m1_bundle_dir / "textures", dest_dir / "textures")
    shutil.copytree(m1_bundle_dir / "engines", dest_dir / "engines")

    # Localize high-poly PBR USDA inside deps/usd/ and rewrite paths/prim names uniquely
    deps_usd = dest_dir / "deps" / "usd"
    deps_usd.mkdir(parents=True, exist_ok=True)
    vis_raw = (m1_bundle_dir / "visual_highpoly.usda").read_text(encoding="utf-8")
    scope_mat = f"{prim_name}_Looks"
    vis_raw = vis_raw.replace('def Scope "Looks"', f'def Scope "{scope_mat}"')
    vis_raw = vis_raw.replace("/World/Looks/PBRMat", f"/World/{scope_mat}/PBRMat")
    vis_raw = vis_raw.replace('def Mesh "VisualHighPoly"', f'def Mesh "{prim_name}"')
    vis_raw = vis_raw.replace("@./textures/", "@../../textures/")
    (deps_usd / "scoped_source.usda").write_text(vis_raw, encoding="utf-8")

    asset_usd = _wrap_usd_asset(dest_dir, vis_raw)
    return {
        "asset_id": asset_id,
        "structural_family": str(source_meta["structural_family"]),
        "asset_usd": asset_usd,
        "m1_manifest": manifest,
        "budget": budget,
    }

"""Build the complete Bilibili BV17t4y1V7XH distillation_v06 OpenUSD scene package with rear arms & 5 cameras."""

from __future__ import annotations

import json
import math
from pathlib import Path
import shutil
from typing import Any

import numpy as np
import yaml

from scenario_forge.adapters.deformable_v02.usd_localizer import (
    create_robot_pedestal_usd,
    vendor_franka_panda_assets,
)
from scenario_forge.assets.checksum import compute_sha256
from scenario_forge.assets.lock import generate_asset_lock, write_asset_lock


V06_CAMERAS: dict[str, dict[str, Any]] = {
    "Cam_Master_Front": {
        "eye": [0.000, -1.380, 1.110],
        "target": [0.000, -0.020, 0.990],
        "focal_mm": 21.5,
        "role": "master_uncut_front",
    },
    "Cam_Bosshead_Close": {
        "eye": [-0.235, -0.210, 1.035],
        "target": [-0.280, 0.062, 0.992],
        "focal_mm": 42.0,
        "role": "macro_bosshead_open_up",
    },
    "Cam_Clamp3Prong_Close": {
        "eye": [0.035, -0.340, 1.015],
        "target": [0.032, 0.010, 1.010],
        "focal_mm": 32.0,
        "role": "macro_3prong_fixed_below_hoses",
    },
    "Cam_Thermometer_Bulb": {
        "eye": [-0.140, -0.240, 1.090],
        "target": [-0.176, 0.000, 1.080],
        "focal_mm": 44.0,
        "role": "macro_bulb_sidearm_flush",
    },
    "Cam_Receiver_Drip": {
        "eye": [0.215, -0.340, 0.935],
        "target": [0.205, 0.000, 0.905],
        "focal_mm": 34.0,
        "role": "macro_receiver_distillate_drip",
    },
}


def _lookat_quat_wxyz(eye: list[float], target: list[float]) -> list[float]:
    e = np.asarray(eye, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)
    up = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    fwd = (t - e) / max(float(np.linalg.norm(t - e)), 1e-12)
    z_c = -fwd
    x_c = np.cross(up, z_c)
    x_c = x_c / max(float(np.linalg.norm(x_c)), 1e-12)
    y_c = np.cross(z_c, x_c)
    R = np.column_stack([x_c, y_c, z_c])
    tr = float(np.trace(R))
    if tr > 0.0:
        s = math.sqrt(tr + 1.0) * 2.0
        qw = 0.25 * s
        qx = (R[2, 1] - R[1, 2]) / s
        qy = (R[0, 2] - R[2, 0]) / s
        qz = (R[1, 0] - R[0, 1]) / s
    else:
        qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
    n = max(math.sqrt(qw * qw + qx * qx + qy * qy + qz * qz), 1e-12)
    return [qw / n, qx / n, qy / n, qz / n]


def _make_tube_skin_topology(n_rings: int = 64, n_circ: int = 24, r_outer: float = 0.0052) -> tuple[np.ndarray, np.ndarray]:
    """Build initial UV-smooth 64x24 cylindrical hose mesh topology (updated each frame by Cosserat centerline)."""
    pts = []
    for i in range(n_rings):
        s = i / float(n_rings - 1)
        for j in range(n_circ):
            ang = 2.0 * math.pi * j / n_circ
            pts.append([s * 0.40, r_outer * math.cos(ang), 0.78 + r_outer * math.sin(ang)])
    tris = []
    for i in range(n_rings - 1):
        for j in range(n_circ):
            jn = (j + 1) % n_circ
            a = i * n_circ + j
            b = i * n_circ + jn
            c = (i + 1) * n_circ + jn
            d = (i + 1) * n_circ + j
            tris.append([a, b, c])
            tris.append([a, c, d])
    return np.asarray(pts, dtype=np.float32), np.asarray(tris, dtype=np.int32)


def build_distillation_v06_package(
    output_dir: Path | None = None,
    m1_assets_dir: Path | None = None,
) -> dict[str, Any]:
    """Compose the complete Bilibili-aligned distillation_v06 OpenUSD package."""
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade, Vt

    repo_root = Path(__file__).resolve().parents[4]
    pkg_root = output_dir or (repo_root / "external_artifacts" / "distillation_v06_package" / "scenario_package")
    m1_root = m1_assets_dir or (repo_root.parent / "ConvertAsset" / "external_artifacts" / "distillation_v06_assets")

    if pkg_root.exists():
        shutil.rmtree(pkg_root)
    assets_root = pkg_root / "assets"
    assets_root.mkdir(parents=True, exist_ok=True)

    # Copy M1 OmniGlass MDL shaders & 20 instrument USDs into package assets
    shutil.copytree(m1_root / "deps", assets_root / "deps", dirs_exist_ok=True)
    cad_specs = json.loads((m1_root / "v06_cad_specs.json").read_text(encoding="utf-8"))
    shutil.copy2(m1_root / "v06_cad_specs.json", assets_root / "v06_cad_specs.json")

    inst_dir = assets_root / "instruments"
    inst_dir.mkdir(parents=True, exist_ok=True)
    for usda in sorted((m1_root / "instruments").glob("*.usda")):
        shutil.copy2(usda, inst_dir / usda.name)

    # Vendor Franka Panda + Rear Pedestals
    vendor_franka_panda_assets(assets_root / "franka_panda")
    create_robot_pedestal_usd(assets_root / "robot_pedestal")

    # Create main OpenUSD stage
    scene_path = pkg_root / "scene" / "main.usda"
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(scene_path))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)

    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())

    # PhysX 5 GPU Scene (120 Hz, TGS, CCD enabled!)
    phys_scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
    phys_scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(0.0, 0.0, -1.0))
    phys_scene.CreateGravityMagnitudeAttr().Set(9.81)
    pprim = phys_scene.GetPrim()
    pprim.CreateAttribute("physxScene:enableGPUDynamics", Sdf.ValueTypeNames.Bool, custom=True).Set(True)
    pprim.CreateAttribute("physxScene:enableCCD", Sdf.ValueTypeNames.Bool, custom=True).Set(True)
    pprim.CreateAttribute("physxScene:solverType", Sdf.ValueTypeNames.Token, custom=True).Set("TGS")
    pprim.CreateAttribute("physxScene:timeStepsPerSecond", Sdf.ValueTypeNames.UInt, custom=True).Set(120)

    # Studio Environment matching Bilibili BV17t4y1V7XH (sky-blue teaching wall + matte-white lab bench + swan-neck water tap + drain)
    UsdGeom.Scope.Define(stage, "/World/Environment")
    UsdGeom.Scope.Define(stage, "/World/Looks")

    def _pbr(name: str, rgb: tuple[float, float, float], rough: float, metal: float = 0.0) -> Any:
        mat = UsdShade.Material.Define(stage, f"/World/Looks/{name}")
        sh = UsdShade.Shader.Define(stage, f"/World/Looks/{name}/Shader")
        sh.CreateIdAttr("UsdPreviewSurface")
        sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb))
        sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(rough)
        sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(metal)
        mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
        return mat

    def _omniglass(name: str, rgb: tuple[float, float, float], ior: float, depth: float) -> Any:
        mat = UsdShade.Material.Define(stage, f"/World/Looks/{name}")
        sh = UsdShade.Shader.Define(stage, f"/World/Looks/{name}/OmniGlassShader")
        sp = sh.GetPrim()
        sp.CreateAttribute("info:implementationSource", Sdf.ValueTypeNames.Token).Set("sourceAsset")
        sp.CreateAttribute("info:mdl:sourceAsset", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath("../assets/deps/mdl/OmniGlass.mdl"))
        sp.CreateAttribute("info:mdl:sourceAsset:subIdentifier", Sdf.ValueTypeNames.Token).Set("OmniGlass")
        sh.CreateInput("glass_color", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb))
        sh.CreateInput("frosting_roughness", Sdf.ValueTypeNames.Float).Set(0.015)
        sh.CreateInput("glass_ior", Sdf.ValueTypeNames.Float).Set(ior)
        sh.CreateInput("depth", Sdf.ValueTypeNames.Float).Set(depth)
        sh.CreateInput("thin_walled", Sdf.ValueTypeNames.Bool).Set(True)
        out = sh.CreateOutput("out", Sdf.ValueTypeNames.Token)
        for c in ("mdl:surface", "mdl:volume", "mdl:displacement"):
            mat.CreateOutput(c, Sdf.ValueTypeNames.Token).ConnectToSource(out)
        return mat

    mat_bench = _pbr("BenchWhite", (0.76, 0.79, 0.83), 0.44, 0.02)
    mat_trim = _pbr("BenchTrimDark", (0.18, 0.21, 0.25), 0.42, 0.12)
    mat_backdrop = _pbr("BilibiliBlueWall", (0.04, 0.44, 0.74), 0.68, 0.0)
    mat_floor = _pbr("LabFloor", (0.72, 0.75, 0.79), 0.55, 0.0)
    mat_chrome = _pbr("TapChrome", (0.84, 0.86, 0.89), 0.16, 0.92)
    mat_amber_latex = _pbr("AmberLatexHose", (0.76, 0.43, 0.13), 0.38, 0.0)

    # Vivid translucent royal-purple KMnO4 shader (100% readable through clear OmniGlass!)
    mat_purple_liq = UsdShade.Material.Define(stage, "/World/Looks/PurpleKMnO4")
    p_sh = UsdShade.Shader.Define(stage, "/World/Looks/PurpleKMnO4/Shader")
    p_sh.CreateIdAttr("UsdPreviewSurface")
    p_sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.56, 0.03, 0.72))
    p_sh.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.26, 0.01, 0.36))
    p_sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.08)
    p_sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(0.88)
    mat_purple_liq.CreateSurfaceOutput().ConnectToSource(p_sh.ConnectableAPI(), "surface")

    # Glistening clear distillate / hanging condensate droplet shader
    mat_clear_liq = UsdShade.Material.Define(stage, "/World/Looks/ClearDistillate")
    c_sh = UsdShade.Shader.Define(stage, "/World/Looks/ClearDistillate/Shader")
    c_sh.CreateIdAttr("UsdPreviewSurface")
    c_sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.88, 0.97, 1.00))
    c_sh.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.10, 0.16, 0.22))
    c_sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.04)
    c_sh.CreateInput("ior", Sdf.ValueTypeNames.Float).Set(1.334)
    c_sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(0.76)
    mat_clear_liq.CreateSurfaceOutput().ConnectToSource(c_sh.ConnectableAPI(), "surface")

    # White benchtop (top at z = 0.750 m)
    bench = UsdGeom.Cube.Define(stage, "/World/Environment/LabBenchTop")
    bench.CreateSizeAttr(1.0)
    bxf = UsdGeom.Xformable(bench)
    bxf.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.02, 0.730))
    bxf.AddScaleOp().Set(Gf.Vec3f(1.56, 0.76, 0.040))
    UsdShade.MaterialBindingAPI.Apply(bench.GetPrim()).Bind(mat_bench)
    UsdPhysics.CollisionAPI.Apply(bench.GetPrim()).CreateCollisionEnabledAttr(True)

    # Front phenolic edge trim & cabinet base
    trim = UsdGeom.Cube.Define(stage, "/World/Environment/LabBenchEdgeTrim")
    trim.CreateSizeAttr(1.0)
    txf = UsdGeom.Xformable(trim)
    txf.AddTranslateOp().Set(Gf.Vec3d(0.0, -0.362, 0.730))
    txf.AddScaleOp().Set(Gf.Vec3f(1.565, 0.008, 0.041))
    UsdShade.MaterialBindingAPI.Apply(trim.GetPrim()).Bind(mat_trim)

    cabinet = UsdGeom.Cube.Define(stage, "/World/Environment/LabBenchCabinet")
    cabinet.CreateSizeAttr(1.0)
    cxf = UsdGeom.Xformable(cabinet)
    cxf.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.05, 0.355))
    cxf.AddScaleOp().Set(Gf.Vec3f(1.48, 0.68, 0.71))
    UsdShade.MaterialBindingAPI.Apply(cabinet.GetPrim()).Bind(mat_trim)

    # Sky-blue teaching studio backdrop behind the rear robot arms (y = +0.96 m)
    wall = UsdGeom.Cube.Define(stage, "/World/Environment/TeachingBlueWall")
    wall.CreateSizeAttr(1.0)
    wxf = UsdGeom.Xformable(wall)
    wxf.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.96, 1.15))
    wxf.AddScaleOp().Set(Gf.Vec3f(3.20, 0.02, 2.30))
    UsdShade.MaterialBindingAPI.Apply(wall.GetPrim()).Bind(mat_backdrop)

    floor_p = UsdGeom.Cube.Define(stage, "/World/Environment/Floor")
    floor_p.CreateSizeAttr(1.0)
    fxf = UsdGeom.Xformable(floor_p)
    fxf.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, -0.01))
    fxf.AddScaleOp().Set(Gf.Vec3f(4.0, 4.0, 0.02))
    UsdShade.MaterialBindingAPI.Apply(floor_p.GetPrim()).Bind(mat_floor)

    # Right Swan-Neck Lab Water Tap (+0.390, -0.185) & Left Brushed-Steel Sink Drain Cup (-0.390, -0.185)
    tap_col = UsdGeom.Cylinder.Define(stage, "/World/Environment/WaterTapRiser")
    tap_col.CreateRadiusAttr(0.009)
    tap_col.CreateHeightAttr(0.145)
    UsdGeom.Xformable(tap_col).AddTranslateOp().Set(Gf.Vec3d(0.425, -0.185, 0.8225))
    UsdShade.MaterialBindingAPI.Apply(tap_col.GetPrim()).Bind(mat_chrome)

    tap_arm = UsdGeom.Cylinder.Define(stage, "/World/Environment/WaterTapArm")
    tap_arm.CreateRadiusAttr(0.006)
    tap_arm.CreateHeightAttr(0.042)
    taxf = UsdGeom.Xformable(tap_arm)
    taxf.AddTranslateOp().Set(Gf.Vec3d(0.406, -0.185, 0.888))
    taxf.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(0.7071068, 0.0, 0.7071068, 0.0))
    UsdShade.MaterialBindingAPI.Apply(tap_arm.GetPrim()).Bind(mat_chrome)

    tap_noz = UsdGeom.Cylinder.Define(stage, "/World/Environment/WaterTapNozzle")
    tap_noz.CreateRadiusAttr(0.0046)
    tap_noz.CreateHeightAttr(0.036)
    UsdGeom.Xformable(tap_noz).AddTranslateOp().Set(Gf.Vec3d(0.390, -0.185, 0.872))
    UsdShade.MaterialBindingAPI.Apply(tap_noz.GetPrim()).Bind(mat_chrome)

    drain = UsdGeom.Cylinder.Define(stage, "/World/Environment/SinkDrainCup")
    drain.CreateRadiusAttr(0.020)
    drain.CreateHeightAttr(0.055)
    UsdGeom.Xformable(drain).AddTranslateOp().Set(Gf.Vec3d(-0.390, -0.185, 0.7775))
    UsdShade.MaterialBindingAPI.Apply(drain.GetPrim()).Bind(mat_chrome)

    # Studio 4-Point Softbox + Rim Lighting for crystal-clear OmniGlass refraction against the blue studio backdrop
    UsdGeom.Scope.Define(stage, "/World/Lights")
    dome = UsdLux.DomeLight.Define(stage, "/World/Lights/LabStudioDome")
    dome.CreateIntensityAttr(520.0)
    dome.CreateColorAttr(Gf.Vec3f(0.95, 0.97, 1.0))

    lights = [
        ("KeyLightFrontLeft", (-0.85, -1.15, 1.85), 0.36, 4200.0, (1.00, 0.98, 0.95)),
        ("FillLightFrontRight", (0.95, -1.05, 1.75), 0.38, 2800.0, (0.94, 0.97, 1.00)),
        ("TopGlassSpecular", (0.00, -0.25, 2.05), 0.42, 3100.0, (0.98, 0.99, 1.00)),
        ("BackRimGlass", (0.00, 0.32, 1.58), 0.28, 2200.0, (0.95, 0.99, 1.00)),
    ]
    for lname, lpos, lrad, lint, lcol in lights:
        sl = UsdLux.SphereLight.Define(stage, f"/World/Lights/{lname}")
        UsdGeom.Xformable(sl).AddTranslateOp().Set(Gf.Vec3d(*lpos))
        sl.CreateRadiusAttr(lrad)
        sl.CreateNormalizeAttr(True)
        sl.CreateIntensityAttr(lint)
        sl.CreateColorAttr(Gf.Vec3f(*lcol))
        sl.GetPrim().CreateAttribute("visibleInPrimaryRay", Sdf.ValueTypeNames.Bool).Set(False)

    # Rear-Standing Dual Franka Arms (+Y side, facing -Y toward bench & front camera -> 0% foreground occlusion!)
    rear_bases = cad_specs["layout"]["rear_robot_bases"]
    for side, rkey in (("left", "franka_left"), ("right", "franka_right")):
        bxyz = rear_bases[rkey]["xyz"]
        bwxyz = rear_bases[rkey]["wxyz"]
        ped = UsdGeom.Xform.Define(stage, f"/World/pedestal_{side}")
        ped.GetPrim().GetReferences().AddReference("../assets/robot_pedestal/asset.usd", "/World/robot_pedestal")
        ped.AddTranslateOp().Set(Gf.Vec3d(float(bxyz[0]), float(bxyz[1]), -0.005))
        ped.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(1.0, 0.0, 0.0, 0.0))

        arm = UsdGeom.Xform.Define(stage, f"/World/{rkey}")
        arm.GetPrim().GetReferences().AddReference("../assets/franka_panda/asset.usd", "/World/franka_panda")
        arm.AddTranslateOp().Set(Gf.Vec3d(*map(float, bxyz)))
        arm.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(*map(float, bwxyz)))

    # Reference all 20 M1 OmniGlass instruments at their staged bench poses
    UsdGeom.Scope.Define(stage, "/World/Instruments")
    instances_list: list[dict[str, Any]] = []
    for aid, cinfo in cad_specs["components"].items():
        iprim = UsdGeom.Xform.Define(stage, f"/World/Instruments/{aid}")
        iprim.GetPrim().GetReferences().AddReference(f"../assets/instruments/{aid}.usda", f"/{aid}")
        sxyz = cinfo["staged_xyz"]
        swxyz = cinfo["staged_wxyz"]
        p_raw = iprim.GetPrim()
        t_attr = p_raw.GetAttribute("xformOp:translate")
        if t_attr and t_attr.IsValid():
            t_attr.Set(Gf.Vec3d(*map(float, sxyz)))
        else:
            iprim.AddTranslateOp().Set(Gf.Vec3d(*map(float, sxyz)))
        o_attr = p_raw.GetAttribute("xformOp:orient")
        if o_attr and o_attr.IsValid():
            o_attr.Set(Gf.Quatd(*map(float, swxyz)))
        else:
            iprim.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(*map(float, swxyz)))
        instances_list.append(
            {
                "id": aid,
                "prim_path": f"/World/Instruments/{aid}",
                "staged_xyz": sxyz,
                "staged_wxyz": swxyz,
                "assembled_xyz": cinfo["assembled_xyz"],
                "assembled_wxyz": cinfo["assembled_wxyz"],
            }
        )

    # Two 64-Segment Smooth Amber Latex Cooling Hoses (1536 vertices each, driven by zero-penetration Cosserat solver)
    hose_pts, hose_tris = _make_tube_skin_topology(n_rings=64, n_circ=24, r_outer=0.0052)
    UsdGeom.Scope.Define(stage, "/World/CoolingHoses")
    for hname in ("Hose_Inlet_Lower", "Hose_Outlet_Upper"):
        hm = UsdGeom.Mesh.Define(stage, f"/World/CoolingHoses/{hname}")
        hm.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(float(p[0]), float(p[1]), float(p[2])) for p in hose_pts]))
        hm.CreateFaceVertexCountsAttr(Vt.IntArray([3] * len(hose_tris)))
        hm.CreateFaceVertexIndicesAttr(Vt.IntArray(hose_tris.reshape(-1).tolist()))
        hm.CreateNormalsAttr(Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 1.0)] * len(hose_pts)))
        hm.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
        hm.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        UsdShade.MaterialBindingAPI.Apply(hm.GetPrim()).Bind(mat_amber_latex)

    # Dynamic Fluid & Droplet Visuals (Flask purple solution, funnel pour stream, bulb condensate drop, receiver distillate drops + pool)
    UsdGeom.Scope.Define(stage, "/World/DynamicFluids")
    flk_liq = UsdGeom.Sphere.Define(stage, "/World/DynamicFluids/FlaskPurplePool")
    flk_liq.CreateRadiusAttr(0.0365)
    flxf = UsdGeom.Xformable(flk_liq)
    flxf.AddTranslateOp().Set(Gf.Vec3d(-0.180, 0.000, 0.922))
    flxf.AddScaleOp().Set(Gf.Vec3f(1.0, 1.0, 0.01))
    UsdGeom.Imageable(flk_liq).GetVisibilityAttr().Set(UsdGeom.Tokens.invisible)
    UsdShade.MaterialBindingAPI.Apply(flk_liq.GetPrim()).Bind(mat_purple_liq)

    rec_liq = UsdGeom.Cylinder.Define(stage, "/World/DynamicFluids/ReceiverClearPool")
    rec_liq.CreateRadiusAttr(0.030)
    rec_liq.CreateHeightAttr(0.012)
    rcxf = UsdGeom.Xformable(rec_liq)
    rcxf.AddTranslateOp().Set(Gf.Vec3d(0.215, 0.000, 0.838))
    rcxf.AddScaleOp().Set(Gf.Vec3f(1.0, 1.0, 0.01))
    UsdGeom.Imageable(rec_liq).GetVisibilityAttr().Set(UsdGeom.Tokens.invisible)
    UsdShade.MaterialBindingAPI.Apply(rec_liq.GetPrim()).Bind(mat_clear_liq)

    bulb_drop = UsdGeom.Sphere.Define(stage, "/World/DynamicFluids/BulbCondensateDrop")
    bulb_drop.CreateRadiusAttr(0.0036)
    UsdGeom.Xformable(bulb_drop).AddTranslateOp().Set(Gf.Vec3d(-0.180, -0.0025, 1.0645))
    UsdGeom.Imageable(bulb_drop).GetVisibilityAttr().Set(UsdGeom.Tokens.invisible)
    UsdShade.MaterialBindingAPI.Apply(bulb_drop.GetPrim()).Bind(mat_clear_liq)

    for di in range(18):
        sp = UsdGeom.Sphere.Define(stage, f"/World/DynamicFluids/PourDrop_{di:02d}")
        sp.CreateRadiusAttr(0.0038)
        UsdGeom.Xformable(sp).AddTranslateOp().Set(Gf.Vec3d(-0.180, 0.000, 1.180))
        UsdGeom.Imageable(sp).GetVisibilityAttr().Set(UsdGeom.Tokens.invisible)
        UsdShade.MaterialBindingAPI.Apply(sp.GetPrim()).Bind(mat_purple_liq)

    for di in range(6):
        dp = UsdGeom.Sphere.Define(stage, f"/World/DynamicFluids/DistillateDrop_{di:02d}")
        dp.CreateRadiusAttr(0.0035)
        UsdGeom.Xformable(dp).AddTranslateOp().Set(Gf.Vec3d(0.215, 0.000, 0.916))
        UsdGeom.Imageable(dp).GetVisibilityAttr().Set(UsdGeom.Tokens.invisible)
        UsdShade.MaterialBindingAPI.Apply(dp.GetPrim()).Bind(mat_clear_liq)

    # 5 Calibrated Cameras (1 Front Uncut Master + 4 Bilibili Red-Line Macro Close-ups)
    UsdGeom.Scope.Define(stage, "/World/Cameras")
    for cname, ccfg in V06_CAMERAS.items():
        cam = UsdGeom.Camera.Define(stage, f"/World/Cameras/{cname}")
        cam.CreateFocalLengthAttr().Set(float(ccfg["focal_mm"]))
        cam.CreateHorizontalApertureAttr().Set(20.955)
        cam.CreateVerticalApertureAttr().Set(11.787)
        cam.CreateClippingRangeAttr().Set(Gf.Vec2f(0.04, 50.0))
        cq = _lookat_quat_wxyz(ccfg["eye"], ccfg["target"])
        cxf_c = UsdGeom.Xformable(cam)
        cxf_c.AddTranslateOp().Set(Gf.Vec3d(*map(float, ccfg["eye"])))
        cxf_c.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(*map(float, cq)))

    stage.GetRootLayer().Save()

    # Package metadata & asset lock
    (pkg_root / "semantics").mkdir(parents=True, exist_ok=True)
    (pkg_root / "semantics" / "v06_scene_spec.json").write_text(
        json.dumps(
            {
                "schema_version": "distillation-v06-scene-spec/v1.0",
                "package_id": "distillation_v06_full_bilibili_sop",
                "reference_bvid": "BV17t4y1V7XH",
                "cameras": V06_CAMERAS,
                "cad_specs": cad_specs,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (pkg_root / "scene" / "instances.yaml").write_text(
        yaml.safe_dump({"schema_version": "scene-instances/v0.6", "instances": instances_list}, sort_keys=False),
        encoding="utf-8",
    )
    (pkg_root / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "scenario-package/v0.2",
                "package_id": "distillation_v06_full_bilibili_sop",
                "entrypoints": {"scene_usd": "scene/main.usda", "scene_spec": "semantics/v06_scene_spec.json"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    # Asset manifest & lock
    manifest_assets: list[dict[str, Any]] = []
    for aid in cad_specs["components"]:
        upath = inst_dir / f"{aid}.usda"
        manifest_assets.append(
            {
                "asset_id": aid,
                "role": "instrument",
                "asset_type": "usd",
                "canonical_usd": f"assets/instruments/{aid}.usda",
                "license": "Apache-2.0",
                "sha256": compute_sha256(upath),
            }
        )
    for sys_id, rel_u in (("franka_panda", "assets/franka_panda/asset.usd"), ("robot_pedestal", "assets/robot_pedestal/asset.usd")):
        manifest_assets.append(
            {
                "asset_id": sys_id,
                "role": "robot",
                "asset_type": "usd",
                "canonical_usd": rel_u,
                "license": "Apache-2.0",
                "sha256": compute_sha256(pkg_root / rel_u),
            }
        )
    (assets_root / "asset_manifest.yaml").write_text(
        yaml.safe_dump({"schema_version": "asset-manifest/v0.2", "assets": manifest_assets}, sort_keys=False),
        encoding="utf-8",
    )
    write_asset_lock(pkg_root, generate_asset_lock(pkg_root, lock_id="distillation_v06_lock"))
    return {
        "package_root": str(pkg_root),
        "scene_usd": str(scene_path),
        "scene_sha256": compute_sha256(scene_path),
        "instrument_count": len(instances_list),
        "camera_count": len(V06_CAMERAS),
    }

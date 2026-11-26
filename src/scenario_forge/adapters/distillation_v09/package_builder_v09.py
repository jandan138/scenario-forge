"""Build the distillation_v09 Full S01-S12 One-Shot True-Dynamic OpenUSD Scene Package.

Unifies:
- `v0.7` Articulated Mechanisms:
  * `scissor_jack_blue_art001` & `scissor_jack_white_art001` (`BasePlate`, `TopPlatform`, rotary `Handwheel`)
  * `flask_clamp_2prong_art001` (`FixedLeftYoke`, `MovableRightJaw`, rotary `ButterflyWingnut`) + open-upward `bosshead_left`
  * `condenser_clamp_3prong_art001` (`FixedLowerBase` below, `MovableUpperJaw` above, rotary `TopButterflyWingnut`) + open-upward `bosshead_right`
  * Dual 64x24 Amber Latex Cooling Hoses skinned live onto 48 dynamic PhysX 5 spherical-jointed links
- `v0.8` Standard-Taper Ground-Glass Method B Physics & Articulated POM Keck Clips:
  * All 4 ground-glass joints (`Flask 24/29`, `Head 15-deg Sidearm 24/29`, `Condenser Lower 15-deg 24/29`, `Head Top 19/26` for Funnel & Thermometer)
    exclusively use Method B internal radial micro-spring wedges for genuine push-in self-locking & twist-and-pull disassembly
  * Two 3-link articulated green POM Keck clips (`keck_clip_head_cond_art001`, `keck_clip_cond_tail_art001`)
  * Calibrated `thermometer_adapter_unit_v08` seating with `0.00 mm` mercury bulb upper-rim alignment at `z = 1.0800 m`
- Full `S01 -> S12` Bilibili `BV17t4y1V7XH` (`02:27 - 06:20`) 15-instrument kit including `long_stem_funnel`, `pour_beaker_100ml`,
  purple KMnO4 solution pour/fill, mercury bulb condensate drop, and clear distillate dripping.
"""

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


TH15 = math.radians(15.0)
Q15_WXYZ = [math.cos(0.5 * TH15), 0.0, math.sin(0.5 * TH15), 0.0]

V09_ROBOT_BASES: dict[str, dict[str, Any]] = {
    "franka_left": {
        "xyz": [-0.420, 0.360, 0.750],
        "yaw_deg": -62.0,
        "wxyz": [math.cos(math.radians(-31.0)), 0.0, 0.0, math.sin(math.radians(-31.0))],
    },
    "franka_right": {
        "xyz": [0.420, 0.360, 0.750],
        "yaw_deg": -118.0,
        "wxyz": [math.cos(math.radians(-59.0)), 0.0, 0.0, math.sin(math.radians(-59.0))],
    },
}

V09_CAMERAS: dict[str, dict[str, Any]] = {
    "Cam_Front_Master": {
        "eye": [0.000, -1.320, 1.095],
        "target": [0.000, -0.010, 0.985],
        "focal_mm": 22.5,
        "role": "master_uncut_front",
    },
    "Cam_Ortho_Side_Left": {
        "eye": [-0.900, 0.005, 1.065],
        "target": [-0.180, 0.005, 1.045],
        "focal_mm": 35.0,
        "role": "ortho_90deg_profile_left_column",
    },
    "Cam_Ortho_Side_Right": {
        "eye": [0.880, 0.005, 1.015],
        "target": [0.060, 0.005, 0.995],
        "focal_mm": 34.0,
        "role": "ortho_90deg_profile_right_train",
    },
    "Cam_Bosshead_Close": {
        "eye": [-0.215, -0.245, 1.045],
        "target": [-0.225, 0.035, 1.005],
        "focal_mm": 38.0,
        "role": "macro_01_bosshead_open_up",
    },
    "Cam_Clamp3Prong_Close": {
        "eye": [0.030, -0.355, 1.045],
        "target": [0.015, 0.005, 1.025],
        "focal_mm": 32.0,
        "role": "macro_02_clamp3prong_hoses",
    },
    "Cam_Thermometer_Bulb": {
        "eye": [-0.055, -0.255, 1.115],
        "target": [-0.176, 0.000, 1.092],
        "focal_mm": 44.0,
        "role": "macro_03_thermometer_bulb_flush",
    },
    "Cam_Receiver_Drip": {
        "eye": [0.215, -0.345, 0.935],
        "target": [0.205, 0.000, 0.895],
        "focal_mm": 34.0,
        "role": "macro_04_receiver_drip",
    },
    "Cam_JackBlue_Close": {
        "eye": [-0.045, -0.310, 0.885],
        "target": [-0.180, 0.025, 0.805],
        "focal_mm": 36.0,
        "role": "macro_jack_blue_handwheel",
    },
    "Cam_HeadFlask_Close": {
        "eye": [-0.045, -0.275, 1.065],
        "target": [-0.180, 0.000, 1.032],
        "focal_mm": 42.0,
        "role": "macro_head_flask_24_29_taper",
    },
    "Cam_FunnelPour_Close": {
        "eye": [-0.035, -0.335, 1.165],
        "target": [-0.165, 0.000, 1.135],
        "focal_mm": 34.0,
        "role": "macro_funnel_purple_pour",
    },
}


def _make_tube_skin_topology(n_rings: int = 64, n_circ: int = 24, r_outer: float = 0.0052) -> tuple[np.ndarray, np.ndarray]:
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


def build_distillation_v09_package(
    output_dir: Path | None = None,
    v06_assets_dir: Path | None = None,
    v07_mechanisms_dir: Path | None = None,
    v08_assets_dir: Path | None = None,
) -> dict[str, Any]:
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade, Vt

    repo_root = Path(__file__).resolve().parents[4]
    pkg_root = output_dir or (repo_root / "external_artifacts" / "distillation_v09_package" / "scenario_package")
    v06_root = v06_assets_dir or (repo_root.parent / "ConvertAsset" / "external_artifacts" / "distillation_v06_assets")
    v07_root = v07_mechanisms_dir or (repo_root.parent / "ConvertAsset" / "external_artifacts" / "distillation_v07_assets")
    v08_root = v08_assets_dir or (repo_root.parent / "ConvertAsset" / "external_artifacts" / "distillation_v08_assets")

    if pkg_root.exists():
        shutil.rmtree(pkg_root)
    assets_root = pkg_root / "assets"
    assets_root.mkdir(parents=True, exist_ok=True)

    shutil.copytree(v06_root / "deps", assets_root / "deps", dirs_exist_ok=True)
    cad_v06 = json.loads((v06_root / "v06_cad_specs.json").read_text(encoding="utf-8"))

    inst_dir = assets_root / "instruments"
    inst_dir.mkdir(parents=True, exist_ok=True)
    needed_v06_insts = (
        "iron_stand_left",
        "iron_stand_right",
        "bosshead_left",
        "bosshead_right",
        "heating_stirrer_bath",
        "round_bottom_flask_250ml",
        "distillation_head_75deg",
        "liebig_condenser_24_29",
        "vacuum_tail_adapter",
        "erlenmeyer_flask_150ml",
        "long_stem_funnel",
        "pour_beaker_100ml",
    )
    for aid in needed_v06_insts:
        shutil.copy2(v06_root / "instruments" / f"{aid}.usda", inst_dir / f"{aid}.usda")

    mech_v07 = json.loads((v07_root / "v07_mechanisms_manifest.json").read_text(encoding="utf-8"))
    mech_v08 = json.loads((v08_root / "v08_assets_manifest.json").read_text(encoding="utf-8"))

    link_meshes_dir = assets_root / "link_meshes"
    link_meshes_dir.mkdir(parents=True, exist_ok=True)
    for npz_f in sorted((v07_root / "link_meshes").glob("*.npz")):
        shutil.copy2(npz_f, link_meshes_dir / npz_f.name)
    for npz_f in sorted((v08_root / "link_meshes").glob("*.npz")):
        shutil.copy2(npz_f, link_meshes_dir / npz_f.name)

    mech_usd_dir = assets_root / "mechanisms_art001"
    mech_usd_dir.mkdir(parents=True, exist_ok=True)
    for mid, uinfo in mech_v07["simready_art001_usd"].items():
        shutil.copy2(Path(uinfo["usda_path"]), mech_usd_dir / f"{mid}.usda")

    vendor_franka_panda_assets(assets_root / "franka_panda")
    create_robot_pedestal_usd(assets_root / "robot_pedestal")

    scene_path = pkg_root / "scene" / "main.usda"
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(scene_path))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)

    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())

    phys_scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
    phys_scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(0.0, 0.0, -1.0))
    phys_scene.CreateGravityMagnitudeAttr().Set(9.81)
    pprim = phys_scene.GetPrim()
    pprim.CreateAttribute("physxScene:enableGPUDynamics", Sdf.ValueTypeNames.Bool, custom=True).Set(True)
    pprim.CreateAttribute("physxScene:enableCCD", Sdf.ValueTypeNames.Bool, custom=True).Set(True)
    pprim.CreateAttribute("physxScene:solverType", Sdf.ValueTypeNames.Token, custom=True).Set("TGS")
    pprim.CreateAttribute("physxScene:timeStepsPerSecond", Sdf.ValueTypeNames.UInt, custom=True).Set(240)

    UsdGeom.Scope.Define(stage, "/World/Environment")
    UsdGeom.Scope.Define(stage, "/World/Looks")

    def _pbr(name: str, rgb: tuple[float, float, float], rough: float, metal: float = 0.0, opacity: float = 1.0) -> Any:
        mat = UsdShade.Material.Define(stage, f"/World/Looks/{name}")
        sh = UsdShade.Shader.Define(stage, f"/World/Looks/{name}/Shader")
        sh.CreateIdAttr("UsdPreviewSurface")
        sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb))
        sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(rough)
        sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(metal)
        if opacity < 0.999:
            sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(opacity)
            sh.CreateInput("ior", Sdf.ValueTypeNames.Float).Set(1.48)
        mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
        return mat

    def _omniglass(name: str, rgb: tuple[float, float, float], ior: float = 1.474, frost: float = 0.015) -> Any:
        mat = UsdShade.Material.Define(stage, f"/World/Looks/{name}")
        sh = UsdShade.Shader.Define(stage, f"/World/Looks/{name}/OmniGlassShader")
        sp = sh.GetPrim()
        sp.CreateAttribute("info:implementationSource", Sdf.ValueTypeNames.Token).Set("sourceAsset")
        sp.CreateAttribute("info:mdl:sourceAsset", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath("../assets/deps/mdl/OmniGlass.mdl"))
        sp.CreateAttribute("info:mdl:sourceAsset:subIdentifier", Sdf.ValueTypeNames.Token).Set("OmniGlass")
        sh.CreateInput("glass_color", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb))
        sh.CreateInput("frosting_roughness", Sdf.ValueTypeNames.Float).Set(frost)
        sh.CreateInput("glass_ior", Sdf.ValueTypeNames.Float).Set(ior)
        sh.CreateInput("depth", Sdf.ValueTypeNames.Float).Set(0.002)
        sh.CreateInput("thin_walled", Sdf.ValueTypeNames.Bool).Set(True)
        out = sh.CreateOutput("out", Sdf.ValueTypeNames.Token)
        for c in ("mdl:surface", "mdl:volume", "mdl:displacement"):
            mat.CreateOutput(c, Sdf.ValueTypeNames.Token).ConnectToSource(out)
        fb = UsdShade.Shader.Define(stage, f"/World/Looks/{name}/PreviewFallback")
        fb.CreateIdAttr("UsdPreviewSurface")
        fb.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb))
        fb.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(frost)
        fb.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(0.22 if frost < 0.1 else 0.65)
        mat.CreateSurfaceOutput().ConnectToSource(fb.ConnectableAPI(), "surface")
        return mat

    mat_bench = _pbr("BenchWhite", (0.76, 0.79, 0.83), 0.45, 0.02)
    mat_trim = _pbr("BenchTrimDark", (0.18, 0.21, 0.25), 0.42, 0.12)
    mat_backdrop = _pbr("BilibiliBlueWall", (0.04, 0.43, 0.73), 0.68, 0.0)
    mat_floor = _pbr("LabFloor", (0.72, 0.75, 0.79), 0.55, 0.0)
    mat_chrome = _pbr("TapChrome", (0.84, 0.86, 0.89), 0.16, 0.92)
    mat_amber_latex = _pbr("AmberLatexHose", (0.76, 0.43, 0.13), 0.38, 0.0)

    # Vivid translucent royal-purple KMnO4 & glistening clear distillate shaders
    mat_purple_liq = UsdShade.Material.Define(stage, "/World/Looks/PurpleKMnO4")
    p_sh = UsdShade.Shader.Define(stage, "/World/Looks/PurpleKMnO4/Shader")
    p_sh.CreateIdAttr("UsdPreviewSurface")
    p_sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.56, 0.03, 0.72))
    p_sh.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.26, 0.01, 0.36))
    p_sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.08)
    p_sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(0.88)
    mat_purple_liq.CreateSurfaceOutput().ConnectToSource(p_sh.ConnectableAPI(), "surface")

    mat_clear_liq = UsdShade.Material.Define(stage, "/World/Looks/ClearDistillate")
    c_sh = UsdShade.Shader.Define(stage, "/World/Looks/ClearDistillate/Shader")
    c_sh.CreateIdAttr("UsdPreviewSurface")
    c_sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.88, 0.97, 1.00))
    c_sh.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.10, 0.16, 0.22))
    c_sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.04)
    c_sh.CreateInput("ior", Sdf.ValueTypeNames.Float).Set(1.334)
    c_sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(0.76)
    mat_clear_liq.CreateSurfaceOutput().ConnectToSource(c_sh.ConnectableAPI(), "surface")

    mech_mats = {
        "stainless_steel": _pbr("MechStainless", (0.78, 0.80, 0.84), 0.20, 0.92),
        "cast_blue": _pbr("MechCastBlue", (0.10, 0.26, 0.50), 0.38, 0.28),
        "enamel_blue": _pbr("MechEnamelBlue", (0.06, 0.36, 0.74), 0.28, 0.12),
        "enamel_white": _pbr("MechEnamelWhite", (0.91, 0.93, 0.96), 0.30, 0.04),
        "red_rubber": _pbr("MechCrimsonRubber", (0.64, 0.06, 0.05), 0.66, 0.00),
        "dark_rubber": _pbr("MechDarkRubber", (0.09, 0.10, 0.12), 0.52, 0.05),
        "knurled_knob_red": _pbr("MechKnobRed", (0.78, 0.08, 0.08), 0.32, 0.08),
        "keck_green": _pbr("KeckClipGreen", (0.05, 0.68, 0.26), 0.26, 0.00),
        "ptfe_white": _pbr("PTFEWhite", (0.95, 0.96, 0.98), 0.32, 0.00),
        "mercury_silver": _pbr("MercurySilver", (0.91, 0.93, 0.96), 0.04, 0.98),
        "frosted_glass": _omniglass("FrostedTaperGlass", (0.94, 0.97, 1.00), 1.474, 0.34),
        "clear_glass": _omniglass("ClearStemGlass", (0.985, 0.996, 1.00), 1.474, 0.015),
    }

    # Benchtop (z_top = 0.750 m), edge trim, cabinet, surround blue teaching walls, floor, tap & drain
    bench = UsdGeom.Cube.Define(stage, "/World/Environment/LabBenchTop")
    bench.CreateSizeAttr(1.0)
    bxf = UsdGeom.Xformable(bench)
    bxf.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.02, 0.730))
    bxf.AddScaleOp().Set(Gf.Vec3f(1.56, 0.76, 0.040))
    UsdShade.MaterialBindingAPI.Apply(bench.GetPrim()).Bind(mat_bench)
    UsdPhysics.CollisionAPI.Apply(bench.GetPrim()).CreateCollisionEnabledAttr(True)

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

    for wname, wpos, wscale in (
        ("TeachingBlueWallRear", (0.0, 1.05, 1.15), (3.20, 0.02, 2.30)),
        ("TeachingBlueWallRight", (1.28, 0.10, 1.15), (0.02, 2.40, 2.30)),
        ("TeachingBlueWallLeft", (-1.28, 0.10, 1.15), (0.02, 2.40, 2.30)),
    ):
        wall = UsdGeom.Cube.Define(stage, f"/World/Environment/{wname}")
        wall.CreateSizeAttr(1.0)
        wxf = UsdGeom.Xformable(wall)
        wxf.AddTranslateOp().Set(Gf.Vec3d(*wpos))
        wxf.AddScaleOp().Set(Gf.Vec3f(*wscale))
        UsdShade.MaterialBindingAPI.Apply(wall.GetPrim()).Bind(mat_backdrop)

    floor_p = UsdGeom.Cube.Define(stage, "/World/Environment/Floor")
    floor_p.CreateSizeAttr(1.0)
    fxf = UsdGeom.Xformable(floor_p)
    fxf.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, -0.01))
    fxf.AddScaleOp().Set(Gf.Vec3f(4.0, 4.0, 0.02))
    UsdShade.MaterialBindingAPI.Apply(floor_p.GetPrim()).Bind(mat_floor)
    UsdPhysics.CollisionAPI.Apply(floor_p.GetPrim()).CreateCollisionEnabledAttr(True)

    # Realistic Chemistry Lab Gooseneck Cold-Water Faucet (right: blue valve + brass barb nozzle @ x=+0.390, y=-0.245, z=0.855)
    mat_brass_tap = _pbr("LabBrassBarb", (0.80, 0.64, 0.24), 0.22, 0.88)
    mat_pp_sink = _pbr("LabDarkPPSink", (0.12, 0.14, 0.17), 0.48, 0.04)
    mat_sil_mat = _pbr("LabAntiRollSiliconeMat", (0.14, 0.34, 0.56), 0.68, 0.00)

    tap_base = UsdGeom.Cylinder.Define(stage, "/World/Environment/WaterTapBaseFlange")
    tap_base.CreateRadiusAttr(0.022)
    tap_base.CreateHeightAttr(0.012)
    UsdGeom.Xformable(tap_base).AddTranslateOp().Set(Gf.Vec3d(0.425, -0.245, 0.756))
    UsdShade.MaterialBindingAPI.Apply(tap_base.GetPrim()).Bind(mat_chrome)

    tap_col = UsdGeom.Cylinder.Define(stage, "/World/Environment/WaterTapRiser")
    tap_col.CreateRadiusAttr(0.010)
    tap_col.CreateHeightAttr(0.155)
    UsdGeom.Xformable(tap_col).AddTranslateOp().Set(Gf.Vec3d(0.425, -0.245, 0.8275))
    UsdShade.MaterialBindingAPI.Apply(tap_col.GetPrim()).Bind(mat_chrome)

    tap_valve = UsdGeom.Cube.Define(stage, "/World/Environment/WaterTapBlueColdValve")
    tap_valve.CreateSizeAttr(1.0)
    tvxf = UsdGeom.Xformable(tap_valve)
    tvxf.AddTranslateOp().Set(Gf.Vec3d(0.448, -0.245, 0.805))
    tvxf.AddScaleOp().Set(Gf.Vec3f(0.036, 0.012, 0.012))
    UsdShade.MaterialBindingAPI.Apply(tap_valve.GetPrim()).Bind(mech_mats["enamel_blue"])

    tap_arm = UsdGeom.Cylinder.Define(stage, "/World/Environment/WaterTapArm")
    tap_arm.CreateRadiusAttr(0.007)
    tap_arm.CreateHeightAttr(0.044)
    taxf = UsdGeom.Xformable(tap_arm)
    taxf.AddTranslateOp().Set(Gf.Vec3d(0.406, -0.245, 0.896))
    taxf.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(0.7071068, 0.0, 0.7071068, 0.0))
    UsdShade.MaterialBindingAPI.Apply(tap_arm.GetPrim()).Bind(mat_chrome)

    tap_noz = UsdGeom.Cylinder.Define(stage, "/World/Environment/WaterTapNozzle")
    tap_noz.CreateRadiusAttr(0.0048)
    tap_noz.CreateHeightAttr(0.044)
    UsdGeom.Xformable(tap_noz).AddTranslateOp().Set(Gf.Vec3d(0.390, -0.245, 0.874))
    UsdShade.MaterialBindingAPI.Apply(tap_noz.GetPrim()).Bind(mat_brass_tap)

    # Embedded Black PP Lab Cup Sink (left: drains outlet hose cleanly into recessed basin @ x=-0.390, y=-0.245, 30mm clear of bath!)
    sink_rim = UsdGeom.Cube.Define(stage, "/World/Environment/LabPPDrainSinkRim")
    sink_rim.CreateSizeAttr(1.0)
    srxf = UsdGeom.Xformable(sink_rim)
    srxf.AddTranslateOp().Set(Gf.Vec3d(-0.390, -0.245, 0.754))
    srxf.AddScaleOp().Set(Gf.Vec3f(0.115, 0.095, 0.008))
    UsdShade.MaterialBindingAPI.Apply(sink_rim.GetPrim()).Bind(mat_pp_sink)

    drain = UsdGeom.Cylinder.Define(stage, "/World/Environment/SinkDrainCup")
    drain.CreateRadiusAttr(0.032)
    drain.CreateHeightAttr(0.022)
    UsdGeom.Xformable(drain).AddTranslateOp().Set(Gf.Vec3d(-0.390, -0.245, 0.761))
    UsdShade.MaterialBindingAPI.Apply(drain.GetPrim()).Bind(mat_pp_sink)

    strainer = UsdGeom.Cylinder.Define(stage, "/World/Environment/SinkDrainStrainer")
    strainer.CreateRadiusAttr(0.015)
    strainer.CreateHeightAttr(0.003)
    UsdGeom.Xformable(strainer).AddTranslateOp().Set(Gf.Vec3d(-0.390, -0.245, 0.772))
    UsdShade.MaterialBindingAPI.Apply(strainer.GetPrim()).Bind(mat_chrome)

    # Standardized Organic-Lab Anti-Roll Silicone Staging Mats (non-colliding 1.6 mm pads framing glassware zones)
    for mname, mpos, mscale in (
        ("StagingMat_LeftGlassware", (-0.415, -0.075, 0.7508), (0.24, 0.22, 0.0016)),
        ("StagingMat_CenterCondenser", (0.020, -0.105, 0.7508), (0.28, 0.10, 0.0016)),
        ("StagingMat_RightReceiverReagent", (0.395, -0.045, 0.7508), (0.24, 0.20, 0.0016)),
    ):
        sm = UsdGeom.Cube.Define(stage, f"/World/Environment/{mname}")
        sm.CreateSizeAttr(1.0)
        sxf = UsdGeom.Xformable(sm)
        sxf.AddTranslateOp().Set(Gf.Vec3d(*mpos))
        sxf.AddScaleOp().Set(Gf.Vec3f(*mscale))
        UsdShade.MaterialBindingAPI.Apply(sm.GetPrim()).Bind(mat_sil_mat)

    # Studio Lighting
    UsdGeom.Scope.Define(stage, "/World/Lights")
    dome = UsdLux.DomeLight.Define(stage, "/World/Lights/LabStudioDome")
    dome.CreateIntensityAttr(540.0)
    dome.CreateColorAttr(Gf.Vec3f(0.95, 0.97, 1.0))
    for lname, lpos, lrad, lint, lcol in (
        ("KeyLightFrontLeft", (-0.85, -1.15, 1.85), 0.36, 4100.0, (1.00, 0.98, 0.95)),
        ("FillLightFrontRight", (0.95, -1.05, 1.75), 0.38, 2900.0, (0.94, 0.97, 1.00)),
        ("TopGlassSpecular", (0.00, -0.20, 2.05), 0.42, 3000.0, (0.98, 0.99, 1.00)),
        ("SideProfileFill", (-0.95, 0.25, 1.45), 0.32, 2200.0, (0.96, 0.98, 1.00)),
    ):
        sl = UsdLux.SphereLight.Define(stage, f"/World/Lights/{lname}")
        UsdGeom.Xformable(sl).AddTranslateOp().Set(Gf.Vec3d(*lpos))
        sl.CreateRadiusAttr(lrad)
        sl.CreateNormalizeAttr(True)
        sl.CreateIntensityAttr(lint)
        sl.CreateColorAttr(Gf.Vec3f(*lcol))
        sl.GetPrim().CreateAttribute("visibleInPrimaryRay", Sdf.ValueTypeNames.Bool).Set(False)

    # Diagonal Rear-Flank Dual Franka Pandas (`0%` front occlusion!)
    for side, rkey in (("left", "franka_left"), ("right", "franka_right")):
        bxyz = V09_ROBOT_BASES[rkey]["xyz"]
        bwxyz = V09_ROBOT_BASES[rkey]["wxyz"]
        ped = UsdGeom.Xform.Define(stage, f"/World/pedestal_{side}")
        ped.GetPrim().GetReferences().AddReference("../assets/robot_pedestal/asset.usd", "/World/robot_pedestal")
        ped.AddTranslateOp().Set(Gf.Vec3d(float(bxyz[0]), float(bxyz[1]), -0.005))
        ped.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(1.0, 0.0, 0.0, 0.0))

        arm = UsdGeom.Xform.Define(stage, f"/World/{rkey}")
        arm.GetPrim().GetReferences().AddReference("../assets/franka_panda/asset.usd", "/World/franka_panda")
        arm.AddTranslateOp().Set(Gf.Vec3d(*map(float, bxyz)))
        arm.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(*map(float, bwxyz)))

    # Reference All Staged Lab Instruments at `t = 0` (`S01` initial bench layout)
    UsdGeom.Scope.Define(stage, "/World/Instruments")
    initial_inst_poses: dict[str, tuple[list[float], list[float]]] = {
        "iron_stand_left": ([-0.255, 0.075, 0.750], [1.0, 0.0, 0.0, 0.0]),
        "bosshead_left": ([-0.255, 0.075, 0.996], [1.0, 0.0, 0.0, 0.0]),
        "iron_stand_right": ([0.0866, 0.112, 0.750], [1.0, 0.0, 0.0, 0.0]),
        "bosshead_right": ([0.0866, 0.085, 1.021], [1.0, 0.0, 0.0, 0.0]),
        "heating_stirrer_bath": ([-0.180, 0.000, 0.8165], [1.0, 0.0, 0.0, 0.0]),
        "round_bottom_flask_250ml": ([-0.455, -0.020, 0.793], [1.0, 0.0, 0.0, 0.0]),
        "distillation_head_75deg": ([-0.335, -0.115, 0.785], [1.0, 0.0, 0.0, 0.0]),
        "liebig_condenser_24_29": ([0.020, -0.105, 0.808], [1.0, 0.0, 0.0, 0.0]),
        "vacuum_tail_adapter": ([0.310, 0.015, 0.855], [1.0, 0.0, 0.0, 0.0]),
        "erlenmeyer_flask_150ml": ([0.455, 0.015, 0.750], [1.0, 0.0, 0.0, 0.0]),
        "long_stem_funnel": ([-0.465, -0.135, 0.862], [1.0, 0.0, 0.0, 0.0]),
        "pour_beaker_100ml": ([0.445, -0.105, 0.792], [1.0, 0.0, 0.0, 0.0]),
    }
    for aid, (pos, wxyz) in initial_inst_poses.items():
        xf = UsdGeom.Xform.Define(stage, f"/World/Instruments/{aid}")
        xf.GetPrim().GetReferences().AddReference(f"../assets/instruments/{aid}.usda", f"/{aid}")
        tr_attr = xf.GetPrim().GetAttribute("xformOp:translate")
        if tr_attr and tr_attr.IsValid():
            tr_attr.Set(Gf.Vec3d(*map(float, pos)))
        else:
            xf.AddTranslateOp().Set(Gf.Vec3d(*map(float, pos)))
        or_attr = xf.GetPrim().GetAttribute("xformOp:orient")
        if or_attr and or_attr.IsValid():
            or_attr.Set(Gf.Quatd(*map(float, wxyz)))
        else:
            xf.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(*map(float, wxyz)))

    def _populate_npz_visuals(parent_path: str, npz_file: Path, mat_remap: dict[str, str] | None = None) -> None:
        with np.load(npz_file, allow_pickle=False) as z:
            for sname in [str(s) for s in z["submesh_names"]]:
                v = z[f"{sname}__verts"]
                f = z[f"{sname}__tris"]
                n = z[f"{sname}__norms"]
                uv = z[f"{sname}__uvs"]
                m = UsdGeom.Mesh.Define(stage, f"{parent_path}/Vis_{sname}")
                m.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(v))
                m.CreateFaceVertexCountsAttr(Vt.IntArray([3] * len(f)))
                m.CreateFaceVertexIndicesAttr(Vt.IntArray(f.reshape(-1).tolist()))
                m.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(n))
                m.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
                pv = UsdGeom.PrimvarsAPI(m).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex)
                pv.Set(Vt.Vec2fArray.FromNumpy(uv))
                mkey = mat_remap.get(sname, sname) if mat_remap else sname
                UsdShade.MaterialBindingAPI.Apply(m.GetPrim()).Bind(mech_mats.get(mkey, mat_chrome))

    # Calibrated Screw-Cap Mercury Thermometer Unit (`/World/Instruments/thermometer_adapter_unit_v08`)
    th_xf = UsdGeom.Xform.Define(stage, "/World/Instruments/thermometer_adapter_unit_v08")
    th_xf.AddTranslateOp().Set(Gf.Vec3d(-0.335, 0.025, 0.855))
    th_xf.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(1.0, 0.0, 0.0, 0.0))
    _populate_npz_visuals(
        "/World/Instruments/thermometer_adapter_unit_v08",
        link_meshes_dir / "thermometer_adapter_unit_v08.npz",
    )

    # 6 Articulated Lab Mechanisms (`2 Scissor Jacks + 2 Clamps + 2 Green POM Keck Clips`)
    UsdGeom.Scope.Define(stage, "/World/Mechanisms")
    u15 = np.array([math.cos(TH15), 0.0, -math.sin(TH15)], dtype=np.float64)
    n15 = np.array([math.sin(TH15), 0.0, +math.cos(TH15)], dtype=np.float64)
    clamp3_pos = np.array([0.022844, 0.0, 1.033648], dtype=np.float64) + 0.048 * u15 - 0.0038 * n15

    mech_specs: dict[str, dict[str, Any]] = {
        "scissor_jack_blue_art001": {
            "base_xyz": [-0.180, 0.000, 0.750],
            "base_wxyz": [1.0, 0.0, 0.0, 0.0],
            "mat_remap": None,
            "links": {
                "BasePlate": ("scissor_jack_blue_art001__BasePlate.npz", [0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]),
                "TopPlatform": ("scissor_jack_blue_art001__TopPlatform.npz", [0.0, 0.0, 0.062], [1.0, 0.0, 0.0, 0.0]),
                "Handwheel": ("scissor_jack_blue_art001__Handwheel.npz", [0.0, 0.088, 0.035], [1.0, 0.0, 0.0, 0.0]),
            },
        },
        "scissor_jack_white_art001": {
            "base_xyz": [0.215, 0.000, 0.750],
            "base_wxyz": [1.0, 0.0, 0.0, 0.0],
            "mat_remap": {"enamel_blue": "enamel_white"},
            "links": {
                "BasePlate": ("scissor_jack_blue_art001__BasePlate.npz", [0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]),
                "TopPlatform": ("scissor_jack_blue_art001__TopPlatform.npz", [0.0, 0.0, 0.040], [1.0, 0.0, 0.0, 0.0]),
                "Handwheel": ("scissor_jack_blue_art001__Handwheel.npz", [0.0, 0.088, 0.026], [1.0, 0.0, 0.0, 0.0]),
            },
        },
        "flask_clamp_2prong_art001": {
            "base_xyz": [-0.180, 0.000, 0.996],
            "base_wxyz": [1.0, 0.0, 0.0, 0.0],
            "mat_remap": None,
            "links": {
                "FixedLeftYoke": ("flask_clamp_2prong_art001__FixedLeftYoke.npz", [0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]),
                "MovableRightJaw": ("flask_clamp_2prong_art001__MovableRightJaw.npz", [0.0, 0.024, 0.0], [1.0, 0.0, 0.0, 0.0]),
                "ButterflyWingnut": ("flask_clamp_2prong_art001__ButterflyWingnut.npz", [0.024, 0.044, 0.0], [1.0, 0.0, 0.0, 0.0]),
            },
        },
        "condenser_clamp_3prong_art001": {
            "base_xyz": [float(clamp3_pos[0]), float(clamp3_pos[1]), float(clamp3_pos[2])],
            "base_wxyz": Q15_WXYZ,
            "mat_remap": None,
            "links": {
                "FixedLowerBase": ("condenser_clamp_3prong_art001__FixedLowerBase.npz", [0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]),
                "MovableUpperJaw": ("condenser_clamp_3prong_art001__MovableUpperJaw.npz", [0.0, 0.024, 0.014], [1.0, 0.0, 0.0, 0.0]),
                "TopButterflyWingnut": ("condenser_clamp_3prong_art001__TopButterflyWingnut.npz", [0.0, 0.048, 0.018], [1.0, 0.0, 0.0, 0.0]),
            },
        },
    }

    for mid, mcfg in mech_specs.items():
        mroot = UsdGeom.Xform.Define(stage, f"/World/Mechanisms/{mid}")
        mroot.AddTranslateOp().Set(Gf.Vec3d(*map(float, mcfg["base_xyz"])))
        mroot.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(*map(float, mcfg["base_wxyz"])))
        for lid, (npz_name, lpos, lwxyz) in mcfg["links"].items():
            lxf = UsdGeom.Xform.Define(stage, f"/World/Mechanisms/{mid}/{lid}")
            lxf.AddTranslateOp().Set(Gf.Vec3d(*map(float, lpos)))
            lxf.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(*map(float, lwxyz)))
            _populate_npz_visuals(
                f"/World/Mechanisms/{mid}/{lid}",
                link_meshes_dir / npz_name,
                mat_remap=mcfg["mat_remap"],
            )

    # Dual 64x24 Amber Latex Cooling Hose visual meshes
    UsdGeom.Scope.Define(stage, "/World/CoolingHoses")
    h_pts, h_tris = _make_tube_skin_topology(64, 24, 0.0052)
    for hname in ("Hose_Inlet_Lower", "Hose_Outlet_Upper"):
        hm = UsdGeom.Mesh.Define(stage, f"/World/CoolingHoses/{hname}")
        hm.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(h_pts))
        hm.CreateFaceVertexCountsAttr(Vt.IntArray([3] * len(h_tris)))
        hm.CreateFaceVertexIndicesAttr(Vt.IntArray(h_tris.reshape(-1).tolist()))
        hm.CreateNormalsAttr(Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 1.0)] * len(h_pts)))
        hm.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
        UsdShade.MaterialBindingAPI.Apply(hm.GetPrim()).Bind(mat_amber_latex)

    # Dynamic Visual Fluid Pools & Droplets (`collisionEnabled = False` -> zero fake force on PhysX!)
    UsdGeom.Scope.Define(stage, "/World/DynamicFluids")
    flk_liq = UsdGeom.Sphere.Define(stage, "/World/DynamicFluids/FlaskPurplePool")
    flk_liq.CreateRadiusAttr(0.0365)
    flxf = UsdGeom.Xformable(flk_liq)
    flxf.AddTranslateOp().Set(Gf.Vec3d(-0.455, -0.020, 0.778))
    flxf.AddScaleOp().Set(Gf.Vec3f(1.0, 1.0, 0.01))
    UsdGeom.Imageable(flk_liq).GetVisibilityAttr().Set(UsdGeom.Tokens.invisible)
    UsdShade.MaterialBindingAPI.Apply(flk_liq.GetPrim()).Bind(mat_purple_liq)

    rec_liq = UsdGeom.Cylinder.Define(stage, "/World/DynamicFluids/ReceiverClearPool")
    rec_liq.CreateRadiusAttr(0.030)
    rec_liq.CreateHeightAttr(0.012)
    rcxf = UsdGeom.Xformable(rec_liq)
    rcxf.AddTranslateOp().Set(Gf.Vec3d(0.215, 0.000, 0.854))
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

    UsdGeom.Scope.Define(stage, "/World/Cameras")
    stage.GetRootLayer().Save()

    sem_dir = pkg_root / "semantics"
    sem_dir.mkdir(parents=True, exist_ok=True)
    scene_spec = {
        "schema_version": "distillation-v09-s01-s12-method-b-oneshot/v1.0",
        "package_id": "distillation_v09_s01_s12_method_b_oneshot",
        "reference_bvid": "BV17t4y1V7XH",
        "physx_hz": 240,
        "taper_method": "method_b_radial_micro_spring_only",
        "robot_bases": V09_ROBOT_BASES,
        "cameras": V09_CAMERAS,
        "staged_poses": {k: {"xyz": v[0], "wxyz": v[1]} for k, v in initial_inst_poses.items()},
        "taper_targets": {
            "bath_lifted_z_world": 0.8405,
            "flask_clamped_world": [-0.180, 0.000, 0.9400],
            "joint_01_head_seated_world": [-0.180, 0.000, 1.0260],
            "joint_02_sidearm_cone_world": [-0.097896, 0.000, 1.0660],
            "joint_02_condenser_seated_world": [0.022844, 0.000, 1.033648],
            "joint_03_cond_lower_cone_world": [0.143585, 0.000, 1.001296],
            "receiver_lifted_world": [0.215, 0.000, 0.8505],
            "funnel_seated_world": [-0.180, 0.000, 1.1380],
            "joint_04_thermo_seated_world": [-0.180, 0.000, 1.1320],
            "sidearm_bottom_lip_z_world": 1.0800,
            "thermometer_bulb_top_local_z": -0.0520,
        },
        "stages": cad_v06["stages"],
    }
    (sem_dir / "v09_scene_spec.json").write_text(json.dumps(scene_spec, indent=2), encoding="utf-8")

    (pkg_root / "task.yaml").write_text(
        yaml.safe_dump(
            {
                "task_id": "distillation_v09_s01_s12_method_b_oneshot",
                "physics_hz": 240,
                "taper_physics": "method_b_only",
                "anti_cheat_kinematic_manipulated_allowed": False,
                "anti_cheat_weld_joints_allowed": False,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (pkg_root / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "scenario-package/v0.2",
                "package_id": "distillation_v09_s01_s12_method_b_oneshot",
                "entrypoints": {"scene_usd": "scene/main.usda", "scene_spec": "semantics/v09_scene_spec.json"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    manifest_assets: list[dict[str, Any]] = []
    for aid in needed_v06_insts:
        up = inst_dir / f"{aid}.usda"
        manifest_assets.append(
            {
                "asset_id": aid,
                "role": "instrument",
                "asset_type": "usd",
                "canonical_usd": f"assets/instruments/{aid}.usda",
                "license": "Apache-2.0",
                "sha256": compute_sha256(up),
            }
        )
    for m_usda in sorted(mech_usd_dir.glob("*.usda")):
        manifest_assets.append(
            {
                "asset_id": m_usda.stem,
                "role": "articulated_mechanism",
                "asset_type": "usd",
                "canonical_usd": f"assets/mechanisms_art001/{m_usda.name}",
                "license": "Apache-2.0",
                "sha256": compute_sha256(m_usda),
            }
        )
    for sys_id, rel_u in (
        ("franka_panda", "assets/franka_panda/asset.usd"),
        ("robot_pedestal", "assets/robot_pedestal/asset.usd"),
    ):
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
    write_asset_lock(pkg_root, generate_asset_lock(pkg_root, lock_id="distillation_v09_lock"))
    return {
        "package_root": pkg_root.as_posix(),
        "scene_usd": scene_path.as_posix(),
        "scene_sha256": compute_sha256(scene_path),
        "camera_count": len(V09_CAMERAS),
        "stage_count": len(cad_v06["stages"]),
    }
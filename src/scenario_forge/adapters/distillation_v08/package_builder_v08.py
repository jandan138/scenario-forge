"""Build the distillation_v08 True-Dynamic 4-Taper-Joint & Articulated Keck Clip OpenUSD Scene Package.

Covers all 4 standard-taper ground-glass joints + green POM Keck clips + thermometer flush-bulb SOP red-line:
1. `joint_01_head_into_flask_24_29_vertical` (`S04`): 75-deg distillation head male 24/29 cone -> 250 mL flask female 24/29 socket.
2. `joint_02_condenser_to_sidearm_15deg_keck` (`S05`): Liebig condenser female 24/29 socket (+ dual live dynamic PhysX hoses) -> 15-deg sidearm male 24/29 cone + 3-prong clamp tightening + articulated green `keck_clip_head_cond_art001` snap-on!
3. `joint_03_tail_adapter_to_condenser_keck` (`S07`): Vacuum tail adapter female 24/29 socket -> condenser lower 15-deg male 24/29 cone + articulated green `keck_clip_cond_tail_art001` snap-lock holding tail suspended over 150 mL Erlenmeyer flask!
4. `joint_04_thermometer_screw_cap_flush_bulb` (`S09`): Calibrated screw-cap mercury thermometer unit -> distillation head top 19/26 female socket until mercury bulb top rim == sidearm bottom lip (`z = 1.0800 m`, `0.0 mm` flush SOP alignment!).
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


V08_ROBOT_BASES: dict[str, dict[str, Any]] = {
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

V08_CAMERAS: dict[str, dict[str, Any]] = {
    "Cam_Front_Master": {
        "eye": [-0.020, -1.180, 1.065],
        "target": [-0.020, 0.010, 1.015],
        "focal_mm": 26.0,
        "role": "front_master",
    },
    "Cam_Ortho_Side_Left": {
        "eye": [-0.880, 0.005, 1.075],
        "target": [-0.180, 0.005, 1.075],
        "focal_mm": 38.0,
        "role": "ortho_90deg_profile_left_column",
    },
    "Cam_Ortho_Side_Right": {
        "eye": [0.780, 0.005, 1.035],
        "target": [0.020, 0.005, 1.035],
        "focal_mm": 36.0,
        "role": "ortho_90deg_profile_15deg_train",
    },
    "Cam_Macro_Joint01_HeadFlask": {
        "eye": [-0.045, -0.265, 1.065],
        "target": [-0.180, 0.000, 1.032],
        "focal_mm": 44.0,
        "role": "macro_24_29_head_flask_taper",
    },
    "Cam_Macro_Joint02_HeadCondKeck": {
        "eye": [-0.020, -0.275, 1.115],
        "target": [-0.095, 0.005, 1.062],
        "focal_mm": 42.0,
        "role": "macro_15deg_condenser_taper_and_keck",
    },
    "Cam_Macro_Joint03_CondTailKeck": {
        "eye": [0.255, -0.280, 1.045],
        "target": [0.150, 0.005, 0.992],
        "focal_mm": 40.0,
        "role": "macro_tail_adapter_taper_and_keck",
    },
    "Cam_Macro_Joint04_ThermoBulb": {
        "eye": [-0.055, -0.255, 1.115],
        "target": [-0.176, 0.000, 1.098],
        "focal_mm": 44.0,
        "role": "macro_19_26_thermometer_and_flush_bulb",
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


def build_distillation_v08_package(
    output_dir: Path | None = None,
    v06_assets_dir: Path | None = None,
    v07_mechanisms_dir: Path | None = None,
    v08_assets_dir: Path | None = None,
) -> dict[str, Any]:
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade, Vt

    repo_root = Path(__file__).resolve().parents[4]
    pkg_root = output_dir or (repo_root / "external_artifacts" / "distillation_v08_package" / "scenario_package")
    v06_root = v06_assets_dir or (repo_root.parent / "ConvertAsset" / "external_artifacts" / "distillation_v06_assets")
    v07_root = v07_mechanisms_dir or (repo_root.parent / "ConvertAsset" / "external_artifacts" / "distillation_v07_assets")
    v08_root = v08_assets_dir or (repo_root.parent / "ConvertAsset" / "external_artifacts" / "distillation_v08_assets")

    if pkg_root.exists():
        shutil.rmtree(pkg_root)
    assets_root = pkg_root / "assets"
    assets_root.mkdir(parents=True, exist_ok=True)

    shutil.copytree(v06_root / "deps", assets_root / "deps", dirs_exist_ok=True)
    inst_dir = assets_root / "instruments"
    inst_dir.mkdir(parents=True, exist_ok=True)
    needed_v06_insts = (
        "iron_stand_left",
        "iron_stand_right",
        "scissor_jack_white",
        "heating_stirrer_bath",
        "round_bottom_flask_250ml",
        "distillation_head_75deg",
        "liebig_condenser_24_29",
        "vacuum_tail_adapter",
        "erlenmeyer_flask_150ml",
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
    shutil.copy2(
        Path(mech_v08["keck_clip_24_29_art001"]["simready_usd"]["usda_path"]),
        mech_usd_dir / "keck_clip_24_29_art001.usda",
    )

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

    mat_bench = _pbr("BenchWhite", (0.75, 0.78, 0.82), 0.46, 0.02)
    mat_trim = _pbr("BenchTrimDark", (0.18, 0.21, 0.25), 0.42, 0.12)
    mat_backdrop = _pbr("BilibiliBlueWall", (0.04, 0.42, 0.72), 0.68, 0.0)
    mat_floor = _pbr("LabFloor", (0.72, 0.75, 0.79), 0.55, 0.0)
    mat_chrome = _pbr("TapChrome", (0.84, 0.86, 0.89), 0.16, 0.92)
    mat_amber_latex = _pbr("AmberLatexHose", (0.76, 0.43, 0.13), 0.38, 0.0)

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
        "frosted_glass": _pbr("FrostedTaperGlass", (0.88, 0.92, 0.96), 0.36, 0.02, opacity=0.68),
        "clear_glass": _pbr("ClearStemGlass", (0.94, 0.98, 1.00), 0.04, 0.02, opacity=0.26),
    }

    # Benchtop, trim, cabinet, surround blue walls, floor, water tap & drain
    bench = UsdGeom.Cube.Define(stage, "/World/Environment/LabBenchTop")
    bench.CreateSizeAttr(1.0)
    bxf = UsdGeom.Xformable(bench)
    bxf.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.02, 0.730))
    bxf.AddScaleOp().Set(Gf.Vec3f(1.56, 0.76, 0.040))
    UsdShade.MaterialBindingAPI.Apply(bench.GetPrim()).Bind(mat_bench)
    UsdPhysics.CollisionAPI.Apply(bench.GetPrim()).CreateCollisionEnabledAttr(True)

    for wname, wpos, wscale in (
        ("TeachingBlueWallRear", (0.0, 1.05, 1.15), (3.20, 0.02, 2.30)),
        ("TeachingBlueWallRight", (1.25, 0.10, 1.15), (0.02, 2.40, 2.30)),
        ("TeachingBlueWallLeft", (-1.25, 0.10, 1.15), (0.02, 2.40, 2.30)),
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

    tap_col = UsdGeom.Cylinder.Define(stage, "/World/Environment/WaterTapRiser")
    tap_col.CreateRadiusAttr(0.009)
    tap_col.CreateHeightAttr(0.145)
    UsdGeom.Xformable(tap_col).AddTranslateOp().Set(Gf.Vec3d(0.425, -0.185, 0.8225))
    UsdShade.MaterialBindingAPI.Apply(tap_col.GetPrim()).Bind(mat_chrome)

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

    # Diagonal Rear-Flank Dual Frankas
    for side, rkey in (("left", "franka_left"), ("right", "franka_right")):
        bxyz = V08_ROBOT_BASES[rkey]["xyz"]
        bwxyz = V08_ROBOT_BASES[rkey]["wxyz"]
        ped = UsdGeom.Xform.Define(stage, f"/World/pedestal_{side}")
        ped.GetPrim().GetReferences().AddReference("../assets/robot_pedestal/asset.usd", "/World/robot_pedestal")
        ped.AddTranslateOp().Set(Gf.Vec3d(float(bxyz[0]), float(bxyz[1]), -0.005))
        ped.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(1.0, 0.0, 0.0, 0.0))

        arm = UsdGeom.Xform.Define(stage, f"/World/{rkey}")
        arm.GetPrim().GetReferences().AddReference("../assets/franka_panda/asset.usd", "/World/franka_panda")
        arm.AddTranslateOp().Set(Gf.Vec3d(*map(float, bxyz)))
        arm.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(*map(float, bwxyz)))

    # Reference Instruments
    UsdGeom.Scope.Define(stage, "/World/Instruments")
    initial_inst_poses = {
        "iron_stand_left": ([-0.250, 0.062, 0.750], [1.0, 0.0, 0.0, 0.0]),
        "iron_stand_right": ([0.0634, 0.112, 0.750], [1.0, 0.0, 0.0, 0.0]),
        "scissor_jack_white": ([0.215, 0.000, 0.750], [1.0, 0.0, 0.0, 0.0]),
        "heating_stirrer_bath": ([-0.180, 0.000, 0.822], [1.0, 0.0, 0.0, 0.0]),
        "round_bottom_flask_250ml": ([-0.180, 0.000, 0.940], [1.0, 0.0, 0.0, 0.0]),
        "distillation_head_75deg": ([-0.180, 0.000, 1.026], [1.0, 0.0, 0.0, 0.0]),
        "liebig_condenser_24_29": ([0.022844, 0.000, 1.033648], [0.9914449, 0.0, 0.1305262, 0.0]),
        "vacuum_tail_adapter": ([0.143585, 0.000, 1.001296], [1.0, 0.0, 0.0, 0.0]),
        "erlenmeyer_flask_150ml": ([0.215, 0.000, 0.832], [1.0, 0.0, 0.0, 0.0]),
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

    def _populate_npz_visuals(parent_path: str, npz_file: Path) -> None:
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
                UsdShade.MaterialBindingAPI.Apply(m.GetPrim()).Bind(mech_mats.get(sname, mat_chrome))

    # Calibrated Thermometer Unit (`/World/Instruments/thermometer_adapter_unit_v08`)
    th_xf = UsdGeom.Xform.Define(stage, "/World/Instruments/thermometer_adapter_unit_v08")
    th_xf.AddTranslateOp().Set(Gf.Vec3d(-0.180, 0.000, 1.1320))
    th_xf.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(1.0, 0.0, 0.0, 0.0))
    _populate_npz_visuals("/World/Instruments/thermometer_adapter_unit_v08", link_meshes_dir / "thermometer_adapter_unit_v08.npz")

    # Articulated Mechanisms (`/World/Mechanisms/*`, including TWO 3-link Keck clips!)
    UsdGeom.Scope.Define(stage, "/World/Mechanisms")
    mech_specs = {
        "scissor_jack_blue_art001": {
            "base_xyz": [-0.180, 0.000, 0.750],
            "base_wxyz": [1.0, 0.0, 0.0, 0.0],
            "links": {
                "BasePlate": ("scissor_jack_blue_art001__BasePlate.npz", [0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]),
                "TopPlatform": ("scissor_jack_blue_art001__TopPlatform.npz", [0.0, 0.0, 0.072], [1.0, 0.0, 0.0, 0.0]),
                "Handwheel": ("scissor_jack_blue_art001__Handwheel.npz", [0.0, 0.088, 0.035], [1.0, 0.0, 0.0, 0.0]),
            },
        },
        "flask_clamp_2prong_art001": {
            "base_xyz": [-0.180, 0.000, 1.008],
            "base_wxyz": [1.0, 0.0, 0.0, 0.0],
            "links": {
                "FixedLeftYoke": ("flask_clamp_2prong_art001__FixedLeftYoke.npz", [0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]),
                "MovableRightJaw": ("flask_clamp_2prong_art001__MovableRightJaw.npz", [0.0, 0.024, 0.0], [1.0, 0.0, 0.0, 0.0]),
                "ButterflyWingnut": ("flask_clamp_2prong_art001__ButterflyWingnut.npz", [0.024, 0.044, 0.0], [1.0, 0.0, 0.0, 0.0]),
            },
        },
        "condenser_clamp_3prong_art001": {
            "base_xyz": [0.0460, 0.000, 1.0274],
            "base_wxyz": [0.9914449, 0.0, 0.1305262, 0.0],
            "links": {
                "FixedLowerBase": ("condenser_clamp_3prong_art001__FixedLowerBase.npz", [0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]),
                "MovableUpperJaw": ("condenser_clamp_3prong_art001__MovableUpperJaw.npz", [0.0, 0.024, 0.014], [1.0, 0.0, 0.0, 0.0]),
                "TopButterflyWingnut": ("condenser_clamp_3prong_art001__TopButterflyWingnut.npz", [0.0, 0.048, 0.018], [1.0, 0.0, 0.0, 0.0]),
            },
        },
        "keck_clip_head_cond_art001": {
            "base_xyz": [0.220, -0.115, 0.770],
            "base_wxyz": [1.0, 0.0, 0.0, 0.0],
            "links": {
                "ClipSpine": ("keck_clip_spine.npz", [0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]),
                "LeftSpringJaw": ("keck_clip_left_jaw.npz", [0.0, 0.0056, 0.0172], [1.0, 0.0, 0.0, 0.0]),
                "RightSpringJaw": ("keck_clip_right_jaw.npz", [0.0, -0.0056, 0.0172], [1.0, 0.0, 0.0, 0.0]),
            },
        },
        "keck_clip_cond_tail_art001": {
            "base_xyz": [-0.285, -0.115, 0.770],
            "base_wxyz": [1.0, 0.0, 0.0, 0.0],
            "links": {
                "ClipSpine": ("keck_clip_spine.npz", [0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]),
                "LeftSpringJaw": ("keck_clip_left_jaw.npz", [0.0, 0.0056, 0.0172], [1.0, 0.0, 0.0, 0.0]),
                "RightSpringJaw": ("keck_clip_right_jaw.npz", [0.0, -0.0056, 0.0172], [1.0, 0.0, 0.0, 0.0]),
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
            _populate_npz_visuals(f"/World/Mechanisms/{mid}/{lid}", link_meshes_dir / npz_name)

    # Dual 64x24 Amber Latex Cooling Hose visual meshes
    UsdGeom.Scope.Define(stage, "/World/CoolingHoses")
    h_pts, h_tris = _make_tube_skin_topology(64, 24, 0.0052)
    for hname in ("Hose_Inlet_Lower", "Hose_Outlet_Upper"):
        hm = UsdGeom.Mesh.Define(stage, f"/World/CoolingHoses/{hname}")
        hm.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(h_pts))
        hm.CreateFaceVertexCountsAttr(Vt.IntArray([3] * len(h_tris)))
        hm.CreateFaceVertexIndicesAttr(Vt.IntArray(h_tris.reshape(-1).tolist()))
        UsdShade.MaterialBindingAPI.Apply(hm.GetPrim()).Bind(mat_amber_latex)

    UsdGeom.Scope.Define(stage, "/World/Cameras")
    stage.GetRootLayer().Save()

    sem_dir = pkg_root / "semantics"
    sem_dir.mkdir(parents=True, exist_ok=True)
    scene_spec = {
        "schema_version": "distillation-v08-taper-keck-scene-spec/v1.0",
        "package_id": "distillation_v08_4taper_keck_true_dynamic",
        "reference_bvid": "BV17t4y1V7XH",
        "physx_hz": 240,
        "robot_bases": V08_ROBOT_BASES,
        "cameras": V08_CAMERAS,
        "taper_targets": {
            "joint_01_flask_socket_world": [-0.180, 0.000, 1.0260],
            "joint_02_sidearm_cone_world": [-0.097896, 0.000, 1.0660],
            "joint_02_condenser_seated_world": [0.022844, 0.000, 1.033648],
            "joint_03_cond_lower_cone_world": [0.143585, 0.000, 1.001296],
            "joint_04_thermo_seated_world": [-0.180, 0.000, 1.1320],
            "sidearm_bottom_lip_z_world": 1.0800,
            "thermometer_bulb_top_local_z": -0.0520,
        },
    }
    (sem_dir / "v08_scene_spec.json").write_text(json.dumps(scene_spec, indent=2), encoding="utf-8")
    (pkg_root / "task.yaml").write_text(
        yaml.safe_dump(
            {
                "task_id": "distillation_v08_4taper_keck_slice",
                "physics_hz": 240,
                "anti_cheat_kinematic_manipulated_allowed": False,
                "counterfactual_zero_friction_required": True,
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
    for up in sorted(mech_usd_dir.glob("*.usda")):
        manifest_assets.append(
            {
                "asset_id": up.stem,
                "role": "articulated_mechanism_art001",
                "asset_type": "usd",
                "canonical_usd": f"assets/mechanisms_art001/{up.name}",
                "license": "Apache-2.0",
                "sha256": compute_sha256(up),
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
    write_asset_lock(pkg_root, generate_asset_lock(pkg_root, lock_id="distillation_v08_lock"))
    return {
        "package_dir": pkg_root.as_posix(),
        "scene_usda": scene_path.as_posix(),
        "scene_sha256": compute_sha256(scene_path),
    }

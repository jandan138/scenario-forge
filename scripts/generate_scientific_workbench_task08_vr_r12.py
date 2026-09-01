#!/usr/bin/env python3
"""Generate the Task 08 r12 VR action-collection candidate."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import tarfile
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.generate_visual_static_liquid_prototype import build_liquid_mesh  # noqa: E402


TASK_ID = "scientific_workbench_tighten_centrifuge_tube_cap_vr_r12"
DEFAULT_OUT = ROOT / "outputs/scientific_workbench_task08_vr_r12_20260901"
BASE_VR = (
    ROOT
    / "outputs/scientific_workbench_tasks_02_07_08_r10_1_20260817/packages/"
    "task08/bioclean/adapters/vr_teleop"
)
ASSET_SET = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "scientific_workbench_task08_r12_assets_20260901"
)
TRAY_ARCHIVE = (
    ROOT
    / "external_artifacts/incoming/from_xinyu/steel_plate_30cm_simready_v1.tar.gz"
)
RACK_ENTRY = "/TubeRack15ml50ml_OriginalMesh"
BODY_ENTRY = "/World/Tube15LongNeckThreadedBody"
CAP_ENTRY = "/World/Tube15LongNeckThreadedClosedCap"
RACK_XYZ = (0.16, -0.14, 0.755)
TRAY_XYZ = (-0.23, -0.17, 0.755)
SLOTS = ("slot_15ml_r00_c01", "slot_15ml_r00_c02", "slot_15ml_r00_c03")
CAP_X = (-0.29, -0.23, -0.17)
TARGET_INDEX = 1
LIQUID_PROFILE_M = (
    (0.0020, 0.0006),
    (0.02284, 0.0070),
    (0.0910, 0.0070),
)
LIQUID_FILL_FRACTION = 0.80
LIQUID_COLOR = (0.03, 0.34, 0.82)
CONTEXT = {
    "obj_r9_clear_bottle": (
        "r9_clear_bottle",
        (-0.78, 0.18, 0.755),
    ),
    "obj_r9_tip_box": ("r9_tip_box", (-0.58, 0.22, 0.755)),
    "obj_r9_wash_bottle": ("r9_wash_bottle", (0.78, 0.18, 0.755)),
    "obj_r9_pipette_carousel": (
        "r9_pipette_carousel",
        (0.62, 0.20, 0.755),
    ),
}


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _copytree(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination)


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _install_tray(destination: Path) -> dict[str, Any]:
    unpack = destination / "_unpack"
    unpack.mkdir(parents=True)
    with tarfile.open(TRAY_ARCHIVE, "r:gz") as archive:
        archive.extractall(unpack)
    payload = unpack / "final"
    manifest = json.loads((payload / "manifest.json").read_text())
    if manifest.get("validation_status") != "ok":
        raise RuntimeError("steel tray source is not validated")
    shutil.copytree(payload / "simready", destination / "simready")
    (destination / "visual").mkdir()
    shutil.copy2(
        payload / "visual/steel_plate_visual.usdc",
        destination / "visual/steel_plate_visual.usdc",
    )
    shutil.copy2(payload / "manifest.json", destination / "manifest.json")
    shutil.copy2(payload / "README.md", destination / "README.md")
    shutil.rmtree(unpack)
    return manifest


def _define_ref(stage, path: str, asset: str, prim: str, xyz) -> Any:
    from pxr import Gf, Sdf, UsdGeom

    root = UsdGeom.Xform.Define(stage, path)
    root.GetPrim().GetReferences().AddReference(asset, prim)
    translate = root.GetPrim().GetAttribute("xformOp:translate")
    if translate:
        value = Gf.Vec3f(*xyz) if translate.GetTypeName() == Sdf.ValueTypeNames.Float3 else Gf.Vec3d(*xyz)
        translate.Set(value)
    else:
        root.AddTranslateOp().Set(Gf.Vec3d(*xyz))
    orient = root.GetPrim().GetAttribute("xformOp:orient")
    if orient:
        value = Gf.Quatd(1.0) if orient.GetTypeName() == Sdf.ValueTypeNames.Quatd else Gf.Quatf(1.0)
        orient.Set(value)
    else:
        root.AddOrientOp().Set(Gf.Quatf(1.0))
    scale = root.GetPrim().GetAttribute("xformOp:scale")
    if scale:
        value = Gf.Vec3f(1.0) if scale.GetTypeName() == Sdf.ValueTypeNames.Float3 else Gf.Vec3d(1.0)
        scale.Set(value)
    else:
        root.AddScaleOp().Set(Gf.Vec3d(1.0))
    root.SetXformOpOrder(
        [
            UsdGeom.XformOp(root.GetPrim().GetAttribute("xformOp:translate")),
            UsdGeom.XformOp(root.GetPrim().GetAttribute("xformOp:orient")),
            UsdGeom.XformOp(root.GetPrim().GetAttribute("xformOp:scale")),
        ]
    )
    return root.GetPrim()


def _slot_positions(rack_asset: Path) -> list[tuple[float, float, float]]:
    from pxr import Usd, UsdGeom

    stage = Usd.Stage.Open(str(rack_asset))
    cache = UsdGeom.XformCache()
    result = []
    for slot in SLOTS:
        frame = stage.GetPrimAtPath(f"{RACK_ENTRY}/__frames/{slot}_inserted_bottom")
        point = cache.GetLocalToWorldTransform(frame).ExtractTranslation()
        result.append(
            tuple(float(point[index]) + RACK_XYZ[index] for index in range(3))
        )
    return result


def _author_mesh(stage, path: str, data: dict[str, Any], material, *, double_sided: bool) -> None:
    from pxr import Gf, UsdGeom, UsdShade

    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr([Gf.Vec3f(*point) for point in data["points"]])
    mesh.CreateFaceVertexCountsAttr(data["face_vertex_counts"])
    mesh.CreateFaceVertexIndicesAttr(data["face_vertex_indices"])
    mesh.CreateExtentAttr([Gf.Vec3f(*point) for point in data["extent"]])
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateDoubleSidedAttr(double_sided)
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)


def _author_liquid(stage, tube_path: str, index: int, material) -> dict[str, Any]:
    from pxr import Sdf, UsdGeom

    mesh = build_liquid_mesh(
        LIQUID_PROFILE_M,
        LIQUID_FILL_FRACTION,
        radial_segments=32,
        meniscus_depth_m=0.0004,
    )
    root_path = tube_path + "/VisualLiquid"
    root = UsdGeom.Xform.Define(stage, root_path).GetPrim()
    root.CreateAttribute("scenarioForge:role", Sdf.ValueTypeNames.Token).Set(
        "visual_static_liquid"
    )
    root.CreateAttribute("scenarioForge:interactive", Sdf.ValueTypeNames.Bool).Set(
        False
    )
    root.CreateAttribute("scenarioForge:fillFraction", Sdf.ValueTypeNames.Float).Set(
        LIQUID_FILL_FRACTION
    )
    _author_mesh(stage, root_path + "/Body", mesh["body"], material, double_sided=False)
    _author_mesh(
        stage, root_path + "/Surface", mesh["surface"], material, double_sided=True
    )
    return {
        "id": f"tube_{index:02d}_visual_liquid",
        "container": tube_path,
        "liquid_prim": root_path,
        "fill_fraction": LIQUID_FILL_FRACTION,
        "fill_height_m": mesh["fill_height_m"],
        "interactive": False,
    }


def _task_config(object_names: list[str]) -> str:
    def group(names: list[str]) -> dict[str, Any]:
        return {
            "objs": names,
            "mode": "local",
            "yaw_range_degrees": [0.0, 0.0],
            "x_offset_range": [-0.01, 0.01],
            "y_offset_range": [-0.01, 0.01],
        }

    task = {
        "scene_usd_file_path": {"scene1": "__SCENE_PATH__"},
        "obj_prim_list": [f"/World/_scene/{name}" for name in object_names],
        "layout_randomization": {
            "table": "table",
            "objects": [
                group(["obj_tube_rack", "obj_tube_00", "obj_tube_01", "obj_tube_02"]),
                group(["obj_steel_plate", "obj_cap_00", "obj_cap_01", "obj_cap_02"]),
                *[group([name]) for name in CONTEXT],
            ],
        },
        "robot_cfg": {
            "position": [0.0, -1.02, 0.31],
            "orientation": [0.7071067812, 0.0, 0.0, 0.7071067812],
        },
        "physx_scene_cfg": {
            "BroadphaseType": "GPU",
            "EnableGPUDynamics": True,
            "SolverType": "TGS",
            "TimeStepsPerSecond": 120,
        },
        "task_semantics": {
            "target_tube": "obj_tube_01",
            "target_cap": "obj_cap_01",
            "sequence": ["pick_cap", "pick_tube", "align", "mate", "twist", "return_tube"],
            "terminal_cap_release_required": False,
            "thread_success_claimed": False,
        },
        "visual_liquid": {
            "mode": "visual_static_liquid",
            "fill_fraction": LIQUID_FILL_FRACTION,
            "interactive": False,
            "particle_system_count": 0,
        },
    }
    return (
        "from pathlib import Path\n"
        "_ASSETS_DIR = Path(__file__).resolve().parent\n"
        "TASKS = "
        + repr({TASK_ID: task}).replace(
            "'__SCENE_PATH__'", "str(_ASSETS_DIR / 'scene.usd')"
        )
        + "\n"
    )


def build(output: Path = DEFAULT_OUT) -> Path:
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade, UsdUtils

    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to replace output: {output}")
    asset_manifest = json.loads((ASSET_SET / "asset_set_manifest.json").read_text())
    if (
        asset_manifest.get("status") != "pass"
        or asset_manifest.get("claims", {}).get("rack_scaled_sdf_ready") is not True
        or asset_manifest.get("claims", {}).get("visual_material_variants_ready")
        is not True
    ):
        raise RuntimeError("Task 08 r12 ConvertAsset set is not promoted")
    vr = output / "vr"
    deps = vr / "deps"
    deps.mkdir(parents=True)
    _copytree(BASE_VR / "deps/environment", deps / "environment")
    _copytree(BASE_VR / "deps/table", deps / "table")
    for _name, (source, _xyz) in CONTEXT.items():
        _copytree(BASE_VR / f"deps/context/{source}", deps / f"context/{source}")
    packages = ASSET_SET / "packages"
    _copytree(packages / "mixed_rack_18plus4_scaled_sdf_r3", deps / "rack")
    _copytree(
        packages / "tube15_long_neck_threaded_body_glass_v1_2", deps / "tube"
    )
    _copytree(
        packages / "tube15_long_neck_threaded_closed_cap_red_v1_2", deps / "cap"
    )
    tray_manifest = _install_tray(deps / "tray")
    scene = vr / "scene.usd"
    stage = Usd.Stage.CreateNew(str(scene))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    _define_ref(
        stage,
        "/World/background",
        "deps/environment/asset.usd",
        "/World",
        (0.002882434, -0.0069055, 0.0),
    )
    _define_ref(stage, "/World/table", "deps/table/asset.usd", "/World/table", (0, 0, 0))
    for table_surface_path in (
        "/World/table/Surface/Source/mesh",
        "/World/table/table/Surface/Source/mesh",
    ):
        stage.OverridePrim(table_surface_path).CreateAttribute(
            "visibility", Sdf.ValueTypeNames.Token
        ).Set("invisible")
    _define_ref(stage, "/World/obj_tube_rack", "deps/rack/asset.usd", RACK_ENTRY, RACK_XYZ)
    tube_positions = _slot_positions(deps / "rack/asset.usd")
    for index, xyz in enumerate(tube_positions):
        prim = _define_ref(
            stage,
            f"/World/obj_tube_{index:02d}",
            "deps/tube/asset.usd",
            BODY_ENTRY,
            xyz,
        )
        prim.CreateAttribute("scenarioForge:taskTarget", Sdf.ValueTypeNames.Bool).Set(
            index == TARGET_INDEX
        )
    _define_ref(
        stage,
        "/World/obj_steel_plate",
        "deps/tray/simready/steel_plate_30cm_simready.usdc",
        "/SteelPlate",
        TRAY_XYZ,
    )
    for index, x in enumerate(CAP_X):
        prim = _define_ref(
            stage,
            f"/World/obj_cap_{index:02d}",
            "deps/cap/asset.usd",
            CAP_ENTRY,
            (x, TRAY_XYZ[1], 0.766),
        )
        prim.CreateAttribute("scenarioForge:taskTarget", Sdf.ValueTypeNames.Bool).Set(
            index == TARGET_INDEX
        )
    for name, (source, xyz) in CONTEXT.items():
        _define_ref(
            stage,
            f"/World/{name}",
            f"deps/context/{source}/asset.usd",
            "/ObjectRoot",
            xyz,
        )
    liquid_material = UsdShade.Material.Define(stage, "/World/Looks/VisualLiquidBlue")
    shader = UsdShade.Shader.Define(
        stage, "/World/Looks/VisualLiquidBlue/PreviewSurface"
    )
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(*LIQUID_COLOR)
    )
    shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(*(value * 0.18 for value in LIQUID_COLOR))
    )
    shader.CreateInput("ior", Sdf.ValueTypeNames.Float).Set(1.333)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(0.72)
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.12)
    liquid_material.CreateSurfaceOutput().ConnectToSource(
        shader.ConnectableAPI(), "surface"
    )
    liquids = [
        _author_liquid(stage, f"/World/obj_tube_{index:02d}", index, liquid_material)
        for index in range(3)
    ]
    light = UsdLux.DomeLight.Define(stage, "/World/vr_direct_open_light")
    light.CreateIntensityAttr(750.0)
    light.CreateExposureAttr(0.0)
    physics = UsdPhysics.Scene.Define(stage, "/World/physicsScene")
    physics.CreateGravityDirectionAttr(Gf.Vec3f(0.0, 0.0, -1.0))
    physics.CreateGravityMagnitudeAttr(9.81)
    physics.GetPrim().CreateAttribute(
        "physxScene:broadphaseType", Sdf.ValueTypeNames.Token, custom=True
    ).Set("GPU")
    physics.GetPrim().CreateAttribute(
        "physxScene:enableGPUDynamics", Sdf.ValueTypeNames.Bool, custom=True
    ).Set(True)
    physics.GetPrim().CreateAttribute(
        "physxScene:solverType", Sdf.ValueTypeNames.Token, custom=True
    ).Set("TGS")
    physics.GetPrim().CreateAttribute(
        "physxScene:timeStepsPerSecond", Sdf.ValueTypeNames.UInt, custom=True
    ).Set(120)
    stage.GetRootLayer().Save()
    layers, dependencies, unresolved = UsdUtils.ComputeAllDependencies(str(scene))
    if unresolved:
        raise RuntimeError(f"scene has unresolved dependencies: {unresolved}")
    object_names = [
        "obj_tube_rack",
        "obj_steel_plate",
        "obj_tube_00",
        "obj_tube_01",
        "obj_tube_02",
        "obj_cap_00",
        "obj_cap_01",
        "obj_cap_02",
        *CONTEXT,
    ]
    (vr / "task_config.py").write_text(_task_config(object_names), encoding="utf-8")
    _write_json(
        output / "visual_liquid_manifest.json",
        {
            "schema_version": "scenario-forge.task08-r12-visual-liquid/v0.1",
            "status": "authored_pending_runtime",
            "instances": liquids,
            "physics_contract": {
                "interactive": False,
                "particle_system_count": 0,
                "rigid_body_count": 0,
                "collider_count": 0,
            },
        },
    )
    _write_json(
        output / "manifest.json",
        {
            "schema_version": "scenario-forge.task08-vr-candidate/v0.12",
            "release_id": "r12",
            "task_id": TASK_ID,
            "status": "r12_scene_pending_runtime",
            "scene": "vr/scene.usd",
            "task_config": "vr/task_config.py",
            "target": {"tube": "obj_tube_01", "cap": "obj_cap_01"},
            "objects": object_names,
            "visual_liquids": liquids,
            "tray": {
                "asset_id": tray_manifest["asset_id"],
                "source_archive_sha256": _sha(TRAY_ARCHIVE),
            },
            "closure": {
                "layers": len(layers),
                "dependencies": len(dependencies),
                "unresolved": [],
            },
            "claims": {
                "vr_action_collection_layout_ready": False,
                "scene_static_stability": False,
                "three_interactive_tubes_and_caps": True,
                "visual_static_liquid_only": True,
                "thread_interaction_ready": False,
                "task08_success": False,
                "robot_policy_success": False,
                "benchmark_success": False,
            },
        },
    )
    (output / "README_CN.md").write_text(
        "# Task 08 r12 VR 动作数采候选\n\n"
        "打开 `vr/scene.usd`。目标为中间离心管与中间红盖；另外两组同样可交互。"
        "三根管内是 80% 非 PBD 蓝色视觉液体。该包不声明真实螺纹旋入或松手锁定。\n",
        encoding="utf-8",
    )
    return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    print(build(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

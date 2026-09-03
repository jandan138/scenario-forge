#!/usr/bin/env python3
"""Generate the preheated PBD water-bath centrifuge-tube VR candidate."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Sequence
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts.generate_visual_static_liquid_prototype import build_liquid_mesh  # noqa: E402
from scenario_forge.adapters.vr_object_materialization import (  # noqa: E402
    materialize_vr_object_subtrees,
)


BASE = ROOT / "outputs/scientific_workbench_insert_stir_bar_into_beaker_vr_r5_20260825"
RACK_PACKAGE = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "scientific_workbench_task08_r12_assets_20260901/packages/"
    "mixed_rack_18plus4_scaled_sdf_r3"
)
TUBE_PACKAGE = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "scientific_workbench_r7_task_assets_20260813/packages/"
    "centrifuge_tube_15ml_closed"
)
DEFAULT_OUTPUT = ROOT / "outputs/scientific_workbench_water_bath_tube_heat_vr_r1_20260902"
HANDOFF_ID = "scientific_workbench_water_bath_tube_heat_vr_r1"
TASK_ID = "scientific_workbench_water_bath_heat_centrifuge_tube"

STIRRER_XYZ = (0.37, -0.04, 0.755)
BEAKER_XYZ = (0.37, -0.028, 0.8267)
BASE_BEAKER_XYZ = (-0.16, -0.17, 0.755)
RACK_XYZ = (0.05, -0.14, 0.755)
SLOT_LOCAL_XYZ = (0.0715, -0.0061325, 0.0234)
TUBE_XYZ = tuple(RACK_XYZ[index] + SLOT_LOCAL_XYZ[index] for index in range(3))
TUBE_PROFILE_M = (
    (0.0020, 0.0006),
    (0.02284, 0.0070),
    (0.0910, 0.0070),
)
TUBE_FILL_FRACTION = 0.70
TUBE_LIQUID_COLOR = (0.78, 0.45, 0.12)
BACKGROUND_OBJECTS = (
    "obj_r9_amber_bottle",
    "obj_r9_tip_box",
    "obj_r9_wash_bottle",
    "obj_r9_clear_bottle",
    "obj_r9_pipette_carousel",
)


@dataclass(frozen=True)
class WaterBathHandoff:
    root: Path
    archive: Path
    manifest: Path


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _set_translation(prim: Any, xyz: tuple[float, float, float]) -> None:
    from pxr import Gf, Sdf, UsdGeom

    attr = prim.GetAttribute("xformOp:translate")
    if attr.IsValid():
        value = Gf.Vec3f(*xyz) if attr.GetTypeName() == Sdf.ValueTypeNames.Float3 else Gf.Vec3d(*xyz)
        attr.Set(value)
        return
    UsdGeom.Xformable(prim).AddTranslateOp(UsdGeom.XformOp.PrecisionDouble).Set(
        Gf.Vec3d(*xyz)
    )


def _ensure_full_trs(prim: Any, xyz: tuple[float, float, float]) -> None:
    from pxr import Gf, UsdGeom

    xform = UsdGeom.Xformable(prim)
    xform.ClearXformOpOrder()
    xform.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(*xyz))
    xform.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(1.0))
    xform.AddScaleOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(1.0))


def _define_reference(
    stage: Any,
    path: str,
    asset: str,
    entry_prim: str,
    xyz: tuple[float, float, float],
) -> Any:
    from pxr import UsdGeom

    prim = UsdGeom.Xform.Define(stage, path).GetPrim()
    prim.GetReferences().AddReference(asset, entry_prim)
    _ensure_full_trs(prim, xyz)
    return prim


def _author_mesh(
    stage: Any,
    path: str,
    data: dict[str, Any],
    material: Any,
    *,
    double_sided: bool,
) -> None:
    from pxr import Gf, UsdGeom, UsdShade

    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr([Gf.Vec3f(*point) for point in data["points"]])
    mesh.CreateFaceVertexCountsAttr(data["face_vertex_counts"])
    mesh.CreateFaceVertexIndicesAttr(data["face_vertex_indices"])
    mesh.CreateExtentAttr([Gf.Vec3f(*point) for point in data["extent"]])
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateDoubleSidedAttr(double_sided)
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)


def _author_tube_liquid(stage: Any) -> dict[str, Any]:
    from pxr import Gf, Sdf, UsdGeom, UsdShade

    root_path = "/World/obj_sample_tube/VisualLiquid"
    root = UsdGeom.Xform.Define(stage, root_path).GetPrim()
    root.CreateAttribute("scenarioForge:role", Sdf.ValueTypeNames.Token).Set(
        "visual_static_liquid"
    )
    root.CreateAttribute("scenarioForge:interactive", Sdf.ValueTypeNames.Bool).Set(
        False
    )
    root.CreateAttribute("scenarioForge:fillFraction", Sdf.ValueTypeNames.Float).Set(
        TUBE_FILL_FRACTION
    )
    material = UsdShade.Material.Define(stage, root_path + "/Looks/AmberSample")
    shader = UsdShade.Shader.Define(
        stage, root_path + "/Looks/AmberSample/PreviewSurface"
    )
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(*TUBE_LIQUID_COLOR)
    )
    shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(*(value * 0.10 for value in TUBE_LIQUID_COLOR))
    )
    shader.CreateInput("ior", Sdf.ValueTypeNames.Float).Set(1.333)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(0.55)
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.08)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    data = build_liquid_mesh(
        TUBE_PROFILE_M,
        TUBE_FILL_FRACTION,
        radial_segments=32,
        meniscus_depth_m=0.0004,
    )
    _author_mesh(
        stage, root_path + "/Body", data["body"], material, double_sided=False
    )
    _author_mesh(
        stage, root_path + "/Surface", data["surface"], material, double_sided=True
    )
    return {
        "container_prim": "/World/obj_sample_tube",
        "liquid_prim": root_path,
        "fill_fraction": TUBE_FILL_FRACTION,
        "fill_height_m": data["fill_height_m"],
        "color": list(TUBE_LIQUID_COLOR),
        "opacity": 0.55,
        "interactive": False,
    }


def _local_group(objects: list[str]) -> dict[str, Any]:
    return {
        "objs": objects,
        "mode": "local",
        "yaw_range_degrees": [0.0, 0.0],
        "x_offset_range": [-0.01, 0.01],
        "y_offset_range": [-0.01, 0.01],
    }


def _fixed_group(objects: list[str]) -> dict[str, Any]:
    group = _local_group(objects)
    group["x_offset_range"] = [0.0, 0.0]
    group["y_offset_range"] = [0.0, 0.0]
    return group


def _task_config() -> str:
    objects = [
        "obj_magnetic_stirrer",
        "obj_beaker",
        "obj_tube_rack",
        "obj_sample_tube",
        *BACKGROUND_OBJECTS,
    ]
    task = {
        "scene_usd_file_path": {"scene1": "__SCENE_PATH__"},
        "obj_prim_list": [f"/World/_scene/{name}" for name in objects],
        "layout_randomization": {
            "table": "table",
            "objects": [
                _fixed_group(
                    ["obj_magnetic_stirrer", "obj_beaker", "fluid_runtime"]
                ),
                _local_group(["obj_tube_rack", "obj_sample_tube"]),
                *[_local_group([name]) for name in BACKGROUND_OBJECTS],
            ],
        },
        "robot_cfg": {
            "position": [0.0, -1.02, 0.31],
            "orientation": [0.7071067812, 0.0, 0.0, 0.7071067812],
        },
        "physx_scene_cfg": {
            "BroadphaseType": "GPU",
            "SolverType": "TGS",
            "EnableGPUDynamics": True,
            "GpuMaxParticleContacts": 1048576,
            "TimeStepsPerSecond": 120,
        },
        "water_bath": {
            "state": "preheated",
            "temperature_setpoint_c": 60.0,
            "immersion_depth_range_m": [0.035, 0.055],
            "hold_seconds": 5.0,
            "thermal_transfer_simulated": False,
            "pbd_particle_count": 969,
        },
    }
    body = repr(task).replace(
        "'__SCENE_PATH__'", "str(_ASSETS_DIR / 'scene.usd')"
    )
    return (
        "from pathlib import Path\n"
        "_ASSETS_DIR = Path(__file__).resolve().parent\n"
        f"TASKS = {{{TASK_ID!r}: {body}}}\n"
    )


def _task() -> dict[str, Any]:
    return {
        "schema_version": "task/v0.4",
        "task_id": TASK_ID,
        "instruction": (
            "操作臂从试管架前排外角孔拿起闭盖离心管，将管体下部浸入60°C预热"
            "水浴并保持5秒，随后垂直取出并放回原孔位。"
        ),
        "temperature_setpoint_c": 60.0,
        "immersion_hold_seconds": 5.0,
        "target_tube": "obj_sample_tube",
        "source_and_return_slot": "slot_15ml_r00_c05",
        "steps": [
            {
                "id": "pick_tube_from_rack",
                "actor": "operating_arm",
                "skill": "pick",
            },
            {
                "id": "align_over_water_bath",
                "actor": "operating_arm",
                "skill": "align",
            },
            {
                "id": "immerse_tube",
                "actor": "operating_arm",
                "skill": "insert",
            },
            {
                "id": "hold_in_water_bath",
                "actor": "operating_arm",
                "skill": "hold",
                "duration_seconds": 5.0,
            },
            {
                "id": "withdraw_tube",
                "actor": "operating_arm",
                "skill": "lift",
            },
            {
                "id": "return_tube_to_rack",
                "actor": "operating_arm",
                "skill": "place",
            },
        ],
    }


def _metrics() -> dict[str, Any]:
    metrics = (
        ("tube_lifted_from_rack", 0.15),
        ("tube_aligned_over_bath", 0.10),
        ("tube_immersed_35_to_55mm", 0.20),
        ("tube_held_in_bath_5s", 0.25),
        ("tube_withdrawn_from_bath", 0.10),
        ("tube_returned_to_source_slot", 0.20),
    )
    return {
        "schema_version": "metrics/v0.4",
        "aggregation": {
            "type": "weighted_progress_score",
            "normalization": "declared_sum",
            "primary_metric_id": "tube_held_in_bath_5s",
        },
        "metrics": [
            {
                "id": metric_id,
                "type": "rubric_condition",
                "weight": weight,
                "source_ref": {"task": TASK_ID, "item": index + 1},
            }
            for index, (metric_id, weight) in enumerate(metrics)
        ],
    }


def _configure_scene(scene: Path) -> dict[str, Any]:
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdUtils

    stage = Usd.Stage.Open(str(scene), Usd.Stage.LoadAll)
    if stage is None:
        raise RuntimeError(f"cannot open {scene}")
    for path in ("/World/obj_steel_plate", "/World/obj_stir_bar"):
        stage.RemovePrim(path)

    stirrer = stage.GetPrimAtPath("/World/obj_magnetic_stirrer")
    _set_translation(stirrer, STIRRER_XYZ)
    stirrer.CreateAttribute(
        "scenarioForge:heatingState", Sdf.ValueTypeNames.Token
    ).Set("preheated")
    stirrer.CreateAttribute(
        "scenarioForge:temperatureSetpointC", Sdf.ValueTypeNames.Double
    ).Set(60.0)
    stirrer.CreateAttribute(
        "scenarioForge:stirringEnabled", Sdf.ValueTypeNames.Bool
    ).Set(False)
    stirrer.CreateAttribute(
        "scenarioForge:thermalTransferSimulated", Sdf.ValueTypeNames.Bool
    ).Set(False)

    beaker = stage.GetPrimAtPath("/World/obj_beaker")
    _set_translation(beaker, BEAKER_XYZ)
    delta = tuple(BEAKER_XYZ[index] - BASE_BEAKER_XYZ[index] for index in range(3))
    fluid = stage.GetPrimAtPath("/World/fluid_runtime")
    UsdGeom.Xformable(fluid).ClearXformOpOrder()
    particle_set = stage.GetPrimAtPath(
        "/World/fluid_runtime/ParticleSets/beaker_liquid"
    )
    for attribute_name in ("points", "physxParticle:simulationPoints"):
        attribute = particle_set.GetAttribute(attribute_name)
        values = attribute.Get() or []
        attribute.Set(
            [
                Gf.Vec3f(
                    float(value[0]) + delta[0],
                    float(value[1]) + delta[1],
                    float(value[2]) + delta[2],
                )
                for value in values
            ]
        )
    extent = particle_set.GetAttribute("extent")
    extent.Set(
        [
            Gf.Vec3f(
                float(value[0]) + delta[0],
                float(value[1]) + delta[1],
                float(value[2]) + delta[2],
            )
            for value in (extent.Get() or [])
        ]
    )

    _define_reference(
        stage,
        "/World/obj_tube_rack",
        "deps/objects/obj_tube_rack/asset.usd",
        "/TubeRack15ml50ml_OriginalMesh",
        RACK_XYZ,
    )
    tube = _define_reference(
        stage,
        "/World/obj_sample_tube",
        "deps/objects/obj_sample_tube/asset.usd",
        "/World/CentrifugeTube15mlClosed",
        TUBE_XYZ,
    )
    tube.CreateAttribute("scenarioForge:taskTarget", Sdf.ValueTypeNames.Bool).Set(True)
    tube.CreateAttribute("scenarioForge:sourceSlot", Sdf.ValueTypeNames.Token).Set(
        "slot_15ml_r00_c05"
    )
    tube_liquid = _author_tube_liquid(stage)

    for table_surface_path in (
        "/World/table/Surface/Source/mesh",
        "/World/table/table/Surface/Source/mesh",
    ):
        stage.OverridePrim(table_surface_path).CreateAttribute(
            "visibility", Sdf.ValueTypeNames.Token
        ).Set("invisible")
    stage.GetPrimAtPath("/World").SetCustomDataByKey(
        "scenario_forge:taskId", TASK_ID
    )
    stage.GetRootLayer().Save()
    layers, dependencies, unresolved = UsdUtils.ComputeAllDependencies(str(scene))
    if unresolved:
        raise RuntimeError(f"unresolved scene dependencies: {unresolved}")
    return {
        "tube_liquid": tube_liquid,
        "closure": {
            "layer_count": len(layers),
            "asset_count": len(dependencies),
            "unresolved": [],
        },
    }


def build_handoff(output: Path = DEFAULT_OUTPUT) -> WaterBathHandoff:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to replace output: {output}")
    for required in (
        BASE / "vr/scene.usd",
        RACK_PACKAGE / "asset.usd",
        TUBE_PACKAGE / "asset.usd",
    ):
        if not required.is_file():
            raise FileNotFoundError(required)

    shutil.copytree(BASE, output)
    for stale in (
        output / "handoff",
        output / "vr/evidence",
    ):
        if stale.exists():
            shutil.rmtree(stale)
    for stale in (
        output / "scenario.json",
        output / "vr/scene_liquid_edit.usd",
        output / "vr/task_config_liquid_edit.py",
    ):
        if stale.exists():
            stale.unlink()
    shutil.copytree(RACK_PACKAGE, output / "vr/deps/objects/obj_tube_rack")
    shutil.copytree(TUBE_PACKAGE, output / "vr/deps/objects/obj_sample_tube")
    configured = _configure_scene(output / "vr/scene.usd")
    materialize_vr_object_subtrees(
        scene_path=output / "vr/scene.usd",
        scene_prim_paths=["/World/obj_tube_rack", "/World/obj_sample_tube"],
        runtime_prim_paths=[
            "/World/_scene/obj_tube_rack",
            "/World/_scene/obj_sample_tube",
        ],
        evidence_path=output / "vr/object_materialization.json",
    )
    from pxr import UsdUtils

    layers, dependencies, unresolved = UsdUtils.ComputeAllDependencies(
        str(output / "vr/scene.usd")
    )
    if unresolved:
        raise RuntimeError(f"materialized scene has unresolved dependencies: {unresolved}")
    configured["closure"] = {
        "layer_count": len(layers),
        "asset_count": len(dependencies),
        "unresolved": [],
    }

    (output / "vr/task_config.py").write_text(_task_config(), encoding="utf-8")
    (output / "task.yaml").write_text(
        yaml.safe_dump(_task(), allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (output / "metrics.yaml").write_text(
        yaml.safe_dump(_metrics(), allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (output / "visual_liquid_manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "scenario-forge.water-bath-liquid/v0.1",
                "pbd_water": {
                    "container": "/World/obj_beaker",
                    "particle_set": "/World/fluid_runtime/ParticleSets/beaker_liquid",
                    "particle_count": 969,
                    "color": [0.32, 0.72, 0.95],
                    "opacity": 0.34,
                },
                "tube_sample": configured["tube_liquid"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (output / "README_CN.md").write_text(
        """# 预热水浴离心管浸泡 VR r1

使用 Isaac Sim 4.1 打开 `vr/scene.usd`。淡蓝色烧杯水体是969粒子GPU PBD
液体；闭盖15 mL离心管内的浅琥珀色内容物只是无碰撞视觉液体。

任务从试管架前排靠水浴侧外角孔取管，将管体下部浸入语义温度60°C的预热
水浴并保持5秒，再取出并放回原孔位。磁力搅拌器的现有旋钮不可操作；本包
只声明预热状态，不模拟真实热传递。

水浴粒子使用Isaac Sim 4.1要求的世界坐标烘焙，因此热台、烧杯和水体在本
任务中固定摆放，不对该三件套应用运行时XY随机化。

保留架中起始姿态是已知VR试采风险。本包在真实VR试采通过前不得描述为稳定
量产任务，也不声明机器人策略或benchmark成功。
""",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "scenario-forge.water-bath-vr-candidate/v0.1",
        "package_id": HANDOFF_ID,
        "task_id": TASK_ID,
        "status": "scene_built_runtime_pending",
        "entrypoints": {
            "scene": "vr/scene.usd",
            "task_config": "vr/task_config.py",
            "task": "task.yaml",
            "metrics": "metrics.yaml",
        },
        "source_hashes": {
            "base_scene": _sha(BASE / "vr/scene.usd"),
            "rack_asset": _sha(RACK_PACKAGE / "asset.usd"),
            "tube_asset": _sha(TUBE_PACKAGE / "asset.usd"),
        },
        "closure": configured["closure"],
        "claims": {
            "pbd_water": True,
            "pbd_particle_count": 969,
            "transparent_light_blue_water": True,
            "tube_visual_static_liquid": True,
            "single_closed_tube_in_rack": True,
            "preheated_state_semantic": True,
            "thermal_transfer_simulated": False,
            "stirring_simulated": False,
            "vr_action_collection_ready": False,
            "robot_policy_success": False,
            "benchmark_success": False,
        },
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    handoff = output / "handoff"
    handoff.mkdir()
    archive = handoff / f"{HANDOFF_ID}_candidate.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for path in sorted(output.rglob("*")):
            if path.is_file() and handoff not in path.parents:
                target.write(path, path.relative_to(output))
    return WaterBathHandoff(output, archive, manifest_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    print(build_handoff(args.out).archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

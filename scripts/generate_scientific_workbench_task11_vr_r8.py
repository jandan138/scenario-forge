#!/usr/bin/env python3
"""Generate Task 11 r8 with fitted lid collision and visual-only tube liquid."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts import generate_scientific_workbench_task11_vr_static as base  # noqa: E402
from scripts.generate_visual_static_liquid_prototype import build_liquid_mesh  # noqa: E402

from scenario_forge.adapters.vr_object_materialization import (  # noqa: E402
    materialize_vr_object_subtrees,
)


TASK_ID = "scientific_workbench_centrifuge_unload_shutdown"
DEFAULT_OUT = ROOT / "outputs/scientific_workbench_task11_vr_r8_20260826"
DEFAULT_CENTRIFUGE = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "labspin_x8_task11_r6_visual_fitted_lid_collision_20260826/package"
)
DEFAULT_TUBE = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "task11_r5_context_assets_20260824/target_tube_r2/package"
)
DEVICE_XYZ = (0.0, -0.1, 0.755)
RACK_XYZ = (-0.4, -0.3, 0.755)
CONTEXT_LAYOUT = {
    "obj_r9_amber_bottle": (-0.78, 0.18, 0.755),
    "obj_r9_tip_box": (-0.58, 0.22, 0.755),
    "obj_r9_wash_bottle": (0.78, 0.18, 0.755),
    "obj_r9_clear_bottle": (0.58, 0.22, 0.755),
    "obj_r9_pipette_carousel": (0.82, -0.04, 0.755),
}
CONTEXT_ASSETS = {
    "obj_r9_amber_bottle": "scientific_workbench_r9_context_amber_reagent_bottle",
    "obj_r9_tip_box": "scientific_workbench_r9_context_pipette_tip_box",
    "obj_r9_wash_bottle": "scientific_workbench_r9_context_wash_bottle",
    "obj_r9_clear_bottle": "scientific_workbench_r9_context_clear_reagent_bottle",
    "obj_r9_pipette_carousel": "scientific_workbench_r9_context_pipette_carousel",
}
BASE_OBJECTS = (
    "obj_centrifuge",
    "obj_mixed_rack",
    "obj_primary_tube",
    "obj_balance_tube",
    *(f"obj_bg_15ml_{index:02d}" for index in range(6)),
    "obj_bg_50ml_00",
    "obj_bg_50ml_01",
)
LIQUID_PROFILE_M = (
    (0.0020, 0.0006),
    (0.02284, 0.0070),
    (0.0910, 0.0070),
)
LIQUID_FILL_FRACTION = 0.95
LIQUID_COLOR = (0.03, 0.34, 0.82)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _local_group(names: list[str]) -> dict[str, object]:
    return {
        "objs": names,
        "mode": "local",
        "yaw_range_degrees": [0.0, 0.0],
        "x_offset_range": [-0.01, 0.01],
        "y_offset_range": [-0.01, 0.01],
    }


def _author_mesh(stage, path: str, data: dict, material, *, double_sided: bool) -> None:
    from pxr import Gf, UsdGeom, UsdShade

    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr([Gf.Vec3f(*point) for point in data["points"]])
    mesh.CreateFaceVertexCountsAttr(data["face_vertex_counts"])
    mesh.CreateFaceVertexIndicesAttr(data["face_vertex_indices"])
    mesh.CreateExtentAttr([Gf.Vec3f(*point) for point in data["extent"]])
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateDoubleSidedAttr(double_sided)
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)


def _author_visual_liquid(stage, object_path: str, liquid_id: str) -> dict[str, object]:
    from pxr import Gf, Sdf, UsdGeom, UsdShade

    mesh = build_liquid_mesh(
        LIQUID_PROFILE_M,
        LIQUID_FILL_FRACTION,
        radial_segments=32,
        meniscus_depth_m=0.0004,
    )
    root_path = f"{object_path}/VisualLiquid"
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
    material = UsdShade.Material.Define(stage, f"{root_path}/Looks/BlueLiquid")
    shader = UsdShade.Shader.Define(stage, f"{root_path}/Looks/BlueLiquid/PreviewSurface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(*LIQUID_COLOR)
    )
    shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(*(value * 0.18 for value in LIQUID_COLOR))
    )
    shader.CreateInput("ior", Sdf.ValueTypeNames.Float).Set(1.333)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(1.0)
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.12)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    _author_mesh(stage, f"{root_path}/Body", mesh["body"], material, double_sided=False)
    _author_mesh(stage, f"{root_path}/Surface", mesh["surface"], material, double_sided=True)
    return {
        "id": liquid_id,
        "container_prim": object_path,
        "liquid_prim": root_path,
        "role": "visual_static_liquid",
        "fill_fraction": LIQUID_FILL_FRACTION,
        "fill_height_m": mesh["fill_height_m"],
        "top_radius_m": mesh["top_radius_m"],
        "color": list(LIQUID_COLOR),
        "interactive": False,
    }


def build(
    output: Path,
    centrifuge: Path,
    tube: Path,
    *,
    required_tube_claim: str = "target_slot_insertion",
    tube_entry_prim: str = "/World/CentrifugeTube15mlClosed",
    tube_asset_filename: str = "asset.usd",
    replace_all_15ml: bool = False,
    release_id: str = "r8",
    primary_socket: int = base.PRIMARY_SOCKET,
    balance_socket: int = base.BALANCE_SOCKET,
) -> Path:
    from pxr import Sdf, Usd

    device_manifest = json.loads(
        (centrifuge / "evidence/manifest.json").read_text(encoding="utf-8")
    )
    if (
        device_manifest.get("overall_status") != "pass"
        or device_manifest.get("claims", {}).get("visual_fitted_lid_collision")
        is not True
    ):
        raise RuntimeError("visual-fitted centrifuge r6 qualification is incomplete")
    tube_manifest = json.loads((tube / "evidence/manifest.json").read_text())
    if (
        tube_manifest.get("overall_status") != "pass"
        or tube_manifest.get("claims", {}).get(required_tube_claim) is not True
    ):
        raise RuntimeError("producer stable target-tube insertion qualification is incomplete")

    output = base.build(
        output.resolve(),
        base.DEFAULT_CONTEXT_ASSETS,
        centrifuge.resolve(),
        base.DEFAULT_BASE,
        base.DEFAULT_LIQUID,
        device_xyz=DEVICE_XYZ,
        target_tube=tube.resolve(),
        rack_xyz=RACK_XYZ,
        target_tube_entry_prim=tube_entry_prim,
        target_tube_asset_filename=tube_asset_filename,
        context_15ml_package=tube.resolve() if replace_all_15ml else None,
        context_15ml_entry_prim=(
            tube_entry_prim if replace_all_15ml else "/World/ContextTube15mlClosed"
        ),
        context_15ml_asset_filename=(
            tube_asset_filename if replace_all_15ml else "asset.usd"
        ),
        author_target_kinematic_override=not replace_all_15ml,
        primary_socket=primary_socket,
        balance_socket=balance_socket,
    )
    vr = output / "vr"
    scene_path = vr / "scene.usd"
    stage = Usd.Stage.Open(str(scene_path), Usd.Stage.LoadAll)
    stage.SetEditTarget(stage.GetRootLayer())
    stage.RemovePrim("/World/fluid_runtime")
    physics = stage.GetPrimAtPath("/World/physicsScene")
    physics.CreateAttribute(
        "physxScene:broadphaseType", Sdf.ValueTypeNames.Token, custom=True
    ).Set("GPU")
    physics.CreateAttribute(
        "physxScene:enableGPUDynamics", Sdf.ValueTypeNames.Bool, custom=True
    ).Set(True)
    physics.CreateAttribute(
        "physxScene:solverType", Sdf.ValueTypeNames.Token, custom=True
    ).Set("TGS")
    physics.CreateAttribute(
        "physxScene:timeStepsPerSecond", Sdf.ValueTypeNames.UInt, custom=True
    ).Set(120)
    for name, xyz in CONTEXT_LAYOUT.items():
        base._define_ref(
            stage,
            f"/World/{name}",
            f"deps/environment/source_bundle/{CONTEXT_ASSETS[name]}/asset.usd",
            "/ObjectRoot",
            xyz,
        )
    visual_liquids = [
        _author_visual_liquid(stage, "/World/obj_primary_tube", "primary_visual_liquid"),
        _author_visual_liquid(stage, "/World/obj_balance_tube", "balance_visual_liquid"),
    ]
    stage.GetRootLayer().Save()
    stage = None
    materialize_vr_object_subtrees(
        scene_path=scene_path,
        scene_prim_paths=[f"/World/{name}" for name in CONTEXT_LAYOUT],
        runtime_prim_paths=[f"/World/_scene/{name}" for name in CONTEXT_LAYOUT],
        evidence_path=vr / "context_object_materialization.json",
    )

    object_names = [*BASE_OBJECTS, *CONTEXT_LAYOUT]
    task = {
        "scene_usd_file_path": {"scene1": "__SCENE_PATH__"},
        "obj_prim_list": [f"/World/_scene/{name}" for name in object_names],
        "layout_randomization": {
            "table": "table",
            "objects": [
                _local_group(["obj_centrifuge", "obj_primary_tube", "obj_balance_tube"]),
                _local_group(
                    [
                        name
                        for name in BASE_OBJECTS
                        if name.startswith("obj_mixed") or name.startswith("obj_bg_")
                    ]
                ),
                *[_local_group([name]) for name in CONTEXT_LAYOUT],
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
        "visual_liquid": {
            "mode": "visual_static_liquid",
            "liquid_interactive": False,
            "particle_system_count": 0,
            "instances": [item["liquid_prim"] for item in visual_liquids],
        },
        "validation_scope": "scene_static_and_robot_free_device_mechanics",
        "rotor_layout": {
            "primary_socket": primary_socket,
            "balance_socket": balance_socket,
        },
    }
    config = (
        "from pathlib import Path\n_ASSETS_DIR = Path(__file__).resolve().parent\nTASKS = "
        + repr({TASK_ID: task}).replace(
            "'__SCENE_PATH__'", "str(_ASSETS_DIR / 'scene.usd')"
        )
        + "\n"
    )
    (vr / "task_config.py").write_text(config, encoding="utf-8")

    stale_validation = output / "validation_manifest.json"
    if stale_validation.exists():
        stale_validation.unlink()
    visual_manifest = {
        "schema_version": "scenario-forge-task11-visual-liquid/v0.1",
        "status": "authored_pending_runtime_inspection",
        "instances": visual_liquids,
        "physics_contract": {
            "liquid_interactive": False,
            "particle_system_count": 0,
            "liquid_rigid_body_count": 0,
            "liquid_collider_count": 0,
            "motion_behavior": "rigidly_follows_container",
            "gpu_dynamics_reason": "dynamic_sdf_rigid_container_collision_not_particles",
        },
    }
    (output / "visual_liquid_manifest.json").write_text(
        json.dumps(visual_manifest, indent=2, sort_keys=True) + "\n"
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.pop("particle_sets", None)
    manifest["schema_version"] = {
        "r9_2": "scenario-forge-task11-vr-candidate/v0.9",
        "r9_1": "scenario-forge-task11-vr-candidate/v0.8",
        "r9": "scenario-forge-task11-vr-candidate/v0.7",
    }.get(release_id, "scenario-forge-task11-vr-candidate/v0.6")
    manifest["release_id"] = release_id
    manifest["status"] = f"{release_id}_scene_pending_runtime"
    manifest["device_xyz_m"] = list(DEVICE_XYZ)
    manifest["rack_xyz_m"] = list(RACK_XYZ)
    manifest["primary_socket"] = primary_socket
    manifest["balance_socket"] = balance_socket
    manifest["background_objects"] = list(CONTEXT_LAYOUT)
    manifest["visual_liquids"] = visual_liquids
    manifest["physics_contract"] = visual_manifest["physics_contract"]
    manifest["producer_qualifications"]["device"] = (
        "vr/deps/centrifuge/evidence/manifest.json"
    )
    manifest["producer_qualifications"]["target_tube"] = (
        "vr/deps/tube/evidence/manifest.json"
    )
    manifest["source_hashes"] = {
        "centrifuge_asset": _sha(centrifuge / "asset.usd"),
        "target_tube_asset": _sha(tube / tube_asset_filename),
    }
    manifest["claims"].update(
        {
            "visual_fitted_lid_collision": True,
            "visual_static_liquid_only": True,
            "particle_free_scene": True,
            "scene_static_stability": False,
            "mechanical_oracle_success": False,
            "canonical_task11_scripted_oracle_success": False,
            "robot_policy_success": False,
            "benchmark_success": False,
            "task11_success": False,
            "single_rigid_body_closed_15ml": replace_all_15ml,
            "all_15ml_tubes_replaced": replace_all_15ml,
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--centrifuge", type=Path, default=DEFAULT_CENTRIFUGE)
    parser.add_argument("--tube", type=Path, default=DEFAULT_TUBE)
    args = parser.parse_args()
    print(build(args.out, args.centrifuge, args.tube))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

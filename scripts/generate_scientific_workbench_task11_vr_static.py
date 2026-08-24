#!/usr/bin/env python3
"""Generate the VR-only Task 11 r5 stable-context PBD candidate."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import shutil
import sys

_ROOT = Path(__file__).resolve().parents[1]
for _path in (_ROOT, _ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scenario_forge.adapters.vr_object_materialization import (  # noqa: E402
    materialize_vr_object_subtrees,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "scientific_workbench_centrifuge_unload_shutdown"
DEFAULT_CONTEXT_ASSETS = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/task11_r5_context_assets_20260824"
)
DEFAULT_CENTRIFUGE_R4 = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/labspin_x8_task11_r4_20260824/package"
)
DEFAULT_BASE = (
    REPO_ROOT
    / "outputs/scientific_workbench_task02_r10_2_fill_sweep_20260819/packages/fill40/vr/deps/r7_scene"
)
DEFAULT_LIQUID = (
    REPO_ROOT
    / "outputs/simple_sdf_multi_liquid_golden_20260820/liquid_package_qualified/liquid_overlay.usda"
)
DEFAULT_OUT = REPO_ROOT / "outputs/scientific_workbench_task11_vr_r5_20260824"
DEVICE_XYZ = (0.22, 0.09, 0.82)
RACK_XYZ = (-0.50, -0.17, 0.755)
ROTOR_ORIGIN = (-0.03, 0.005, 0.27)
PRIMARY_SOCKET = 18
BALANCE_SOCKET = 6
REQUIRED_DEVICE_CLAIMS = (
    "contact_press_qualified",
    "button_causes_lid_open",
    "lid_remains_open_after_release",
    "rotor_open_interlock",
    "shutdown_causes_power_off",
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _copytree(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def _orientation_z_to(axis: tuple[float, float, float]):
    from pxr import Gf

    dot = max(-1.0, min(1.0, axis[2]))
    cross = (-axis[1], axis[0], 0.0)
    scale = math.sqrt((1.0 + dot) * 2.0)
    return Gf.Quatf(scale * 0.5, Gf.Vec3f(cross[0] / scale, cross[1] / scale, 0.0))


def _socket_pose(profile: dict, index: int, device_xyz=DEVICE_XYZ):
    socket = profile["tube_sockets"][index]
    bottom = tuple(
        device_xyz[i] + ROTOR_ORIGIN[i] + socket["inserted_bottom_rotor_local_m"][i]
        for i in range(3)
    )
    axis = tuple(float(v) for v in socket["axis_out_rotor_local"])
    return bottom, _orientation_z_to(axis)


def _rack_frame(stage, name: str):
    from pxr import UsdGeom

    prim = stage.GetPrimAtPath(f"/TubeRack15ml50ml_OriginalMesh/__frames/{name}_inserted_bottom")
    matrix = UsdGeom.XformCache().GetLocalToWorldTransform(prim)
    point = matrix.ExtractTranslation()
    return (RACK_XYZ[0] + point[0], RACK_XYZ[1] + point[1], RACK_XYZ[2] + point[2])


def _define_ref(stage, path: str, asset: str, prim: str, xyz, orient=None):
    from pxr import Gf, UsdGeom

    root = UsdGeom.Xform.Define(stage, path)
    root.GetPrim().GetReferences().AddReference(asset, prim)
    translate = root.GetPrim().GetAttribute("xformOp:translate")
    if translate:
        translate.Set(Gf.Vec3d(*xyz))
    else:
        root.AddTranslateOp().Set(Gf.Vec3d(*xyz))
    if orient is not None:
        orient_attr = root.GetPrim().GetAttribute("xformOp:orient")
        if orient_attr:
            orient_attr.Set(orient)
        else:
            root.AddOrientOp().Set(orient)
    return root.GetPrim()


def _copy_liquid(stage, liquid_source: Path, tube_poses: list[tuple[str, tuple, object]]) -> None:
    from pxr import Gf, Sdf, Usd, UsdGeom

    source = Usd.Stage.Open(str(liquid_source))
    flat = source.Flatten(False)
    layer = stage.GetRootLayer()
    Sdf.CreatePrimInLayer(layer, "/World/fluid_runtime")
    for name in ("ParticleSystem", "LiquidMaterial"):
        Sdf.CopySpec(flat, f"/__ScenarioForgeFluid/{name}", layer, f"/World/fluid_runtime/{name}")
    source_set = source.GetPrimAtPath("/__ScenarioForgeFluid/ParticleSets/tube15_liquid")
    original = source_set.GetAttribute("points").Get()
    local_points = [Gf.Vec3f(p[0] + 0.18, p[1], p[2]) for p in original]
    for group, (name, position, orientation) in enumerate(tube_poses):
        destination = f"/World/fluid_runtime/ParticleSets/{name}"
        Sdf.CreatePrimInLayer(layer, "/World/fluid_runtime/ParticleSets")
        Sdf.CopySpec(flat, "/__ScenarioForgeFluid/ParticleSets/tube15_liquid", layer, destination)
        prim = stage.GetPrimAtPath(destination)
        points = [orientation.Transform(p) + Gf.Vec3f(*position) for p in local_points]
        prim.GetAttribute("points").Set([Gf.Vec3f(*p) for p in points])
        prim.GetAttribute("physxParticle:simulationPoints").Set([Gf.Vec3f(*p) for p in points])
        prim.GetAttribute("physxParticle:particleGroup").Set(group)
        prim.GetRelationship("physxParticle:particleSystem").SetTargets(
            ["/World/fluid_runtime/ParticleSystem"]
        )
        prim.GetRelationship("material:binding").SetTargets(["/World/fluid_runtime/LiquidMaterial"])
    physics = UsdGeom.Scope.Define(stage, "/World/fluid_runtime/metadata").GetPrim()
    physics.CreateAttribute("scenarioForge:claim", Sdf.ValueTypeNames.String).Set(
        "static_candidate_only"
    )


def build(
    output: Path,
    context_assets: Path,
    centrifuge: Path,
    base: Path,
    liquid: Path,
    device_xyz=DEVICE_XYZ,
) -> Path:
    from pxr import Usd, UsdGeom, UsdPhysics

    device_manifest = json.loads(
        (centrifuge / "evidence/manifest.json").read_text(encoding="utf-8")
    )
    if device_manifest.get("overall_status") != "pass" or not all(
        device_manifest["claims"].get(name) is True
        for name in REQUIRED_DEVICE_CLAIMS
    ):
        raise RuntimeError("centrifuge r4 device qualification is incomplete")
    producer_packages = {
        "rack": context_assets / "mixed_rack_r2/package",
        "context15": context_assets / "context_15ml_closed/package",
        "context50": context_assets / "context_50ml_closed/package",
        "target_tube": context_assets / "target_tube_r2/package",
    }
    for label, package in producer_packages.items():
        manifest = json.loads((package / "evidence/manifest.json").read_text())
        status = manifest.get("overall_status")
        if status != "pass":
            raise RuntimeError(
                f"{label} producer status must be pass, got {status}; "
                "candidate_pending_runtime is forbidden"
            )
    if output.exists():
        shutil.rmtree(output)
    vr = output / "vr"
    deps = vr / "deps"
    deps.mkdir(parents=True)
    _copytree(base, deps / "environment")
    _copytree(centrifuge, deps / "centrifuge")
    _copytree(producer_packages["rack"], deps / "rack")
    _copytree(producer_packages["target_tube"], deps / "tube")
    _copytree(producer_packages["context15"], deps / "context15")
    _copytree(producer_packages["context50"], deps / "context50")
    scene_path = vr / "scene.usd"
    stage = Usd.Stage.CreateNew(str(scene_path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    _define_ref(
        stage, "/World/background", "deps/environment/scene.usda", "/World/_scene/room", (0, 0, 0)
    )
    _define_ref(
        stage,
        "/World/table",
        "deps/environment/source_bundle/scenario_forge_runtime/table.usd",
        "/Asset",
        (0, 0, 0),
    )
    _define_ref(
        stage, "/World/obj_centrifuge", "deps/centrifuge/asset.usd", "/World/Centrifuge", device_xyz
    )
    _define_ref(
        stage,
        "/World/obj_mixed_rack",
        "deps/rack/asset.usd",
        "/TubeRack15ml50ml_OriginalMesh",
        RACK_XYZ,
    )
    profile = json.loads((deps / "centrifuge/articulation/device_profile.json").read_text())
    primary_pose = _socket_pose(profile, PRIMARY_SOCKET, device_xyz)
    balance_pose = _socket_pose(profile, BALANCE_SOCKET, device_xyz)
    primary = _define_ref(
        stage,
        "/World/obj_primary_tube",
        "deps/tube/asset.usd",
        "/World/CentrifugeTube15mlClosed",
        *primary_pose,
    )
    balance = _define_ref(
        stage,
        "/World/obj_balance_tube",
        "deps/tube/asset.usd",
        "/World/CentrifugeTube15mlClosed",
        *balance_pose,
    )
    for prim in (primary, balance):
        UsdPhysics.RigidBodyAPI(prim).CreateKinematicEnabledAttr(False)
    rack_stage = Usd.Stage.Open(str(deps / "rack/asset.usd"))
    object_paths = [
        "/World/obj_centrifuge",
        "/World/obj_mixed_rack",
        "/World/obj_primary_tube",
        "/World/obj_balance_tube",
    ]
    for index, slot in enumerate([f"slot_15ml_r01_c{i:02d}" for i in range(6)]):
        path = f"/World/obj_bg_15ml_{index:02d}"
        pos = _rack_frame(rack_stage, slot)
        _define_ref(
            stage,
            path,
            "deps/context15/asset.usd",
            "/World/ContextTube15mlClosed",
            pos,
        )
        object_paths.append(path)
    for index, slot in enumerate(("slot_50ml_r00_c00", "slot_50ml_r00_c03")):
        path = f"/World/obj_bg_50ml_{index:02d}"
        pos = _rack_frame(rack_stage, slot)
        _define_ref(
            stage,
            path,
            "deps/context50/asset.usd",
            "/World/ContextTube50mlClosed",
            pos,
        )
        object_paths.append(path)
    _copy_liquid(
        stage, liquid, [("primary_liquid", *primary_pose), ("balance_liquid", *balance_pose)]
    )
    light = UsdGeom.Sphere.Define(stage, "/World/__light_marker")
    light.GetPrim().SetActive(False)
    from pxr import UsdLux

    dome = UsdLux.DomeLight.Define(stage, "/World/vr_direct_open_light")
    dome.CreateIntensityAttr(750.0)
    physics = UsdPhysics.Scene.Define(stage, "/World/physicsScene")
    physics.CreateGravityDirectionAttr((0, 0, -1))
    physics.CreateGravityMagnitudeAttr(9.81)
    stage.GetRootLayer().Save()
    materialize_vr_object_subtrees(
        scene_path=scene_path,
        scene_prim_paths=object_paths,
        runtime_prim_paths=[p.replace("/World/", "/World/_scene/") for p in object_paths],
        evidence_path=vr / "object_materialization.json",
        prunable_dependency_roots=[
            deps / "centrifuge",
            deps / "rack",
            deps / "tube",
            deps / "context15",
            deps / "context50",
        ],
    )
    names = [p.rsplit("/", 1)[-1] for p in object_paths]
    task = {
        "scene_usd_file_path": {"scene1": "__SCENE_PATH__"},
        "obj_prim_list": [f"/World/_scene/{n}" for n in names],
        "layout_randomization": {
            "table": "table",
            "objects": [
                {
                    "objs": [
                        "obj_centrifuge",
                        "obj_primary_tube",
                        "obj_balance_tube",
                        "fluid_runtime",
                    ],
                    "mode": "local",
                    "yaw_range_degrees": [0.0, 0.0],
                    "x_offset_range": [-0.01, 0.01],
                    "y_offset_range": [-0.01, 0.01],
                },
                {
                    "objs": [
                        n for n in names if n.startswith("obj_mixed") or n.startswith("obj_bg_")
                    ],
                    "mode": "local",
                    "yaw_range_degrees": [0.0, 0.0],
                    "x_offset_range": [-0.01, 0.01],
                    "y_offset_range": [-0.01, 0.01],
                },
            ],
        },
        "robot_cfg": {
            "position": [0.0, -1.02, 0.31],
            "orientation": [0.7071067812, 0.0, 0.0, 0.7071067812],
        },
        "physx_scene_cfg": {
            "EnableGPUDynamics": True,
            "GpuMaxParticleContacts": 1048576,
            "TimeStepsPerSecond": 120,
        },
        "validation_scope": "static_candidate_only",
    }
    config = (
        "from pathlib import Path\n_ASSETS_DIR = Path(__file__).resolve().parent\nTASKS = "
        + repr({TASK_ID: task}).replace("'__SCENE_PATH__'", "str(_ASSETS_DIR / 'scene.usd')")
        + "\n"
    )
    (vr / "task_config.py").write_text(config, encoding="utf-8")
    manifest = {
        "schema_version": "scenario-forge-task11-vr-candidate/v0.3",
        "scenario_id": TASK_ID,
        "status": "device_qualified_static_pbd_pending_runtime",
        "primary_socket": PRIMARY_SOCKET,
        "balance_socket": BALANCE_SOCKET,
        "target_rack_slot": "slot_15ml_r00_c02",
        "device_xyz_m": list(device_xyz),
        "particle_sets": [
            {"id": "primary_liquid", "count": 2640, "scoring": True},
            {"id": "balance_liquid", "count": 2640, "scoring": False},
        ],
        "claims": {
            "static_stability": False,
            "background_context_static": True,
            "rack_target_slot_insertion_qualified": True,
            "contact_press_qualified": True,
            "button_causes_lid_open": True,
            "lid_remains_open_after_release": True,
            "rotor_open_interlock": True,
            "shutdown_causes_power_off": True,
            "manual_close_and_latch": False,
            "robot_policy_success": False,
            "benchmark_success": False,
        },
        "producer_qualifications": {
            "device": "vr/deps/centrifuge/evidence/lid_behavior/report.json",
            "rack": "vr/deps/rack/evidence/manifest.json",
            "context15": "vr/deps/context15/evidence/manifest.json",
            "context50": "vr/deps/context50/evidence/manifest.json",
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    validation = {
        "schema_version": "aan.multi_liquid_sample_result.v1",
        "sampling": {"spacing_m": 0.001},
        "sets": [
            {
                "id": "primary_liquid",
                "container_prim": "/World/obj_primary_tube",
                "particle_prim": "/World/fluid_runtime/ParticleSets/primary_liquid",
                "particle_count": 2640,
            },
            {
                "id": "balance_liquid",
                "container_prim": "/World/obj_balance_tube",
                "particle_prim": "/World/fluid_runtime/ParticleSets/balance_liquid",
                "particle_count": 2640,
            },
        ],
    }
    (output / "validation_manifest.json").write_text(json.dumps(validation, indent=2) + "\n")
    return output


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--context-assets", type=Path, default=DEFAULT_CONTEXT_ASSETS)
    p.add_argument("--centrifuge", type=Path, default=DEFAULT_CENTRIFUGE_R4)
    args = p.parse_args()
    print(
        build(
            args.out,
            args.context_assets,
            args.centrifuge,
            DEFAULT_BASE,
            DEFAULT_LIQUID,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

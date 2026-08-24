#!/usr/bin/env python3
"""Derive the r3 stir-bar VR scene with a stirrer and fill40 liquid."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import traceback
import zipfile


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scenario_forge.adapters.vr_object_materialization import (  # noqa: E402
    materialize_vr_object_subtrees,
)


TASK_ID = "scientific_workbench_insert_stir_bar_into_beaker"
DEFAULT_BASE = (
    ROOT
    / "outputs/scientific_workbench_insert_stir_bar_into_beaker_vr_r2_20260824"
)
DEFAULT_STIRRER = (
    ROOT
    / "external_artifacts/incoming/from_xinyu/"
    "scientific_workbench_magnetic_stirrer_machine_20260821.zip"
)
DEFAULT_LIQUID = (
    ROOT
    / "outputs/liquid_autofill_tool_beaker_fill_sweep_20260820/"
    "task02_r10_3_no_fluid_source__liquid__obj_beaker__fill40_deps"
)
DEFAULT_OUT = (
    ROOT
    / "outputs/scientific_workbench_insert_stir_bar_into_beaker_vr_r3_20260824"
)
STIRRER_PREFIX = (
    "scientific_workbench_magnetic_stirrer_machine_20260821/"
    "packages/magnetic_stirrer/"
)
STIRRER_XYZ = (0.37, -0.04, 0.755)
OBJECTS = (
    "obj_beaker",
    "obj_steel_plate",
    "obj_stir_bar",
    "obj_magnetic_stirrer",
    "obj_r9_amber_bottle",
    "obj_r9_tip_box",
    "obj_r9_wash_bottle",
    "obj_r9_clear_bottle",
    "obj_r9_pipette_carousel",
)


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


def build(base: Path, stirrer_archive: Path, liquid: Path, output: Path) -> Path:
    from pxr import Gf, PhysxSchema, Sdf, Usd, UsdGeom, UsdPhysics

    base = base.resolve()
    stirrer_archive = stirrer_archive.resolve()
    liquid = liquid.resolve()
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(base, output)
    for stale in (
        output / "handoff",
        output / "vr/evidence/runtime",
        output / "vr/evidence/initial_scene",
    ):
        if stale.exists():
            shutil.rmtree(stale)
    for stale_file in (output / "README_CN.md",):
        if stale_file.exists():
            stale_file.unlink()

    stirrer_dep = output / "vr/deps/objects/obj_magnetic_stirrer"
    with zipfile.ZipFile(stirrer_archive) as source:
        for member in source.namelist():
            if member.startswith(STIRRER_PREFIX) and not member.endswith("/"):
                destination = stirrer_dep / member[len(STIRRER_PREFIX) :]
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read(member))
        evidence_member = (
            "scientific_workbench_magnetic_stirrer_machine_20260821/"
            "evidence/magnetic_stirrer/manifest.json"
        )
        stirrer_evidence = source.read(evidence_member)
    evidence = json.loads(stirrer_evidence)
    if evidence.get("overall_status") != "pass":
        raise RuntimeError("magnetic stirrer archive evidence is not pass")

    scene_path = output / "vr/scene.usd"
    stage = Usd.Stage.Open(str(scene_path))
    root = UsdGeom.Xform.Define(stage, "/World/obj_magnetic_stirrer")
    root.GetPrim().GetReferences().AddReference(
        "deps/objects/obj_magnetic_stirrer/asset.usd",
        "/World/MagneticStirrer",
    )
    root.AddTranslateOp().Set(Gf.Vec3d(*STIRRER_XYZ))

    stage.GetRootLayer().Save()
    stage = None
    materialize_vr_object_subtrees(
        scene_path=scene_path,
        scene_prim_paths=["/World/obj_magnetic_stirrer"],
        runtime_prim_paths=["/World/_scene/obj_magnetic_stirrer"],
        evidence_path=output / "vr/stirrer_materialization.json",
    )

    stage = Usd.Stage.Open(str(scene_path))
    physics_scene = stage.GetPrimAtPath("/World/physicsScene")
    PhysxSchema.PhysxSceneAPI.Apply(physics_scene)
    physics_scene.CreateAttribute(
        "physxScene:broadphaseType", Sdf.ValueTypeNames.Token
    ).Set("GPU")
    physics_scene.CreateAttribute(
        "physxScene:enableGPUDynamics", Sdf.ValueTypeNames.Bool
    ).Set(True)
    physics_scene.CreateAttribute(
        "physxScene:gpuMaxParticleContacts", Sdf.ValueTypeNames.UInt
    ).Set(1048576)
    physics_scene.CreateAttribute(
        "physxScene:solverType", Sdf.ValueTypeNames.Token
    ).Set("TGS")
    physics_scene.CreateAttribute(
        "physxScene:timeStepsPerSecond", Sdf.ValueTypeNames.UInt
    ).Set(120)
    liquid_dep = output / "vr/deps/liquid/producer_overlay.usda"
    liquid_dep.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(liquid / "liquid/producer_overlay.usda", liquid_dep)
    beaker_collision = {
        "/World/obj_beaker/Visual/Source/Rolled_Rim/Torus": "sdf",
        "/World/obj_beaker/Visual/Source/Beaker_Hollow_Body/Beaker_Hollow_Body_Mesh": "sdf",
        "/World/obj_beaker/Visual/Source/Pour_Spout/Pour_Spout_Mesh": "convexHull",
    }
    stage.GetPrimAtPath(
        "/World/obj_beaker/__aan_pbd_collision_proxy/PBD_Unified_Vessel_Mesh"
    ).GetAttribute("physics:collisionEnabled").Set(True)
    for path, approximation in beaker_collision.items():
        prim = stage.GetPrimAtPath(path)
        UsdPhysics.CollisionAPI.Apply(prim).CreateCollisionEnabledAttr(False)
        UsdPhysics.MeshCollisionAPI.Apply(prim).CreateApproximationAttr().Set(
            approximation
        )

    fluid = UsdGeom.Xform.Define(stage, "/World/fluid_runtime")
    fluid.GetPrim().GetReferences().AddReference(
        "deps/liquid/producer_overlay.usda",
        "/__ScenarioForgeLiquid_obj_beaker",
    )
    stage.OverridePrim("/World/fluid_runtime/PhysicsScene").SetActive(False)
    stage.GetRootLayer().Save()

    task = {
        "scene_usd_file_path": {"scene1": "__SCENE_PATH__"},
        "obj_prim_list": [f"/World/_scene/{name}" for name in OBJECTS],
        "layout_randomization": {
            "table": "table",
            "objects": [
                _local_group(["obj_beaker", "fluid_runtime"]),
                _local_group(["obj_steel_plate", "obj_stir_bar"]),
                _local_group(["obj_magnetic_stirrer"]),
                *[
                    _local_group([name])
                    for name in OBJECTS
                    if name.startswith("obj_r9_")
                ],
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
        "prototype_fluid": {
            "status": "qualified_gpu_pbd_loaded_start",
            "particle_count": 816,
            "target_fill_ratio": 0.4,
            "metric_enabled": False,
        },
        "validation_scope": "single_short_scene_integration_only",
    }
    body = repr(task).replace(
        "'__SCENE_PATH__'", "str(_ASSETS_DIR / 'scene.usd')"
    )
    (output / "vr/task_config.py").write_text(
        "from pathlib import Path\n"
        "_ASSETS_DIR = Path(__file__).resolve().parent\n"
        f"TASKS = {{{TASK_ID!r}: {body}}}\n",
        encoding="utf-8",
    )

    scenario_path = output / "scenario.json"
    scenario = json.loads(scenario_path.read_text())
    scenario["instruction"] = (
        "辅助臂固定装有液体的烧杯；操作臂从托盘上拿起磁力搅拌子，"
        "对准烧杯口并放入烧杯。"
    )
    scenario["context_objects"].append(
        {
            "id": "obj_magnetic_stirrer",
            "metric_participation": "none",
            "future_role": "beaker_support_and_stirring_device",
        }
    )
    scenario["initial_liquid"] = {
        "container": "obj_beaker",
        "particle_count": 816,
        "target_fill_ratio": 0.4,
        "producer_claim": "qualified_gpu_pbd_loaded_start",
    }
    scenario_path.write_text(
        json.dumps(scenario, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )

    provenance = output / "provenance"
    provenance.mkdir(exist_ok=True)
    (provenance / "magnetic_stirrer_manifest.json").write_bytes(
        stirrer_evidence
    )
    for name in ("producer_manifest.json", "recipe.json"):
        shutil.copy2(liquid / f"liquid/{name}", provenance / f"liquid_{name}")
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["package_id"] = "scientific_workbench_insert_stir_bar_into_beaker_vr_r3"
    manifest["status"] = "layout_ready_short_runtime_pending"
    manifest["assets"]["magnetic_stirrer"] = evidence["source_sha256"]
    manifest["assets"]["beaker_liquid"] = "fill40_816_particles"
    manifest["claims"].update(
        {
            "short_scene_integration": False,
            "gpu_pbd_loaded_start": True,
            "magnetic_stirring_simulated": False,
            "heating_simulated": False,
            "robot_policy_success": False,
        }
    )
    manifest["source_hashes"]["magnetic_stirrer_archive"] = _sha(
        stirrer_archive
    )
    manifest["source_hashes"]["liquid_producer_overlay"] = _sha(
        liquid / "liquid/producer_overlay.usda"
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--stirrer", type=Path, default=DEFAULT_STIRRER)
    parser.add_argument("--liquid", type=Path, default=DEFAULT_LIQUID)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    app = None
    try:
        try:
            import pxr  # noqa: F401
        except ImportError:
            from isaacsim import SimulationApp

            app = SimulationApp({"headless": True, "multi_gpu": False})
        print(build(args.base, args.stirrer, args.liquid, args.out))
        return 0
    except BaseException:
        traceback.print_exc()
        return 2
    finally:
        if app is not None:
            app.close()


if __name__ == "__main__":
    raise SystemExit(main())

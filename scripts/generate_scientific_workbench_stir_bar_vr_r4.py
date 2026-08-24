#!/usr/bin/env python3
"""Build stir-bar VR r4 with the canonical SDF beaker and dual liquid entrypoints."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import traceback


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scenario_forge.adapters.vr_object_materialization import (  # noqa: E402
    materialize_vr_object_subtrees,
)


TASK_ID = "scientific_workbench_insert_stir_bar_into_beaker"
DEFAULT_BASE = ROOT / "outputs/scientific_workbench_insert_stir_bar_into_beaker_vr_r3_20260824"
DEFAULT_BEAKER = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "scientific_workbench_beaker_325ml_sdf_web_standard_20260824/package"
)
DEFAULT_LIQUID = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "scientific_workbench_stir_bar_beaker_dual_liquid_20260824"
)
DEFAULT_OUT = ROOT / "outputs/scientific_workbench_insert_stir_bar_into_beaker_vr_r4_20260824"
BEAKER_ID = "scientific_workbench_beaker_325ml_sdf_web_standard_v1"
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


def _write_task_config(path: Path, *, scene_name: str, particle_count: int) -> None:
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
            "material": {
                "diffuse_color": [0.32, 0.72, 0.95],
                "emissive_color": [0.02, 0.12, 0.28],
                "opacity": 0.34,
                "ior": 1.333,
                "roughness": 0.02,
            },
            "particle_count": particle_count,
            "particle_sets": ["beaker_liquid"],
            "shared_particle_system": True,
            "metric_enabled": False,
        },
        "validation_scope": "dual_entry_scene_and_static_liquid_only",
    }
    body = repr(task).replace(
        "'__SCENE_PATH__'", f"str(_ASSETS_DIR / {scene_name!r})"
    )
    path.write_text(
        "from pathlib import Path\n"
        "_ASSETS_DIR = Path(__file__).resolve().parent\n"
        f"TASKS = {{{TASK_ID!r}: {body}}}\n",
        encoding="utf-8",
    )


def build_base(base: Path, beaker: Path, output: Path) -> Path:
    from pxr import Gf, Usd, UsdGeom

    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(base, output)
    for stale in (
        output / "handoff",
        output / "vr/evidence/r3_short_run",
        output / "vr/evidence/initial_scene",
    ):
        if stale.exists():
            shutil.rmtree(stale)
    for stale in (
        output / "README_CN.md",
        output / "vr/scene_liquid_edit.usd",
        output / "vr/scene80.usd",
        output / "provenance/liquid_producer_manifest.json",
        output / "provenance/liquid_recipe.json",
    ):
        if stale.exists():
            stale.unlink()

    beaker_dep = output / "vr/deps/objects/obj_beaker"
    if beaker_dep.exists():
        shutil.rmtree(beaker_dep)
    shutil.copytree(beaker, beaker_dep)
    scene = output / "vr/scene.usd"
    stage = Usd.Stage.Open(str(scene), Usd.Stage.LoadAll)
    stage.RemovePrim("/World/fluid_runtime")
    stage.RemovePrim("/World/obj_beaker")
    root = UsdGeom.Xform.Define(stage, "/World/obj_beaker")
    root.AddTranslateOp().Set(Gf.Vec3d(-0.16, -0.17, 0.755))
    root.GetPrim().GetReferences().AddReference(
        "deps/objects/obj_beaker/asset.usd", "/World/Beaker325mlSdf"
    )
    physics_scenes = [
        str(prim.GetPath())
        for prim in stage.Traverse()
        if prim.IsActive() and prim.GetTypeName() == "PhysicsScene"
    ]
    if physics_scenes != ["/World/physicsScene"]:
        raise RuntimeError(f"expected one /World/physicsScene: {physics_scenes}")
    stage.GetRootLayer().Save()
    stage = None
    materialize_vr_object_subtrees(
        scene_path=scene,
        scene_prim_paths=["/World/obj_beaker"],
        runtime_prim_paths=["/World/_scene/obj_beaker"],
        evidence_path=output / "vr/beaker_materialization.json",
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["package_id"] = "scientific_workbench_insert_stir_bar_into_beaker_vr_r4"
    manifest["status"] = "base_ready_liquid_pending"
    manifest["assets"]["beaker"] = BEAKER_ID
    manifest["source_hashes"]["beaker_asset"] = _sha(beaker / "asset.usd")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return output


def add_dual_liquid(output: Path, liquid: Path) -> Path:
    from pxr import Usd, UsdGeom

    manifest = json.loads((liquid / "manifest.json").read_text())
    if manifest.get("schema_version") != "aan.multi_liquid_sample_result.v3":
        raise RuntimeError("r4 requires a v3 dual-entry liquid package")
    if manifest.get("overall_status") != "pass":
        raise RuntimeError("r4 requires a validated v3 liquid package")
    if "PhysxParticleSamplingAPI" not in (
        liquid / manifest["entrypoints"]["editable_samplers_usd"]
    ).read_text():
        raise RuntimeError("editable liquid entry lacks PhysxParticleSamplingAPI")
    liquid_dep = output / "vr/deps/liquid_v3"
    if liquid_dep.exists():
        shutil.rmtree(liquid_dep)
    shutil.copytree(liquid, liquid_dep)
    count = int(manifest["sets"][0]["particle_count"])

    frozen = output / "vr/scene.usd"
    stage = Usd.Stage.Open(str(frozen), Usd.Stage.LoadAll)
    fluid = UsdGeom.Xform.Define(stage, "/World/fluid_runtime")
    fluid.GetPrim().GetReferences().AddReference(
        "deps/liquid_v3/liquid_overlay.usda", "/__ScenarioForgeFluid"
    )
    stage.OverridePrim("/World/fluid_runtime/PhysicsScene").SetActive(False)
    stage.GetRootLayer().Save()

    editable = output / "vr/scene_liquid_edit.usd"
    shutil.copy2(frozen, editable)
    edit_stage = Usd.Stage.Open(str(editable), Usd.Stage.LoadAll)
    edit_fluid = edit_stage.GetPrimAtPath("/World/fluid_runtime")
    edit_fluid.GetReferences().ClearReferences()
    edit_fluid.GetReferences().AddReference(
        "deps/liquid_v3/scene_liquid_edit.usda", "/__ScenarioForgeFluid"
    )
    edit_stage.OverridePrim("/World/fluid_runtime/PhysicsScene").SetActive(False)
    edit_stage.GetRootLayer().Save()

    _write_task_config(output / "vr/task_config.py", scene_name="scene.usd", particle_count=count)
    _write_task_config(
        output / "vr/task_config_liquid_edit.py",
        scene_name="scene_liquid_edit.usd",
        particle_count=count,
    )
    provenance = output / "provenance"
    shutil.copy2(liquid / "manifest.json", provenance / "liquid_v3_manifest.json")
    shutil.copy2(liquid / "recipe.json", provenance / "liquid_v3_recipe.json")
    scenario_path = output / "scenario.json"
    scenario = json.loads(scenario_path.read_text())
    scenario["initial_liquid"] = {
        "container": "obj_beaker",
        "set_id": "beaker_liquid",
        "particle_count": count,
        "target_fill_ratio": 0.4,
        "material": "transparent_blue_task02_r10_3",
        "editable_sampler": "height_z",
    }
    scenario_path.write_text(
        json.dumps(scenario, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    package_manifest_path = output / "manifest.json"
    package_manifest = json.loads(package_manifest_path.read_text())
    package_manifest["status"] = "dual_entry_ready_runtime_pending"
    package_manifest["assets"]["beaker_liquid"] = "v3_dual_editable_frozen"
    package_manifest["claims"].update(
        {
            "editable_liquid_sampler": True,
            "independent_particle_sets": True,
            "single_shared_particle_system": True,
            "transparent_blue_liquid": True,
            "robot_policy_success": False,
        }
    )
    package_manifest_path.write_text(
        json.dumps(package_manifest, indent=2, sort_keys=True) + "\n"
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--beaker", type=Path, default=DEFAULT_BEAKER)
    parser.add_argument("--liquid", type=Path, default=DEFAULT_LIQUID)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-only", action="store_true")
    args = parser.parse_args()
    app = None
    try:
        try:
            import pxr  # noqa: F401
        except ImportError:
            from isaacsim import SimulationApp

            app = SimulationApp({"headless": True, "multi_gpu": False})
        output = build_base(args.base.resolve(), args.beaker.resolve(), args.out.resolve())
        if not args.base_only:
            add_dual_liquid(output, args.liquid.resolve())
        print(output)
        return 0
    except BaseException:
        traceback.print_exc()
        return 2
    finally:
        if app is not None:
            app.close()


if __name__ == "__main__":
    raise SystemExit(main())

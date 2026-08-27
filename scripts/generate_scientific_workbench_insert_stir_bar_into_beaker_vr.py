#!/usr/bin/env python3
"""Generate the VR-only empty-beaker magnetic stir-bar task."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import tarfile


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scenario_forge.adapters.vr_object_materialization import (  # noqa: E402
    materialize_vr_object_subtrees,
)


TASK_ID = "scientific_workbench_insert_stir_bar_into_beaker"
SOURCE_TASK_ID = "scientific_workbench_insert_stir_bar_and_closure"
DEFAULT_BASE = (
    ROOT
    / "outputs/scientific_workbench_task02_r10_3_fill_sweep_20260819/packages/fill40/vr"
)
DEFAULT_STIR_BAR = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "scientific_workbench_magnetic_stir_bar_29_77_20260824/package"
)
DEFAULT_STEEL_PLATE = (
    ROOT
    / "external_artifacts/incoming/from_xinyu/steel_plate_30cm_simready_v1.tar.gz"
)
DEFAULT_OUT = (
    ROOT
    / "outputs/scientific_workbench_insert_stir_bar_into_beaker_vr_r2_20260824"
)
PLATE_XYZ = (0.09, -0.17, 0.755)
STIR_BAR_XYZ = (0.09, -0.17, 0.760)
OBJECT_SOURCES = {
    "obj_beaker": "/World/_scene/obj_obj_beaker",
    "obj_r9_amber_bottle": "/World/_scene/obj_r9_amber_bottle",
    "obj_r9_tip_box": "/World/_scene/obj_r9_tip_box",
    "obj_r9_wash_bottle": "/World/_scene/obj_r9_wash_bottle",
    "obj_r9_clear_bottle": "/World/_scene/obj_r9_clear_bottle",
    "obj_r9_pipette_carousel": "/World/_scene/obj_r9_pipette_carousel",
}
OBJECT_NAMES = (
    "obj_beaker",
    "obj_steel_plate",
    "obj_stir_bar",
    "obj_r9_amber_bottle",
    "obj_r9_tip_box",
    "obj_r9_wash_bottle",
    "obj_r9_clear_bottle",
    "obj_r9_pipette_carousel",
)
TASK_OBJECTS = {"obj_beaker", "obj_stir_bar"}


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _copytree(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def _local_group(name: str) -> dict[str, object]:
    return {
        "objs": [name],
        "mode": "local",
        "yaw_range_degrees": [0.0, 0.0],
        "x_offset_range": [-0.01, 0.01],
        "y_offset_range": [-0.01, 0.01],
    }


def _layout_groups() -> list[dict[str, object]]:
    groups = [
        _local_group(name)
        for name in OBJECT_NAMES
        if name not in {"obj_steel_plate", "obj_stir_bar"}
    ]
    groups.append(
        {
            "objs": ["obj_steel_plate", "obj_stir_bar"],
            "mode": "local",
            "yaw_range_degrees": [0.0, 0.0],
            "x_offset_range": [-0.01, 0.01],
            "y_offset_range": [-0.01, 0.01],
        }
    )
    return groups


def _set_translate(root, xyz: tuple[float, float, float]) -> None:
    from pxr import Gf

    translate = root.GetPrim().GetAttribute("xformOp:translate")
    if translate:
        translate.Set(Gf.Vec3d(*xyz))
        return
    root.AddTranslateOp().Set(Gf.Vec3d(*xyz))


def _install_steel_plate(archive: Path, dest: Path) -> dict[str, object]:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    unpack = dest / "_unpack"
    unpack.mkdir()
    with tarfile.open(archive, "r:gz") as source:
        source.extractall(unpack)
    payload = unpack / "final"
    manifest = json.loads((payload / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("validation_status") != "ok":
        raise RuntimeError("steel plate package is not marked validation_status=ok")
    entry = payload / manifest["entrypoint"]
    if not entry.is_file():
        raise RuntimeError(f"steel plate entrypoint missing: {entry}")
    shutil.copytree(payload / "simready", dest / "simready")
    (dest / "visual").mkdir()
    shutil.copy2(
        payload / "visual/steel_plate_visual.usdc",
        dest / "visual/steel_plate_visual.usdc",
    )
    shutil.copy2(payload / "manifest.json", dest / "manifest.json")
    shutil.copy2(payload / "README.md", dest / "README.md")
    shutil.rmtree(unpack)
    return manifest


def build(
    output: Path,
    base: Path,
    stir_bar: Path,
    steel_plate: Path,
) -> Path:
    from pxr import Gf, Usd, UsdGeom, UsdLux, UsdPhysics

    base = base.resolve()
    stir_bar = stir_bar.resolve()
    steel_plate = steel_plate.resolve()
    producer_manifest_path = stir_bar / "evidence/manifest.json"
    producer_manifest = json.loads(producer_manifest_path.read_text())
    if (
        producer_manifest.get("overall_status") != "pass"
        or not producer_manifest["claims"].get("isaac41_stable_support")
    ):
        raise RuntimeError("29.77 mm stir-bar package is not runtime-qualified")

    if output.exists():
        shutil.rmtree(output)
    vr = output / "vr"
    vr.mkdir(parents=True)
    shutil.copy2(base / "legacy_scene.usd", vr / "legacy_scene.usd")
    _copytree(base / "deps", vr / "deps")
    stir_dependency = vr / "deps/objects/obj_stir_bar"
    _copytree(stir_bar, stir_dependency)
    plate_dependency = vr / "deps/objects/obj_steel_plate"
    plate_manifest = _install_steel_plate(steel_plate, plate_dependency)
    provenance = output / "provenance"
    provenance.mkdir()
    shutil.copy2(
        producer_manifest_path,
        provenance / "magnetic_stir_bar_29_77_manifest.json",
    )
    shutil.copy2(
        plate_dependency / "manifest.json",
        provenance / "steel_plate_30cm_manifest.json",
    )

    scene_path = vr / "scene.usd"
    stage = Usd.Stage.CreateNew(str(scene_path))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.SetMetadata("kilogramsPerUnit", 1.0)
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)

    def reference(path: str, asset: str, prim: str):
        root = UsdGeom.Xform.Define(stage, path)
        root.GetPrim().GetReferences().AddReference(asset, prim)
        return root

    reference("/World/background", "legacy_scene.usd", "/World/_scene/room")
    reference("/World/table", "legacy_scene.usd", "/World/_scene/obj_table")
    for name, source_prim in OBJECT_SOURCES.items():
        reference(f"/World/{name}", "legacy_scene.usd", source_prim)
    plate = reference(
        "/World/obj_steel_plate",
        "deps/objects/obj_steel_plate/simready/steel_plate_30cm_simready.usdc",
        "/SteelPlate",
    )
    _set_translate(plate, PLATE_XYZ)
    stir = reference(
        "/World/obj_stir_bar",
        "deps/objects/obj_stir_bar/asset.usd",
        "/World/MagneticStirBar",
    )
    _set_translate(stir, STIR_BAR_XYZ)

    light = UsdLux.DomeLight.Define(stage, "/World/vr_direct_open_light")
    light.CreateIntensityAttr(750.0)
    physics = UsdPhysics.Scene.Define(stage, "/World/physicsScene")
    physics.CreateGravityDirectionAttr(Gf.Vec3f(0.0, 0.0, -1.0))
    physics.CreateGravityMagnitudeAttr(9.81)
    stage.GetRootLayer().Save()

    materialize_vr_object_subtrees(
        scene_path=scene_path,
        scene_prim_paths=[f"/World/{name}" for name in OBJECT_NAMES],
        runtime_prim_paths=[f"/World/_scene/{name}" for name in OBJECT_NAMES],
        evidence_path=vr / "object_materialization.json",
        prunable_dependency_roots=[stir_dependency, plate_dependency],
    )

    task = {
        "scene_usd_file_path": {"scene1": "__SCENE_PATH__"},
        "obj_prim_list": [f"/World/_scene/{name}" for name in OBJECT_NAMES],
        "layout_randomization": {
            "table": "table",
            "objects": _layout_groups(),
        },
        "robot_cfg": {
            "position": [0.0, -1.02, 0.31],
            "orientation": [0.7071067812, 0.0, 0.0, 0.7071067812],
        },
        "physx_scene_cfg": {
            "BroadphaseType": "GPU",
            "SolverType": "TGS",
            "EnableGPUDynamics": True,
            "TimeStepsPerSecond": 120,
        },
        "validation_scope": "layout_static_and_non_robot_drop_only",
    }
    body = repr(task).replace(
        "'__SCENE_PATH__'", "str(_ASSETS_DIR / 'scene.usd')"
    )
    (vr / "task_config.py").write_text(
        "from pathlib import Path\n"
        "_ASSETS_DIR = Path(__file__).resolve().parent\n"
        f"TASKS = {{{TASK_ID!r}: {body}}}\n",
        encoding="utf-8",
    )
    scenario = {
        "schema_version": "scenario-forge.experimental-vr-task.v1",
        "scenario_id": TASK_ID,
        "source_task_id": SOURCE_TASK_ID,
        "instruction": (
            "辅助臂固定空烧杯；操作臂从托盘上拿起磁力搅拌子，对准烧杯口并放入烧杯。"
        ),
        "steps": [
            {"id": "hold_beaker", "actor": "auxiliary_arm", "skill": "grasp_and_hold"},
            {"id": "pick_stir_bar", "actor": "operating_arm", "skill": "pick"},
            {"id": "align_over_beaker", "actor": "operating_arm", "skill": "align"},
            {"id": "place_inside_beaker", "actor": "operating_arm", "skill": "place"},
        ],
        "success": {
            "experimental_task_success": "stir_bar_inside_beaker_and_beaker_upright",
            "canonical_task04_success": False,
            "canonical_task04_active_score_ceiling": 0.55,
        },
        "context_objects": [
            {"id": name, "metric_participation": "none"}
            for name in OBJECT_NAMES
            if name not in TASK_OBJECTS
        ],
    }
    (output / "scenario.json").write_text(
        json.dumps(scenario, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    manifest = {
        "schema_version": "scenario-forge.vr-handoff.v1",
        "package_id": "scientific_workbench_insert_stir_bar_into_beaker_vr_r2",
        "scenario_id": TASK_ID,
        "status": "package_ready_runtime_validation_pending",
        "entrypoints": {"scene_usd": "vr/scene.usd", "task_config": "vr/task_config.py"},
        "assets": {
            "beaker": "task02_r10.3_empty_beaker_glass_web_standard",
            "stir_bar": producer_manifest["package_id"],
            "steel_plate": plate_manifest.get("asset_id", "steel_plate_30cm"),
        },
        "claims": {
            "vr_package_openable": False,
            "static_stability": False,
            "non_robot_drop_inside_beaker": False,
            "robot_policy_success": False,
            "canonical_task04_success": False,
        },
        "source_hashes": {
            "base_scene": _sha(base / "scene.usd"),
            "stir_bar_manifest": _sha(producer_manifest_path),
            "steel_plate_archive": _sha(steel_plate),
        },
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--stir-bar", type=Path, default=DEFAULT_STIR_BAR)
    parser.add_argument("--steel-plate", type=Path, default=DEFAULT_STEEL_PLATE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(build(args.out, args.base, args.stir_bar, args.steel_plate))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

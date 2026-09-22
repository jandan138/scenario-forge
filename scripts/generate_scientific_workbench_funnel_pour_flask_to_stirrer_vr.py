#!/usr/bin/env python3
"""Build the funnel-pour-then-place-on-stirrer VR collection handoff."""

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

from scenario_forge.adapters.isaac41_vr600_profile import PROFILE_ID  # noqa: E402
from scenario_forge.adapters.vr_object_materialization import (  # noqa: E402
    materialize_vr_object_subtrees,
)


SCENE_USDS = Path(
    "/cpfs/shared/simulation/chenjiantong/scene_usds/scientific_experiments"
)
TASK04_SCENE = (
    SCENE_USDS / "task_04_pour_liquid_with_funnel/seen_scene_1/scene.usd"
)
TASK01_SCENE = (
    SCENE_USDS / "task_01_pour_flask_to_cylinder/seen_scene_1/scene.usd"
)
TASK10_SCENE = (
    SCENE_USDS / "task_10_titration_experiment/seen_scene_1/scene.usd"
)
DEFAULT_OUTPUT = (
    ROOT / "outputs/scientific_workbench_funnel_pour_flask_to_stirrer_vr_r1_2_20260920"
)
TASK_ID = "scientific_workbench_funnel_pour_flask_to_stirrer"
HANDOFF_ID = "scientific_workbench_funnel_pour_flask_to_stirrer_vr_r1_2"
TABLE_SURFACE = "/World/table/obj_table/table/Surface/Source/mesh"
TABLE_HEIGHT_M = 0.755

FLASK_XYZ = (-0.11, -0.16, TABLE_HEIGHT_M)
STIRRER_XYZ = (0.53, -0.205, TABLE_HEIGHT_M)

REMOVE_PRIMS = (
    "/World/obj_beaker",
    "/World/obj_plate",
    "/World/obj_glass_rod",
    "/World/obj_acrylic_rod_rack",
    "/World/obj_target_reagent_bottle",
)
REQUIRED_OBJECTS = (
    "obj_funnel",
    "obj_funnel_rack",
    "obj_graduated_cylinder",
    "obj_conical_flask",
    "obj_magnetic_stirrer",
)
CONTEXT_OBJECTS = (
    "obj_r9_amber_bottle",
    "obj_r9_tip_box",
    "obj_r9_wash_bottle",
    "obj_r9_clear_bottle",
    "obj_r9_pipette_carousel",
)


@dataclass(frozen=True)
class FunnelPourHandoff:
    root: Path
    archive: Path
    manifest: Path
    scene: Path
    config: Path


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _set_translate(prim: Any, xyz: tuple[float, float, float]) -> None:
    from pxr import Gf, Sdf, UsdGeom

    attr = prim.GetAttribute("xformOp:translate")
    if attr and attr.IsValid():
        if attr.GetTypeName() == Sdf.ValueTypeNames.Float3:
            attr.Set(Gf.Vec3f(*xyz))
        else:
            attr.Set(Gf.Vec3d(*xyz))
        return
    UsdGeom.Xformable(prim).AddTranslateOp(UsdGeom.XformOp.PrecisionDouble).Set(
        Gf.Vec3d(*xyz)
    )


def _copy_prim(source_scene: Path, source_path: str, dest_stage: Any, dest_path: str) -> None:
    from pxr import Sdf, Usd

    source = Usd.Stage.Open(str(source_scene), Usd.Stage.LoadAll)
    if source is None:
        raise FileNotFoundError(source_scene)
    flattened = source.Flatten(addSourceFileComment=False)
    layer = dest_stage.GetRootLayer()
    existing = layer.GetPrimAtPath(dest_path)
    if existing is not None:
        edit = Sdf.BatchNamespaceEdit()
        edit.Add(Sdf.NamespaceEdit.Remove(dest_path))
        if not layer.Apply(edit):
            raise RuntimeError(f"cannot replace {dest_path}")
    if not Sdf.CopySpec(flattened, source_path, layer, dest_path):
        raise RuntimeError(f"cannot copy {source_path} from {source_scene}")


def _hide_table_surface(stage: Any) -> None:
    from pxr import UsdGeom

    prim = stage.GetPrimAtPath(TABLE_SURFACE)
    if not prim.IsValid():
        raise RuntimeError(f"missing scene_usds table surface: {TABLE_SURFACE}")
    imageable = UsdGeom.Imageable(prim)
    imageable.MakeInvisible()


FLASK_GLASS_MDLS = (
    "OmniSurfacePresets.mdl",
    "OmniSurface.mdl",
    "OmniSurfaceLite.mdl",
)
FLASK_MDL_SHADER = (
    "/World/obj_conical_flask/ConicalFlask90x35Warp/Visual/Source/"
    "__aan_materials/OmniSurface_Glass/Shader"
)


def _install_flask_materials(package_root: Path) -> None:
    source = (TASK01_SCENE.parent / "SubUSDs" / "materials").resolve()
    dest = package_root / "SubUSDs" / "materials"
    dest.mkdir(parents=True, exist_ok=True)
    for name in FLASK_GLASS_MDLS:
        target = dest / name
        if not target.exists():
            shutil.copy2(source / name, target)


def _relocate_escaped_assets(stage: Any, package_root: Path) -> None:
    from pxr import Sdf

    package_root = package_root.resolve()
    for prim in stage.TraverseAll():
        for attribute in prim.GetAttributes():
            value = attribute.Get()
            if not isinstance(value, Sdf.AssetPath) or not value.path:
                continue
            raw = value.path
            resolved = Path(raw)
            if not resolved.is_absolute():
                resolved = (package_root / raw).resolve()
            else:
                resolved = resolved.resolve()
            try:
                resolved.relative_to(package_root)
                continue
            except ValueError:
                pass
            if not resolved.is_file():
                raise FileNotFoundError(f"escaped asset missing: {raw}")
            dest = package_root / "SubUSDs" / Path(*resolved.parts[-2:])
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(resolved, dest)
            attribute.Set(Sdf.AssetPath("./" + dest.relative_to(package_root).as_posix()))


def _add_direct_open_light(stage: Any) -> None:
    from pxr import Gf, UsdLux

    if stage.GetPrimAtPath("/World/vr_direct_open_light").IsValid():
        return
    light = UsdLux.DomeLight.Define(stage, "/World/vr_direct_open_light")
    light.CreateIntensityAttr(750.0)
    light.CreateColorAttr(Gf.Vec3f(1.0, 1.0, 1.0))


def _local_group(objects: list[str], *, fixed: bool = False) -> dict[str, Any]:
    span = [0.0, 0.0] if fixed else [-0.01, 0.01]
    return {
        "objs": objects,
        "mode": "local",
        "yaw_range_degrees": [0.0, 0.0],
        "x_offset_range": span,
        "y_offset_range": span,
    }


def _task_config() -> str:
    objects = list(REQUIRED_OBJECTS) + list(CONTEXT_OBJECTS)
    task = {
        "scene_usd_file_path": {
            "scene1": "__SCENE_PATH__",
        },
        "obj_prim_list": [f"/World/_scene/{name}" for name in objects],
        "layout_randomization": {
            "table": "table",
            "objects": [
                _local_group(["obj_funnel", "obj_funnel_rack"]),
                _local_group(["obj_conical_flask"]),
                _local_group(["obj_magnetic_stirrer"]),
                _local_group(["obj_graduated_cylinder"], fixed=True),
                *[_local_group([name]) for name in CONTEXT_OBJECTS],
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
        "claim_scope": "layout_and_authored_pbd_at_rest",
        "canonical_task13_success": False,
    }
    body = repr(task).replace(
        "'__SCENE_PATH__'",
        f'str(_ASSETS_DIR / "scenes/{TASK_ID}/scene.usd")',
    )
    return (
        "# Merge this TASKS entry into the VR plugin mapping.\n"
        "from pathlib import Path\n"
        "_ASSETS_DIR = Path(__file__).resolve().parents[3]\n"
        f"TASKS = {{{TASK_ID!r}: {body}}}\n"
    )


def _task() -> dict[str, Any]:
    return {
        "schema_version": "task/v0.4",
        "task_id": TASK_ID,
        "instruction": (
            "从漏斗架拿起漏斗并插入桌面上的锥形瓶口，用量筒经漏斗倒液，"
            "将漏斗放回原架槽，最后把锥形瓶放到磁力搅拌器上。本包不做塞子。"
        ),
        "claim_scope": "layout_and_authored_pbd_at_rest",
        "canonical_task13_success": False,
        "steps": [
            {"id": "pick_funnel_from_rack", "skill": "pick"},
            {"id": "insert_funnel_in_flask", "skill": "insert"},
            {"id": "pour_cylinder_through_funnel", "skill": "pour"},
            {"id": "return_funnel_to_rack", "skill": "place"},
            {"id": "place_flask_on_stirrer", "skill": "place"},
        ],
    }


def _metrics() -> dict[str, Any]:
    return {
        "schema_version": "metrics/v0.4",
        "aggregation": {
            "type": "weighted_progress_score",
            "normalization": "declared_sum",
            "inactive_treatment": "zero",
            "primary_metric_id": "funnel_returned_to_rack",
        },
        "metrics": [
            {"id": "funnel_lifted_from_rack", "weight": 0.15, "active": True},
            {"id": "funnel_inserted_in_flask", "weight": 0.20, "active": True},
            {
                "id": "liquid_transfer_majority",
                "weight": 0.20,
                "active": False,
                "requires": ["liquid_sim.contained_volume_ratio"],
            },
            {"id": "funnel_returned_to_rack", "weight": 0.20, "active": True},
            {"id": "flask_placed_on_stirrer", "weight": 0.25, "active": True},
        ],
    }


def _configure_scene(scene: Path) -> None:
    from pxr import Usd, UsdGeom

    stage = Usd.Stage.Open(str(scene), Usd.Stage.LoadAll)
    if stage is None:
        raise RuntimeError(f"cannot open {scene}")
    if stage.GetDefaultPrim() is None or stage.GetDefaultPrim().GetPath() != "/World":
        world = stage.GetPrimAtPath("/World")
        if world.IsValid():
            stage.SetDefaultPrim(world)

    for path in REMOVE_PRIMS:
        if stage.GetPrimAtPath(path).IsValid():
            stage.RemovePrim(path)

    preview = stage.GetPrimAtPath("/World/obj_funnel_rack/Preview")
    if preview.IsValid():
        preview.SetActive(False)

    _copy_prim(TASK01_SCENE, "/World/obj_conical_flask", stage, "/World/obj_conical_flask")
    flask = stage.GetPrimAtPath("/World/obj_conical_flask")
    if not stage.GetPrimAtPath(
        "/World/obj_conical_flask/ConicalFlask90x35Warp"
    ).IsValid():
        raise RuntimeError("90x35 conical flask subtree missing after copy")
    _set_translate(flask, FLASK_XYZ)

    _copy_prim(
        TASK10_SCENE,
        "/World/obj_magnetic_stirrer",
        stage,
        "/World/obj_magnetic_stirrer",
    )
    _set_translate(stage.GetPrimAtPath("/World/obj_magnetic_stirrer"), STIRRER_XYZ)

    _install_flask_materials(Path(stage.GetRootLayer().realPath).parent)
    _relocate_escaped_assets(stage, Path(stage.GetRootLayer().realPath).parent)
    shader = stage.GetPrimAtPath(FLASK_MDL_SHADER)
    if shader.IsValid():
        from pxr import Sdf

        shader.GetAttribute("info:mdl:sourceAsset").Set(
            Sdf.AssetPath("./SubUSDs/materials/OmniSurfacePresets.mdl")
        )
    _hide_table_surface(stage)
    _add_direct_open_light(stage)
    stage.GetPrimAtPath("/World").SetCustomDataByKey("scenario_forge:taskId", TASK_ID)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.GetRootLayer().Save()


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _closure(scene: Path) -> dict[str, Any]:
    from pxr import UsdUtils

    layers, dependencies, unresolved = UsdUtils.ComputeAllDependencies(str(scene))
    return {
        "layer_count": len(layers),
        "asset_count": len(dependencies),
        "unresolved": [str(item) for item in unresolved],
        "dependencies": [str(item) for item in dependencies],
    }


def build_handoff(output: Path = DEFAULT_OUTPUT) -> FunnelPourHandoff:
    output = Path(output).resolve()
    for required in (TASK04_SCENE, TASK01_SCENE, TASK10_SCENE):
        if not required.is_file():
            raise FileNotFoundError(required)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    shutil.copy2(TASK04_SCENE, output / "scene.usd")
    shutil.copytree((TASK04_SCENE.parent / "SubUSDs").resolve(), output / "SubUSDs")
    _configure_scene(output / "scene.usd")

    object_names = list(REQUIRED_OBJECTS) + list(CONTEXT_OBJECTS)
    materialize_vr_object_subtrees(
        scene_path=output / "scene.usd",
        scene_prim_paths=[f"/World/{name}" for name in object_names],
        runtime_prim_paths=[f"/World/_scene/{name}" for name in object_names],
        evidence_path=output / "object_materialization.json",
        prunable_dependency_roots=(output / "SubUSDs",),
    )
    closure = _closure(output / "scene.usd")
    if closure["unresolved"]:
        raise RuntimeError(f"unresolved scene dependencies: {closure['unresolved']}")

    config_path = output / "task_config.py"
    _write_text(config_path, _task_config())
    _write_text(
        output / "task.yaml",
        yaml.safe_dump(_task(), allow_unicode=True, sort_keys=False),
    )
    _write_text(
        output / "metrics.yaml",
        yaml.safe_dump(_metrics(), allow_unicode=True, sort_keys=False),
    )
    _write_text(
        output / "evidence/package_closure.json",
        json.dumps(closure, indent=2, sort_keys=True) + "\n",
    )
    _write_text(
        output / "README_CN.md",
        """# 漏斗倒液后上搅拌器 VR r1.2

用 Isaac Sim 4.1 直接打开 `scene.usd`。量筒内液体是从
`task_04_pour_liquid_with_funnel` 原样拷来的 986 粒 GPU PBD，青绿配方，
3 mm contact/rest。本包只保证布局和静止粒子，不声称液体能顺利过漏斗、
不声称倒通，也不声称机器人或 VR 策略成功。

采集顺序：从木制漏斗架拿漏斗 → 插入桌面上的 90×35 锥形瓶 →
经漏斗倒液 → 漏斗放回原架槽 → 把锥形瓶放到磁力搅拌器上。
不做塞子，也不再放扁圆柱底座。r1 / r1.1 底座在 Isaac 4.5 Play 后仍晃，
因此瓶子直接坐在桌面上。

量筒粒子是世界坐标烘焙的，因此量筒不做 XY 随机化。漏斗与漏斗架共组，
锥形瓶单独一组。
""",
    )
    manifest = {
        "schema_version": "scenario-forge.funnel-pour-flask-to-stirrer-vr/v0.1",
        "package_id": HANDOFF_ID,
        "task_id": TASK_ID,
        "status": "scene_built_runtime_pending",
        "entrypoints": {
            "scene": "scene.usd",
            "task_config": "task_config.py",
            "task": "task.yaml",
            "metrics": "metrics.yaml",
        },
        "source_hashes": {
            "task04_scene": _sha(TASK04_SCENE),
            "task01_scene": _sha(TASK01_SCENE),
            "task10_scene": _sha(TASK10_SCENE),
        },
        "assets": {
            "conical_flask": "ConicalFlask90x35Warp",
            "liquid": {
                "particle_count": 986,
                "particle_contact_offset_m": 0.003,
                "rest_offset_m": 0.003,
                "source": "task_04_pour_liquid_with_funnel",
            },
        },
        "closure": {
            "layer_count": closure["layer_count"],
            "asset_count": closure["asset_count"],
            "unresolved": [],
        },
        "isaac41_pour_run": "not_run",
        "claims": {
            "layout_authored": True,
            "authored_pbd_at_rest": True,
            "pbd_particle_count": 986,
            "funnel_rack_pick_and_return": True,
            "flask_starts_on_table": True,
            "flask_starts_on_task_local_base": False,
            "stirrer_is_terminal_place_target": True,
            "stopper_included": False,
            "liquid_transfer_verified": False,
            "funnel_conduit_qualified": False,
            "canonical_task13_success": False,
            "isaac41_pour_run": "not_run",
            "vr_action_collection_ready": False,
            "robot_policy_success": False,
            "benchmark_success": False,
        },
    }
    manifest_path = output / "manifest.json"
    _write_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    parity = {
        "schema_version": "scenario-forge-vr-ebench-parity/v0.1",
        "status": "layout_only_runtime_pending",
        "vr_task_id": TASK_ID,
        "shared_runtime_profile": PROFILE_ID,
        "vr_presentation_policy": {
            "policy": "standard_workbench_surface_hidden",
            "status": "applied_scene_usds_table_path",
            "prim_path": TABLE_SURFACE,
            "note": (
                "apply_standard_workbench_vr_presentation does not know "
                "obj_table/table/Surface/Source/mesh; visibility is set on that path."
            ),
        },
        "exceptions": [
            "robot joint initialization not authored in task_config",
            "isaac41 pour / headset load not_run",
        ],
    }
    _write_text(
        output / "parity_manifest.json",
        json.dumps(parity, indent=2, sort_keys=True) + "\n",
    )

    handoff = output / "handoff"
    handoff.mkdir()
    archive = handoff / f"{HANDOFF_ID}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for path in sorted(output.rglob("*")):
            if path.is_file() and handoff not in path.parents:
                target.write(path, path.relative_to(output))
    (archive.with_suffix(archive.suffix + ".sha256")).write_text(
        _sha(archive) + "\n", encoding="utf-8"
    )
    return FunnelPourHandoff(
        root=output,
        archive=archive,
        manifest=manifest_path,
        scene=output / "scene.usd",
        config=config_path,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = build_handoff(args.out)
    print(result.archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build the boat-pour-then-stir Isaac 4.5 VR collection handoff."""

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
TASK14_SCENE = (
    SCENE_USDS / "task_14_fixed_weight_weighing/seen_scene_1/scene.usd"
)
TASK04_SCENE = (
    SCENE_USDS / "task_04_pour_liquid_with_funnel/seen_scene_1/scene.usd"
)
TASK02_SCENE = (
    SCENE_USDS / "task_02_pour_liquid_and_stir/seen_scene_1/scene.usd"
)
R57_SCENE = (
    ROOT
    / "outputs/task09_powder_bottle_r5_7_20260915/handoff/task09_powder_bottle_r5_7/scene.usda"
)
DEFAULT_OUTPUT = (
    ROOT / "outputs/scientific_workbench_boat_pour_stir_vr_r1_20260920"
)
TASK_ID = "scientific_workbench_boat_pour_stir"
HANDOFF_ID = "scientific_workbench_boat_pour_stir_vr_r1"
TABLE_SURFACE = "/World/table/obj_table/table/Surface/Source/mesh"
GRAIN_COUNT = 30
GRAIN_MASS_KG = 2.155132560362598e-6
TARE_G = 10.0
# force_r1 BalanceState requires a positive finite target; this is not a 1 g task.
INSTRUMENT_TARGET_G = 1.0
PLATE_XYZ = (-0.34, -0.20, 0.755)
BOAT_PAN_GAP_M = 0.002
PROXY_CONTACT_OFFSET_M = 0.0005
PROXY_REST_OFFSET_M = 0.00015

TASK14_OBJECTS = (
    "obj_analytical_balance",
    "obj_weighing_boat",
    "obj_beaker",
    "obj_graduated_cylinder",
    "obj_glass_rod",
    "obj_acrylic_rod_rack",
    "obj_sampling_spoon",
    "obj_weighing_bottle_body",
    "obj_powder_bottle",
    "obj_r9_amber_bottle",
    "obj_r9_tip_box",
    "obj_r9_wash_bottle",
    "obj_r9_clear_bottle",
    "obj_r9_pipette_carousel",
)
BALANCE_LINKS = (
    "obj_analytical_balance/Instance/RightTare",
    "obj_analytical_balance/Instance/Body",
    "obj_analytical_balance/Instance/WeighingPan",
)
RANDOMIZED_ALONE = (
    "obj_beaker",
    "obj_sampling_spoon",
    "obj_weighing_bottle_body",
    "obj_powder_bottle",
    "obj_plate",
    "obj_r9_amber_bottle",
    "obj_r9_tip_box",
    "obj_r9_wash_bottle",
    "obj_r9_clear_bottle",
    "obj_r9_pipette_carousel",
)


@dataclass(frozen=True)
class BoatPourStirHandoff:
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
    UsdGeom.Imageable(prim).MakeInvisible()


def _add_direct_open_light(stage: Any) -> None:
    from pxr import Gf, UsdLux

    if stage.GetPrimAtPath("/World/vr_direct_open_light").IsValid():
        return
    light = UsdLux.DomeLight.Define(stage, "/World/vr_direct_open_light")
    light.CreateIntensityAttr(750.0)
    light.CreateColorAttr(Gf.Vec3f(1.0, 1.0, 1.0))


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


def _world_box(stage: Any, path: str) -> Any:
    from pxr import Usd, UsdGeom

    prim = stage.GetPrimAtPath(path)
    if not prim.IsValid():
        raise RuntimeError(f"missing prim {path}")
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
    return cache.ComputeWorldBound(prim).ComputeAlignedBox()


def _place_boat_on_pan(stage: Any) -> None:
    from pxr import Gf

    boat = stage.GetPrimAtPath("/World/obj_weighing_boat")
    if not boat.IsValid():
        raise RuntimeError("missing weighing boat")
    boat_box = _world_box(stage, "/World/obj_weighing_boat")
    pan_box = _world_box(stage, "/World/obj_analytical_balance/Instance/WeighingPan")
    translate = boat.GetAttribute("xformOp:translate").Get()
    if translate is None:
        raise RuntimeError("weighing boat has no translate")
    current = Gf.Vec3d(float(translate[0]), float(translate[1]), float(translate[2]))
    boat_min = boat_box.GetMin()
    pan_mid = pan_box.GetMidpoint()
    new_xyz = (
        float(pan_mid[0] + (current[0] - boat_box.GetMidpoint()[0])),
        float(pan_mid[1] + (current[1] - boat_box.GetMidpoint()[1])),
        float(pan_box.GetMax()[2] + (current[2] - boat_min[2]) + BOAT_PAN_GAP_M),
    )
    _set_translate(boat, new_xyz)


def _tune_boat_proxy_collisions(stage: Any) -> None:
    from pxr import Usd, UsdPhysics

    proxy = stage.GetPrimAtPath("/World/obj_weighing_boat/PowderProxy")
    if not proxy.IsValid():
        raise RuntimeError("missing weighing-boat powder proxy")
    for prim in Usd.PrimRange(proxy):
        if not prim.HasAPI(UsdPhysics.CollisionAPI):
            continue
        contact = prim.GetAttribute("physxCollision:contactOffset")
        rest = prim.GetAttribute("physxCollision:restOffset")
        if contact:
            contact.Set(float(PROXY_CONTACT_OFFSET_M))
        if rest:
            rest.Set(float(PROXY_REST_OFFSET_M))


def _grain_positions(stage: Any) -> list[tuple[float, float, float]]:
    floor_box = _world_box(stage, "/World/obj_weighing_boat/PowderProxy/Floor")
    inset = 0.004
    xs = [
        float(floor_box.GetMin()[0] + inset + (floor_box.GetSize()[0] - 2 * inset) * i / 5)
        for i in range(6)
    ]
    ys = [
        float(floor_box.GetMin()[1] + inset + (floor_box.GetSize()[1] - 2 * inset) * j / 4)
        for j in range(5)
    ]
    grain_z = float(floor_box.GetMax()[2] + 0.0009)
    return [(x, y, grain_z) for y in ys for x in xs]


def _author_grains(stage: Any) -> None:
    from pxr import Sdf, Usd

    source = Usd.Stage.Open(str(R57_SCENE), Usd.Stage.LoadAll)
    if source is None:
        raise FileNotFoundError(R57_SCENE)
    prototype = "/World/obj_powder_grain_00000"
    if not source.GetPrimAtPath(prototype).IsValid():
        raise RuntimeError("r5.7 grain prototype missing")
    layer = stage.GetRootLayer()
    positions = _grain_positions(stage)
    if len(positions) != GRAIN_COUNT:
        raise RuntimeError(f"expected {GRAIN_COUNT} grain slots, got {len(positions)}")
    if not stage.GetPrimAtPath("/World/PowderLooks/Surface").IsValid():
        raise RuntimeError("task_14 PowderLooks/Surface missing")
    if not Sdf.CopySpec(source.GetRootLayer(), prototype, layer, prototype):
        raise RuntimeError("cannot copy r5.7 grain prototype")
    for index in range(1, GRAIN_COUNT):
        dest = f"/World/obj_powder_grain_{index:05d}"
        if not Sdf.CopySpec(layer, prototype, layer, dest):
            raise RuntimeError(f"cannot duplicate grain {dest}")
    for index, xyz in enumerate(positions):
        path = f"/World/obj_powder_grain_{index:05d}"
        grain = stage.GetPrimAtPath(path)
        _set_translate(grain, xyz)
        grain.GetAttribute("physics:mass").Set(float(GRAIN_MASS_KG))


def _install_task04_pbd(stage: Any) -> None:
    from pxr import Gf, Usd

    source = Usd.Stage.Open(str(TASK04_SCENE), Usd.Stage.LoadAll)
    if source is None:
        raise FileNotFoundError(TASK04_SCENE)
    src_mid = _world_box(source, "/World/obj_graduated_cylinder").GetMidpoint()
    dest_mid = _world_box(stage, "/World/obj_graduated_cylinder").GetMidpoint()
    delta = dest_mid - src_mid
    for path in ("/World/ParticleSystem", "/World/ParticleSet", "/World/fluid_runtime"):
        _copy_prim(TASK04_SCENE, path, stage, path)
    particle_set = stage.GetPrimAtPath("/World/ParticleSet")
    if not particle_set.IsValid():
        raise RuntimeError("ParticleSet missing after copy")
    points = particle_set.GetAttribute("points").Get()
    if points is None:
        raise RuntimeError("ParticleSet has no points")
    shifted = [Gf.Vec3f(p[0] + delta[0], p[1] + delta[1], p[2] + delta[2]) for p in points]
    particle_set.GetAttribute("points").Set(shifted)
    for name in ("primvars:displayColor", "primvars:displayOpacity"):
        attr = particle_set.GetAttribute(name)
        if attr and attr.HasAuthoredValue():
            attr.Clear()


def _install_plate(stage: Any) -> None:
    _copy_prim(TASK02_SCENE, "/World/obj_plate", stage, "/World/obj_plate")
    plate = stage.GetPrimAtPath("/World/obj_plate")
    if not plate.IsValid():
        raise RuntimeError("obj_plate missing after copy")
    _set_translate(plate, PLATE_XYZ)


def _author_physics_scene(stage: Any) -> None:
    from pxr import Gf, Sdf, UsdPhysics

    for prim in list(stage.TraverseAll()):
        if prim.GetTypeName() == "PhysicsScene" and str(prim.GetPath()) != "/World/PhysicsScene":
            stage.RemovePrim(prim.GetPath())
    physics = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
    physics.CreateGravityDirectionAttr(Gf.Vec3f(0, 0, -1))
    physics.CreateGravityMagnitudeAttr(9.81)
    prim = physics.GetPrim()
    prim.AddAppliedSchema("PhysxSceneAPI")
    for name, kind, value in (
        ("enableGPUDynamics", Sdf.ValueTypeNames.Bool, True),
        ("broadphaseType", Sdf.ValueTypeNames.Token, "GPU"),
        ("solverType", Sdf.ValueTypeNames.Token, "TGS"),
        ("timeStepsPerSecond", Sdf.ValueTypeNames.UInt, 120),
    ):
        prim.CreateAttribute(f"physxScene:{name}", kind).Set(value)
    system = stage.GetPrimAtPath("/World/ParticleSystem")
    if system.IsValid():
        system.CreateRelationship("simulationOwner", custom=False).SetTargets(
            ["/World/PhysicsScene"]
        )


def _configure_balance(stage: Any) -> None:
    from pxr import Sdf

    balance = stage.GetPrimAtPath("/World/obj_analytical_balance")
    if not balance.IsValid():
        raise RuntimeError("missing analytical balance")
    balance.GetAttribute("balance:tare_g").Set(float(TARE_G))
    balance.GetAttribute("balance:tared").Set(True)
    balance.GetAttribute("balance:lcd_readout").Set("0.06 g")
    balance.GetAttribute("balance:resolution_g").Set(0.01)
    balance.GetAttribute("balance:measurement_source").Set("pan_contact_force")
    balance.GetAttribute("balance:success").Set(False)
    balance.GetAttribute("balance:completed_net_g").Set(0.0)
    if not balance.HasAttribute("balance:target_g"):
        balance.CreateAttribute("balance:target_g", Sdf.ValueTypeNames.Double)
    balance.GetAttribute("balance:target_g").Set(float(INSTRUMENT_TARGET_G))


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
    objects = list(TASK14_OBJECTS) + ["obj_plate"]
    registered = [f"/World/_scene/{name}" for name in objects]
    registered.extend(f"/World/_scene/{link}" for link in BALANCE_LINKS)
    task = {
        "scene_usd_file_path": {
            "scene1": "__SCENE_PATH__",
        },
        "obj_prim_list": registered,
        "layout_randomization": {
            "table": "table",
            "objects": [
                _local_group(["obj_analytical_balance", "obj_weighing_boat"], fixed=True),
                _local_group(["obj_graduated_cylinder"], fixed=True),
                _local_group(["obj_glass_rod", "obj_acrylic_rod_rack"]),
                *[_local_group([name]) for name in RANDOMIZED_ALONE],
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
        "claim_scope": "layout_authored_pbd_and_rigid_grains_at_rest",
        "qualified_runtime": "Isaac Sim 4.5.0",
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
            "称量舟已在天平上并已去皮，内有 30 粒刚体粉末。拿起称量舟把颗粒倒入空烧杯，"
            "把称量舟放回桌面，再拿起量筒把液体倒入烧杯，最后拿起玻璃棒搅拌。"
        ),
        "claim_scope": "layout_authored_pbd_and_rigid_grains_at_rest",
        "steps": [
            {"id": "boat_poured_toward_beaker", "skill": "pour"},
            {"id": "boat_returned_to_table", "skill": "place"},
            {"id": "cylinder_poured_toward_beaker", "skill": "pour"},
            {"id": "rod_stirring_in_beaker", "skill": "stir"},
        ],
    }


def _metrics() -> dict[str, Any]:
    return {
        "schema_version": "metrics/v0.4",
        "aggregation": {
            "type": "weighted_progress_score",
            "normalization": "declared_sum",
            "inactive_treatment": "zero",
            "primary_metric_id": "rod_stirring_in_beaker",
        },
        "metrics": [
            {"id": "boat_poured_toward_beaker", "weight": 0.25, "active": True},
            {"id": "boat_returned_to_table", "weight": 0.25, "active": True},
            {"id": "cylinder_poured_toward_beaker", "weight": 0.25, "active": True},
            {"id": "rod_stirring_in_beaker", "weight": 0.25, "active": True},
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
    if stage.GetPrimAtPath("/World/powder_pbd").IsValid():
        stage.RemovePrim("/World/powder_pbd")
    _place_boat_on_pan(stage)
    _tune_boat_proxy_collisions(stage)
    _author_grains(stage)
    _install_task04_pbd(stage)
    _install_plate(stage)
    _author_physics_scene(stage)
    _configure_balance(stage)
    _relocate_escaped_assets(stage, Path(stage.GetRootLayer().realPath).parent)
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


def build_handoff(output: Path = DEFAULT_OUTPUT) -> BoatPourStirHandoff:
    output = Path(output).resolve()
    for required in (TASK14_SCENE, TASK04_SCENE, TASK02_SCENE, R57_SCENE):
        if not required.is_file():
            raise FileNotFoundError(required)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    shutil.copy2(TASK14_SCENE, output / "scene.usd")
    shutil.copytree((TASK14_SCENE.parent / "SubUSDs").resolve(), output / "SubUSDs")
    _configure_scene(output / "scene.usd")

    object_names = list(TASK14_OBJECTS) + ["obj_plate"]
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
        """# 称量舟倒粒倒液搅拌 VR r1

用 Isaac Sim 4.5 直接打开 `scene.usd`。开局称量舟在秤盘上，已按 10 g 去皮，
舟内 30 粒 r5.7 刚体粉（单粒 2.155 mg）。量筒液体是从
`task_04_pour_liquid_with_funnel` 平移过来的 986 粒 GPU PBD。玻璃棒用完的托盘
来自 `task_02_pour_liquid_and_stir`。桌面其余 task_14 物体原位保留。

本包只保证布局、静止刚体粒和静止 PBD。不声称颗粒会倒进烧杯、液体会倒通、
会溶解、headset 可采，也不声称机器人或 VR 策略成功。天平 LCD 开局写成
`0.06 g`，冷启动后的真实读数要在 Isaac 4.5 里再看。

采集顺序：拿起称量舟把颗粒倒入烧杯 → 舟放回桌面 → 量筒倒液入烧杯 →
拿起玻璃棒搅拌。

量筒粒子和舟内颗粒都是世界坐标，因此天平+舟、量筒都不做 XY 随机化。
棒与架共组。
""",
    )
    manifest = {
        "schema_version": "scenario-forge.boat-pour-stir-vr/v0.1",
        "package_id": HANDOFF_ID,
        "task_id": TASK_ID,
        "status": "scene_built_runtime_pending",
        "qualified_runtime": "Isaac Sim 4.5.0",
        "entrypoints": {
            "scene": "scene.usd",
            "task_config": "task_config.py",
            "task": "task.yaml",
            "metrics": "metrics.yaml",
        },
        "source_hashes": {
            "task14_scene": _sha(TASK14_SCENE),
            "task04_scene": _sha(TASK04_SCENE),
            "task02_scene": _sha(TASK02_SCENE),
            "r57_scene": _sha(R57_SCENE),
        },
        "assets": {
            "grains": {
                "count": GRAIN_COUNT,
                "mass_per_grain_kg": GRAIN_MASS_KG,
                "source": "task09_powder_bottle_r5_7",
            },
            "liquid": {
                "particle_count": 986,
                "particle_contact_offset_m": 0.003,
                "rest_offset_m": 0.003,
                "source": "task_04_pour_liquid_with_funnel",
            },
            "plate": {
                "source": "task_02_pour_liquid_and_stir",
                "xyz": list(PLATE_XYZ),
            },
        },
        "closure": {
            "layer_count": closure["layer_count"],
            "asset_count": closure["asset_count"],
            "unresolved": [],
        },
        "isaac45_runtime_smoke": "not_run",
        "claims": {
            "layout_authored": True,
            "authored_pbd_at_rest": True,
            "authored_rigid_grains_at_rest": True,
            "pbd_particle_count": 986,
            "rigid_grain_count": GRAIN_COUNT,
            "boat_starts_on_pan": True,
            "balance_pretared": True,
            "liquid_transfer_verified": False,
            "dissolve_verified": False,
            "scene_fixture_verified": False,
            "isaac45_runtime_smoke": "not_run",
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
        "qualified_runtime": "Isaac Sim 4.5.0",
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
            "isaac45 cold-start smoke not_run",
            "force-r1 balance is free-base, not fixed-base v2",
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
    return BoatPourStirHandoff(
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

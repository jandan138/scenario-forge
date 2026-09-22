#!/usr/bin/env python3
"""Build v0.2 fat packages from colleague-reviewed flattened scientific scenes.

This is a one-off outputs batch. Flattened-scene inventory stays in this script;
it is not a core package-layer API. Unique objects are locked by geometry
fingerprint. Composed colleague crates stay the scene entry. This does not claim
ConvertAsset runtime admission or scene_fixture_verified.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Iterable

import yaml

_ROOT = Path(__file__).resolve().parents[1]
for _path in (_ROOT, _ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scenario_forge.assets.checksum import compute_sha256  # noqa: E402
from scenario_forge.assets.lock import generate_asset_lock, write_asset_lock  # noqa: E402
from scenario_forge.package import validate_package  # noqa: E402

SOURCE_DEFAULT = Path(
    "/cpfs/shared/simulation/chenjiantong/scene_usds/scientific_experiments"
)
OUT_DEFAULT = _ROOT / "outputs" / "scientific_experiments_colleague_final_20260920"
LICENSE = "internal-colleague-reviewed-20260920"
RESOLVER = "scenario-forge/colleague-flattened-inventory-v1"
DOMAIN = "scientific_workbench"

SKIP_WORLD_NAMES = {
    "ParticleSystem",
    "ParticleSet",
    "fluid_runtime",
    "Looks",
    "BlueBottleGraph",
    "Cylinder",
    "LiquidMaterial",
    "PowderLooks",
    "CompactBottleLooks",
    "powder_pbd",
    "Render",
    "Environment",
}
SKIP_PREFIXES = ("obj_grain_",)
RECURSE_GROUPS = {"background_object"}
# Rooms are 440–456 meshes. Ordinary glassware stays under this and gets CopySpec.
ROOM_MESH_EXPORT_LIMIT = 200

TASKS = (
    "task_01_pour_flask_to_cylinder",
    "task_02_pour_liquid_and_stir",
    "task_03_magnetic_beaker_stirrer",
    "task_04_pour_liquid_with_funnel",
    "task_05_remove_container_lid",
    "task_06_remove_centrifuge_tubes",
    "task_07_insert_centrifuge_tubes",
    "task_08_place_container_in_oven",
    "task_09_solid_weighing",
    "task_10_titration_experiment",
    "task_11_remove_container_from_oven",
    "task_12_fehling_test",
    "task_13_blue_bottle_reaction",
    "task_14_fixed_weight_weighing",
)

TASK_SPECS: dict[str, dict[str, Any]] = {
    "task_01_pour_flask_to_cylinder": {
        "mode": "port",
        "title_zh": "液体倾倒：锥形瓶→量筒",
        "source_head": "task01_flask_to_cylinder / scientific_workbench_pour_flask_to_cylinder",
        "instruction": (
            "辅助臂抓量筒并保持目标位置；操作臂拿起锥形瓶，对准量筒口后倾倒，"
            "再把锥形瓶正立放回承托面并释放。"
        ),
        "progress_items": [
            {"id": "flask_lifted", "note": "锥形瓶离开桌面"},
            {"id": "flask_aligned", "note": "锥形瓶口位于量筒口上方"},
            {"id": "liquid_half_transferred", "note": "量筒含锥形瓶初始液体超过50%"},
            {"id": "liquid_fully_transferred", "note": "达到全部转移阈值"},
            {"id": "flask_returned", "note": "锥形瓶正立归还并释放"},
        ],
        "primary_objects": ["obj_conical_flask", "obj_graduated_cylinder"],
    },
    "task_02_pour_liquid_and_stir": {
        "mode": "port",
        "title_zh": "液体倾倒：量筒→烧杯，并带搅拌棒",
        "source_head": "task02_cylinder_to_beaker (pour only; stir rod is scene dressing)",
        "instruction": (
            "辅助臂固定烧杯并保持目标位置；操作臂拿起量筒，对准烧杯口倾倒后放回。"
            "同事精校场景另含玻璃棒与棒架，本批只移植倾倒语义，不宣称搅拌成功已验证。"
        ),
        "progress_items": [
            {"id": "cylinder_lifted", "note": "量筒离开桌面"},
            {"id": "cylinder_aligned", "note": "量筒口位于烧杯口上方"},
            {"id": "liquid_half_transferred", "note": "烧杯含量筒初始液体超过50%"},
            {"id": "liquid_fully_transferred", "note": "达到全部转移阈值"},
            {"id": "cylinder_returned", "note": "量筒正立归还并释放"},
        ],
        "primary_objects": ["obj_graduated_cylinder", "obj_beaker", "obj_glass_rod"],
    },
    "task_03_magnetic_beaker_stirrer": {
        "mode": "stub",
        "title_zh": "磁力搅拌：烧杯与磁子/搅拌器",
        "instruction": "将烧杯与磁子按任务要求与磁力搅拌器配合放置。语义待正式目录补全。",
        "primary_objects": ["obj_beaker", "obj_stir_bar", "obj_magnetic_stirrer"],
    },
    "task_04_pour_liquid_with_funnel": {
        "mode": "stub",
        "title_zh": "漏斗倒液",
        "instruction": "使用漏斗完成量筒到目标容器的倾倒。语义待正式目录补全。",
        "primary_objects": ["obj_funnel", "obj_graduated_cylinder", "obj_target_reagent_bottle"],
    },
    "task_05_remove_container_lid": {
        "mode": "port",
        "title_zh": "锥形瓶/烧杯去除瓶塞/盖子",
        "source_head": "task05_remove_ground_glass_stopper r11",
        "instruction": "辅助臂固定原底烧瓶；操作臂抓住29/42磨口瓶塞，轻微扭转后向上取出，再放入桌面放置架。",
        "progress_items": [
            {"id": "stopper_contact", "note": "抓住瓶塞"},
            {"id": "stopper_removed", "note": "瓶塞相对容器已取出"},
            {"id": "stopper_racked", "note": "瓶塞放入放置架"},
            {"id": "flask_upright", "note": "容器保持正立"},
        ],
        "primary_objects": ["obj_flask", "obj_stopper", "obj_stopper_rack"],
    },
    "task_06_remove_centrifuge_tubes": {
        "mode": "port",
        "title_zh": "仪器交互/结束离心并取出离心管",
        "source_head": "task11_centrifuge_unload_shutdown",
        "instruction": "按下离心机开盖按钮；拿起转子中的离心管并放到管架；按下关机按钮。",
        "progress_items": [
            {"id": "lid_opened", "note": "离心机开盖"},
            {"id": "tubes_removed", "note": "离心管离开转子"},
            {"id": "tubes_racked", "note": "离心管放到管架"},
            {"id": "powered_off", "note": "关机"},
        ],
        "primary_objects": ["obj_centrifuge", "obj_primary_tube", "obj_balance_tube", "obj_mixed_rack"],
    },
    "task_07_insert_centrifuge_tubes": {
        "mode": "port",
        "title_zh": "将离心管放入转子",
        "source_head": "task12_centrifuge_rack_to_rotor",
        "instruction": "从管架取出离心管并插入离心机转子对应孔位。",
        "progress_items": [
            {"id": "tubes_picked", "note": "从管架拿起离心管"},
            {"id": "tubes_inserted", "note": "离心管插入转子孔位"},
        ],
        "primary_objects": ["obj_centrifuge", "obj_primary_tube", "obj_balance_tube", "obj_mixed_rack"],
    },
    "task_08_place_container_in_oven": {
        "mode": "port",
        "title_zh": "仪器交互/开启烘箱并放入容器",
        "source_head": "task09_oven_load_start r16",
        "instruction": "辅助臂拉开并保持烘箱门；操作臂拿起烧杯并放到烘箱层架；辅助臂关门；操作臂将设定温度从60°C调到65°C并按下旋钮启动加热。",
        "progress_items": [
            {"id": "door_opened", "note": "拉开烘箱门"},
            {"id": "beaker_loaded", "note": "烧杯放到烘箱层架"},
            {"id": "door_closed", "note": "关闭烘箱门"},
            {"id": "heat_started", "note": "调温并启动加热"},
        ],
        "primary_objects": ["obj_oven", "obj_sample_beaker", "obj_oven_cart"],
    },
    "task_09_solid_weighing": {
        "mode": "port",
        "title_zh": "固体样品称量",
        "source_head": "solid_sample_weighing",
        "instruction": "将称量舟放到分析天平上并去皮，用药匙从粉末瓶舀取固体样品，使去皮后终帧 LCD 显示 1.00 g。勺数不限。本批不重跑 LCD/粉末 runtime。",
        "progress_items": [
            {"id": "boat_on_pan", "note": "称量舟放到天平盘"},
            {"id": "tared", "note": "去皮"},
            {"id": "sampled", "note": "从粉末瓶取样"},
            {"id": "target_mass", "note": "终帧 LCD 1.00 g"},
        ],
        "primary_objects": [
            "obj_analytical_balance",
            "obj_sampling_spoon",
            "obj_weighing_boat",
            "obj_weighing_bottle_body",
        ],
    },
    "task_10_titration_experiment": {
        "mode": "port",
        "title_zh": "传统酸碱滴定",
        "source_head": "traditional_acid_base_titration r1.7",
        "instruction": "使用左臂自由调节旋塞流量；锥形瓶呈稳定淡粉色时，将旋塞关至≤5°并连续保持3秒，然后释放旋塞。本批不重跑显色 runtime。",
        "progress_items": [
            {"id": "stopcock_adjusted", "note": "调节旋塞流量"},
            {"id": "endpoint_pink", "note": "接收瓶稳定淡粉色"},
            {"id": "closed_hold", "note": "旋塞关至≤5°并保持3秒"},
        ],
        "primary_objects": ["obj_titration_station", "obj_receiver_flask", "obj_sample_beaker"],
    },
    "task_11_remove_container_from_oven": {
        "mode": "port",
        "title_zh": "仪器交互/结束烘干并取出容器",
        "source_head": "task12_oven_unload_dual_glassware r2",
        "instruction": "辅助臂打开并保持已完成加热的烘箱门；操作臂依次取出烧杯和锥形瓶并放到主实验桌指定区域；辅助臂关闭烘箱门；操作臂按下电源摇臂关闭烘箱。",
        "progress_items": [
            {"id": "door_opened", "note": "打开烘箱门"},
            {"id": "beaker_unloaded", "note": "烧杯放到桌面"},
            {"id": "flask_unloaded", "note": "锥形瓶放到桌面"},
            {"id": "door_closed", "note": "关闭烘箱门"},
            {"id": "powered_off", "note": "关闭烘箱电源"},
        ],
        "primary_objects": ["obj_oven", "obj_sample_beaker", "obj_sample_conical_flask"],
    },
    "task_12_fehling_test": {
        "mode": "port",
        "title_zh": "斐林试剂还原糖水浴",
        "source_head": "fehlings_reducing_sugar_water_bath r10",
        "instruction": (
            "让装有样液的试管下段接触水浴；五层样液依次经过蓝、绿、黄、橙、橙红，"
            "累计触水30秒完成显色，取出后近竖直稳定观察3秒。离水暂停，重新接触继续。"
            "本批只移植语义，不重跑水浴 runtime。"
        ),
        "progress_items": [
            {"id": "tube_immersed", "note": "试管下段接触水浴"},
            {"id": "color_complete", "note": "五层显色完成"},
            {"id": "observed", "note": "取出后近竖直观察3秒"},
        ],
        "primary_objects": ["obj_sample_tube", "obj_beaker", "obj_tube_rack"],
    },
    "task_13_blue_bottle_reaction": {
        "mode": "stub",
        "title_zh": "蓝瓶子反应",
        "instruction": "完成蓝瓶子反应场景中的振荡/静置观察。语义待正式目录补全。",
        "primary_objects": ["obj_conical_flask", "obj_beaker", "obj_graduated_cylinder"],
    },
    "task_14_fixed_weight_weighing": {
        "mode": "stub",
        "title_zh": "定质量称量",
        "instruction": "按固定目标质量完成固体称量。语义待正式目录补全。",
        "primary_objects": [
            "obj_analytical_balance",
            "obj_powder_bottle",
            "obj_sampling_spoon",
            "obj_weighing_boat",
        ],
    },
}


@dataclass
class PrimHit:
    task: str
    variant: str
    prim_path: str
    name: str
    fingerprint: str
    mesh_count: int
    xyz: tuple[float, float, float]
    wxyz: tuple[float, float, float, float]


@dataclass
class UniqueAsset:
    asset_id: str
    name: str
    fingerprint: str
    mesh_count: int
    role: str
    asset_type: str
    first_source: str
    first_prim: str
    users: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    identity_relpath: str = ""


_FILE_HASHES: dict[str, str] = {}


def _sha256_file(path: Path) -> str:
    key = str(path.resolve())
    cached = _FILE_HASHES.get(key)
    if cached:
        return cached
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    hexdigest = digest.hexdigest()
    _FILE_HASHES[key] = hexdigest
    return hexdigest


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _link_or_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if dst.stat().st_size == src.stat().st_size:
            return
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def _variant_dirs(task_dir: Path) -> list[Path]:
    variants = []
    for split in ("seen", "unseen"):
        for index in range(1, 11):
            path = task_dir / f"{split}_scene_{index}"
            if path.is_dir():
                variants.append(path)
    return variants


def _variant_key(scene_dir: Path) -> str:
    name = scene_dir.name
    split, _, number = name.partition("_scene_")
    return f"{split}_scene_{int(number):02d}"


def _should_skip_name(name: str) -> bool:
    if name in SKIP_WORLD_NAMES:
        return True
    return any(name.startswith(prefix) for prefix in SKIP_PREFIXES)


def _role_for(name: str) -> tuple[str, str]:
    if name == "Room":
        return "environment", "usd_scene"
    if name == "table":
        return "support", "static_support"
    if name.startswith("obj_r9_") or name.startswith("obj_context_"):
        return "context_prop", "flattened_object"
    return "manipulated_object", "flattened_object"


def _geom_fingerprint(prim: Any) -> tuple[str, int]:
    from pxr import Usd, UsdGeom

    digest = sha256()
    root = prim.GetPath()
    mesh_count = 0
    for child in Usd.PrimRange(prim):
        if not child.IsA(UsdGeom.Mesh):
            continue
        mesh_count += 1
        mesh = UsdGeom.Mesh(child)
        digest.update(str(child.GetPath().MakeRelativePath(root)).encode("utf-8"))
        points = mesh.GetPointsAttr().Get()
        counts = mesh.GetFaceVertexCountsAttr().Get()
        point_count = len(points) if points else 0
        digest.update(str(point_count).encode("ascii"))
        if counts:
            digest.update(str(len(counts)).encode("ascii"))
        if points and point_count:
            for index in (0, point_count // 2, point_count - 1):
                digest.update(
                    ",".join(f"{float(value):.6f}" for value in points[index]).encode("ascii")
                )
    digest.update(f"meshes={mesh_count}".encode("ascii"))
    return digest.hexdigest(), mesh_count


def _world_pose(prim: Any) -> tuple[tuple[float, float, float], tuple[float, float, float, float]]:
    from pxr import Usd, UsdGeom

    xform = UsdGeom.Xformable(prim)
    matrix = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    translation = matrix.ExtractTranslation()
    quat = matrix.ExtractRotationQuat()
    imag = quat.GetImaginary()
    xyz = (float(translation[0]), float(translation[1]), float(translation[2]))
    wxyz = (float(quat.GetReal()), float(imag[0]), float(imag[1]), float(imag[2]))
    return xyz, wxyz


def _iter_candidate_prims(stage: Any) -> Iterable[Any]:
    from pxr import Usd

    world = stage.GetPrimAtPath("/World")
    if not world:
        return
    for child in world.GetChildren():
        name = child.GetName()
        if name in RECURSE_GROUPS:
            for descendant in Usd.PrimRange(child):
                dname = descendant.GetName()
                if not dname.startswith("obj_") or _should_skip_name(dname):
                    continue
                parent = descendant.GetParent()
                if parent and parent.GetName().startswith("obj_"):
                    continue
                yield descendant
            continue
        if _should_skip_name(name):
            continue
        if name.startswith("obj_") or name in {"table", "Room"}:
            yield child


def _open_stage(path: Path) -> Any:
    from pxr import Usd

    stage = Usd.Stage.Open(str(path))
    if stage is None:
        raise RuntimeError(f"failed to open USD: {path}")
    return stage


def _export_identity_usd(
    src_stage: Any,
    prim_path: str,
    dest: Path,
    root_name: str,
    *,
    fingerprint: str,
    mesh_count: int,
    source_uri: str,
    full_geometry: bool,
) -> None:
    from pxr import Sdf, Usd, UsdGeom

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    if not full_geometry:
        _write_text(
            dest,
            (
                "#usda 1.0\n"
                f'(\n    defaultPrim = "{root_name}"\n    metersPerUnit = 1\n'
                '    upAxis = "Z"\n'
                "    customLayerData = {\n"
                f'        string colleague_geom_fingerprint = "{fingerprint}"\n'
                f"        int colleague_mesh_count = {mesh_count}\n"
                f'        string colleague_source_uri = "{source_uri}"\n'
                '        string colleague_identity = "fingerprint_record"\n'
                "    }\n)\n\n"
                f'def Xform "{root_name}"\n{{\n}}\n'
            ),
        )
        return

    dst = Usd.Stage.CreateNew(str(dest))
    dest_path = Sdf.Path(f"/{root_name}")
    Sdf.CopySpec(src_stage.GetRootLayer(), Sdf.Path(prim_path), dst.GetRootLayer(), dest_path)
    copied = dst.GetPrimAtPath(dest_path)
    if copied:
        dst.SetDefaultPrim(copied)
        xform = UsdGeom.Xformable(copied)
        xform.ClearXformOpOrder()
        xform.AddTranslateOp().Set((0.0, 0.0, 0.0))
    UsdGeom.SetStageUpAxis(dst, UsdGeom.GetStageUpAxis(src_stage))
    UsdGeom.SetStageMetersPerUnit(dst, UsdGeom.GetStageMetersPerUnit(src_stage))
    dst.GetRootLayer().customLayerData = {
        "colleague_geom_fingerprint": fingerprint,
        "colleague_mesh_count": mesh_count,
        "colleague_source_uri": source_uri,
    }
    dst.GetRootLayer().Save()


def _asset_id_for(name: str, fingerprint: str) -> str:
    return f"colleague_{name}_{fingerprint[:12]}"


def _source_usd(source_root: Path, task: str, variant: str) -> Path:
    split, _, number = variant.partition("_scene_")
    return source_root / task / f"{split}_scene_{int(number)}" / "scene.usd"


def rebuild_uniques_from_hits(
    hits: list[PrimHit], source_root: Path
) -> dict[str, UniqueAsset]:
    """Admit once per geometry fingerprint; first-seen name becomes asset_id."""
    by_fingerprint: dict[str, UniqueAsset] = {}
    for hit in hits:
        user = f"{hit.task}/{hit.variant}:{hit.prim_path}"
        existing = by_fingerprint.get(hit.fingerprint)
        if existing is None:
            role, asset_type = _role_for(hit.name)
            by_fingerprint[hit.fingerprint] = UniqueAsset(
                asset_id=_asset_id_for(hit.name, hit.fingerprint),
                name=hit.name,
                fingerprint=hit.fingerprint,
                mesh_count=hit.mesh_count,
                role=role,
                asset_type=asset_type,
                first_source=str(_source_usd(source_root, hit.task, hit.variant)),
                first_prim=hit.prim_path,
                users=[user],
            )
        else:
            existing.users.append(user)
            if hit.name != existing.name and hit.name not in existing.aliases:
                existing.aliases.append(hit.name)
    return {asset.asset_id: asset for asset in by_fingerprint.values()}


def _unique_index(uniques: dict[str, UniqueAsset]) -> dict[str, UniqueAsset]:
    return {asset.fingerprint: asset for asset in uniques.values()}


def _unique_for_hit(uniques: dict[str, UniqueAsset], hit: PrimHit) -> UniqueAsset:
    index = getattr(_unique_for_hit, "_index", None)
    if index is None or getattr(_unique_for_hit, "_id", None) is not id(uniques):
        index = _unique_index(uniques)
        _unique_for_hit._index = index  # type: ignore[attr-defined]
        _unique_for_hit._id = id(uniques)  # type: ignore[attr-defined]
    try:
        return index[hit.fingerprint]
    except KeyError as exc:
        raise KeyError(f"no unique asset for fingerprint {hit.fingerprint}") from exc


def _dump_inventory_cache(
    cache_path: Path, hits: list[PrimHit], uniques: dict[str, UniqueAsset]
) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "hits": [hit.__dict__ for hit in hits],
                "uniques": {key: value.__dict__ for key, value in uniques.items()},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def inventory_source(
    source_root: Path,
    cache_path: Path | None = None,
    hits: list[PrimHit] | None = None,
    uniques: dict[str, UniqueAsset] | None = None,
) -> tuple[list[PrimHit], dict[str, UniqueAsset]]:
    hits = list(hits or [])
    uniques = dict(uniques or {})
    seen_scenes = {f"{hit.task}/{hit.variant}" for hit in hits}
    for task in TASKS:
        task_dir = source_root / task
        for scene_dir in _variant_dirs(task_dir):
            usd = scene_dir / "scene.usd"
            if not usd.is_file():
                continue
            variant = _variant_key(scene_dir)
            scene_key = f"{task}/{variant}"
            if scene_key in seen_scenes:
                continue
            print(f"inventory {scene_key}", flush=True)
            stage = _open_stage(usd)
            for prim in _iter_candidate_prims(stage):
                fingerprint, mesh_count = _geom_fingerprint(prim)
                xyz, wxyz = _world_pose(prim)
                name = prim.GetName()
                hit = PrimHit(
                    task=task,
                    variant=variant,
                    prim_path=str(prim.GetPath()),
                    name=name,
                    fingerprint=fingerprint,
                    mesh_count=mesh_count,
                    xyz=xyz,
                    wxyz=wxyz,
                )
                hits.append(hit)
            seen_scenes.add(scene_key)
            if cache_path is not None:
                uniques = rebuild_uniques_from_hits(hits, source_root)
                _dump_inventory_cache(cache_path, hits, uniques)
    if hits:
        uniques = rebuild_uniques_from_hits(hits, source_root)
    if cache_path is not None:
        _dump_inventory_cache(cache_path, hits, uniques)
    return hits, uniques


def export_unique_assets(
    uniques: dict[str, UniqueAsset], admitted_root: Path
) -> None:
    cache: dict[str, Any] = {}
    for asset in sorted(uniques.values(), key=lambda item: item.asset_id):
        kind = "environments" if asset.role == "environment" else "objects"
        dest = admitted_root / kind / asset.asset_id / "model.usd"
        asset.identity_relpath = str(dest.relative_to(admitted_root.parent))
        if dest.is_file():
            continue
        print(f"export {asset.asset_id} meshes={asset.mesh_count}", flush=True)
        src = Path(asset.first_source)
        stage = cache.get(str(src))
        if stage is None:
            stage = _open_stage(src)
            cache[str(src)] = stage
        full_geometry = asset.mesh_count <= ROOM_MESH_EXPORT_LIMIT
        _export_identity_usd(
            stage,
            asset.first_prim,
            dest,
            asset.name,
            fingerprint=asset.fingerprint,
            mesh_count=asset.mesh_count,
            source_uri=f"{asset.first_source}#{asset.first_prim}",
            full_geometry=full_geometry,
        )
    wanted = {
        ("environments" if asset.role == "environment" else "objects", asset.asset_id)
        for asset in uniques.values()
    }
    for kind in ("objects", "environments"):
        kind_root = admitted_root / kind
        if not kind_root.is_dir():
            continue
        for child in kind_root.iterdir():
            if child.is_dir() and (kind, child.name) not in wanted:
                shutil.rmtree(child)


def collect_subusd_blobs(source_root: Path, blob_root: Path) -> dict[str, str]:
    """Map content sha256 -> blob path name."""
    blobs: dict[str, str] = {}
    roots: list[Path] = []
    for task in TASKS:
        task_dir = source_root / task
        if (task_dir / "SubUSDs").is_dir():
            roots.append(task_dir / "SubUSDs")
        for scene_dir in _variant_dirs(task_dir):
            if (scene_dir / "SubUSDs").is_dir():
                roots.append(scene_dir / "SubUSDs")
    for sub in roots:
        for path in sorted(p for p in sub.rglob("*") if p.is_file()):
            digest = _sha256_file(path)
            if digest in blobs:
                continue
            dest = blob_root / digest[:2] / digest
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                _link_or_copy(path, dest)
            blobs[digest] = str(dest)
            print(f"blob {digest[:12]} {path.relative_to(source_root)}", flush=True)
    return blobs


def _place_subusds(src_sub: Path, dst_sub: Path, blob_root: Path) -> None:
    if not src_sub.is_dir():
        return
    for path in (p for p in src_sub.rglob("*") if p.is_file()):
        rel = path.relative_to(src_sub)
        digest = _sha256_file(path)
        blob = blob_root / digest[:2] / digest
        if not blob.is_file():
            blob.parent.mkdir(parents=True, exist_ok=True)
            _link_or_copy(path, blob)
        _link_or_copy(blob, dst_sub / rel)


def _default_hits(hits: list[PrimHit], task: str) -> list[PrimHit]:
    return [hit for hit in hits if hit.task == task and hit.variant == "seen_scene_01"]


def _task_asset_ids(hits: list[PrimHit], uniques: dict[str, UniqueAsset], task: str) -> set[str]:
    return {
        _unique_for_hit(uniques, hit).asset_id
        for hit in hits
        if hit.task == task
    }


def _main_usda(composed_rel: str) -> str:
    return (
        "#usda 1.0\n"
        "(\n"
        '    defaultPrim = "World"\n'
        "    metersPerUnit = 1.0\n"
        '    upAxis = "Z"\n'
        ")\n\n"
        'def Xform "World"\n'
        "{\n"
        '    def Xform "_scene" (\n'
        f"        prepend payload = @{composed_rel}@\n"
        "    )\n"
        "    {\n"
        "    }\n"
        "}\n"
    )


def _task_yaml(task: str, package_id: str) -> dict[str, Any]:
    spec = TASK_SPECS[task]
    payload: dict[str, Any] = {
        "schema_version": "task/v0.5",
        "task_id": package_id,
        "task_family": task,
        "title_zh": spec["title_zh"],
        "instruction": spec["instruction"],
        "semantics_mode": spec["mode"],
        "robot_grasp_verified": False,
        "primary_objects": spec["primary_objects"],
        "claim_boundary": (
            "Semantic transplant or stub only. This package does not claim ConvertAsset "
            "runtime admission, scene_fixture_verified, grasp, liquid transfer, or benchmark success."
        ),
    }
    if spec["mode"] == "port":
        payload["source_head"] = spec["source_head"]
        payload["runtime_evidence"] = "not_run"
        payload["success"] = {
            "operator": "all",
            "claim_scope": "ported_semantics_unvalidated_on_colleague_scene",
            "predicates": [
                {
                    "id": item["id"],
                    "type": "not_run",
                    "status": "not_run",
                    "note": (
                        f"{item['note']}. Transplanted from {spec['source_head']}; "
                        "this batch did not re-execute the predicate."
                    ),
                }
                for item in spec.get("progress_items", [])
            ]
            or [
                {
                    "id": "ported_success_not_rerun",
                    "type": "not_run",
                    "status": "not_run",
                    "note": (
                        "Predicates were transplanted from "
                        f"{spec['source_head']}; this batch did not re-execute them."
                    ),
                }
            ],
        }
    else:
        payload["runtime_evidence"] = "not_run"
        payload["success"] = {
            "operator": "all",
            "claim_scope": "stub_awaiting_catalog",
            "predicates": [
                {
                    "id": "catalog_pending",
                    "type": "not_run",
                    "status": "not_run",
                    "note": "No verified predicate set for this colleague task id.",
                }
            ],
        }
    return payload


def _metrics_yaml(task: str) -> dict[str, Any]:
    spec = TASK_SPECS[task]
    if spec["mode"] == "port":
        items = spec.get("progress_items") or [
            {"id": "ported_success_not_rerun", "note": "Ported metric placeholder"}
        ]
        return {
            "schema_version": "metrics/v0.4",
            "aggregation": {
                "type": "weighted_progress_score",
                "normalization": "declared_sum",
                "inactive_treatment": "zero",
                "primary_metric_id": items[0]["id"],
            },
            "metrics": [
                {
                    "id": item["id"],
                    "type": "not_run",
                    "role": "progress_component",
                    "weight": 1.0 / len(items),
                    "active": False,
                    "status": "not_run",
                    "source_head": spec["source_head"],
                    "note": (
                        f"{item['note']}. Semantic transplant; runtime not rerun "
                        "on colleague USD."
                    ),
                }
                for item in items
            ],
        }
    return {
        "schema_version": "metrics/v0.4",
        "aggregation": {
            "type": "weighted_progress_score",
            "normalization": "declared_sum",
            "inactive_treatment": "zero",
            "primary_metric_id": "catalog_pending",
        },
        "metrics": [
            {
                "id": "catalog_pending",
                "type": "not_run",
                "role": "progress_component",
                "weight": 1.0,
                "active": False,
                "status": "not_run",
                "note": "Stub task; no verified metric.",
            }
        ],
    }


def assemble_package(
    *,
    task: str,
    source_root: Path,
    out_root: Path,
    hits: list[PrimHit],
    uniques: dict[str, UniqueAsset],
    blob_root: Path,
) -> Path:
    package_id = f"scientific_experiments_colleague_{task}"
    pkg = out_root / "packages" / task
    pkg.mkdir(parents=True, exist_ok=True)

    task_src = source_root / task
    composed_ids: list[str] = []
    splits = []
    for scene_dir in _variant_dirs(task_src):
        variant = _variant_key(scene_dir)
        dest = pkg / "assets" / "composed" / variant
        _link_or_copy(scene_dir / "scene.usd", dest / "scene.usd")
        scene_sub = scene_dir / "SubUSDs"
        _place_subusds(
            scene_sub if scene_sub.is_dir() else task_src / "SubUSDs",
            dest / "SubUSDs",
            blob_root,
        )
        composed_id = f"colleague_composed_{task}_{variant}"
        composed_ids.append(composed_id)
        splits.append(
            {
                "name": variant,
                "split": "seen" if variant.startswith("seen_") else "unseen",
                "composed_usd": f"assets/composed/{variant}/scene.usd",
                "default": variant == "seen_scene_01",
            }
        )

    default_composed = "assets/composed/seen_scene_01/scene.usd"
    _write_text(pkg / "scene" / "main.usda", _main_usda(f"../{default_composed}"))

    instances = []
    for hit in _default_hits(hits, task):
        instances.append(
            {
                "id": hit.prim_path.lstrip("/").replace("/", "__"),
                "asset_id": _unique_for_hit(uniques, hit).asset_id,
                "name": hit.name,
                "source_prim_path": hit.prim_path,
                "role": _role_for(hit.name)[0],
                "pose": {"xyz": list(hit.xyz), "wxyz": list(hit.wxyz)},
                "semantic_tags": [hit.name],
                "initial_state": {},
            }
        )
    _write_yaml(
        pkg / "scene" / "instances.yaml",
        {
            "schema_version": "scene-instances/v0.2",
            "coordinate_system": {"units": "meters", "up_axis": "Z"},
            "instances": instances,
        },
    )

    used_ids = sorted(_task_asset_ids(hits, uniques, task))
    manifest_assets: list[dict[str, Any]] = []
    for asset_id in used_ids:
        asset = uniques[asset_id]
        kind = "environments" if asset.role == "environment" else "objects"
        rel = f"assets/{kind}/{asset.asset_id}/model.usd"
        src_identity = out_root / "admitted_assets" / kind / asset.asset_id / "model.usd"
        _link_or_copy(src_identity, pkg / rel)
        manifest_assets.append(
            {
                "asset_id": asset.asset_id,
                "role": asset.role,
                "asset_type": asset.asset_type,
                "canonical_usd": rel,
                "license": LICENSE,
                "sha256": compute_sha256(pkg / rel),
                "source_kind": "colleague_flattened_identity",
                "source_uri": f"{asset.first_source}#{asset.first_prim}",
                "resolver_version": RESOLVER,
                "geom_fingerprint": asset.fingerprint,
                "mesh_count": asset.mesh_count,
            }
        )
    for kind in ("objects", "environments"):
        kind_root = pkg / "assets" / kind
        if not kind_root.is_dir():
            continue
        for child in kind_root.iterdir():
            if child.is_dir() and child.name not in used_ids:
                shutil.rmtree(child)

    for variant_split in splits:
        variant = variant_split["name"]
        composed_id = f"colleague_composed_{task}_{variant}"
        rel = f"assets/composed/{variant}/scene.usd"
        number = int(variant.rsplit("_", 1)[-1])
        split = "seen" if variant.startswith("seen_") else "unseen"
        source_usd = task_src / f"{split}_scene_{number}" / "scene.usd"
        manifest_assets.append(
            {
                "asset_id": composed_id,
                "role": "composed_scene",
                "asset_type": "usd_scene",
                "canonical_usd": rel,
                "license": LICENSE,
                "sha256": compute_sha256(pkg / rel),
                "source_kind": "colleague_composed_crate",
                "source_uri": str(source_usd),
                "resolver_version": RESOLVER,
            }
        )

    _write_yaml(
        pkg / "assets" / "asset_manifest.yaml",
        {"schema_version": "asset-manifest/v0.2", "assets": manifest_assets},
    )
    write_asset_lock(pkg, generate_asset_lock(pkg, lock_id=f"{package_id}_asset_lock"))

    _write_yaml(
        pkg / "manifest.yaml",
        {
            "schema_version": "scenario-package/v0.2",
            "package_id": package_id,
            "scenario_domain": DOMAIN,
            "package_mode": "fat",
            "targets": ["ebench", "embodied-eval-os"],
            "entrypoints": {
                "generation_plan": "generation_plan.yaml",
                "scene_usd": "scene/main.usda",
                "scene_instances": "scene/instances.yaml",
                "task": "task/task.yaml",
                "robot": "robot/robot.yaml",
                "metrics": "metrics/metrics.yaml",
            },
            "assets": {
                "manifest": "assets/asset_manifest.yaml",
                "lock": "locks/asset_lock.yaml",
            },
            "validation": {
                "report": "evidence/validation_report.yaml",
                "minimum_required_level": "asset_locked",
            },
            "provenance": {"summary": "provenance/provenance.yaml"},
        },
    )
    _write_yaml(
        pkg / "generation_plan.yaml",
        {
            "schema_version": "scenario-generation-plan/v0.2",
            "package_id": package_id,
            "seed": 0,
            "target_exports": ["ebench", "embodied-eval-os"],
            "package_mode": "fat",
            "producer": "build_scientific_experiments_colleague_final",
            "source_root": str(source_root / task),
        },
    )
    _write_yaml(pkg / "task" / "task.yaml", _task_yaml(task, package_id))
    _write_yaml(
        pkg / "robot" / "robot.yaml",
        {
            "schema_version": "robot/v0.2",
            "robot_id": "lift2_placeholder",
            "embodiment": "lift2",
            "profile_ref": "manip/lift2/R5a_isaac41_vr600_v1",
            "robot_grasp_verified": False,
            "note": "Colleague scenes contain no robot. Lift2 is a contract placeholder.",
            "spawn": {
                "xyz": [0.0, -1.02, 0.31],
                "wxyz": [0.7071067812, 0.0, 0.0, 0.7071067812],
            },
            "actors": [
                {
                    "id": "auxiliary_arm",
                    "end_effector": "right",
                    "capabilities": ["grasp", "hold", "release"],
                },
                {
                    "id": "operating_arm",
                    "end_effector": "left",
                    "capabilities": ["grasp", "lift", "place", "release"],
                },
            ],
        },
    )
    _write_yaml(pkg / "metrics" / "metrics.yaml", _metrics_yaml(task))
    _write_yaml(
        pkg / "metrics" / "splits.yaml",
        {"schema_version": "splits/v0.2", "splits": splits},
    )
    _write_yaml(
        pkg / "evidence" / "validation_report.yaml",
        {
            "schema_version": "validation-report/v0.2",
            "package_id": package_id,
            "status": "passed",
            "overall_level": "asset_locked",
            "checks": [
                {"id": "colleague_scene_copied", "status": "passed"},
                {"id": "unique_assets_locked", "status": "passed"},
                {"id": "asset_lock_generated", "status": "passed"},
            ],
            "runtime_claims": [],
            "not_claimed": [
                "convertasset_runtime_admission",
                "scene_fixture_verified",
                "robot_grasp",
                "liquid_transfer",
                "benchmark_success",
            ],
        },
    )
    _write_yaml(
        pkg / "provenance" / "provenance.yaml",
        {
            "schema_version": "scenario-provenance/v0.2",
            "package_id": package_id,
            "generator": "scripts/build_scientific_experiments_colleague_final.py",
            "source_kind": "colleague_reviewed_flattened_scene",
            "source_root": str(source_root / task),
            "license": LICENSE,
            "semantics_mode": TASK_SPECS[task]["mode"],
            "source_head": TASK_SPECS[task].get("source_head"),
            "variant_count": len(splits),
            "unique_object_assets": used_ids,
            "skipped_helpers": {
                "obj_grain_*": (
                    "World-level powder grains are recipe instances, not admitted identities."
                    if task in {"task_09_solid_weighing", "task_14_fixed_weight_weighing"}
                    else "none_observed_at_world_root"
                )
            },
        },
    )
    return pkg


def write_batch_docs(
    *,
    out_root: Path,
    source_root: Path,
    uniques: dict[str, UniqueAsset],
    hits: list[PrimHit],
    check_results: list[dict[str, Any]],
) -> None:
    inventory = []
    for asset in sorted(uniques.values(), key=lambda item: item.asset_id):
        inventory.append(
            {
                "asset_id": asset.asset_id,
                "name": asset.name,
                "geom_fingerprint": asset.fingerprint,
                "mesh_count": asset.mesh_count,
                "role": asset.role,
                "first_source_prim": f"{asset.first_source}#{asset.first_prim}",
                "aliases": asset.aliases,
                "user_count": len(asset.users),
                "users": asset.users,
            }
        )
    _write_yaml(
        out_root / "admitted_assets" / "inventory.yaml",
        {
            "schema_version": "colleague-unique-asset-inventory/v1",
            "source_root": str(source_root),
            "license": LICENSE,
            "asset_count": len(inventory),
            "skipped_helpers": {
                "obj_grain_*": {
                    "note": "World-level powder grains are recipe instances, not admitted identities.",
                    "task_09_solid_weighing": "5 per variant, 100 total",
                }
            },
            "assets": inventory,
        },
    )
    _write_yaml(out_root / "evidence" / "unique_asset_inventory.yaml", {"asset_count": len(inventory), "assets": inventory})
    _write_yaml(out_root / "evidence" / "package_check_summary.yaml", {"packages": check_results})
    _write_text(
        out_root / "evidence" / "claim_boundary.md",
        (
            "# Claim boundary\n\n"
            "This batch statically inventories unique flattened prims from colleague-reviewed "
            "composed USDs and wraps them as `scenario-package/v0.2` fat packages.\n\n"
            "It does **not** claim ConvertAsset visual/runtime admission, "
            "`scene_fixture_verified`, robot grasp, liquid transfer, or benchmark success.\n"
            "`minimum_required_level` is `asset_locked`.\n"
        ),
    )
    catalog = {
        "schema_version": "colleague-scientific-experiments-catalog/v1",
        "output_root": str(out_root),
        "source_root": str(source_root),
        "tasks": [
            {
                "task": task,
                "package_id": f"scientific_experiments_colleague_{task}",
                "package_dir": f"packages/{task}",
                "title_zh": TASK_SPECS[task]["title_zh"],
                "semantics_mode": TASK_SPECS[task]["mode"],
                "variants": 20,
            }
            for task in TASKS
        ],
    }
    _write_yaml(out_root / "catalog.yaml", catalog)
    lines = [
        "# Scientific experiments colleague final 20260920",
        "",
        "Colleague-reviewed flattened scenes packaged as 14 v0.2 fat family packages.",
        "Unique `obj_*` / table / Room identities are deduplicated by geometry fingerprint.",
        "Scene entry is the original composed crate under `assets/composed/`.",
        "",
        "Validation level: `asset_locked` only.",
        "",
        "| Task | Mode | Package |",
        "|---|---|---|",
    ]
    for task in TASKS:
        lines.append(
            f"| `{task}` | {TASK_SPECS[task]['mode']} | `packages/{task}` |"
        )
    lines.extend(
        [
            "",
            "Source: `/cpfs/shared/simulation/chenjiantong/scene_usds/scientific_experiments`",
            f"Unique admitted identities: {len(uniques)}",
            f"Prim observations: {len(hits)}",
            "Each package contains 20 variants (`seen_scene_01`–`10`, `unseen_scene_01`–`10`).",
            "Default scene entry is `seen_scene_01`.",
            "",
            "See `evidence/claim_boundary.md`.",
            "",
        ]
    )
    _write_text(out_root / "README.md", "\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE_DEFAULT)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    parser.add_argument("--tasks", nargs="*", default=None)
    args = parser.parse_args()
    source_root = args.source.resolve()
    out_root = args.out.resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    selected = tuple(args.tasks) if args.tasks else TASKS
    unknown = [task for task in selected if task not in TASKS]
    if unknown:
        raise SystemExit(f"unknown tasks: {unknown}")

    cache_path = out_root / "evidence" / "inventory_cache.json"
    hits: list[PrimHit] = []
    uniques: dict[str, UniqueAsset] = {}
    if cache_path.is_file():
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
        hits = [PrimHit(**item) for item in raw["hits"]]
        print(f"loaded inventory cache ({len(hits)} hits)", flush=True)
    expected = {
        f"{task}/{_variant_key(scene_dir)}"
        for task in TASKS
        for scene_dir in _variant_dirs(source_root / task)
    }
    cached = {f"{hit.task}/{hit.variant}" for hit in hits}
    if cached != expected:
        print(f"inventory resume {len(cached)}/{len(expected)} scenes", flush=True)
        hits, _ignored = inventory_source(
            source_root, cache_path=cache_path, hits=hits
        )
    uniques = rebuild_uniques_from_hits(hits, source_root) if hits else {}
    fingerprints = [asset.fingerprint for asset in uniques.values()]
    if len(fingerprints) != len(set(fingerprints)):
        raise RuntimeError("duplicate geometry fingerprints in unique inventory")
    _dump_inventory_cache(cache_path, hits, uniques)

    export_unique_assets(uniques, out_root / "admitted_assets")
    blob_root = out_root / "admitted_assets" / "subusd_blobs"
    collect_subusd_blobs(source_root, blob_root)

    check_results = []
    for task in selected:
        print(f"assemble {task}", flush=True)
        pkg = assemble_package(
            task=task,
            source_root=source_root,
            out_root=out_root,
            hits=hits,
            uniques=uniques,
            blob_root=blob_root,
        )
        report = validate_package(pkg)
        check_results.append(
            {
                "task": task,
                "package": str(pkg),
                "ok": report.ok,
                "messages": list(report.messages),
            }
        )
        print(f"package check {task}: {'PASS' if report.ok else 'FAIL'} {report.messages}", flush=True)

    write_batch_docs(
        out_root=out_root,
        source_root=source_root,
        uniques=uniques,
        hits=hits,
        check_results=check_results,
    )
    failed = [item for item in check_results if not item["ok"]]
    if failed:
        print(f"FAILED {len(failed)} packages", flush=True)
        return 1
    print(f"done: {out_root}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

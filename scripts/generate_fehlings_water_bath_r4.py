"""r4: keep r3 poses and visual water; replace GPU-only SDF colliders with CPU contact."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import runpy
import shutil

import yaml

from scripts.generate_fehlings_water_bath_r3 import BEAKER, TUBE, contract

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r3_20260909/"
    "handoff/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r3"
)
TASK_ID = "scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r4"
OUTPUT = ROOT / (f"outputs/{TASK_ID}_cpu_schema_fixed_20260911")
RACK_MESH = "/World/obj_tube_rack/Cube_015"
TUBE_MESH = (
    "/World/obj_sample_tube/Visual/Source/centrifuge_tube_15ml_red_cap_ROOT"
    "/Tube_Body_Hollow/Tube_Body_Hollow_Mesh"
)
TUBE_CYL = TUBE + "/CpuContactCylinder"
TUBE_RADIUS = 0.00861
TUBE_HEIGHT = 0.101


def world_translations(stage):
    from pxr import UsdGeom

    cache = UsdGeom.XformCache()
    poses = {}
    for child in stage.GetPrimAtPath("/World").GetChildren():
        name = child.GetName()
        if name.startswith("obj_") or name in ("table", "background"):
            t = cache.GetLocalToWorldTransform(child).ExtractTranslation()
            poses[str(child.GetPath())] = (float(t[0]), float(t[1]), float(t[2]))
    return poses


def _strip_collision_apis(prim):
    # GetAppliedSchemas/HasAPI omit unknown plugins in usd-core. Remove authored
    # tokens directly so a later PhysX loader cannot rediscover a leftover SDF.
    for name in (
        "PhysxSDFMeshCollisionAPI", "PhysxConvexDecompositionCollisionAPI",
        "PhysxConvexHullCollisionAPI", "PhysxTriangleMeshCollisionAPI",
        "PhysxCollisionAPI", "PhysicsMeshCollisionAPI", "PhysicsCollisionAPI",
    ):
        prim.RemoveAppliedSchema(name)


def apply_cpu_contact_colliders(stage):
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

    rack = stage.GetPrimAtPath(RACK_MESH)
    if not rack:
        raise ValueError("missing tube rack mesh")
    _strip_collision_apis(rack)
    mesh = stage.GetPrimAtPath(TUBE_MESH)
    if not mesh:
        raise ValueError("missing sample tube mesh")
    _strip_collision_apis(mesh)
    beaker = stage.GetPrimAtPath(BEAKER)
    if not beaker:
        raise ValueError("missing beaker")
    UsdPhysics.RigidBodyAPI.Apply(beaker).CreateKinematicEnabledAttr(True)
    for prim in Usd.PrimRange(beaker):
        approx = prim.GetAttribute("physics:approximation")
        if approx and approx.Get() == "sdf":
            enabled = prim.GetAttribute("physics:collisionEnabled").Get()
            _strip_collision_apis(prim)
            UsdPhysics.CollisionAPI.Apply(prim).CreateCollisionEnabledAttr(
                True if enabled is None else bool(enabled)
            )
            UsdPhysics.MeshCollisionAPI.Apply(prim).CreateApproximationAttr().Set("none")
    if stage.GetPrimAtPath(TUBE_CYL):
        stage.RemovePrim(TUBE_CYL)
    cyl = UsdGeom.Cylinder.Define(stage, TUBE_CYL)
    cyl.CreateAxisAttr("Z")
    cyl.CreateRadiusAttr(TUBE_RADIUS)
    cyl.CreateHeightAttr(TUBE_HEIGHT)
    cyl.AddTranslateOp().Set(Gf.Vec3d(0, 0, TUBE_HEIGHT / 2))
    UsdGeom.Imageable(cyl).MakeInvisible()
    prim = cyl.GetPrim()
    UsdPhysics.CollisionAPI.Apply(prim).CreateCollisionEnabledAttr(True)
    UsdShade.MaterialBindingAPI.Apply(prim)
    prim.CreateAttribute("physxCollision:contactOffset", Sdf.ValueTypeNames.Float).Set(0.0005)
    prim.CreateAttribute("physxCollision:restOffset", Sdf.ValueTypeNames.Float).Set(0.0)
    prim.CreateAttribute("physics:staticFriction", Sdf.ValueTypeNames.Float).Set(1.0)
    prim.CreateAttribute("physics:dynamicFriction", Sdf.ValueTypeNames.Float).Set(1.0)
    prim.CreateAttribute("physics:restitution", Sdf.ValueTypeNames.Float).Set(0.0)


def write_task_documents(root):
    task = yaml.safe_load((root / "task.yaml").read_text())
    task.update(
        task_id=TASK_ID,
        instruction=(
            "让装有样液的试管下段接触水浴；浅浸、倾斜或部分接触均可累计。"
            "30秒开始变化、60秒完成；取出后近竖直稳定观察3秒。"
        ),
        reaction_policy=contract(),
        time_basis="sample_region_contact_time",
        invalid_immersion="pause_without_reset",
    )
    (root / "task.yaml").write_text(yaml.safe_dump(task, allow_unicode=True, sort_keys=False))
    metrics = yaml.safe_load((root / "metrics.yaml").read_text())
    for item in metrics["metrics"]:
        item["source_ref"]["task"] = TASK_ID
    (root / "metrics.yaml").write_text(yaml.safe_dump(metrics, allow_unicode=True, sort_keys=False))
    cfg = next(iter(runpy.run_path(str(root / "task_config.py"))["TASKS"].values()))
    cfg["scene_usd_file_path"] = {"scene1": "__SCENE__"}
    cfg["water_bath"] = dict(cfg.get("water_bath") or {})
    cfg["water_bath"].update(
        reaction_policy=contract(),
        water_representation="visual_mesh",
        contact_rule=contract()["contact_rule"],
        cpu_contact_colliders=True,
    )
    text = repr({TASK_ID: cfg}).replace(
        "'__SCENE__'", "str(Path(__file__).resolve().parent / 'scene.usd')"
    )
    (root / "task_config.py").write_text("from pathlib import Path\nTASKS = " + text + "\n")


def build(source=SOURCE, output=OUTPUT, overwrite=False):
    from pxr import Usd

    if not source.exists():
        raise FileNotFoundError(source)
    root = output / "handoff" / TASK_ID
    if root.exists():
        if not overwrite:
            raise FileExistsError(root)
        shutil.rmtree(root)
    shutil.copytree(
        source,
        root,
        ignore=lambda directory, names: {"evidence", ".thumbs"} if Path(directory) == source else set(),
    )
    evidence = root / "evidence"
    evidence.mkdir()
    source_scene = source / "scene.usd"
    dest_scene = root / "scene.usd"
    source_sha = sha256(source_scene.read_bytes()).hexdigest()
    stage = Usd.Stage.Open(str(dest_scene))
    before = world_translations(stage)
    apply_cpu_contact_colliders(stage)
    stage.GetDefaultPrim().SetCustomDataByKey("scenario_forge:taskId", TASK_ID)
    if not stage.GetRootLayer().Export(str(dest_scene)):
        raise RuntimeError(f"failed to export {dest_scene}")
    if sha256(source_scene.read_bytes()).hexdigest() != source_sha:
        raise RuntimeError("r3 source scene was mutated; abort")
    after = world_translations(Usd.Stage.Open(str(dest_scene)))
    if before != after:
        raise ValueError("object world translations changed")
    digest = sha256(dest_scene.read_bytes()).hexdigest()
    (evidence / "cpu_contact_colliders.json").write_text(
        json.dumps(
            {
                "status": "authored",
                "scene_sha256": digest,
                "source_scene_sha256": sha256((source / "scene.usd").read_bytes()).hexdigest(),
                "placements_unchanged": True,
                "rack_mesh": RACK_MESH,
                "rack_mesh_collision_stripped": True,
                "rack_slots_kept": True,
                    "tube_mesh_collision_stripped": True,
                    "authored_collision_schema_tokens_removed": True,
                "beaker_kinematic": True,
                "tube_cylinder": TUBE_CYL,
                "tube_radius_m": TUBE_RADIUS,
                "tube_height_m": TUBE_HEIGHT,
                "isaac41_cpu_sdf_actors": "not_added",
            },
            indent=2,
        )
        + "\n"
    )
    path = root / "manifest.json"
    manifest = json.loads(path.read_text())
    for key in ("runtime_cold_starts", "runtime_reports", "render_evidence", "closure"):
        manifest.pop(key, None)
    manifest.update(
        package_id=TASK_ID,
        status="runtime_pending",
        scene_sha256=digest,
        source_scene_sha256=sha256((source / "scene.usd").read_bytes()).hexdigest(),
        reaction_policy=contract(),
        cpu_contact_colliders="evidence/cpu_contact_colliders.json",
    )
    manifest["claims"].update(
        pbd_water=False,
        particle_count=0,
        scene_fixture_verified=False,
        visual_reaction_verified=False,
        robot_policy_success=False,
        continuous_robot_grasp_verified=False,
        cpu_contact_colliders_authored=True,
    )
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    write_task_documents(root)
    (root / "README_CN.md").write_text(
        """# 斐林水浴 r4：CPU 可接触碰撞（摆放与 r3 相同）

从 r3 派生。对象世界坐标不变。烧杯假水仍无碰撞。
本候选经过静态检查，尚未取得包内运行资格。碰撞 API 按原始 schema token 移除，普通 USD 环境也不会残留 SDF 标记。
试管架视觉网格去掉碰撞，只保留 r3 的孔底圆柱，避免三角网格把插孔卡住导致夹住上沿后抽不出来。
试管空心 SDF 碰撞 API 全部去掉，改为与外形包络一致的不可见圆柱（半径 8.61 mm，高 101 mm），避免残留 SDF shape 让整根试管刚体被拒收。
烧杯改为 kinematic，杯壁 SDF 改为三角网格，便于浸入时的 CPU 接触。
反应策略仍是 r3 的样液区域触水累计；本包不宣称机器人抓取已验证。
Isaac 4.1 CPU 场景不会加入 SDF 刚体；这是本修订的原因，不是 metric 设计问题。

节点与读取方法见 [颜色与假水教学文档](COLOR_GUIDE_CN.md)。
"""
    )
    shutil.copy2(ROOT / "docs/operations/fehlings-r3-color-guide.md", root / "COLOR_GUIDE_CN.md")
    return root


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    print(build(args.source, args.out, overwrite=args.overwrite))

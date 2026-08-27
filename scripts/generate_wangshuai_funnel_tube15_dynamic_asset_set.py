#!/usr/bin/env python3
"""Import the promoted dynamic Wangshuai funnel/tube producer packages."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCER = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "wangshuai_funnel_tube15_dynamic_asset_set_20260827"
)
DEFAULT_OUT = (
    ROOT / "outputs/scientific_workbench_funnel_tube15_liquid_asset_set_v2_20260827"
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _tree_hash(root: Path) -> str:
    digest = sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def build_asset_set(producer: Path, output: Path) -> Path:
    from pxr import Usd, UsdGeom, UsdUtils

    producer = producer.resolve()
    output = output.resolve()
    source_index_path = producer / "asset_set_manifest.json"
    source_index = json.loads(source_index_path.read_text())
    if (
        source_index.get("status") != "pass"
        or source_index.get("default_consumption") != "dynamic"
        or source_index.get("claims", {}).get("dynamic_runtime_qualified") is not True
        or source_index.get("claims", {}).get("effective_kinematic") is not False
    ):
        raise RuntimeError("ConvertAsset dynamic producer asset set is not promoted")
    staging = output.parent / f".{output.name}.staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        assets = []
        closures = []
        for item in source_index["assets"]:
            asset_id = item["id"]
            source_package = producer / item["package"]
            destination = staging / "assets" / asset_id
            shutil.copytree(source_package, destination)
            producer_manifest_path = destination / "evidence/manifest.json"
            producer_manifest = json.loads(producer_manifest_path.read_text())
            if producer_manifest.get("overall_status") != "pass":
                raise RuntimeError(f"producer package is not pass: {asset_id}")
            entry = destination / "asset.usda"
            stage = Usd.Stage.Open(str(entry))
            if not stage:
                raise RuntimeError(f"cannot open copied asset: {entry}")
            if UsdGeom.Xformable(stage.GetDefaultPrim()).GetOrderedXformOps():
                raise RuntimeError(f"entry root is not identity: {asset_id}")
            layers, dependencies, unresolved = UsdUtils.ComputeAllDependencies(str(entry))
            if unresolved:
                raise RuntimeError(f"unresolved dependencies for {asset_id}: {unresolved}")
            outside = [
                str(path)
                for path in dependencies
                if not Path(str(path)).resolve().is_relative_to(destination.resolve())
            ]
            if outside:
                raise RuntimeError(f"non-local dependencies for {asset_id}: {outside}")
            contains_liquid = bool(item.get("contains_liquid"))
            assets.append(
                {
                    "id": asset_id,
                    "entry_usd": f"assets/{asset_id}/asset.usda",
                    "entry_prim": item["entry_prim"],
                    "producer_package": item["package"],
                    "producer_manifest": f"assets/{asset_id}/evidence/manifest.json",
                    "producer_manifest_sha256": _sha(producer_manifest_path),
                    "package_tree_sha256": _tree_hash(destination),
                    "default_consumption": item["default_consumption"],
                    "contains_liquid": contains_liquid,
                    "particle_count": 1948 if contains_liquid else 0,
                    "effective_kinematic": None if contains_liquid else False,
                    "overall_status": "pass",
                }
            )
            closures.append(
                {
                    "id": asset_id,
                    "layers": len(layers),
                    "dependencies": len(dependencies),
                    "unresolved": [],
                    "default_prim": str(stage.GetDefaultPrim().GetPath()),
                }
            )
        shutil.copytree(producer / "evidence", staging / "evidence/producer")
        shutil.copy2(
            source_index_path, staging / "evidence/producer/final_asset_set_manifest.json"
        )
        manifest = {
            "schema_version": "scenario-forge.liquid-interactive-asset-set/v2",
            "asset_set_id": "scientific_workbench_funnel_tube15_dynamic_v2",
            "status": "pass",
            "default_consumption": "dynamic",
            "producer_manifest": "evidence/producer/final_asset_set_manifest.json",
            "producer_manifest_sha256": _sha(source_index_path),
            "exact_source_asset_set": source_index["exact_source_asset_set"],
            "exact_source_manifest_sha256": source_index["exact_source_manifest_sha256"],
            "assets": assets,
            "claims": {
                "effective_kinematic": False,
                "collision_geometry_unchanged": True,
                "dynamic_runtime_qualified": True,
                "dynamic_loaded_liquid_transport": source_index["claims"].get(
                    "dynamic_loaded_liquid_transport", False
                ),
                "robot_policy_success": False,
                "task_success": False,
                "benchmark_success": False,
                "physical_parameters_measured": False,
            },
            "delivery": {"kind": "directory_only", "zip": None, "demo": None},
        }
        (staging / "asset_set_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        )
        (staging / "evidence/import_report.json").write_text(
            json.dumps(
                {
                    "schema_version": "scenario-forge.asset-set-import-report/v2",
                    "status": "pass",
                    "producer_manifest_sha256": _sha(source_index_path),
                    "closures": closures,
                    "byte_identical_package_copy": True,
                    "scenario_forge_physics_overrides": False,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        (staging / "README_CN.md").write_text(
            "# 漏斗—15 mL 螺纹离心管动态液体交互资产集 v2\n\n"
            "默认消费动态版；原 exact-source kinematic v1 保留为来源夹具，不被覆盖。\n\n"
            "| 资产 | 入口 USD | 用法 |\n| --- | --- | --- |\n"
            + "\n".join(
                f"| {item['id']} | `{item['entry_usd']}` | {item['default_consumption']} |"
                for item in assets
            )
            + "\n\n三件器材根节点为 dynamic，带 provisional_geometry 质量/惯量；"
            "碰撞、SDF、视觉和 1948 粒子 overlay 均未由 Scenario Forge 修改。"
            "Isaac 4.1 证据覆盖三次刚体冷启动、三次漏斗导流和开放离心管缓慢抬升。"
            "不声明机器人、任务、benchmark 或真实材料参数已标定。\n",
            encoding="utf-8",
        )
        if output.exists():
            shutil.rmtree(output)
        staging.rename(output)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--producer", type=Path, default=DEFAULT_PRODUCER)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(build_asset_set(args.producer, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

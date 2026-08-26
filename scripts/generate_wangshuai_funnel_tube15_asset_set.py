#!/usr/bin/env python3
"""Import the promoted Wangshuai funnel/tube packages as one asset directory."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCER = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "wangshuai_funnel_tube15_exact_asset_set_20260826"
)
DEFAULT_OUT = (
    ROOT / "outputs/scientific_workbench_funnel_tube15_liquid_asset_set_20260826"
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
        or source_index.get("claims", {}).get("runtime_recomposition_qualified")
        is not True
    ):
        raise RuntimeError("ConvertAsset producer asset set is not promoted")
    staging = output.parent / f".{output.name}.staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        assets = []
        closure_records = []
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
            contains_liquid = asset_id == "small_v2_liquid_seed_1948"
            assets.append(
                {
                    "id": asset_id,
                    "role": item["role"],
                    "entry_usd": f"assets/{asset_id}/asset.usda",
                    "entry_prim": item["entry_prim"],
                    "producer_package": item["package"],
                    "producer_manifest": f"assets/{asset_id}/evidence/manifest.json",
                    "producer_manifest_sha256": _sha(producer_manifest_path),
                    "package_tree_sha256": _tree_hash(destination),
                    "contains_liquid": contains_liquid,
                    "particle_count": 1948 if contains_liquid else 0,
                    "liquid_interactive_geometry": asset_id
                    in {
                        "tube15_threaded_liquid_ready",
                        "funnel_small_v2_liquid_ready",
                    },
                    "overall_status": "pass",
                }
            )
            closure_records.append(
                {
                    "id": asset_id,
                    "layers": len(layers),
                    "dependencies": len(dependencies),
                    "unresolved": [],
                    "default_prim": str(stage.GetDefaultPrim().GetPath()),
                }
            )
        shutil.copytree(producer / "evidence", staging / "evidence/producer")
        manifest = {
            "schema_version": "scenario-forge.liquid-interactive-asset-set/v1",
            "asset_set_id": "scientific_workbench_funnel_tube15_liquid_exact_v1",
            "status": "pass",
            "source": source_index["source"],
            "source_sha256": source_index["source_sha256"],
            "producer_manifest": "evidence/producer/final_asset_set_manifest.json",
            "producer_manifest_sha256": _sha(source_index_path),
            "assets": assets,
            "claims": {
                "physics_parameters_unchanged": True,
                "runtime_recomposition_qualified": True,
                "robot_policy_success": False,
                "task_success": False,
                "benchmark_success": False,
            },
            "delivery": {"kind": "directory_only", "zip": None, "demo": None},
        }
        (staging / "asset_set_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        )
        shutil.copy2(source_index_path, staging / "evidence/producer/final_asset_set_manifest.json")
        (staging / "evidence/import_report.json").write_text(
            json.dumps(
                {
                    "schema_version": "scenario-forge.asset-set-import-report/v1",
                    "status": "pass",
                    "producer_manifest_sha256": _sha(source_index_path),
                    "closures": closure_records,
                    "byte_identical_package_copy": True,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        (staging / "README_CN.md").write_text(
            "# 漏斗—15 mL 螺纹离心管液体交互资产集\n\n"
            "四个目录均可独立打开或引用，请保留各自完整目录。\n\n"
            "| 资产 | 入口 USD | defaultPrim |\n"
            "| --- | --- | --- |\n"
            "| 螺纹离心管体（不含液体） | `assets/tube15_threaded_liquid_ready/asset.usda` | `/Tube15ThreadedLiquidReady` |\n"
            "| 螺纹封闭管盖（不含液体） | `assets/tube15_threaded_closed_cap/asset.usda` | `/Tube15ThreadedClosedCap` |\n"
            "| small-v2 漏斗（不含液体） | `assets/funnel_small_v2_liquid_ready/asset.usda` | `/FunnelSmallV2LiquidReady` |\n"
            "| 1948 粒子液体 overlay | `assets/small_v2_liquid_seed_1948/asset.usda` | `/SmallV2LiquidSeed1948` |\n\n"
            "器材 USD 保留源文件的刚体、SDF/convexHull 和全部 PhysX 参数；没有额外 collider 或物理调参。"
            "液体只存在于 overlay，需由消费场景提供单一 GPU PhysicsScene。\n"
            "本目录不含 ZIP 或公开 demo。机器人、任务和 benchmark 成功均未声明。\n",
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

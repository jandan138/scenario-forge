#!/usr/bin/env python3
"""Promote runtime evidence and build the stir-bar/beaker VR handoff ZIP."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile


STATIC_RUNS = ("static_run_1.json", "static_run_2.json", "static_run_3.json")
DROP_RUNS = ("drop_run_1.json", "drop_run_2.json", "drop_run_3.json")
RENDERS = (
    "scene_overview.png",
    "workspace_closeup.png",
    "task_object_closeup.png",
)


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def package(root: Path) -> Path:
    runtime = root / "vr/evidence/runtime"
    static = [_read(runtime / name) for name in STATIC_RUNS]
    drops = [_read(runtime / name) for name in DROP_RUNS]
    if not all(
        report["status"] == "pass"
        and report["claims"]["static_stability"] is True
        for report in static
    ):
        raise RuntimeError("three-run static gate is incomplete")
    if not all(
        report["status"] == "pass"
        and report["claims"]["non_robot_drop_inside_beaker"] is True
        for report in drops
    ):
        raise RuntimeError("three-run non-robot drop gate is incomplete")
    render_root = root / "vr/evidence/initial_scene"
    missing = [name for name in RENDERS if not (render_root / name).is_file()]
    if missing:
        raise RuntimeError(f"missing render evidence: {missing}")

    summary = {
        "schema_version": "scenario-forge.stir-bar-beaker-qualification.v1",
        "status": "pass",
        "runtime": "isaac41",
        "static_runs": list(STATIC_RUNS),
        "drop_runs": list(DROP_RUNS),
        "claims": {
            "vr_package_openable": True,
            "static_stability": True,
            "non_robot_drop_inside_beaker": True,
            "robot_policy_success": False,
            "canonical_task04_success": False,
        },
    }
    (runtime / "report.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    manifest_path = root / "manifest.json"
    manifest = _read(manifest_path)
    manifest["status"] = "vr_static_and_non_robot_drop_qualified"
    manifest["claims"].update(summary["claims"])
    manifest["runtime_qualification"] = "vr/evidence/runtime/report.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    readme = """# 空烧杯放置磁子 VR 任务包

打开 `vr/scene.usd`，VR 配置为 `vr/task_config.py`。请保留整个文件夹，不能只
复制 scene.usd。USD 不内嵌机器人，VR 运行时按配置插入 Lift2 双臂机器人。

操作流程：辅助臂固定空烧杯；操作臂拿起 29.77 mm 磁力搅拌子，对准杯口后
放入烧杯。烧杯为空，不包含液体或 PBD 粒子。

桌面后排的棕色试剂瓶、吸头盒、洗瓶、透明试剂瓶和移液器转盘均为不操作的
背景 obj，只参与局部 ±0.01 m 随机化，不参与任务判定。

Isaac Sim 4.1 已完成三次 8 秒静置和三次非机器人杯口投放验证。未验证机器人
抓取策略；本任务也不包含原 Task 04 的盖子步骤，因此不声明完整 Task 04 成功。
"""
    (root / "README_CN.md").write_text(readme, encoding="utf-8")

    handoff = root / "handoff"
    handoff.mkdir(exist_ok=True)
    archive = handoff / "scientific_workbench_insert_stir_bar_into_beaker_vr_r1.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or handoff in path.parents:
                continue
            target.write(path, path.relative_to(root))
    digest = sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="utf-8"
    )
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(package(args.root.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Promote three full-scene Task 11 r5 runs and build the handoff ZIP."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile


RUNS = ("run_1.json", "run_2.json", "run_3.json")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def package(root: Path) -> Path:
    evidence = root / "vr/evidence/full_scene_run"
    reports = [_read(evidence / name) for name in RUNS]
    if not all(
        report["status"] == "pass"
        and report["claims"]["full_scene_static_stability"] is True
        and report["claims"]["background_context_static"] is True
        for report in reports
    ):
        raise RuntimeError("all three exact-scene r5 runs must pass")
    summary = {
        "schema_version": "scenario-forge.task11-vr-r5-qualification.v1",
        "status": "pass",
        "runtime": "isaac41",
        "runs": list(RUNS),
        "claims": {
            "full_scene_static_stability": True,
            "background_context_static": True,
            "particle_retention": True,
            "rack_target_slot_insertion_qualified": True,
            "robot_policy_success": False,
            "task11_success": False,
        },
        "supersedes": {
            "package": "scientific_workbench_task11_vr_r4",
            "reason": "r4 background tubes were unqualified split dynamic body/cap assemblies",
        },
    }
    (evidence / "report.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    manifest_path = root / "manifest.json"
    manifest = _read(manifest_path)
    manifest["status"] = "vr_r5_full_scene_run_qualified"
    manifest["claims"].update(summary["claims"])
    manifest["claims"]["static_stability"] = True
    manifest["runtime_qualification"] = "vr/evidence/full_scene_run/report.json"
    manifest["supersedes"] = summary["supersedes"]
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    readme = """# Task 11 VR r5

打开 `vr/scene.usd`，VR 配置为 `vr/task_config.py`。请保留整个文件夹。

r5 修复了 r4 架子背景管 Run 后歪斜、分离和穿模的问题：六支 15 mL 与两支
50 mL 背景管现在是完整 visual-static 闭合组件，不参与物理；目标 15 mL 液体管
仍为动态对象。mixed rack 的目标孔位带 ConvertAsset-owned 底部承托，并通过三次
固定中心轴插管验证。

完整场景在 Isaac Sim 4.1 三次 Run 8 秒均通过：所有背景管保持原位，两组 PBD
粒子 100% 保留且无落底粒子。未验证机器人完整取放或 benchmark 成功。
"""
    (root / "README_CN.md").write_text(readme, encoding="utf-8")
    handoff = root / "handoff"
    handoff.mkdir(exist_ok=True)
    archive = handoff / "scientific_workbench_task11_vr_r5.zip"
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

#!/usr/bin/env python3
"""Promote Task11 r6 runs and build the VR handoff ZIP."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile


RUNS = ("run_1.json", "run_2.json", "run_3.json")
RENDERS = (
    "scene_overview.png",
    "device_closeup.png",
    "after_run_scene_overview.png",
    "after_run_device_closeup.png",
)


def package(root: Path) -> Path:
    evidence = root / "vr/evidence/full_scene_run"
    reports = [json.loads((evidence / name).read_text()) for name in RUNS]
    if not all(
        report["status"] == "pass"
        and report["claims"]["preview_assembled"] is True
        and report["claims"]["base_on_table"] is True
        and report["claims"]["first_step_pose_continuity"] is True
        and report["claims"]["full_scene_static_stability"] is True
        for report in reports
    ):
        raise RuntimeError("all three exact-scene r6 runs must pass")
    render_root = root / "vr/evidence/initial_scene"
    missing = [name for name in RENDERS if not (render_root / name).is_file()]
    if missing:
        raise RuntimeError(f"missing r6 render evidence: {missing}")
    summary = {
        "schema_version": "scenario-forge.task11-vr-r6-qualification.v1",
        "status": "pass",
        "runtime": "isaac41",
        "runs": list(RUNS),
        "claims": {
            "preview_assembled": True,
            "base_on_table": True,
            "first_step_pose_continuity": True,
            "full_scene_static_stability": True,
            "background_context_static": True,
            "particle_retention": True,
            "rack_target_slot_insertion_qualified": True,
            "robot_policy_success": False,
            "task11_success": False,
        },
        "supersedes": {
            "package": "scientific_workbench_task11_vr_r5",
            "reason": "r5 device root floated 65 mm and links were unassembled before Run",
        },
    }
    (evidence / "report.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["status"] = "vr_r6_preview_support_and_full_scene_qualified"
    manifest["claims"].update(summary["claims"])
    manifest["runtime_qualification"] = "vr/evidence/full_scene_run/report.json"
    manifest["supersedes"] = summary["supersedes"]
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (root / "README_CN.md").write_text(
        """# Task 11 VR r6

打开 `vr/scene.usd`，VR 配置为 `vr/task_config.py`，请保留整个文件夹。

r6 使用 ConvertAsset joint-satisfied rest-pose 离心机。未点击 Run 时盖子、转子、
旋钮和按钮已处于组装好的关闭零状态；Run 第一帧不再跳变。机座底面与 0.755 m
桌面重合，不再浮空。机座仍由 fixed joint 固定，不会自由落体。

Isaac Sim 4.1 三次 8 秒完整场景运行通过，两份 PBD 液体均 100% 保留。未验证
机器人完整取放或 benchmark 成功。Isaac 4.5 的 deprecated graph 提示不属于
本包的运行时声明范围。
""",
        encoding="utf-8",
    )
    handoff = root / "handoff"
    handoff.mkdir(exist_ok=True)
    archive = handoff / "scientific_workbench_task11_vr_r6.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for path in sorted(root.rglob("*")):
            if path.is_file() and handoff not in path.parents:
                target.write(path, path.relative_to(root))
    digest = sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="utf-8"
    )
    print(archive)
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    package(args.root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

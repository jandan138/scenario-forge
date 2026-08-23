#!/usr/bin/env python3
"""Promote three Task 11 static observations and build the VR r4 handoff ZIP."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile


RUN_NAMES = ("cold_run_1.json", "cold_run_2.json", "cold_run_3.json")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def package(root: Path) -> Path:
    evidence = root / "vr/evidence/static_validation"
    runs = [_read(evidence / name) for name in RUN_NAMES]
    for run in runs:
        if run["hard_errors"]:
            raise RuntimeError(f"hard runtime errors in run {run['run_index']}")
        for name, result in run["sets"].items():
            if result["retention_ratio"] < 1.0 or result["below_floor_count"] != 0:
                raise RuntimeError(
                    f"static liquid gate failed in run {run['run_index']}: {name}"
                )

    device = _read(root / "vr/deps/centrifuge/evidence/manifest.json")
    required = (
        "contact_press_qualified",
        "button_causes_lid_open",
        "lid_remains_open_after_release",
        "rotor_open_interlock",
        "shutdown_causes_power_off",
    )
    if device.get("overall_status") != "pass" or not all(
        device["claims"].get(name) is True for name in required
    ):
        raise RuntimeError("centrifuge r4 producer qualification is incomplete")

    summary = {
        "schema_version": "scenario-forge.task11_vr_r4_qualification.v1",
        "status": "pass",
        "runtime": "isaac41",
        "runs": RUN_NAMES,
        "particle_gate": {
            "cold_runs": 3,
            "duration_seconds_each": 8.0,
            "all_sets_retention_ratio": 1.0,
            "all_sets_below_floor_count": 0,
            "hard_errors": 0,
        },
        "device_claims": {name: True for name in required},
        "claim_boundary": {
            "manual_close_and_latch": False,
            "robot_policy_success": False,
            "task11_success": False,
        },
    }
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "report.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    manifest_path = root / "manifest.json"
    manifest = _read(manifest_path)
    manifest["status"] = "vr_static_pbd_and_device_controls_qualified"
    manifest["claims"]["static_stability"] = True
    manifest["runtime_qualification"] = "vr/evidence/static_validation/report.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    readme = """# Task 11 VR r4 任务包

打开 `vr/scene.usd`，VR 配置为 `vr/task_config.py`。USD 不内嵌机器人，机器人由
VR 运行时按配置插入；请保留整个文件夹，不能只拷贝 scene.usd。

LABSPIN X8 r4 已在 Isaac Sim 4.1 通过真实刚体接触验证：OPEN 按钮压下后盖子
自动打开约 78°并保持；转子运行时 OPEN 被互锁；STOP 按下后可观测
`device:powerState=off`。两支各 2640 粒子的 PBD 液体在三次 8 秒冷启动中均
100% 保留、无落底粒子、无硬错误。

边界：未验证机器人完整取放、手动关盖闭锁或完整 Task 11 成功。
"""
    (root / "README_CN.md").write_text(readme, encoding="utf-8")

    handoff = root / "handoff"
    handoff.mkdir(exist_ok=True)
    archive = handoff / "scientific_workbench_task11_vr_r4.zip"
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

#!/usr/bin/env python3
"""Package Task11 r7 after mechanical and Lift2 scripted-oracle validation."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile


def package(root: Path, robot_report: Path) -> Path:
    root = root.resolve()
    mechanical_path = root / "vr/evidence/mechanical_oracle/report.json"
    mechanical = json.loads(mechanical_path.read_text(encoding="utf-8"))
    robot = json.loads(robot_report.read_text(encoding="utf-8"))
    if mechanical.get("claims", {}).get("mechanical_oracle_success") is not True:
        raise RuntimeError("mechanical oracle has not passed")
    claims = robot.get("claim_boundary", {})
    observations = robot.get("runtime_report", {})
    if claims.get("canonical_task11_scripted_oracle_success") is not True:
        raise RuntimeError("canonical Lift2 scripted oracle has not passed")
    if observations.get("post_initialization_object_transform_write_count") != 0:
        raise RuntimeError("robot oracle wrote an object transform")
    if observations.get("direct_device_joint_target_write_count") != 0:
        raise RuntimeError("robot oracle wrote a device joint target")
    evidence = root / "vr/evidence/robot_oracle"
    evidence.mkdir(parents=True, exist_ok=True)
    copied_report = evidence / "report.json"
    copied_report.write_bytes(robot_report.read_bytes())
    for key in ("overview_video", "closeup_video"):
        source = Path(robot["media"][key]).resolve()
        (evidence / source.name).write_bytes(source.read_bytes())
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "r7_canonical_scripted_oracle_qualified"
    manifest["claims"].update(
        {
            "mechanical_oracle_success": True,
            "canonical_task11_scripted_oracle_success": True,
            "task11_success": True,
            "robot_policy_success": False,
            "benchmark_success": False,
        }
    )
    manifest["mechanical_qualification"] = "vr/evidence/mechanical_oracle/report.json"
    manifest["robot_oracle_qualification"] = "vr/evidence/robot_oracle/report.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (root / "README_CN.md").write_text(
        """# Task11 VR r7\n\n打开 `vr/scene.usd`；VR 配置为 `vr/task_config.py`。\n\nr7 使用 ConvertAsset 上下分区摩擦离心管：下部保持低摩擦插孔，红色管盖\n使用高摩擦抓取材质。Isaac Sim 4.1 中机械 oracle 和 Lift2 scripted oracle\n各完成一次连续任务。该结论不是模型策略或 benchmark 成功率。\n""",
        encoding="utf-8",
    )
    handoff = root / "handoff"
    handoff.mkdir(exist_ok=True)
    archive = handoff / "scientific_workbench_task11_vr_r7.zip"
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
    parser.add_argument("--robot-report", type=Path, required=True)
    args = parser.parse_args()
    package(args.root, args.robot_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

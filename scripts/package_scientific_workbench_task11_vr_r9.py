#!/usr/bin/env python3
"""Package the Task 11 r9 scene-qualified, robot-unvalidated candidate."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = ROOT / "outputs/scientific_workbench_task11_vr_r9_20260827"
REQUIRED_TRUE = (
    "visual_fitted_lid_collision",
    "visual_static_liquid_only",
    "particle_free_scene",
    "scene_static_stability",
    "robot_free_device_mechanics",
    "single_rigid_body_closed_15ml",
    "all_15ml_tubes_replaced",
)
REQUIRED_FALSE = ("task11_success", "robot_policy_success", "benchmark_success")


def package_candidate(package: Path) -> Path:
    package = package.resolve()
    manifest = json.loads((package / "manifest.json").read_text())
    if manifest.get("status") != "scene_qualified_robot_unvalidated":
        raise RuntimeError("r9 is not scene-qualified")
    claims = manifest.get("claims", {})
    if not all(claims.get(name) is True for name in REQUIRED_TRUE):
        raise RuntimeError("r9 scene qualification claims are incomplete")
    if not all(claims.get(name) is False for name in REQUIRED_FALSE):
        raise RuntimeError("r9 success claims must remain false")
    for relative in (
        "vr/evidence/r9_static/report.json",
        "vr/evidence/r9_mechanical/report.json",
        "vr/evidence/initial_scene/visual_review.json",
        "adapters/ebench/genmanip/scenario.yaml",
    ):
        if not (package / relative).is_file():
            raise FileNotFoundError(package / relative)
    (package / "README_CN.md").write_text(
        "# Task 11 r9 候选场景包\n\n"
        "- VR 入口：`vr/scene.usd`\n"
        "- VR 配置：`vr/task_config.py`\n"
        "- GenManip：`adapters/ebench/genmanip/`\n"
        "- 全部八支 15 mL 管均为螺纹管体 + 红色封顶盖单刚体总成。\n"
        "- 两支任务管保留视觉假液体，无 PBD、不可倾倒或计分。\n"
        "- 本包通过场景静置和 robot-free 机械验证；未验证机器人完整任务。\n"
        "- `task11_success`、`robot_policy_success`、`benchmark_success` 均为 false。\n",
        encoding="utf-8",
    )
    handoff = package / "handoff"
    handoff.mkdir(parents=True, exist_ok=True)
    archive = handoff / "scientific_workbench_task11_vr_r9_candidate.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(package.rglob("*")):
            if not path.is_file() or handoff in path.parents:
                continue
            output.write(path, Path(package.name) / path.relative_to(package))
    archive.with_suffix(".zip.sha256").write_text(
        f"{sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n",
        encoding="utf-8",
    )
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    args = parser.parse_args()
    print(package_candidate(args.package))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

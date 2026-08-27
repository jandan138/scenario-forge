#!/usr/bin/env python3
"""Package the scene-qualified Task 12 rack-to-rotor alias candidate."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = ROOT / "outputs/scientific_workbench_task12_alias_centrifuge_rack_to_rotor_vr_r1_20260827"
ARCHIVE_NAME = "scientific_workbench_task12_alias_centrifuge_rack_to_rotor_candidate.zip"


def package_candidate(package: Path) -> Path:
    package = package.resolve()
    manifest = json.loads((package / "manifest.json").read_text())
    if manifest.get("status") != "scene_qualified_robot_unvalidated":
        raise RuntimeError("Task 12 alias is not scene-qualified")
    claims = manifest["claims"]
    for claim in (
        "target_tube_starts_in_rack",
        "target_rotor_socket_initially_empty",
        "no_50ml_tubes",
        "scene_static_stability",
        "robot_free_transfer_oracle_success",
        "adapter_load_smoke",
    ):
        if claims.get(claim) is not True:
            raise RuntimeError(f"required alias claim is not true: {claim}")
    for claim in (
        "manual_close_and_latch",
        "robot_policy_success",
        "task_success",
        "benchmark_success",
    ):
        if claims.get(claim) is not False:
            raise RuntimeError(f"bounded alias claim is not false: {claim}")
    (package / "README_CN.md").write_text(
        "# 临时 Task 12：管架到离心机转子\n\n"
        "- VR：`vr/scene.usd` + `vr/task_config.py`\n"
        "- GenManip：`adapters/ebench/genmanip/`\n"
        "- 目标带蓝色假液体的15 mL管初始位于管架，最终目标是转子 socket 18。\n"
        "- socket 6 保留一支空平衡管；场景不含50 mL管。\n"
        "- OPEN自动开盖；不声明手动关盖锁定。\n"
        "- robot-free搬运oracle通过，但机器人策略、任务和benchmark成功均为false。\n"
        "- 这是临时Task 12别名；正式目录中的Task 12仍是结束烘干。\n",
        encoding="utf-8",
    )
    handoff = package / "handoff"
    handoff.mkdir(parents=True, exist_ok=True)
    archive = handoff / ARCHIVE_NAME
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

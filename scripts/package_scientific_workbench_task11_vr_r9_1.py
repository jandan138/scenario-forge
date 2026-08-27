#!/usr/bin/env python3
"""Package the scene-qualified Task 11 r9.1 left/right candidate."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = ROOT / "outputs/scientific_workbench_task11_vr_r9_1_left_right_20260827"
ARCHIVE_NAME = "scientific_workbench_task11_vr_r9_1_left_right_candidate.zip"


def package_candidate(package: Path, *, archive_name: str = ARCHIVE_NAME) -> Path:
    package = package.resolve()
    manifest = json.loads((package / "manifest.json").read_text())
    if manifest.get("status") != "scene_qualified_robot_unvalidated":
        raise RuntimeError("left/right Task 11 package is not scene-qualified")
    claims = manifest["claims"]
    for claim in (
        "left_right_camera_pair",
        "scene_static_stability",
        "robot_free_device_mechanics",
    ):
        if claims.get(claim) is not True:
            raise RuntimeError(f"required r9.1 claim is not true: {claim}")
    for claim in ("robot_policy_success", "task11_success", "benchmark_success"):
        if claims.get(claim) is not False:
            raise RuntimeError(f"bounded r9.1 claim is not false: {claim}")
    release_id = str(manifest.get("release_id", "r9_1"))
    primary_socket = int(manifest["primary_socket"])
    balance_socket = int(manifest["balance_socket"])
    (package / "README_CN.md").write_text(
        f"# Task 11 {release_id} 左右对称候选包\n\n"
        f"- 两支转子15 mL管位于 socket {primary_socket}/{balance_socket}。\n"
        "- 除孔位外继承r9红盖一体管、视觉假液体、背景和设备行为。\n"
        "- VR入口：`vr/scene.usd`；GenManip：`adapters/ebench/genmanip/`。\n"
        "- 场景静置与robot-free设备机械验证通过；机器人、任务和benchmark成功为false。\n",
        encoding="utf-8",
    )
    handoff = package / "handoff"
    handoff.mkdir(parents=True, exist_ok=True)
    archive = handoff / archive_name
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
    parser.add_argument("--archive-name", default=ARCHIVE_NAME)
    args = parser.parse_args()
    print(package_candidate(args.package, archive_name=args.archive_name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

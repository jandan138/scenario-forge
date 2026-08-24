#!/usr/bin/env python3
"""Package the Task 11 raw-articulated negative-control handoff."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def package(root: Path) -> Path:
    report_path = root / "vr/evidence/raw_runtime/report.json"
    report = json.loads(report_path.read_text())
    if report.get("status") != "expected_failure_observed":
        raise RuntimeError("raw-drop-in diagnostic did not observe the expected failure")
    provenance_path = root / "provenance/raw_centrifuge_source.json"
    provenance = json.loads(provenance_path.read_text())
    raw_root = root / "vr/deps/raw_centrifuge"
    for member, expected in provenance["members"].items():
        actual = _sha(raw_root / member)
        if actual != expected:
            raise RuntimeError(f"raw member hash changed: {member}")

    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["status"] = "negative_control_expected_failure_observed"
    manifest["negative_control"] = True
    manifest["runtime_diagnostic"] = "vr/evidence/raw_runtime/report.json"
    manifest["claims"]["expected_physics_errors_observed"] = True
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    readme = """# Task 11 原始离心机直接拖入负面对照包

打开 `vr/scene.usd`，VR 配置为 `vr/task_config.py`。离心机直接引用原压缩包的
`assets/usd/centrifuge_articulated.usda`，没有经过 ConvertAsset，也没有增加任何
碰撞、质量、惯量、drive、动画清理或关节修复。

点击 Run 后预期出现 PhysX 错误，包括：

- `Articulations with kinematic bodies are not supported`；
- `cannot create a joint between static bodies`。

原作者的盖子、转子、编码旋钮、START、STOP 五个 joint prim 都保留，但 Isaac
Sim 4.1 无法把该原始层级构造成有效 articulation。该包只用于向评审者展示原始
USD 直接拖入的结果，不能用于 VR 数采、benchmark 或机器人任务声明。

正式可用版本仍是 Task 11 VR r5。
"""
    (root / "README_CN.md").write_text(readme, encoding="utf-8")
    handoff = root / "handoff"
    handoff.mkdir(exist_ok=True)
    archive = handoff / "scientific_workbench_task11_raw_articulated_dropin.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or handoff in path.parents:
                continue
            target.write(path, path.relative_to(root))
    digest = _sha(archive)
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

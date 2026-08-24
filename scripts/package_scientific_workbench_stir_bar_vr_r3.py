#!/usr/bin/env python3
"""Promote the short r3 check and build the liquid/stirrer VR handoff ZIP."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile


RENDERS = (
    "scene_overview.png",
    "workspace_closeup.png",
    "task_object_closeup.png",
)


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def package(root: Path) -> Path:
    report_path = root / "vr/evidence/r3_short_run/report.json"
    report = _read(report_path)
    if not (
        report.get("status") == "pass"
        and report["claims"].get("short_scene_integration") is True
        and report["claims"].get("gpu_pbd_loaded_start") is True
    ):
        raise RuntimeError("r3 short scene integration gate is incomplete")

    render_root = root / "vr/evidence/initial_scene"
    missing = [name for name in RENDERS if not (render_root / name).is_file()]
    if missing:
        raise RuntimeError(f"missing render evidence: {missing}")

    manifest_path = root / "manifest.json"
    manifest = _read(manifest_path)
    manifest["status"] = "layout_and_short_runtime_ready"
    manifest["claims"].update(
        {
            "short_scene_integration": True,
            "gpu_pbd_loaded_start": True,
            "magnetic_stirring_simulated": False,
            "heating_simulated": False,
            "robot_policy_success": False,
            "canonical_task04_success": False,
        }
    )
    manifest["runtime_qualification"] = "vr/evidence/r3_short_run/report.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    readme = """# 烧杯液体 + 磁子 + 磁力搅拌器 VR 摆放包 r3

打开 `vr/scene.usd`，VR 配置为 `vr/task_config.py`。必须保留整个文件夹，不能只
复制 scene.usd。USD 不内嵌机器人，VR 运行时按配置插入 Lift2 双臂机器人。

操作布局：辅助臂固定烧杯；操作臂从 30 cm 不锈钢托盘上的磁子开始，拿起磁子、
对准杯口并放入烧杯。桌面右侧新增 `obj_magnetic_stirrer`，为后续把烧杯放到设备
上预留位置；本版本不模拟磁力搅拌或加热，搅拌器不参与任务 metric。

烧杯初始包含 816 个 GPU PBD 粒子，复用 Task02 fill40 配方；生产者实测填充率
约 44.13%。烧杯与液体成组做 local ±0.01 m 随机化，托盘与磁子成组随机化，
搅拌器和后排背景物体各自做 local ±0.01 m 随机化。

Isaac Sim 4.1 只做了一次 3 秒场景静置检查和初始场景渲染，以便快速交付摆放。
未验证机器人抓取、磁子真实投放、磁力搅拌、加热或 benchmark 成功率。
"""
    (root / "README_CN.md").write_text(readme, encoding="utf-8")

    handoff = root / "handoff"
    handoff.mkdir(exist_ok=True)
    archive = handoff / "scientific_workbench_insert_stir_bar_into_beaker_vr_r3.zip"
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

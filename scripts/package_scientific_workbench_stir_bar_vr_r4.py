#!/usr/bin/env python3
"""Promote dual-entry r4 evidence and build the VR handoff ZIP."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile


RENDERS = ("scene_overview.png", "workspace_closeup.png", "task_object_closeup.png")


def package(root: Path) -> Path:
    report_path = root / "vr/evidence/r4_dual_entry/report.json"
    report = json.loads(report_path.read_text())
    if report.get("status") != "pass":
        raise RuntimeError("r4 dual-entry validation is not pass")
    if report["claims"].get("editable_liquid_sampler") is not True:
        raise RuntimeError("editable liquid sampler was not validated")
    if report["claims"].get("robot_policy_success") is not False:
        raise RuntimeError("r4 must not claim robot policy success")
    render_root = root / "vr/evidence/initial_scene"
    missing = [name for name in RENDERS if not (render_root / name).is_file()]
    if missing:
        raise RuntimeError(f"missing render evidence: {missing}")

    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["status"] = "dual_entry_static_liquid_ready"
    manifest["runtime_qualification"] = "vr/evidence/r4_dual_entry/report.json"
    manifest["claims"].update(report["claims"])
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    count = report["observations"]["particle_count"]
    readme = f"""# 磁子放入带液烧杯 VR 任务包 r4

正式数采入口：`vr/scene.usd` + `vr/task_config.py`。这一入口冻结了 {count}
个透明蓝 GPU PBD 粒子，启动结果稳定、可复现。

液量编辑入口：`vr/scene_liquid_edit.usd` +
`vr/task_config_liquid_edit.py`。在 Stage 中选择
`/World/fluid_runtime/Samplers/beaker_liquid`，仅修改 `xformOp:scale` 的 Z
分量（圆柱高度），然后运行仿真即可重新采样。XY、半径、旋转不要修改。

两种入口均使用同一个标准 SDF 烧杯和网页标准 ClearBorosilicate 玻璃材质。
液体材质为透明蓝：diffuseColor=(0.32, 0.72, 0.95)，emissiveColor=
(0.02, 0.12, 0.28)，opacity=0.34，IOR=1.333，roughness=0.02。每摊液体
拥有独立 ParticleSet/particleGroup，
全场共享一个 ParticleSystem。

Isaac Sim 4.1 已验证：全场只有一个活动 PhysicsScene，冻结液体 100% 保留，
0 粒子掉落，实时 Cylinder Sampler 正确指向自己的 ParticleSet。未验证机器人
抓取、磁子投放、磁力搅拌、加热或 benchmark 成功。
"""
    (root / "README_CN.md").write_text(readme, encoding="utf-8")

    handoff = root / "handoff"
    handoff.mkdir(exist_ok=True)
    archive = handoff / "scientific_workbench_insert_stir_bar_into_beaker_vr_r4.zip"
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

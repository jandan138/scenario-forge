#!/usr/bin/env python3
"""Promote r5 4.1/4.5 render evidence and build the VR handoff ZIP."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile


RENDERS = ("scene_overview.png", "workspace_closeup.png", "task_object_closeup.png")


def package(root: Path) -> Path:
    evidence = root / "vr/evidence/r5_runtime"
    isaac41 = json.loads((evidence / "isaac41.json").read_text(encoding="utf-8"))
    isaac45 = json.loads((evidence / "isaac45.json").read_text(encoding="utf-8"))
    for label, report in (("isaac41", isaac41), ("isaac45", isaac45)):
        if (
            report.get("status") != "pass"
            or report.get("hydra_primvar_error_count") != 0
            or report["claims"].get("particle_display_primvars_authored") is not False
        ):
            raise RuntimeError(f"{label} r5 render compatibility has not passed")
    render_root = root / "vr/evidence/initial_scene"
    missing = [name for name in RENDERS if not (render_root / name).is_file()]
    if missing:
        raise RuntimeError(f"missing Isaac 4.1 renders: {missing}")
    isaac45_overview = root / "vr/evidence/isaac45_render/scene_overview.png"
    if not isaac45_overview.is_file():
        raise RuntimeError("missing Isaac 4.5 overview render")

    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "hydra_compatible_dual_entry_ready"
    manifest["runtime_qualification"] = {
        "formal": "vr/evidence/r5_runtime/isaac41.json",
        "compatibility": "vr/evidence/r5_runtime/isaac45.json",
    }
    manifest["claims"].update(
        {
            "particle_display_primvars_authored": False,
            "shared_particle_system_material": True,
            "isaac45_render_compatibility": True,
            "robot_policy_success": False,
            "benchmark_success": False,
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    count = isaac41["entries"]["scene.usd"]["authored_particle_count"]
    (root / "README_CN.md").write_text(
        f"""# 磁子放入带液烧杯 VR 任务包 r5

正式入口为 `vr/scene.usd` + `vr/task_config.py`，液量编辑入口为
`vr/scene_liquid_edit.usd` + `vr/task_config_liquid_edit.py`。冻结入口含
{count} 个透明蓝 GPU PBD 粒子。

r5 删除了 PhysX ParticleSet 上重复 authored 的 displayColor/displayOpacity；
颜色和透明度仍由共享 LiquidMaterial 提供。Isaac Sim 4.1 正式物理/渲染 gate
和 Isaac Sim 4.5 兼容渲染 gate 均未出现 Hydra `Unrecognized primvar` 错误。
正式 benchmark runtime 仍限定 Isaac Sim 4.1。

未验证机器人抓取、磁子投放、磁力搅拌、加热或 benchmark 成功。
""",
        encoding="utf-8",
    )
    handoff = root / "handoff"
    handoff.mkdir(exist_ok=True)
    archive = handoff / "scientific_workbench_insert_stir_bar_into_beaker_vr_r5.zip"
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

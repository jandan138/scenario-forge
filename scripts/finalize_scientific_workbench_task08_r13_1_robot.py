#!/usr/bin/env python3
"""Package Task08 r13.1 adapter with scoped blocked robot evidence."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "outputs/scientific_workbench_task08_vr_r13_1_robot_20260902"
DEFAULT_EOS = Path(
    "/cpfs/user/zhuzihou/dev/embodied-eval-os/outputs/"
    "task08_r13_1_robot_oracle_20260902"
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def finalize(root: Path, eos: Path) -> Path:
    root = root.resolve()
    eos = eos.resolve()
    report = json.loads((eos / "final_report.json").read_text())
    if report.get("status") != "blocked":
        raise RuntimeError("this finalizer expects scoped blocked robot evidence")
    evidence = root / "evidence/robot"
    evidence.mkdir(parents=True, exist_ok=True)
    copied = {}
    for name in (
        "probe_report.json",
        "cap_report.json",
        "grasp_report.json",
        "final_report.json",
    ):
        destination = evidence / name
        shutil.copy2(eos / name, destination)
        copied[name] = _sha(destination)
    manifest = {
        "schema_version": "scenario-forge.task08-r13.1-robot-validation/v1",
        "status": "robot_validation_blocked",
        "adapter": "adapters/ebench/genmanip",
        "evidence": copied,
        "blockers": report["blockers"],
        "claims": {
            "assisted_thread_non_robot_ready": True,
            **report["claims"],
        },
        "claim_boundary": report["claim_boundary"],
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    (root / "README_CN.md").write_text(
        "# Task 08 r13.1 Lift2 验证候选\n\n"
        "r13 的无机器人一圈辅助仍然有效；本包新增 GenManip/Lift2 适配与真实"
        "抓取证据。可达性通过，但管帽抓取冷启动不一致，管体未完成抬升，"
        "因此未执行三段旋转和完整任务，所有机器人成功声明保持 false。\n"
    )
    handoff = root / "handoff"
    handoff.mkdir(exist_ok=True)
    archive = handoff / "scientific_workbench_task08_r13_1_robot_validation_blocked.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            if path == archive or path.suffix == ".sha256":
                continue
            bundle.write(path, Path(root.name) / path.relative_to(root))
    archive.with_suffix(archive.suffix + ".sha256").write_text(
        _sha(archive) + "  " + archive.name + "\n"
    )
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--eos", type=Path, default=DEFAULT_EOS)
    args = parser.parse_args()
    print(finalize(args.root, args.eos))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

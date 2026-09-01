#!/usr/bin/env python3
"""Promote and package Task08 r13 after three Isaac 4.1 observations."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def finalize(root: Path) -> Path:
    root = root.resolve()
    reports = [
        json.loads((root / f"vr/evidence/runtime/run_{index:02d}.json").read_text())
        for index in range(3)
    ]
    if not all(report.get("status") == "pass" for report in reports):
        raise RuntimeError("Task08 r13 one-turn qualification is incomplete")
    if not all(
        report.get("claims", {}).get("one_turn_assisted_thread") is True
        and report.get("claims", {}).get("release_retention") is True
        for report in reports
    ):
        raise RuntimeError("Task08 r13 runtime claims are incomplete")
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["status"] = "r13_one_turn_assisted_thread_ready"
    manifest["claims"].update(
        {
            "vr_action_collection_layout_ready": True,
            "scene_static_stability": True,
            "thread_interaction_ready": True,
            "task08_success": False,
            "robot_policy_success": False,
            "benchmark_success": False,
        }
    )
    manifest["qualification"] = {
        "runtime": "isaac41",
        "protocol": "aligned_capture_clockwise_360deg_release_hold_and_tube_lift",
        "runs": [
            {
                "path": f"vr/evidence/runtime/run_{index:02d}.json",
                "sha256": _sha(
                    root / f"vr/evidence/runtime/run_{index:02d}.json"
                ),
                "terminal_rotation_deg": report["terminal"]["rotation_deg"],
                "closed_relative_z_m": report["closed_relative_z_m"],
            }
            for index, report in enumerate(reports)
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    handoff = root / "handoff"
    handoff.mkdir(exist_ok=True)
    archive = handoff / "scientific_workbench_task08_vr_r13_one_turn.zip"
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
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(finalize(args.root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

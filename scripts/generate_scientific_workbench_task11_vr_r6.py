#!/usr/bin/env python3
"""Generate Task11 VR r6 with the assembled rest-pose centrifuge on the table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import generate_scientific_workbench_task11_vr_static as r5


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "outputs/scientific_workbench_task11_vr_r6_20260824"
DEFAULT_CENTRIFUGE = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "labspin_x8_task11_r5_rest_pose_20260824/package"
)
DEVICE_XYZ = (0.22, 0.09, 0.755)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--centrifuge", type=Path, default=DEFAULT_CENTRIFUGE)
    args = parser.parse_args()
    output = r5.build(
        args.out.resolve(),
        r5.DEFAULT_CONTEXT_ASSETS,
        args.centrifuge.resolve(),
        r5.DEFAULT_BASE,
        r5.DEFAULT_LIQUID,
        device_xyz=DEVICE_XYZ,
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["schema_version"] = "scenario-forge-task11-vr-candidate/v0.4"
    manifest["status"] = "r6_preview_and_support_pending_runtime"
    manifest["device_xyz_m"] = list(DEVICE_XYZ)
    manifest["claims"].update(
        {
            "preview_assembled": False,
            "base_on_table": False,
            "first_step_pose_continuity": False,
            "robot_policy_success": False,
            "task11_success": False,
        }
    )
    manifest["producer_qualifications"]["device_rest_pose"] = (
        "vr/deps/centrifuge/evidence/rest_pose/report.json"
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Generate Task11 VR r7 with the producer-qualified split-friction tube."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import generate_scientific_workbench_task11_vr_static as base


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "outputs/scientific_workbench_task11_vr_r7_20260825"
DEFAULT_CENTRIFUGE = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "labspin_x8_task11_r5_rest_pose_20260824/package"
)
DEFAULT_TUBE = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "task11_r7_target_tube_grasp_20260824/package"
)
DEVICE_XYZ = (0.0, -0.1, 0.755)
RACK_XYZ = (-0.4, -0.3, 0.755)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--centrifuge", type=Path, default=DEFAULT_CENTRIFUGE)
    parser.add_argument("--tube", type=Path, default=DEFAULT_TUBE)
    args = parser.parse_args()
    tube_manifest = json.loads(
        (args.tube / "evidence/manifest.json").read_text(encoding="utf-8")
    )
    if (
        tube_manifest.get("overall_status") != "pass"
        or tube_manifest.get("claims", {}).get("fixed_candidate_close_lift_hold")
        is not True
    ):
        raise RuntimeError("producer tube close/lift/hold qualification is incomplete")
    output = base.build(
        args.out.resolve(),
        base.DEFAULT_CONTEXT_ASSETS,
        args.centrifuge.resolve(),
        base.DEFAULT_BASE,
        base.DEFAULT_LIQUID,
        device_xyz=DEVICE_XYZ,
        target_tube=args.tube,
        rack_xyz=RACK_XYZ,
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = "scenario-forge-task11-vr-candidate/v0.5"
    manifest["status"] = "r7_split_friction_tube_pending_runtime"
    manifest["device_xyz_m"] = list(DEVICE_XYZ)
    manifest["rack_xyz_m"] = list(RACK_XYZ)
    manifest["producer_qualifications"]["target_tube"] = (
        "vr/deps/tube/evidence/manifest.json"
    )
    manifest["claims"].update(
        {
            "producer_tube_fixed_candidate_close_lift_hold": True,
            "mechanical_oracle_success": False,
            "canonical_task11_scripted_oracle_success": False,
            "robot_policy_success": False,
            "benchmark_success": False,
            "task11_success": False,
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

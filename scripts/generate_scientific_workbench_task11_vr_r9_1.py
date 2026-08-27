#!/usr/bin/env python3
"""Generate Task 11 r9.1 with camera-horizontal opposed rotor tubes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import generate_scientific_workbench_task11_vr_r8 as r8  # noqa: E402
from scripts import generate_scientific_workbench_task11_vr_r9 as r9  # noqa: E402


PRIMARY_SOCKET = 3
BALANCE_SOCKET = 15
DEFAULT_OUT = ROOT / "outputs/scientific_workbench_task11_vr_r9_1_left_right_20260827"


def build(output: Path) -> Path:
    result = r8.build(
        output.resolve(),
        r8.DEFAULT_CENTRIFUGE,
        r9.DEFAULT_TUBE,
        required_tube_claim="single_rigid_body_closed_assembly",
        tube_entry_prim="/ThreadedTube15RedClosed",
        tube_asset_filename="asset.usda",
        replace_all_15ml=True,
        release_id="r9_1",
        primary_socket=PRIMARY_SOCKET,
        balance_socket=BALANCE_SOCKET,
    )
    manifest_path = result / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["layout_revision"] = "left_right_camera_pair"
    manifest["claims"].update(
        {
            "left_right_camera_pair": True,
            "scene_static_stability": False,
            "robot_free_device_mechanics": False,
            "robot_policy_success": False,
            "task11_success": False,
            "benchmark_success": False,
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(build(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

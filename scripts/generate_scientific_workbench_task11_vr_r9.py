#!/usr/bin/env python3
"""Generate Task 11 r9 with eight single-rigid threaded red-cap 15 mL tubes."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import generate_scientific_workbench_task11_vr_r8 as r8  # noqa: E402


DEFAULT_OUT = ROOT / "outputs/scientific_workbench_task11_vr_r9_20260827"
DEFAULT_TUBE = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "threaded_tube15_red_closed_assembly_20260827/packages/"
    "threaded_tube15_red_closed_assembly"
)


def build(output: Path, centrifuge: Path, tube: Path) -> Path:
    return r8.build(
        output,
        centrifuge,
        tube,
        required_tube_claim="single_rigid_body_closed_assembly",
        tube_entry_prim="/ThreadedTube15RedClosed",
        tube_asset_filename="asset.usda",
        replace_all_15ml=True,
        release_id="r9",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--centrifuge", type=Path, default=r8.DEFAULT_CENTRIFUGE)
    parser.add_argument("--tube", type=Path, default=DEFAULT_TUBE)
    args = parser.parse_args()
    print(build(args.out, args.centrifuge, args.tube))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

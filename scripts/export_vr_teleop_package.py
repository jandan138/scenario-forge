#!/usr/bin/env python3
"""Export the formal VR-teleop handoff from a compiled Scenario Forge package."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from scenario_forge.adapters.vr_teleop import VR_TASK_ID, export_vr_teleop_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export relocatable scene.usd + task_config.py VR handoff."
    )
    parser.add_argument("package", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--task-id", default=VR_TASK_ID)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = export_vr_teleop_package(
        args.package,
        args.out,
        task_id=args.task_id,
    )
    print(f"VR scene USD: {result.scene_usd}")
    print(f"VR config module: {result.task_config}")
    print(f"Parity evidence: {result.parity_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate a GenManip/CuRobo fixed-base IK result for one Scenario Forge package."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from scenario_forge.adapters.ebench.ik_preflight import validate_provisional_ik_result


REQUEST_RELATIVE_PATH = Path("adapters/ebench/genmanip/provisional_ik_preflight/request.yaml")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    package = args.package.resolve()
    request = package / REQUEST_RELATIVE_PATH
    evidence = validate_provisional_ik_result(request, args.result.resolve())
    print(f"Provisional IK evidence: {evidence.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Create a portable intake for a Code-as-Room source delivery."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import yaml

from scenario_forge.adapters.generated_environment import (
    build_generated_environment_intake,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--delivery-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    output = Path(args.out)
    root = Path(args.delivery_root)
    try:
        output.resolve().relative_to(root.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("--out must be outside delivery_root")

    intake = build_generated_environment_intake(
        asset_id=args.asset_id,
        delivery_root=root,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        yaml.safe_dump(
            intake.to_mapping(),
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

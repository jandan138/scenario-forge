"""Build all 3 frozen-hash v0.8 HermiteTwin vs Spring-Mass A/B thin-shell packages."""

from __future__ import annotations

import argparse
from pathlib import Path

from scenario_forge.adapters.deformable_v08 import build_all_v08_ab_packages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "external_artifacts" / "deformable_v08_ab_packages",
    )
    args = parser.parse_args()
    summary = build_all_v08_ab_packages(args.out_dir)
    print(f"Built {len(summary['task_ids'])} v0.8 A/B packages in {args.out_dir}")


if __name__ == "__main__":
    main()

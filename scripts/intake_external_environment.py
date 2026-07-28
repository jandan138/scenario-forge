#!/usr/bin/env python3
"""Create a portable intake record for an externally extracted environment."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import yaml

from scenario_forge.assets.external_environment import (
    build_external_environment_intake,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-id", required=True)
    parser.add_argument(
        "--source-root",
        required=True,
        help="Extracted top-level source directory; it is never emitted in the record.",
    )
    parser.add_argument(
        "--source-usd",
        required=True,
        help="Canonical USD path relative to --source-root.",
    )
    parser.add_argument(
        "--expected-source-sha256",
        help="Optional lowercase SHA-256 to verify before writing the record.",
    )
    parser.add_argument(
        "--archive-sha256",
        required=True,
        help="Lowercase SHA-256 of the source archive.",
    )
    parser.add_argument(
        "--restricted-provenance-id",
        required=True,
        help="URL-free internal reference beginning with 'restricted/'.",
    )
    parser.add_argument("--out", required=True, help="Output YAML outside --source-root.")
    args = parser.parse_args(argv)

    source_root = Path(args.source_root)
    output_path = Path(args.out)
    if _is_within(output_path, source_root):
        raise ValueError("--out must be outside source_root to preserve the snapshot")

    intake = build_external_environment_intake(
        asset_id=args.asset_id,
        source_root=source_root,
        source_usd_relative_path=args.source_usd,
        archive_sha256=args.archive_sha256,
        restricted_provenance_id=args.restricted_provenance_id,
        expected_source_sha256=args.expected_source_sha256,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(intake.to_mapping(), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return 0


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


if __name__ == "__main__":  # pragma: no cover - CLI entry point.
    raise SystemExit(main())

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scenario_forge.package import validate_package
from scenario_forge.scaffold import scaffold_starter_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scenario-forge",
        description="Generate and validate evaluation-ready embodied scenario packages.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    package_parser = subparsers.add_parser("package", help="Scenario package commands")
    package_subparsers = package_parser.add_subparsers(dest="package_command", required=True)

    scaffold_parser = package_subparsers.add_parser("scaffold", help="Create a starter package")
    scaffold_parser.add_argument("--out", required=True, help="Output package directory")

    check_parser = package_subparsers.add_parser("check", help="Validate a scenario package")
    check_parser.add_argument("package_dir", help="Package directory containing manifest.yaml")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "package" and args.package_command == "scaffold":
        out_dir = scaffold_starter_package(Path(args.out))
        print(f"Created starter package: {out_dir}")
        return 0

    if args.command == "package" and args.package_command == "check":
        report = validate_package(Path(args.package_dir))
        for message in report.messages:
            print(message)
        if report.ok:
            print("Package OK")
            return 0
        return 1

    parser.error("unreachable command")
    return 2


if __name__ == "__main__":
    sys.exit(main())

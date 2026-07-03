from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scenario_forge.package import validate_package


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Scenario Forge package directory.")
    parser.add_argument("package_dir")
    args = parser.parse_args(argv)

    report = validate_package(Path(args.package_dir))
    for message in report.messages:
        print(message)
    if report.ok:
        print("Package OK")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())

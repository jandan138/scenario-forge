"""Build M2 OpenUSD True-Dynamic 4-Taper-Joint & Keck Clip scene package for distillation_v08."""

from __future__ import annotations

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scenario_forge.adapters.distillation_v08.package_builder_v08 import build_distillation_v08_package  # noqa: E402


def main() -> int:
    info = build_distillation_v08_package()
    print(json.dumps(info, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


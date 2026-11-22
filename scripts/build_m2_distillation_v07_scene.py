"""Build M2 distillation_v07 True-Dynamic OpenUSD scene package."""

from __future__ import annotations

import json
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from scenario_forge.adapters.distillation_v07.package_builder_v07 import build_distillation_v07_package  # noqa: E402


def main() -> int:
    res = build_distillation_v07_package()
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


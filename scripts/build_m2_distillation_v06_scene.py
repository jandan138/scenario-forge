"""Build M2 distillation_v06 Bilibili-aligned OpenUSD scene package."""

from __future__ import annotations

import json
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from scenario_forge.adapters.distillation_v06.package_builder_v06 import build_distillation_v06_package  # noqa: E402


def main() -> int:
    res = build_distillation_v06_package()
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


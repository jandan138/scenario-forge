"""Build M2 OpenUSD scene package for distillation_v09 (Full S01-S12 One-Shot Method B)."""

from __future__ import annotations

import json
from pathlib import Path
import sys

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from scenario_forge.adapters.distillation_v09.package_builder_v09 import build_distillation_v09_package  # noqa: E402


if __name__ == "__main__":
    print(json.dumps(build_distillation_v09_package(), indent=2))


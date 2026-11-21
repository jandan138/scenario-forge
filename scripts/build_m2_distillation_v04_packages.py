"""Build all 7 M2 v0.4 dual-arm distillation packages and defective v0 packages."""

from __future__ import annotations

import json
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
for _p in (str(_SRC_ROOT), str(_REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, str(_p))

from scenario_forge.adapters.distillation_v04 import (  # noqa: E402
    build_distillation_v04_defective_packages,
    build_distillation_v04_packages,
)


def main() -> int:
    print("Building 7 nominal distillation_v04 dual-arm OpenUSD scenario packages...")
    nom = build_distillation_v04_packages()
    for tid, res in nom.items():
        print(
            tid,
            json.dumps(
                {
                    "assets": res.asset_count,
                    "deformable": res.deformable_asset_id,
                    "scene_usd": str(res.scene_usd),
                }
            ),
        )

    print("Building 2 defective v0 distillation scene packages...")
    def_pkgs = build_distillation_v04_defective_packages()
    for tid, res in def_pkgs.items():
        print(f"defective_v0::{tid}", str(res.scene_usd))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


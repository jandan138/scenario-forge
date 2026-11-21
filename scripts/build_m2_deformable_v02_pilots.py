"""Build and validate M2 v0.2 dual-engine deformable scenario packages."""

from __future__ import annotations

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scenario_forge.adapters.deformable_v02 import build_deformable_v02_pilots  # noqa: E402
from scenario_forge.package import validate_package  # noqa: E402


def main() -> int:
    results = build_deformable_v02_pilots()
    summary: dict[str, dict] = {}
    all_ok = True
    for pkg_id, res in results.items():
        report = validate_package(res.package_root, require_asset_lock=True)
        all_ok = all_ok and report.ok
        summary[pkg_id] = {
            "package_root": str(res.package_root),
            "scene_usd": str(res.scene_usd),
            "asset_count": res.asset_count,
            "deformable_asset_id": res.deformable_asset_id,
            "structural_family": res.structural_family,
            "validate_ok": report.ok,
            "messages": list(report.messages),
        }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())


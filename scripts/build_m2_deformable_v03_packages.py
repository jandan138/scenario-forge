"""Build all 8 nominal v0.3 OpenUSD scenario packages plus 2 defective v0 packages for EOS self-healing."""

from __future__ import annotations

import json
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
for _p in (str(_SRC_ROOT), str(_REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scenario_forge.adapters.deformable_v03.package_builder_v03 import (  # noqa: E402
    build_deformable_v03_packages,
    build_v03_task_package,
)


def main() -> int:
    nominal = build_deformable_v03_packages()
    m1_r = _REPO_ROOT.parent / "ConvertAsset" / "external_artifacts" / "deformable_v03_bundles"
    r3_r = _REPO_ROOT / "external_artifacts" / "out_of_domain_factory_r3_20261113" / "packages"
    lab_r = _REPO_ROOT / "external_artifacts" / "build_inputs" / "v1" / "environment-0c45bdf06b0d2b2c" / "source_bundle"
    def_root = _REPO_ROOT / "external_artifacts" / "deformable_v03_defective_v0"

    # Defective v0 Case A: ESDTray placed directly over U-clip target (0.14, 0.04) blocking routing
    v0_smt = build_v03_task_package(
        "smt_ribbon_cable_clip_route",
        def_root / "smt_ribbon_cable_clip_route" / "scenario_package",
        m1_bundles_root=m1_r,
        r3_packages_root=r3_r,
        lab_source_root=lab_r,
        layout_overrides={
            "ESDTray": {"xyz": [0.14, 0.04, 0.757], "wxyz": [1.0, 0.0, 0.0, 0.0]},
            "PCBACarrierBoard": {"xyz": [0.14, 0.04, 0.7635], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        },
    )
    # Defective v0 Case B: manifold_fork_saddle placed outside Franka workspace reachability
    v0_lab = build_v03_task_package(
        "lab_silicone_tube_manifold_insert",
        def_root / "lab_silicone_tube_manifold_insert" / "scenario_package",
        m1_bundles_root=m1_r,
        r3_packages_root=r3_r,
        lab_source_root=lab_r,
        layout_overrides={
            "target_fixture": {"xyz": [0.58, 0.36, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        },
    )

    summary = {
        "nominal": {
            k: {
                "asset_count": v.asset_count,
                "deformable_asset_id": v.deformable_asset_id,
                "structural_family": v.structural_family,
                "package_root": str(v.package_root),
            }
            for k, v in nominal.items()
        },
        "defective_v0": {
            "smt_ribbon_cable_clip_route": str(v0_smt.package_root),
            "lab_silicone_tube_manifold_insert": str(v0_lab.package_root),
        },
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


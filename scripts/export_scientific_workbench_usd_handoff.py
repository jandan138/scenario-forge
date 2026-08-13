#!/usr/bin/env python3
"""Export the reviewed scientific-workbench USD + config handoff archives."""

from __future__ import annotations

import argparse
from pathlib import Path

from scenario_forge.artifacts.usd_handoff import build_usd_handoff_archive, build_usd_handoff_bundle


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "outputs/scientific_workbench_asset_expansion_20260812_r6_full/packages"
TASK_PACKAGES = {
    1: "scientific_workbench_bimanual_pour__background_modern_wet_chemistry",
    2: "scientific_workbench_pour_cylinder_to_beaker__background_modern_wet_chemistry",
    4: "scientific_workbench_insert_stir_bar_and_closure__background_teaching_research",
    5: "scientific_workbench_remove_vessel_closure__background_teaching_research",
    7: "scientific_workbench_glass_rod_stir__background_teaching_research",
    8: "scientific_workbench_tighten_centrifuge_tube_cap__background_bioclean",
    13: "scientific_workbench_funnel_pour_cylinder_to_flask__background_modern_wet_chemistry",
    14: "scientific_workbench_funnel_pour_flask_to_centrifuge_tube_prototype__background_bioclean",
    15: "scientific_workbench_solid_sample_weighing_layout_prototype__background_analytical_instrumentation",
    16: "scientific_workbench_two_sample_mix__background_modern_wet_chemistry",
}
R7_SOURCE = REPO_ROOT / "outputs/scientific_workbench_asset_expansion_20260813_r7_full/packages"
R7_PACKAGES = (
    (2, "modern_wet_chemistry", "scientific_workbench_r7_task02_pour_cylinder_to_beaker__background_modern_wet_chemistry"),
    (7, "example4", "scientific_workbench_r7_task07_glass_rod_stir"),
    (7, "teaching_research", "scientific_workbench_r7_task07_glass_rod_stir__background_teaching_research"),
    (7, "modern_wet_chemistry", "scientific_workbench_r7_task07_glass_rod_stir__background_modern_wet_chemistry"),
    (7, "bioclean", "scientific_workbench_r7_task07_glass_rod_stir__background_bioclean"),
    (7, "analytical_instrumentation", "scientific_workbench_r7_task07_glass_rod_stir__background_analytical_instrumentation"),
    (8, "bioclean_15ml_red_cap", "scientific_workbench_r7_task08_tighten_centrifuge_tube_cap__background_bioclean"),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--r7", action="store_true", help="Export the seven-package r7 review bundle")
    args = parser.parse_args()
    if args.r7:
        source = args.source if args.source != DEFAULT_SOURCE else R7_SOURCE
        result = build_usd_handoff_bundle(
            archive_id="scientific_workbench_tasks_02_07_08_r7_20260813",
            packages=[
                (task, label, source / package / "adapters/vr_teleop")
                for task, label, package in R7_PACKAGES
            ],
            output_dir=args.out,
        )
        print(f"R7 handoff: {result.zip_path.resolve()}")
        return 0
    adapters = {
        number: args.source / package / "adapters/vr_teleop"
        for number, package in TASK_PACKAGES.items()
    }
    liquid = build_usd_handoff_archive(
        archive_id="scientific_workbench_task01_bimanual_pour_r6_20260812",
        task_adapters={1: adapters.pop(1)},
        output_dir=args.out,
    )
    regular = build_usd_handoff_archive(
        archive_id="scientific_workbench_regular_tasks_r6_20260812",
        task_adapters=adapters,
        output_dir=args.out,
    )
    print(f"Task 1 handoff: {liquid.zip_path.resolve()}")
    print(f"Regular-task handoff: {regular.zip_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

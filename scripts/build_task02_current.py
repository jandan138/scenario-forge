"""Compile current Task02 fills from locked build inputs, never old output packages."""
from __future__ import annotations

import argparse
from pathlib import Path

from scripts.retained_build_inputs import input_path


def build_variant(fill_id: str, destination: Path, *, target: str = 'colleague',
                  cylinder_visual: Path | None = None, beaker_visual: Path | None = None,
                  fixture_input: Path | None = None) -> Path:
    from scripts import generate_scientific_workbench_task02_r8 as base
    from scripts import generate_scientific_workbench_task02_r10_fill_sweep as fills
    from scripts import generate_scientific_workbench_r10_1 as direct
    from scripts import generate_scientific_workbench_task02_r10_2 as glass
    from scripts import generate_scientific_workbench_task02_r10_3 as fixture
    from scripts import generate_scientific_workbench_task02_r10_3_colleague_collision as collision

    if fill_id not in fills.FILL_LEVEL_IDS:
        raise ValueError(f'unknown fill: {fill_id}')
    if target not in {'r10', 'r10.1', 'r10.2', 'r10.3', 'colleague'}:
        raise ValueError(f'unknown recipe target: {target}')
    if target == 'colleague' and collision._sha(collision.COLLEAGUE_USD) != collision.COLLEAGUE_USD_SHA256:
        raise ValueError('colleague source hash changed')
    if destination.exists():
        raise FileExistsError(destination)
    seed = input_path('task02_base', verify=True)
    rack = fixture_input or input_path('rod_rack', verify=True)
    base.build(r7_package=seed, transfer_package=fills.DEFAULT_TRANSFER_ROOT / fill_id,
               out=destination, scenario_id=fills.r10_scenario_id(fill_id),
               base_scenario_id=fills.R9_SCENARIO_ID, release='r10', supersedes='r8.7')
    if target == 'r10':
        return destination
    direct.upgrade_task02_package(destination, destination)
    if target == 'r10.1':
        return destination
    glass.upgrade_variant(destination, destination,
                          cylinder_visual_package=cylinder_visual or glass.DEFAULT_CYLINDER_VISUAL,
                          beaker_visual_package=beaker_visual or glass.DEFAULT_BEAKER_VISUAL,
                          refresh_preview_request=False)
    if target == 'r10.2':
        return destination
    previous = (fixture.RACK_XYZ, fixture.ROD_XYZ)
    if target == 'colleague':
        fixture.RACK_XYZ, fixture.ROD_XYZ = collision.RACK_XYZ, collision.ROD_XYZ
    try:
        fixture.upgrade_variant(destination, destination, fixture_package=rack,
                                refresh_preview_request=False)
    finally:
        fixture.RACK_XYZ, fixture.ROD_XYZ = previous
    if target == 'colleague':
        collision._apply_profile(destination)
        fixture._materialize_vr_scene(destination)
        collision.finalize_collision_opinions(destination / 'vr/scene.usd')
        collision._mark_unvalidated(destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--fill', choices=['fill20', 'fill40', 'fill60', 'fill80', 'all'], default='all')
    args = parser.parse_args()
    from scripts import generate_scientific_workbench_task02_r10_3_colleague_collision as collision
    ids = collision.FILL_IDS if args.fill == 'all' else (args.fill,)
    packages = {f: build_variant(f, args.out / 'packages' / f) for f in ids}
    if args.fill == 'all':
        print(collision.build_handoff(packages, args.out))
    else:
        print(packages[args.fill])


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Build stir-bar VR r5 with Hydra-compatible shared-material liquid."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from scripts import generate_scientific_workbench_stir_bar_vr_r4 as r4
from scenario_forge.adapters.vr_presentation import (
    STANDARD_WORKBENCH_ASSET_ID,
    apply_standard_workbench_vr_presentation,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "outputs/scientific_workbench_insert_stir_bar_into_beaker_vr_r5_20260825"
DEFAULT_LIQUID = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "scientific_workbench_stir_bar_beaker_dual_liquid_hydra_compat_20260825"
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _apply_vr_presentation(output: Path, scene_names: tuple[str, ...]) -> dict:
    return {
        scene_name: apply_standard_workbench_vr_presentation(
            output / "vr" / scene_name,
            table_asset_id=STANDARD_WORKBENCH_ASSET_ID,
        )
        for scene_name in scene_names
    }


def _assert_hydra_compatible(output: Path) -> None:
    from pxr import Usd, UsdShade

    for scene_name in ("scene.usd", "scene_liquid_edit.usd"):
        stage = Usd.Stage.Open(str(output / "vr" / scene_name), Usd.Stage.LoadAll)
        particles = stage.GetPrimAtPath(
            "/World/fluid_runtime/ParticleSets/beaker_liquid"
        )
        if not particles:
            raise RuntimeError(f"missing beaker liquid in {scene_name}")
        for name in ("primvars:displayColor", "primvars:displayOpacity"):
            if particles.GetAttribute(name).HasAuthoredValueOpinion():
                raise RuntimeError(f"Hydra-incompatible authored {name}: {scene_name}")
        material, _ = UsdShade.MaterialBindingAPI(particles).ComputeBoundMaterial()
        if not material:
            raise RuntimeError(f"particle material binding missing: {scene_name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=r4.DEFAULT_BASE)
    parser.add_argument("--beaker", type=Path, default=r4.DEFAULT_BEAKER)
    parser.add_argument("--liquid", type=Path, default=DEFAULT_LIQUID)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-only", action="store_true")
    args = parser.parse_args()
    output = r4.build_base(
        args.base.resolve(), args.beaker.resolve(), args.out.resolve()
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["package_id"] = "scientific_workbench_insert_stir_bar_into_beaker_vr_r5"
    manifest["status"] = "r5_base_ready_liquid_pending"
    manifest["vr_presentation_policies"] = _apply_vr_presentation(
        output, ("scene.usd",)
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    if args.base_only:
        print(output)
        return 0

    producer = json.loads((args.liquid / "manifest.json").read_text(encoding="utf-8"))
    rendering = producer.get("rendering", {})
    if (
        producer.get("overall_status") != "pass"
        or rendering.get("color_source") != "shared_particle_system_material"
        or rendering.get("particle_display_primvars_authored") is not False
    ):
        raise RuntimeError("Hydra-compatible producer qualification is incomplete")
    r4.add_dual_liquid(output, args.liquid.resolve())
    presentation_policies = _apply_vr_presentation(
        output, ("scene.usd", "scene_liquid_edit.usd")
    )
    _assert_hydra_compatible(output)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["package_id"] = "scientific_workbench_insert_stir_bar_into_beaker_vr_r5"
    manifest["status"] = "hydra_compatible_dual_entry_runtime_pending"
    manifest["assets"]["beaker_liquid"] = "v3_shared_material_no_display_primvars"
    manifest["vr_presentation_policies"] = presentation_policies
    manifest["source_hashes"]["liquid_overlay_hydra_compatible"] = _sha(
        args.liquid / "liquid_overlay.usda"
    )
    manifest["claims"].update(
        {
            "particle_display_primvars_authored": False,
            "shared_particle_system_material": True,
            "isaac45_render_compatibility": False,
            "robot_policy_success": False,
            "benchmark_success": False,
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

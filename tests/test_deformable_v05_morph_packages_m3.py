"""M3 verification tests for scenario-forge v0.5 material-morph & Real2Sim deformable suites."""

from __future__ import annotations

import json
from pathlib import Path

from convert_asset.deformable_parity.contracts import DeformableSourceSpec
from convert_asset.deformable_v05 import (
    MultiEngineDeformableBundleV02,
    compile_deformable_bundle_v02,
)
from convert_asset.video_deformable_intake.synthetic_proxy import (
    run_pilot1_synthetic_intake_to_bundle,
)
from scenario_forge.adapters.deformable_v05 import (
    build_material_morph_suite,
    build_morphed_scenario_package,
)


def test_m3_pilot1_real2sim_video_twin_package_conforms_to_real2sim_schema(tmp_path: Path) -> None:
    p1 = run_pilot1_synthetic_intake_to_bundle(tmp_path / "p1_intake")
    bundle = MultiEngineDeformableBundleV02.from_dict(p1["bundle"])
    res = build_morphed_scenario_package(
        task_id="real2sim_video_sponge_pick_place",
        bundle=bundle,
        bundle_manifest_path=p1["bundle_manifest_path"],
        out_package_dir=tmp_path / "p1_pkg",
    )
    assert res["real2sim_result_path"] is not None
    r2s = json.loads(Path(res["real2sim_result_path"]).read_text(encoding="utf-8"))
    assert r2s["schema_version"] == "real2sim-result/v0.1"
    for req_key in ("result_id", "source", "package", "assets", "instances"):
        assert req_key in r2s
    assert (Path(res["package_dir"]) / "adapters" / "morphtwin_spring_3dgs" / "morphed_carrier.json").exists()


def test_m3_pilot2_material_morph_suite_freezes_geometry_and_transfers_material(tmp_path: Path) -> None:
    croissant = DeformableSourceSpec(
        asset_id="coffee_croissant_v05",
        category="croissant",
        structural_family="soft_solid",
        dimensions_xyz_m=(0.09, 0.055, 0.045),
        mass_kg=0.065,
        density_kg_m3=292.0,
        youngs_modulus_pa=14000.0,
        poissons_ratio=0.28,
        fragility_tier="high",
    )
    silicone_boot = DeformableSourceSpec(
        asset_id="smt_esd_silicone_boot_v05",
        category="silicone_boot",
        structural_family="soft_solid",
        dimensions_xyz_m=(0.05, 0.05, 0.04),
        mass_kg=0.055,
        density_kg_m3=550.0,
        youngs_modulus_pa=42000.0,
        poissons_ratio=0.41,
        fragility_tier="low",
    )
    b_crois, m_crois = compile_deformable_bundle_v02(croissant, tmp_path / "b_crois")
    b_boot, _ = compile_deformable_bundle_v02(silicone_boot, tmp_path / "b_boot")

    suite = build_material_morph_suite(
        task_id="coffee_croissant_tray_to_plate",
        bundle=b_crois,
        bundle_manifest_path=m_crois,
        out_suite_dir=tmp_path / "suite",
        donor_bundle=b_boot,
    )
    assert suite["geometry_and_task_frozen"] is True
    assert "nominal" in suite["variant_ids"]
    assert "soften_2x" in suite["variant_ids"]
    assert "stiffen_2x" in suite["variant_ids"]
    assert "poisson_low" in suite["variant_ids"]
    assert "poisson_high" in suite["variant_ids"]
    assert f"transfer_{silicone_boot.asset_id}" in suite["variant_ids"]

    # Every variant emits matched overlays across all 4 physics engines
    for var_id, entry in suite["variants"].items():
        pkg_dir = Path(entry["package_dir"])
        for rel in (
            "adapters/genesis/genesis_entity_profile.json",
            "adapters/isaac/deformable_v02.usda",
            "adapters/mujoco4/mjc_overlay_v02.usda",
            "adapters/newton18/newton_overlay_v02.usda",
        ):
            assert (pkg_dir / rel).exists(), f"Missing {rel} in variant {var_id}"

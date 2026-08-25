from __future__ import annotations

from pathlib import Path

import pytest

from scenario_forge.generation.funnel_15ml_small_particle import (
    check_funnel_15ml_small_particle_contract,
    load_funnel_15ml_small_particle_contract,
    to_ai3dgen_funnel_config,
)


REPO = Path(__file__).resolve().parents[1]
CONTRACT = REPO / "configs/prototypes/funnel_15ml_small_particle_v1.yaml"


def test_contract_file_exists_and_loads() -> None:
    contract = load_funnel_15ml_small_particle_contract(CONTRACT)
    assert contract["schema_version"] == "scenario_forge.funnel_15ml_small_particle_contract.v1"
    geometry = contract["geometry"]
    assert geometry["top_diameter_mm"] == 76.0
    assert geometry["neck_diameter_mm"] == 10.0
    assert geometry["wall_thickness_mm"] == 1.5


def test_stem_fits_15ml_mouth_after_collision_margin() -> None:
    checked = check_funnel_15ml_small_particle_contract(
        load_funnel_15ml_small_particle_contract(CONTRACT)
    )
    assert checked["throat_inner_diameter_mm"] == pytest.approx(7.0)
    assert checked["radial_insertion_clearance_mm"] == pytest.approx(1.555, abs=0.01)
    assert checked["radial_insertion_clearance_after_collision_mm"] >= 1.0


def test_throat_admits_small_particles_not_task02() -> None:
    checked = check_funnel_15ml_small_particle_contract(
        load_funnel_15ml_small_particle_contract(CONTRACT)
    )
    assert checked["particle_spacing_mm"] == pytest.approx(1.0)
    assert checked["particle_widths_in_throat"] >= 4.0
    assert checked["task02_particle_diameter_mm"] == 18.0
    assert checked["collision_shrunk_throat_mm"] < 18.0
    assert checked["liquid"]["rest_offset_mm"] < checked["liquid"]["particle_contact_offset_mm"]


def test_oversized_stem_is_rejected() -> None:
    contract = load_funnel_15ml_small_particle_contract(CONTRACT)
    contract["geometry"] = dict(contract["geometry"], neck_diameter_mm=26.0)
    with pytest.raises(ValueError, match="15 mL"):
        check_funnel_15ml_small_particle_contract(contract)


def test_ai3dgen_json_uses_generator_field_names() -> None:
    config = to_ai3dgen_funnel_config(load_funnel_15ml_small_particle_contract(CONTRACT))
    geometry = config["geometry"]
    assert geometry["top_diameter_mm"] == 76.0
    assert geometry["neck_diameter_mm"] == 10.0
    assert geometry["frustum_height_mm"] == 60.0
    assert geometry["stem_length_mm"] == 60.0
    assert geometry["wall_thickness_mm"] == 1.5

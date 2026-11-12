"""Independent fluid QA must reject wall leaks and low settled levels."""
import numpy as np
import pytest

from scripts.task10_pbd_geometry import cavity_metrics


ITEM = {
    'cavity_profile_local_m': [[0., 2.], [1., 1.]],
    'lower_flux_boundary_local_z_m': 0.,
    'upper_flux_boundary_local_z_m': 1.,
    'containment_radial_slop_m': .01,
    'containment_z_slop_m': .01,
    'reference_visible_surface_local_z_m': .8,
    'surface_height_tolerance_m': .02,
}


def test_uses_tapered_cavity_instead_of_bounding_box():
    result = cavity_metrics(np.array([[1.8, 0, .8], [0, 0, -.1], [0, 0, .8]]), ITEM)
    assert result['outside_count'] == 2
    assert result['radial_excess_max_m'] == pytest.approx(.6)
    assert not result['contained']


def test_containment_is_not_a_surface_height_pass():
    result = cavity_metrics(np.array([[0, 0, .1], [0, 0, .2]]), ITEM)
    assert result['contained']
    assert not result['surface_height_pass']


def test_surface_reconstruction_radius_is_explicit_and_nonfinite_fails():
    result = cavity_metrics(np.array([[0, 0, .79]]), ITEM, surface_radius_m=.01)
    assert result['surface_height_pass']
    assert result['estimated_surface_local_z_m'] == pytest.approx(.8)
    result = cavity_metrics(np.array([[np.nan, 0, .8]]), ITEM)
    assert not result['contained'] and not result['surface_height_pass']


def test_numerical_flux_cap_is_solid_even_above_the_visual_outlet():
    item = {**ITEM, 'numerical_liquid_floor_local_z_m': .1}
    result = cavity_metrics(np.array([[0, 0, .05]]), item)
    assert not result['contained']
    assert result['below_boundary_count'] == 1
    assert result['below_flux_boundary_count'] == 0

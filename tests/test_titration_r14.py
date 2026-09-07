from scripts.generate_traditional_titration_vr_r14 import stir_bar_dimensions
from scripts.validate_traditional_titration_vr_r1 import evaluate_burette


def test_twenty_mm_includes_capsule_endcaps():
    radius, straight, height = stir_bar_dimensions(0.003684017574414611)
    assert abs(straight+2*radius-0.020) < 1e-10
    assert 2*radius == 0.005
    assert abs(height-radius-0.003684017574414611-0.00015) < 1e-10


def test_missing_lower_charge_fails_runtime_review():
    state = {'remaining_ml': 25, 'surface_z': 0.23, 'column_bottom_z': -0.09,
             'column_visible': True, 'precharge_visible': False}
    assert evaluate_burette({'pre_run': state})['precharge_always_visible'] is False

from scripts.validate_traditional_titration_vr_r1 import evaluate_report


def test_runtime_report_requires_layout_state_and_stability() -> None:
    report = {
        "dof_count": 1,
        "objects": {
            "obj_magnetic_stirrer": {"translation_drift_m": 0.001},
            "obj_receiver_flask": {"translation_drift_m": 0.002},
            "obj_sample_beaker": {"translation_drift_m": 0.001},
            "obj_context_conical_flask": {"translation_drift_m": 0.001},
        },
        "layout": {
            "tip_to_receiver_vertical_clearance_m": 0.013,
            "tip_receiver_xy_error_m": 0.001,
        },
        "state_machine": {
            "success": True,
            "visited": {"open": True, "fine": True, "drip": True},
            "endpoint_dispensed_ml": 15.0,
            "hold_seconds": 3.1,
            "indicator_phase": "endpoint_pale_pink",
            "pale_visual_visible": True,
            "reset_dispensed_ml": 0.0,
        },
    }
    assert evaluate_report(report)["status"] == "pass"
    report["state_machine"]["visited"]["drip"] = False
    assert evaluate_report(report)["status"] == "blocked"

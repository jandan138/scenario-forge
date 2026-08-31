from scripts.validate_scientific_workbench_task09_r13 import evaluate_report


def test_scene_gate_requires_stable_station_and_both_vessels() -> None:
    report = {
        "objects": {
            name: {"translation_drift_m": drift, "final_z_m": z}
            for name, drift, z in (
                ("obj_oven_cart", 0.0, 0.0),
                ("obj_oven", 0.0, 0.755),
                ("obj_sample_beaker", 0.001, 0.755),
                ("obj_context_conical_flask", 0.001, 0.755),
            )
        },
        "control": {
            "mains_power": True,
            "heating_enabled": False,
            "temperature_setpoint_c": 60.0,
        },
    }

    assert evaluate_report(report)["status"] == "pass"
    report["objects"]["obj_sample_beaker"]["final_z_m"] = 0.2
    assert evaluate_report(report)["status"] == "blocked"

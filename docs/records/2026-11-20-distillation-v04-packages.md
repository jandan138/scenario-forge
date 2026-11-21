# Engineering Record — Distillation Apparatus v0.4 Dual-Arm Scenario Packages & Scene Remediation (M2)

- **Date**: 2026-11-20
- **Repository**: `scenario-forge`
- **Scope**: Milestone 2 (`distillation_v04` — 《蒸馏装置的装配与拆除》)

## Summary
Implemented the `scenario_forge.adapters.distillation_v04` package builder and closed-loop scene remediation module without modifying `src/scenario_forge/assets/lock.py` or breaking `v0.2`/`v0.3`:

1. **7 Dual-Arm 18-DOF Scenario Packages (`external_artifacts/distillation_v04_packages/`)**:
   - `distill_01_burner_ring_flask_mount` through `distill_07_full_assembly_disassembly_sop` with dual 9-DOF Franka Panda (`franka_left`, `franka_right`), `main.usda`, `instances.yaml`, `task_spec.json`, and `glassware_cad_specs.json`.
2. **2 Defective `v0` Scene Packages (`external_artifacts/distillation_v04_defective_v0/`)**:
   - `distill_02_head_taper_coaxial_mate` (`+5.8°` tilted retort stand/flask causing `ground_joint_tilt_jam_fracture`).
   - `distill_01_burner_ring_flask_mount` (`+42 mm` miscalibrated iron ring height).
3. **Closed-Loop Scene Remediation (`remediation_v04.py`)**:
   - `apply_scene_remediation_v04(...)` restores coaxial `[1, 0, 0, 0]` fixture orientation and `0.865 m` outer-flame ring calibration on EOS router advisories.

## Verification
- `pytest tests/test_distillation_v04_packages_m2.py -v` -> `2 passed`.


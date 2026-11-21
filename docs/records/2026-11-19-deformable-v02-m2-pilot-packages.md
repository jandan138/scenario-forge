# 2026-11-19 — M2 v0.2 Dual-Engine Deformable Scenario Packages (`scenario-forge`)

- **Date**: 2026-11-19
- **Status**: COMPLETE & VERIFIED
- **Repository**: `I:\cpfs\shared\simulation\zhuzihou\dev\scenario-forge`
- **Builder / Script / Tests**:
  - `src/scenario_forge/adapters/deformable_v02.py`
  - `scripts/build_m2_deformable_v02_pilots.py`
  - `tests/test_deformable_v02_packages_m2.py` (`2 passed in 3.54s` with `tests/test_architecture_boundaries.py`)

---

## 1. Scope & Generated Pilot Packages

Built and validated two portable OpenUSD deformable + articulated scenario packages consuming the M1 four-engine parity bundles (`mujoco4`, `newton18`, `genesis`, `isaac_physx`) alongside the 9-DOF Franka Panda tabletop embodiment (`panda.urdf`, `panda.xml`, no `package://` URIs):

1. `coffee_bar_fragile_pastry_plate` (`external_artifacts/deformable_v02_pilots/coffee_bar_fragile_pastry_plate/scenario_package`)
   - **Deformable asset**: `fragile_pastry` (`pilot_fragile_chocopie_tofu_01`, `structural_family: soft_solid`)
   - **Parameters**: `youngs_modulus_pa = 28000.0`, `poissons_ratio = 0.32`, `mass_kg = 0.13034`, `dimensions_m = (0.07, 0.07, 0.028)`
   - **Integrity contract**: `strain_metric = polar_stretch_frobenius_q95`, `strain_onset_a = 0.15`, `strain_failure_b = 0.45`, `damage_threshold = 0.25`, `max_normal_force_n = 68.1113`
   - **Task props & room**: hinged `pastry_box_hinged` (`/World/pastry_box_hinged/lid_hinge`), `serving_plate`, kitchen/coffee-bar background (`out_of_domain_env_kitchen_coffee_bar_v2`), `franka_panda` on `robot_pedestal`
2. `office_desk_wiping_cloth_clean_and_park` (`external_artifacts/deformable_v02_pilots/office_desk_wiping_cloth_clean_and_park/scenario_package`)
   - **Deformable asset**: `wiping_cloth` (`pilot_flexible_wiping_cloth_01`, `structural_family: cloth_sheet`)
   - **Parameters**: `youngs_modulus_pa = 150000.0`, `poissons_ratio = 0.3`, `mass_kg = 0.045`, `dimensions_m = (0.18, 0.18, 0.004)`
   - **Integrity contract**: `strain_metric = edge_stretch_q95`, `strain_onset_a = 0.20`, `strain_failure_b = 0.48`, `damage_threshold = 0.25`, `max_normal_force_n = 53.2179`
   - **Task props & room**: `wipe_zone_mat`, `cloth_caddy_tray`, office print studio background (`out_of_domain_env_office_print_studio_v2`), `franka_panda` on `robot_pedestal`

---

## 2. Verification & Package Gate Results

- `validate_package(package_root, require_asset_lock=True)` returned `ok=True` on both packages.
- OpenUSD checks verified `/World/table`, `/World/franka_panda`, `/World/robot_pedestal`, `/World/fragile_pastry/CollisionVolume` (`omniphysics:restTetVtxIndices`), `/World/wiping_cloth` (`omniphysics:restTriVtxIndices`), and self-contained four-engine relative config/mesh paths with zero `/cpfs/` or temporary directory leaks.
- Pure-CPU tests (`pytest tests/test_architecture_boundaries.py tests/test_deformable_v02_packages_m2.py -v`): **`2 passed`**.


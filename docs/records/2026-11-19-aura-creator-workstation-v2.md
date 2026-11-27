# AURA creator workstation source assets, 2026-11-19

The workstation, backup drive and wireless mouse are three independently referenceable metre-scale, Z-up components. Each has an `AssetRoot` default prim and a local `textures/` directory. The 580 × 340 mm baseplate carries a 27-inch 16:9 active display. Its bezel overhangs each side of the plate by 12.4 mm. [Source builder](../../external_artifacts/ce_op_home_v2_20261118/builders/build_aura_creator_workstation_v2.py)

| Source | Measured X × Y × Z (mm) | PNGs | SHA-256 of source and textures |
|---|---|---:|---|
| [Workstation](../../external_artifacts/ce_op_home_v2_20261118/hero_workstation/source/aura-creator-workstation-v2/asset.usda) | 604.73 × 340.00 × 440.00 | 18 | `b96d7a0df5e55191498e45e5b20b18f34b0832f64ec7f4d39c63ea49bb14da8b` |
| [Backup drive](../../external_artifacts/ce_op_home_v2_20261118/hero_workstation/source/aluminum_backup_drive_v2/asset.usda) | 95.00 × 58.17 × 16.00 | 2 | `e13c110d8db53627633f0b4da584c5b702f473bb023c40b39fde07fb3985847d` |
| [Mouse](../../external_artifacts/ce_op_home_v2_20261118/hero_workstation/source/ergonomic_wireless_mouse_v2/asset.usda) | 118.16 × 64.00 × 39.09 | 2 | `925e7d886c770dd415c937afe19242aeaf70a7e1d432c3a08920eca4e875d1ad` |

## Controls and placement

Enter saves the project. Closing the shutter exposes the safe-to-power-off page once the project is saved. Tower PWR then enters standby and monitor PWR puts the display to sleep. Early tower power raises the interlock. Page 5 prompts for shutter closure after saving. Each button must be released before another press registers. The monitor power key travels with the display.

The `ceop:frame:*` relationships on each root resolve to link-local interaction frames. The drive enters the front bay from −Y. Magnetic capture acts on an aligned drive during the last 6 mm of approach. The mouse parks with its longitudinal axis rotated +90° about Z. Both docking frames locate the workpiece support origin.

## Offline verification

Run from the repository root. Add `--verify-only` to audit the existing packages.

```sh
/isaac-sim/python.sh external_artifacts/ce_op_home_v2_20261118/builders/build_aura_creator_workstation_v2.py
```

The build returned exit code 0. OpenUSD 26.05 reopened all three layers and resolved all 22 PNGs from package-relative paths. Each visual and collision envelope starts at zero metres to within 0.001 mm. The fixed-base checker found six rigid links, five movable joints, one world anchor and 96 colliders. Individual prismatic swept volumes cleared adjacent colliders. The display and its attached key cleared them at one-degree intervals from −12° to +15°. The drive also cleared the bay along its insertion path.

The serialized physics-step script received prescribed joint readings on a referenced stage. Checks exercised all six pages, both interlock recovery orders, held-button resets, blank-screen and frozen-LED modes, and identical magnetic force requests across modes. The lowest standard deviation of primary text luminance across the live PNGs was 41.8 on a 0–255 scale at one-third resolution. The blank PNG had uniform luminance. The clean-room scanner returned zero findings.

These are source, geometry and scripted-input checks. Live PhysX travel, magnetic retention force under contact and robot operation remain unmeasured. The 12 acceptance-verifier unit tests passed. Repository-wide `make check` stopped in pytest with 44 failures and 25 errors, including missing historical workbench and robot-bundle fixtures.

The applicable rules at `5bde2b4` are GEN-007/008, ART-005, USD-002, MAT-002/004, STATE-001/003/005 and VAL-001/003. The dimensions, spring values, docking geometry and state sequence are specific to these assets. They require no change to a shared standard or compiler contract.

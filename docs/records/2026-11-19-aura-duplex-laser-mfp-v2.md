# AURA OFFICE M280 printer source assets, 2026-11-19

The M280 source set contains a fixed-base duplex printer and scanner, a rigid optical calibration card and an open-front walnut inbox. All three use metre units, Z up and `AssetRoot` as the default prim. The inspection image shows the authored reset on the left. The right view places the card on the platen with the lid raised 61°, the cassette closed and the output flap extended 48°. [Inspection image](../../external_artifacts/ce_op_home_v2_20261118/hero_printer/inspection.png)

| Source | Closed or resting W × D × H, mm | Local PNGs | SHA-256 of asset.usda |
|---|---:|---:|---|
| [AuraDuplexScanLaserMfpV2](../../external_artifacts/ce_op_home_v2_20261118/hero_printer/source/aura-duplex-laser-mfp-v2/asset.usda) | 390 × 340 × 275.13 | 25 | `0c96c97467b3c08f561b6201bcda77b1fea54639e71e2f09c27a34f36f9593eb` |
| [CalibrationTargetSheetV2](../../external_artifacts/ce_op_home_v2_20261118/hero_printer/source/calibration_target_sheet_v2/asset.usda) | 200 × 250 × 3 | 2 | `b99467067d6b1d28c7ad98b0506ac8335fe662c48c3457e3d9232574c418383e` |
| [WalnutDocumentTrayV2](../../external_artifacts/ce_op_home_v2_20261118/hero_printer/source/walnut_document_tray_v2/asset.usda) | 240 × 290 × 32 | 1 | `b806ea021f22eafd2c134090723c11e074d629d5c3694a1bb8ccb8334ce40bd9` |

## Controls and optical path

At reset the cassette extends 55 mm, the console tilts −22° and the dial selects three copies at 33.75°. The printer is 395 mm deep in this pose. MODE and STANDBY are separate caps on a shared spring-loaded plunger. START has its own spring. The dial has 48 convex contact teeth and an inner cylindrical hub, all bound to the 0.95/0.85 friction material.

START responds to a fresh press with the cassette at or above −5 mm and the lid at or above −0.04 radians in copy mode. A scan takes 1.8 seconds of physics-step time. The completion page stays on for another 0.45 seconds. Opening either interlock interrupts the scan. A clear strip in the lid exposes the moving scan line beside a centred target. The named frames on the root include reset poses and relationships to grasp and press frames on the moving links.

## Reproduction and evidence

Run these commands from the repository root. The first builds and verifies the three packages. The second checks the published sources in a fresh process. [Builder](../../external_artifacts/ce_op_home_v2_20261118/builders/build_aura_duplex_laser_mfp_v2.py)

```sh
/isaac-sim/python.sh external_artifacts/ce_op_home_v2_20261118/builders/build_aura_duplex_laser_mfp_v2.py
/isaac-sim/python.sh external_artifacts/ce_op_home_v2_20261118/builders/build_aura_duplex_laser_mfp_v2.py --verify-only
```

- Standalone OpenUSD 26.05 reopened all three files. Dependency discovery resolved all 28 PNGs inside their own packages. All three visual envelopes and supporting contact shapes reached Z = 0 within 0.001 mm. The source checksum manifest covers the three layers and every PNG. [Source checksums](../../external_artifacts/ce_op_home_v2_20261118/hero_printer/source.sha256)
- The fixed-base checker found one articulation root at `Joints/BaseToWorld`, eight rigid bodies and 97 colliders. The builder checked the seven movable joint frames, axes, limits, resets, drives, inertias and dial contact materials. [Fixed-base report](../../external_artifacts/ce_op_home_v2_20261118/hero_printer/fixed_base_check.json)
- The serialized ScriptNode ran against joint-position inputs on a referenced USD stage. The probe exercised every page, all five copy counts, the scan sweep and both interrupted and rejected starts. Root and parent reset epochs cleared an active job with START held. Each sequence passed in `normal`, `osd_blank` and `led_freeze`.
- At 300 pixels of displayed width, the lowest luminance standard deviation of any main text line was 51.34 on a 0–255 scale. The matte blank had uniform dark pixels. The clean-room audit covered builder and layer text, filenames and PNG legend metadata.

The verification scope is source authoring, standalone behavior and posed appearance. Live force-driven joint travel, settling and robot operation remain unmeasured. The dimensions, interlocks, scan duration and material settings are specific to this device. The existing rules and package contracts require no revision. Standards baseline `5bde2b4`. [GEN-005 and GEN-008](../standards/asset-generation.md#gen-005), [ART-005](../standards/articulation.md#art-005), [USD-002](../standards/usd-layout.md#usd-002), [STATE-003](../standards/task-state.md#state-003), [VAL-003](../standards/validation-and-delivery.md#val-003)

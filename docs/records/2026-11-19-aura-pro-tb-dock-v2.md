# AURA PRO TB-DOCK 12-IN-1, 2026-11-19

The dock, NVMe cartridge and SD media card holder are independently referenceable Z-up components in metres. Their geometry, printed legends, surface grain and screen textures were drawn for this release. The dock has ten rear sockets, a front drive bay and a top card reader. The inspection sheet shows the two faces of the dock, both workpieces at independent scales and the six live OLED textures. [Inspection sheet](../../external_artifacts/ce_op_home_v2_20261118/hero_tb_dock/inspection.png)

| Source | Closed or resting envelope in mm | Mass | Source and texture SHA-256 |
|---|---|---|---|
| [Dock](../../external_artifacts/ce_op_home_v2_20261118/hero_tb_dock/source/aura-thunderbolt-raid-dock-v2/asset.usda) | 224.00 × 114.95 × 57.48 | 0.720 kg base plus six moving links | `d9b5f28935f48ad8b5de4735c70b73dc9f9fefcb9c1e17bb35cbb09147b60cee` |
| [NVMe cartridge](../../external_artifacts/ce_op_home_v2_20261118/hero_tb_dock/source/nvme_ssd_cartridge_v2/asset.usda) | 40.20 × 76.00 × 9.65 | 61 g | `9d9c4d5ecabe6779ebb05d3e4fef291d73ad1d3ef30b2fc6d93f7cf4d78ebb6d` |
| [SD card holder](../../external_artifacts/ce_op_home_v2_20261118/hero_tb_dock/source/sd_media_card_holder_v2/asset.usda) | 30.00 × 32.45 × 4.12 | 4.6 g | `6de5c218f74468b3ba5284e63d01e646d3cc4210852c8f57e24eed94fedc9e41` |

## Operation

Press **HOST** to wake the dock. Insert the drive along +Y and close the front door to display `MOUNTED 40Gbps`. The dial selects `EXTEND 4K60` past 52° and returns to storage below 38°. Open the top gate, turn the card holder −90° around X and insert it contact edge first. With both media seated, **INGEST** completes a 0.75 s transfer in simulation time. Removing either workpiece during transfer clears progress. **EJECT** releases the drive and displays `SAFE TO REMOVE`. A bounded spring torque helps open the door through its first 32°. Both hinges have zero authored drive stiffness throughout.

The root frame dictionaries record resting poses. Each `ceop:frame:*` relationship locates its target on the moving link. The `drive_cartridge_seat` and `sd_card_seat` frames give the poses of the **workpiece roots**. Both workpieces lie flat when opened separately.

## Standalone verification

Run the builder from the repository root. Append `--verify-only` to audit the saved files in a fresh process. [Builder](../../external_artifacts/ce_op_home_v2_20261118/builders/build_aura_thunderbolt_raid_dock_v2.py)

```sh
/isaac-sim/python.sh external_artifacts/ce_op_home_v2_20261118/builders/build_aura_thunderbolt_raid_dock_v2.py
```

- Both commands exited 0 with OpenUSD 26.05 and Pillow 11.2.1. All 20 PNGs resolved within their own asset folders. Visual and contact bounds reached 0.000 mm on all three sources. A second build in a separate directory reproduced all 23 source files byte for byte. The release vocabulary scan found zero matches. [Source checks](../../external_artifacts/ce_op_home_v2_20261118/hero_tb_dock/source_checks.json)
- The fixed-base checker found one world anchor, seven rigid links and 76 colliders. Reopen checks confirmed the six joint limits, reset coordinates, mass properties and drive parameters, including the dial's 0.04 angular damping and 0.95/0.85 grip friction. Geometric checks sampled the three rotary controls at 1° intervals, checked the pressed button positions and swept each workpiece along its straight insertion path. [Fixed-base report](../../external_artifacts/ce_op_home_v2_20261118/hero_tb_dock/fixed_base.json)
- Prescribed joint readings and relative media poses exercised the serialized ScriptNode on a translated and rotated mount. The checks covered all six pages, reversed and absent media, transfer interruption, release-before-repress and resets on the device and its parent. All three ablation modes produced the same door-effort trace. The blank mode showed only the matte blank page. The frozen-light mode held all three emitters at standby tint.
- Pillow measured a minimum primary-title luminance standard deviation of 108.45 on the 0–255 scale at one-quarter texture resolution. The blank had uniform dark luminance. The 12 acceptance-verifier unit tests passed. Repository-wide `make check` stopped in pytest with 1,206 passes, 14 skips, 44 failures and 25 errors. Failures included missing historical workbench and robot-bundle fixtures.

Evidence covers standalone authoring, source reopen, static clearances and controller logic. Live PhysX travel, button rebound under contact and robot handling remain unmeasured. The standards baseline was `5bde2b4`. GEN-005/007/008, ART-005, USD-002/008, MAT-002/004, STATE-002/003/005 and VAL-001/003 apply. The dimensions, drive parameters and telemetry sequence are design choices for this fictional product and require no revision to shared standards or compiler contracts.

## Round 1 visual polish

The STORE plaque moved from a 24 mm to a 28 mm radius. Its closest edge now clears the orange scale by 6.875 mm, up from 2.875 mm. The four chassis corner screws use a darker satin steel with roughness 0.28 and metallic 0.83. With the camera, area light and exposure held fixed, peak luminance on the sampled right-front screw rim fell from 255 to 242 on an 8-bit scale. [Matched close-ups](../../external_artifacts/ce_op_home_v2_20261118/hero_tb_dock/round1_polish.png)

The rebuilt dock passed the standalone rig, media insertion and six-page controller checks. Comparing the saved USD layers identified changes to the plaque translation and four screw material bindings. All 20 textures and both workpiece layers were byte-identical to the Round 1 inputs.

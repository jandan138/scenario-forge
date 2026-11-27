# AURA KITCHEN CS-24 steam oven and baking cocotte, 2026-11-19

The CS-24 and its 0.64 kg glazed ceramic cocotte are independently referenceable metre-scale, Z-up sources. The oven has an open cavity, two resistance elements, a warm cavity lamp, a drop-down glass door and a sliding chrome wire rack. The cocotte has an open bowl, an unglazed foot and two pierced handles. The inspection views show the same workpiece during a steam bake and on the extended rack. [Inspection views](../../external_artifacts/ce_op_home_v2_20261118/hero_steam_oven/inspection.png)

| Source | Rest envelope X × Y × Z (mm) | Local PNGs | SHA-256 of layer and textures |
|---|---|---:|---|
| [AuraConvectionSteamOvenV2](../../external_artifacts/ce_op_home_v2_20261118/hero_steam_oven/source/aura-convection-steam-oven-v2/asset.usda) | 433.70 × 411.00 × 316.93 | 19 | `cd59791339eb08959d863ce74d0e8a1e70662486cc48ee03813f66c7ab282bc0` |
| [CeramicBakingCocotteV2](../../external_artifacts/ce_op_home_v2_20261118/hero_steam_oven/source/ceramic_baking_cocotte_v2/asset.usda) | 228.00 × 127.92 × 65.00 | 3 | `0983fcf3b0a426578fd2e2c9f03ed6c9874db6d25cd24b6849137c2cbc4df6b8` |

## Operation

Wake enables the temperature dial. The dial selects 140°C bake, 180°C steam or 210°C air fry. Start latches the displayed preset and energizes the lamp and both elements when the door and rack are closed. A second Start press stops heating. Opening the door or pulling the rack stops heating and displays the loading page. Closing them returns to preset selection. Sliding the 32 mm top latch uncovers the vent and updates the steam-mode readout.

The OLED has six live pages and a separate matte blank. The status pilot is green for preset selection, cyan for loading and amber while baking. A reset epoch on the device or its mount returns the oven to standby. A held key must be released before it can generate another press. Robot frames follow the moving links, including the door handle, rack pull and cocotte seat. The root frame relationships also identify the oven's rear power inlet and the workpiece handles.

## Round-1 visual revision and rack travel

The pull now has 48 samples around its tube and 36 segments through each quarter bend. The 96-sided brass collars have rounded shoulders. Smooth normals carry the highlight through the bends and around the collars. Five brass graduations span the dial's 120° range. Three long marks align with the preset positions, with a short mark between each pair. [Matched before-and-after crops](../../external_artifacts/ce_op_home_v2_20261118/hero_steam_oven/round1_polish/comparison.png) · [Detail](../../external_artifacts/ce_op_home_v2_20261118/hero_steam_oven/round1_polish/preview_detail.png)

The front-facing plaques carry 8.43 mm WAKE, 8.77 mm START and 8.68 mm STEAM VENT lettering. An arrow and a fine line connect the fixed vent plate to the slider on the roof. An independent reviewer read all three inscriptions in the front, isometric and operator views and distinguished all five dial marks. The elevated view also shows the actuator behind the vent plate. [Front](../../external_artifacts/ce_op_home_v2_20261118/hero_steam_oven/round1_polish/preview_front.png) · [Isometric](../../external_artifacts/ce_op_home_v2_20261118/hero_steam_oven/round1_polish/preview_iso.png) · [Operator controls](../../external_artifacts/ce_op_home_v2_20261118/hero_steam_oven/round1_polish/preview_controls.png) · [Blind review and image hashes](../../external_artifacts/ce_op_home_v2_20261118/hero_steam_oven/round1_polish/visual_review.json)

The original rack ended 9.00 mm in front of the liner and extended into the depth occupied by the visual fan guard. The revision removes 27 mm from the rear of the rack, gives the guard a matching collider, and provides a 0.5 mm contact offset on the running surfaces. The front pull, seating frame and joint limits retain their positions. The builder checks the swept box of every rack collider against each fixed collider and the open door over the continuous 120 mm stroke.

| Joint position | Clearance to fan guard | Clearance to rear liner |
|---:|---:|---:|
| −120 mm | 131.05 mm | 156.00 mm |
| −8 mm | 19.05 mm | 44.00 mm |
| 0 mm | 11.05 mm | 36.00 mm |

Standalone CPU PhysX drove the actual USD rack inward, outward and inward at 60 Hz with the door at −1.40 rad. The eight-step endpoint readings were 0.000, −0.120 and 0.000 m. The same test passed with adjacent-link collisions explicitly enabled. An extra fixed obstacle placed for the control run stopped both inward passes at −0.008 m. Round 1's earlier −0.00824 m reading belongs to the separate application-based acceptance run. [Motion results](../../external_artifacts/ce_op_home_v2_20261118/hero_steam_oven/round1_polish/rack_sweep.json) · [Reproducible CPU probe](../../external_artifacts/ce_op_home_v2_20261118/hero_steam_oven/round1_polish/rack_sweep.py)

## Standalone verification

Run the builder from the repository root. Append `--verify-only` to check the published sources in a fresh process. [Builder](../../external_artifacts/ce_op_home_v2_20261118/builders/build_aura_convection_steam_oven_v2.py)

```sh
/isaac-sim/python.sh external_artifacts/ce_op_home_v2_20261118/builders/build_aura_convection_steam_oven_v2.py
```

- The build and independent reopen exited 0 with OpenUSD 26.05. All 22 PNG dependencies resolved within their respective packages. A second build in another directory reproduced all 24 source files byte for byte. The clean-room scan returned zero findings.
- Both visual and collision envelopes started at 0.000000 m. The fixed-base checker found one world anchor, seven rigid links and 66 colliders. The six movable joints have explicit drives, limits and reset states. The dial collider has static/dynamic friction of 0.95/0.85. [Fixed-base report](../../external_artifacts/ce_op_home_v2_20261118/hero_steam_oven/fixed_base.json)
- Geometric checks sampled the door at one-degree intervals down to −85°. The handle clears the ground and the open door clears the rack. The rack travels 120 mm along −Y. The cocotte foot spans seven wire colliders at its seating frame. The hollow dish uses 35 convex or box contacts.
- The embedded controller received prescribed joint readings on a referenced stage. Checks exercised every page, all three baking presets, interruption and restart, held keys, and both reset locations. The two optical ablations preserved logical state and heat output. The `osd_blank` run showed the matte page and suppressed the vent readout. The `led_freeze` run held the pilot at its standby tint.
- At one-quarter texture resolution, the lowest luminance standard deviation in the live title and subtitle crops was 34.5 on a 0–255 scale. The blank page had uniform dark luminance.

The revised rack has standalone CPU evidence for unloaded travel. The 14 acceptance-verifier unit tests passed for this revision. Trajectory Forge passed both `make ci-check` and `make check`. The initial Scenario Forge repository-wide run recorded 1,206 passes, 14 skips, 44 failures and 25 errors, including missing historical workbench and robot-bundle fixtures.

The standards baseline was `5bde2b4`. GEN-005/007/008, ART-005, USD-002/008, MAT-002/003, STATE-003/005 and VAL-001/003 apply to this source-authoring work. The CS-24 dimensions, drive settings and display sequence are product-specific, so the shared standards and compiler contracts require no revision.

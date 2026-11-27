# AURA BOOK · PRO 14 + STAND, 2026-11-19

The laptop ships closed on its riser with the front power switch on. Opening the lid wakes the 14-inch, 16:10 desktop. The left guide accepts the magnetic PD plug. The right accepts the USB-C end of the HDMI adapter. Both connectors are independently referenceable rigid bodies. The Cycles views show the closed stand and the tilted workstation with both connectors seated. [Inspection views](../../external_artifacts/ce_op_home_v2_20261118/hero_laptop_stand/inspection.png)

| Source | Rest envelope in mm | PNGs | SHA-256 of the source layer and textures |
|---|---|---:|---|
| [Laptop and stand](../../external_artifacts/ce_op_home_v2_20261118/hero_laptop_stand/source/aura-creator-laptop-docking-stand-v2/asset.usda) | 380.00 × 228.00 × 137.82 | 17 | `618fb818601503650925e3109bbc9c4ded834eecac18fa7c32ab3441226df276` |
| [Magnetic PD plug](../../external_artifacts/ce_op_home_v2_20261118/hero_laptop_stand/source/magnetic_pd_power_plug_v2/asset.usda) | 68.50 × 17.00 × 12.06 | 2 | `cedb39907f13d305165d73f127e30dae4b95b9541c74d59534314050e1ce5fa5` |
| [HDMI adapter](../../external_artifacts/ce_op_home_v2_20261118/hero_laptop_stand/source/hdmi_adapter_dongle_v2/asset.usda) | 52.12 × 25.00 × 12.06 | 2 | `378fb234446e770bb5e48eaa1e774d77f4be702c56fc33af69a61608965ad3de` |

The dimensions and masses are design values for this fictional product. The overall width includes both connector shelves. The machined lid is 326 mm wide, weighs 0.52 kg and opens to −115°. The riser carries the lid, keyboard, palmrest key and both guide channels. Its knurled latch shares the tilt axis and has overridable detents at 0°, 12° and 24°. The front switch slides 8 mm. The confirm key has 2.8 mm of spring travel and each side guide compresses 2.4 mm.

## Operation

Each root exposes link-local targets through `ceop:frame:*` relationships. Align a connector’s `plug_tip` with `pd_socket` or `hdmi_socket`. The local +X axis of each socket points inward. Short-range magnetic attraction acts on the free connector, and the optical response checks its identity, insertion depth and orientation relative to the moving guide.

With both connectors seated, Page 4 shows **DESKTOP** and prompts for confirmation. On an awake, open laptop, a palmrest keypress latches Page 5, **WORKSTATION CONFIRMED**. The key confirms the operator’s session. The two port sensors and guide lamps continue to report actual seating during tilt or removal. Closing the lid, switching power off, or changing the reset epoch clears the latch. A key held across reset must be released before another press counts. [Desktop and confirmation views](../../external_artifacts/ce_op_home_v2_20261118/hero_laptop_stand/desktop_and_confirmation.png)

## Round 1 visual repair

An import of the original source in Blender 4.4.3 put the first key at 35.1 mm above ground. OpenUSD placed the same key at 129.1 mm. The untyped key and speaker grouping prims broke Blender’s parent chain and lost the riser’s 94 mm offset. The trackpad already inherited the riser height. The corrected asset gives the deck skin, key bed, keycaps, legends, speaker grilles and trackpad a common `Chassis` transform, with explicit key and grille Xforms beneath it. [Matched before and after views](../../external_artifacts/ce_op_home_v2_20261118/hero_laptop_stand/chassis_comparison.jpg)

Each side shelf extends 3 mm into the side wall. The PD shelf projects 26 mm and the wider HDMI shelf projects 30 mm, down from 45 mm per side. Both shortened shelves support the seated workpiece’s center of mass at either guide stop. A blind reviewer identified the detached geometry in the original closed image and passed the corrected closed, open-detail, desktop and confirmed views.

## Verification

Run the following command from the repository root. Add `--verify-only` to inspect the existing sources. The native import check compares the world transforms of all 192 chassis meshes at 0°, 15° and 24°. The largest absolute difference in a matrix component was 7.32 × 10⁻⁸. [Builder](../../external_artifacts/ce_op_home_v2_20261118/builders/build_aura_laptop_docking_stand_v2.py)

```sh
/isaac-sim/python.sh external_artifacts/ce_op_home_v2_20261118/builders/build_aura_laptop_docking_stand_v2.py --verify-blender
```

The build and the fresh-process reopen each returned exit code 0. OpenUSD 26.05 resolved all 21 PNGs from package-relative paths. Visual and collision bounds began at zero metres on all three components. Rebuilding under a different directory reproduced all 24 files byte for byte. The fixed-base checker found one world anchor, seven rigid links, six movable joints and 49 colliders on the hero. [Reopen report](../../external_artifacts/ce_op_home_v2_20261118/hero_laptop_stand/verification.json) · [Fixed-base report](../../external_artifacts/ce_op_home_v2_20261118/hero_laptop_stand/fixed_base_check.json)

The offline clearance check sampled the lid every degree from 0° to −115° against the deck, key and guide boxes. Both plugs cleared their last 30 mm of insertion at 1 mm intervals with the riser at 24° and their guides at either stop. The embedded physics-step script received prescribed joint readings and relative body poses on a relocated stage. It rejected swapped, backward, upside-down, shallow and off-center plugs, exercised all six pages and both reset locations, and produced identical force and torque requests across the three ablation modes.

In the tilt regression, both plugs initially qualified for Page 4. They stayed at their previous world poses while the riser moved to 15°. A 2.2 mm confirm press selected Page 5 with both live port readings false. The page persisted through 32 ticks after key release and through reseating. Normal, blank-screen and frozen-LED modes exercised this sequence. [Controller trace](../../external_artifacts/ce_op_home_v2_20261118/hero_laptop_stand/controller_trace.json)

All six 1920 × 1200 live pages had distinct pixels. At one-third resolution the lowest per-label luminance standard deviation was 44.7 on a 0–255 scale. The blank image was uniform and its matte shader had zero emission. The clean-room scan reported zero findings.

The revised layer has offline and native Cycles evidence. The earlier live reactive strip and qualification report describe the previous layer, whose SHA-256 begins `4eadf9f82089`. Live PhysX travel and connector retention on the revised layer remain unmeasured. The 14 acceptance-verifier unit tests passed.

The portable test run passed 1,186 tests. Repository-wide `make ci-check` stopped at the diff check on an existing trailing blank line in `tests/test_ebench_genmanip_export.py`. The full `make check` run passed 1,208 tests and reported 44 failures and 25 errors, including missing historical workbench and robot-bundle fixtures.

The applicable standards at `5bde2b4` are GEN-005/007/008, ART-005, USD-002, MAT-002/004, STATE-002/003/005 and VAL-001/003. The port geometry, detents and UI behavior are specific to this asset. The existing standards and compiler contracts cover this source delivery without revision.

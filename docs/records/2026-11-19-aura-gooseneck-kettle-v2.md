# AURA BREW · TEMPMASTER 1.0L sources, 2026-11-19

The temperature dock, vessel and removable infuser are independently referenceable metre-scale components with Z up and `AssetRoot` as their default prim. The dock has a satin brushed deck, smoked-glass edge, steel apron and concentric connector. The vessel has an open pouring tip, an insulated loop handle and a recessed heel. The infuser's woven basket enters the vessel until its flange rests on the rim. [Source builder](../../external_artifacts/ce_op_home_v2_20261118/builders/build_aura_gooseneck_kettle_v2.py)

| Source | Resting W × D × H, mm | PNGs | SHA-256 of source and textures |
|---|---:|---:|---|
| [Dock](../../external_artifacts/ce_op_home_v2_20261118/hero_kettle/source/aura-precision-gooseneck-kettle-dock-v2/asset.usda) | 326.00 × 222.00 × 44.60 | 20 | `10fab270906ea4174de31df322da2c3d08f2174bc979c311f289ed7a769af4c0` |
| [Vessel](../../external_artifacts/ce_op_home_v2_20261118/hero_kettle/source/gooseneck_kettle_vessel_v2/asset.usda) | 284.02 × 134.15 × 155.44 | 2 | `cbbef436541ba624690903f04beebd36e6be7344bdd7234bdf6f039a54e89f0f` |
| [Infuser lid](../../external_artifacts/ce_op_home_v2_20261118/hero_kettle/source/infuser_lid_v2/asset.usda) | 99.40 × 99.40 × 47.35 | 2 | `4f29f54c8b1fe4a81786e47c90cff2d2070c4c0c1d9227b7846ff7ec56775c86` |

The bundle digest uses files in sorted relative-path order. For each file it includes the UTF-8 path, a zero byte and the binary SHA-256 of the file contents.

## Round-1 visual corrections

KEEP WARM is printed on the machined front bevel. The nearest point of the slider's swept visual bounds lies 2.25 mm behind the lettering plane. The single-sided lettering therefore stays clear of the knob from every direction that sees the printed face. The tapered brass index sits at 180° on the crown and points along −Y at the zero detent. It aligns with the middle of 11 graduations at 93°C and with the end graduations at 85°C and 100°C.

Each chassis corner has 64 segments per quarter turn. The dock rings use 128 sectors around the circumference and 48 segments across the rounded upper bevels, with interpolated sidewall normals. The exposed deck alloy has roughness 0.38. A 1.7 mm smoked-glass perimeter inlay keeps transmissive geometry clear of the controls. The three deck legends use alpha-masked ink so the actual grain and reflections continue between the letters. An independent image-only review passed the studio overview and both RTX control views. The reviewer identified the center setting as 93°C COFFEE and read the entire KEEP WARM legend at both ends of the stroke. [Control detail](../../external_artifacts/ce_op_home_v2_20261118/hero_kettle/evidence/round1_polish/controls.png), [RTX with the slider engaged](../../external_artifacts/ce_op_home_v2_20261118/hero_kettle/evidence/round1_polish/rtx_slider_on.png)

A render-only RTX viewport captured the original and revised sources at 1280 × 960 with the inspection camera, dome, three sphere lights and exposure held fixed. Across 860 pixels sampled at the same three exposed deck regions, median luma fell from 179.7 to 84.0 on a 0–255 scale. The 95th percentile fell from 184.6 to 114.7. The median varied by less than one level across three successive captures of each source. [Original RTX view](../../external_artifacts/ce_op_home_v2_20261118/hero_kettle/evidence/round1_polish/rtx_before.png), [Revised RTX view](../../external_artifacts/ce_op_home_v2_20261118/hero_kettle/evidence/round1_polish/rtx_after.png)

The pre-polish dock bundle digest was `fbe5b383b3ae17dc07602bc9d46f40813077d655d8606ddf4288e51c280d6f64`. A USD comparison against that source matched every joint, rigid-link property, collision shape, contact material, named frame and the embedded controller. Both workpiece packages matched byte for byte. The revised sources passed the standalone builder, an independent reopen and all 24 fixed-base checks. The three layers resolved all 24 PNG dependencies locally.

## Docking and controls

Align the vessel's `dock_contact` frame with the dock's `dock_socket`. The socket accepts every yaw angle. Its connector has 5.80 mm of vertical clearance inside the heel. Align the lid's `basket_insert` with the vessel's `infuser_lid_seat`. The centred basket has 6.72 mm of radial clearance at the neck. Root relationships named `ceop:frame:*` point to the interaction frames on their rigid bodies.

Seating the vessel changes the display from NO KETTLE to READY at 24°C. The dial selects tea at −60° (85°C), coffee at 0° (93°C) and boil at +60° (100°C). A fresh BOIL press starts heating with the lid seated. Removing the lid interrupts heating. Removing the vessel cancels the cycle. The keep-warm slide holds the selected temperature after the cycle completes. POWER toggles standby. Pressing the independent hinged opener requests one upward impulse on the seated lid.

The two display columns show the estimated water temperature and the selected target. The heating estimate advances at 0.42°C per second of physics time. The controller reads the native step count to avoid advancing twice in one step. The spring buttons and the opener require release before another activation, including after a reset with a control held.

## Initial authoring verification

Both commands returned exit code 0. The second reopened the published assets in a fresh process.

```sh
/isaac-sim/python.sh external_artifacts/ce_op_home_v2_20261118/builders/build_aura_gooseneck_kettle_v2.py
/isaac-sim/python.sh external_artifacts/ce_op_home_v2_20261118/builders/build_aura_gooseneck_kettle_v2.py --verify-only
```

- OpenUSD 26.05 reopened all three layers. All 23 PNG dependencies resolved inside their respective texture directories. Visual and collision geometry reached the ground plane within 0.001 mm on each asset. Rebuilding at a second location produced 26 byte-identical files. The clean-room scan returned zero findings.
- The fixed-base checker passed all 24 checks. It found one world anchor, six rigid links, five movable joints and 65 dock colliders. The dial has 48 convex flute contacts with static/dynamic friction of 0.95/0.85 and angular drive damping of 0.04. The two Z buttons have 2.8 mm of authored travel, stiffness 260.0, damping 5.5 and a 25 N force limit. The passive opener has zero stiffness and disabled gravity. Swept collider bounds cleared the chassis and adjacent controls. [Fixed-base report](../../external_artifacts/ce_op_home_v2_20261118/hero_kettle/evidence/fixed_base.json)
- The serialized ScriptNode received prescribed joint and rigid-pose inputs on a rotated, referenced stage. All 62 observations agreed across normal, blank-screen and frozen-LED runs on control state, readings and lid-release requests. Checks included 24 vessel yaw orientations, rejected seating poses, each target, heating interruption, a repeated physical step and reset epochs on both source and wrapper.
- Pillow measured all ten live page textures after downsampling to one-third size. The minimum luminance standard deviation in the headline and readout regions was 24.5 on a 0–255 scale. The matte blank was uniformly dark. Both numerical overlays disappeared in blank-screen mode.

Live PhysX joint travel, lid motion under the release impulse, settling and robot operation remain unmeasured. The 12 acceptance-verifier unit tests passed. Repository-wide `make check` stopped in pytest with 44 failures and 25 errors, including missing historical workbench and robot-bundle fixtures. A separate repository diff check reported an existing trailing blank line in `tests/test_ebench_genmanip_export.py`.

The existing standards at `5bde2b4` cover this source handoff. The dimensions, detents, seating tolerances and temperature estimate are device-specific and require no shared rule or package contract revision. [GEN-005/007/008](../standards/asset-generation.md#gen-005), [ART-005](../standards/articulation.md#art-005), [USD-002](../standards/usd-layout.md#usd-002), [MAT-002/004](../standards/materials-and-liquids.md#mat-002), [STATE-002/003](../standards/task-state.md#state-002), [VAL-001/003](../standards/validation-and-delivery.md#val-001)

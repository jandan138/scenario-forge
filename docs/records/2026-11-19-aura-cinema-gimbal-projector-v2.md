# AURA VISION · LASER G4, 2026-11-19

`AuraCinemaGimbalProjectorV2` is an original fixed-base projector with a U-arm, a sliding shutter and a rear operator console. The sixth degree of freedom is a yaw bearing beneath the U-arm. The body, optical assembly, artwork and dimensions were authored for this fictional product. The closed envelope is 272.40 × 229.75 × 215.95 mm. [Projector source](../../external_artifacts/ce_op_home_v2_20261118/hero_projector/source/aura-cinema-gimbal-projector-v2/asset.usda)

| Joint | Travel | Interaction |
|---|---|---|
| `GimbalYawJoint` | −40° to +40° | Pan the U-arm using the lower grip. |
| `GimbalPitchJoint` | −5° to +25° | Tilt the head using its top grip. Positive pitch raises the lens. |
| `LensShutterJoint` | 0 to 78 mm | Slide the front grip to the right to uncover the lens. |
| `FocusRingJoint` | −45° to +45° | Turn the hollow fluted ring. Its angular drive damping is 0.04 and its 32 contact pads have 0.95 static and 0.85 dynamic friction. |
| `PowerButtonJoint` | −2.8 to 0 mm | Press the rear power key to toggle power. |
| `KeystoneLockJoint` | −2.8 to 0 mm | Press during projection to capture or release the current pitch for keystone correction. |

Both rear keys use native Z-axis springs with stiffness 260, damping 5.5 and a 25 N force limit. The gimbal is gravity-neutral and moves freely while the digital keystone setting is held. Root `ceop:frame:*` relationships resolve to link-local targets for the support, both gimbal grips, shutter, focus ring, switches, optical axis and HUD.

## Optical behavior

The projector starts in standby with the shutter closed. Opening the shutter to 68 mm wakes it and shows the beam. The beam goes out as travel drops below 64 mm. At that lower threshold the blade still clears the glass by 3.8 mm. This hysteresis prevents flicker while the blade hovers near the opening point. Power can also turn the beam off while the shutter stays open.

The rear HUD shows standby, shutter closed, shutter ajar, projecting, focus trim and keystone locked. The front pilot and rear status bar share amber, cyan and green tints. The matte blank page replaces the HUD in `osd_blank`. The lights hold their idle tint in `led_freeze`. A device or mount epoch change clears power and the stored pitch. A held switch must be released before its next press.

## Round-one visual repairs

The `G4 / OPTICS` plaque sits on a fixed front lip centered beneath the shutter track. Its upper edge clears the lower rail by 3.6 mm. A projection of the guide and shutter geometry onto the printed letters found 19.95% of the ink covered in the original closed detail view. The revised front, isometric and detail cameras each showed zero covered ink at 0, 39 and 78 mm of shutter travel. [Front detail](../../external_artifacts/ce_op_home_v2_20261118/evidence/aura-cinema-gimbal-projector-v2/preview_detail.png)

Each rail is one capped mesh that turns back into the front baffle at both ends. The U-arm is one casting with 48 segments along each lower quarter bend. Its pivot barrels, yaw race and circular lens trim use 128 radial segments and interpolated normals. The casting carries an isotropic satin finish, and the shutter legend uses an antialiased ink mask. The plinth corners and housing bevel shading were also smoothed after visual review. [Isometric view](../../external_artifacts/ce_op_home_v2_20261118/evidence/aura-cinema-gimbal-projector-v2/preview_iso.png)

The builder now measures the visible hardware of each link and combines those ranges in world coordinates. It excludes the optical cone from both the head and whole-projector dimensions. A forced beam-on check produced the same 0.22975 m physical depth as the closed state. The lit visual envelope extends to 0.69620 m. The reference sheet retains the declared dimensions, masses, joints, frames and load-test workpiece. [Reference dimensions](../../external_artifacts/ce_op_home_v2_20261118/evidence/aura-cinema-gimbal-projector-v2/reference_dimensions.json)

## Verification

Run the builder from the repository root. Add `--verify-only` to check the published source in a fresh process. [Builder](../../external_artifacts/ce_op_home_v2_20261118/builders/build_aura_cinema_projector_v2.py)

```sh
/isaac-sim/python.sh external_artifacts/ce_op_home_v2_20261118/builders/build_aura_cinema_projector_v2.py
```

- The build and fresh-process reopen returned exit code 0. OpenUSD 26.05 resolved one source layer and all 18 package-relative PNGs. Rebuilding in another directory reproduced all 19 source files and the dimension sheet byte for byte. The studio staging source matches the authoring source. The clean-room scans covered the builder, USD, filenames and embedded PNG legends.
- The fixed-base checker found one world anchor, seven rigid links and 55 colliders. Both the visual and collision bounds start at 0.000 m. A one-degree geometric sweep of the head and attached control colliders across the specified pitch range gave at least 11.21 mm of clearance above the crossbar. [Fixed-base report](../../external_artifacts/ce_op_home_v2_20261118/hero_projector/fixed_base_check.json)
- The serialized physics-step controller ran on a referenced stage under a translated and rotated mount. Each of three 37-step traces checked page selection, lamp tint, optical clearance transitions, keystone capture, held buttons, epoch changes and sensor recovery. Switching ablation modes while projection was locked preserved the beam and captured pitch. The six live pages had distinct pixels. Across their lettering crops the lowest luminance standard deviation at quarter size was 28.59 on a 0–255 scale. The matte blank had uniform pixels and zero emission. [Standalone verification](../../external_artifacts/ce_op_home_v2_20261118/hero_projector/verification.json)
- An independent image-only review passed the final detail and overall views. The reviewer read both front inscriptions and observed continuous highlights on the guide returns, lower U-arm and circular metal trim. The inspection sheet also shows the open shutter at +12° and the rear controls. A comparison of 97 physics, frame and behavior-graph prims matched the original definitions. The runtime captures and qualification package retain their original source version. [Before and after](../../external_artifacts/ce_op_home_v2_20261118/hero_projector/inspection.png)

For the visual repair, 15 Scenario Forge acceptance-verifier and architecture-boundary tests passed. Trajectory Forge `make ci-check` and `make check` also passed, with 34 and 41 tests respectively. The original Scenario Forge full-suite run stopped in pytest with 44 failures and 25 errors, including missing historical workbench and robot-bundle fixtures.

The applicable standards at `5bde2b4` are GEN-005/007/008, ART-005, USD-002, MAT-002, STATE-002/003/005 and VAL-003. They cover the fixed-base source, relative dependencies, reset behavior and offline evidence. The yaw range and shutter thresholds are design values specific to this projector.

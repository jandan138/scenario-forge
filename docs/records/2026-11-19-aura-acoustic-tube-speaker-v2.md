# AURA SOUND · STUDIO ONE

`AuraAcousticTubeSmartSpeakerV2` is a fixed-base speaker with five independent controls. Its closed envelope measures 146.76 × 155.49 × 194.98 mm. The six rigid links total 1.361 kg. The ground plane meets the isolation foot at Z = 0.000 m. The woven enclosure, alloy crown, control legends and circular display are original procedural geometry and artwork. [Builder](../../external_artifacts/ce_op_home_v2_20261118/builders/build_aura_acoustic_speaker_v2.py) · [USD source](../../external_artifacts/ce_op_home_v2_20261118/hero_speaker/source/aura-acoustic-tube-speaker-v2/asset.usda)

| Control | Authored travel | Visible response |
|---|---|---|
| `VolumeCrownJoint` | −60° to +60° about Z | The OLED shows each integer from VOL 20% to VOL 80%. Centre is 50%. The 72 knurl teeth have angular drive damping 0.04 and static/dynamic contact friction 0.95/0.85. |
| `MicPrivacyJoint` | 24 mm along +X | Sliding the rear cap uncovers fixed crimson enamel. Muting takes priority on the OLED and turns the full halo amber. |
| `AcousticPortJoint` | 0° to 70° about X | The flap lifts away from a recessed duct and the OLED shows BASS / PORT OPEN. Gravity is disabled. Angular stiffness is zero and damping is 0.012. |
| `WakeTouchJoint`, `SourceSelectJoint` | 2.8 mm downward each | Wake toggles standby. Source switches between stream and radio. Each Z spring uses stiffness 260, damping 5.5 and a 25 N force limit. |

The root publishes rest poses in both named-frame dictionaries. The frame relationships resolve to targets on the rigid links, so both crown grasp points, slider, flap lip and keycaps move with their owners. A changed `device:resetEpoch` on the source or its parent clears the electronic state. Held keys require release before the next press. The privacy indication continues to follow the physical slider.

## Round-1 visual polish

The faint outline in the volume gap aligns with the preceding RADIO page in the original strip. The mute gap likewise retains strokes from the preceding BASS page. The old volume tile and mute texture contained only background dots in those gaps. The saved USD placed all seven page meshes at the same depth, with one selected by visibility. The images are consistent with previous-frame carryover. The original runtime capture is preserved with its source-era evidence. [Round-1 strip](../../external_artifacts/ce_op_home_v2_20261118/evidence/aura-acoustic-tube-speaker-v2/reactive_strip.png)

The rebuilt OLED has one opaque circular mesh and one registered UV map. The seven named pages select materials on that mesh. VOL and MIC use separate label and value fields on a shared readout row. A 65-texel-wide strip between the fields stays dark across all six live pages and all 61 volume settings. Each volume cell has 16 texels of dark padding on each edge, and its UV transform samples from the first to the last interior texel centre. The six-panel inspection uses the original strip camera with prescribed joint readings and a second camera for the insets. [Rebuilt display strip](../../external_artifacts/ce_op_home_v2_20261118/hero_speaker/evidence/reactive_strip_offline.png)

The graphite shoulder, halo and crown bearing now use 192 radial segments. Their face-corner normals follow the circumference while preserving each bevel's profile. The comparison uses matched rear cameras, lighting and render settings. [Rear collar comparison](../../external_artifacts/ce_op_home_v2_20261118/hero_speaker/evidence/rear_collar_comparison.png)

## Standalone verification

Both commands exited 0. The second reopened the published source in a fresh process.

```sh
/isaac-sim/python.sh external_artifacts/ce_op_home_v2_20261118/builders/build_aura_acoustic_speaker_v2.py
/isaac-sim/python.sh external_artifacts/ce_op_home_v2_20261118/builders/build_aura_acoustic_speaker_v2.py --verify-only
```

- OpenUSD 26.05 resolved one layer and all 14 PNGs inside the source directory. The clean-room scan returned zero findings. A second build in a different directory produced 15 byte-identical files.
- The fixed-base checker passed all 24 checks. It found one world anchor, six rigid links and 141 colliders. The builder also checked joint settings, mass properties, face winding, UVs, key clearance, both slider endpoints and the open duct sightline. [Fixed-base report](../../external_artifacts/ce_op_home_v2_20261118/hero_speaker/evidence/fixed_base.json)
- The serialized controller received 161 prescribed samples per mode on a rotated reference mount. All three modes produced identical logical state traces. Blank-screen mode selected the dark matte face. Frozen-LED mode held the idle halo tint as the controls and OLED continued to respond. A separate binding check covered all 49 ordered transitions between the six live pages and blank while a second reference stayed in standby.
- Pillow decoded the actual glyphs on all six live pages, including every volume value. At a 96-pixel face diameter the lowest headline luminance standard deviation was 42.2 on the 0–255 scale. The separator also resolved to the unlit background at a 64-pixel face diameter. In the six offline close-ups the central sample measured 44–47 on the 0–255 luminance scale in every state. The original mechanical views show the uncovered mute marker and the open port. [Initial mechanical views](../../external_artifacts/ce_op_home_v2_20261118/hero_speaker/evidence/speaker_inspection.png)

The authored properties of all six rigid bodies, six joints including the world anchor, 141 colliders and the contact material matched the Round-1 source. The new views use standalone Cycles renders of the reopened USD. Live runtime capture and physical travel were outside this polish run. Both Trajectory Forge checks, `make ci-check` and `make check`, exited 0.

At initial authoring, Scenario Forge lint, package smoke, Phase 10.x smoke and all 12 acceptance-verifier unit tests passed. Its repository-wide `make check` stopped in pytest with 44 failures and 25 errors in other suites, including missing historical workbench fixtures. The separate `diff-check` reported an existing trailing blank line in `tests/test_ebench_genmanip_export.py`.

The rebuilt source bundle SHA-256 is `0549a7c462c88598308e2ba2c0181e72bd02093e68b88434d323cebdd3633501`. Both the hero source and the copy in `assets/source` consumed by the strip renderer have this digest. The Round-1 source digest was `87bd5cc6d3cdc23c78c823013877e4e9f4799d3ff704e922f5bc8e788d0b53e7`. Each digest covers relative paths in lexical order, each followed by a zero byte and its binary file digest.

Standards baseline `5bde2b4` applies. These dimensions, controls and optical states are specific to this speaker, so the shared rules and package contracts require no revision. [GEN-005/007/008](../standards/asset-generation.md#gen-005) · [ART-005](../standards/articulation.md#art-005) · [USD-002/008](../standards/usd-layout.md#usd-002) · [MAT-002/004](../standards/materials-and-liquids.md#mat-002) · [STATE-002/003](../standards/task-state.md#state-002) · [VAL-002/003](../standards/validation-and-delivery.md#val-002)

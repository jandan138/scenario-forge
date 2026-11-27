# AURA DESK · PRIVACY RISER HUB

The hub, presenter pen and compact mouse are three independently referenceable, metre-scale sources. Each opens at `/AssetRoot` with Z up. The hero has seven rigid links and six movable joints. The two additional degrees of freedom are the spring-mounted charging pad and the OLED brightness dial. [Builder](../../external_artifacts/ce_op_home_v2_20261118/builders/build_aura_smart_riser_hub_v2.py)

| Source | Resting W × D × H in mm | PNGs | SHA-256 of source and textures |
|---|---:|---:|---|
| [Riser hub](../../external_artifacts/ce_op_home_v2_20261118/hero_riser_hub/source/aura-smart-monitor-riser-hub-v2/asset.usda) | 590.00 × 281.67 × 149.33 | 15 | `6b51e6165c1c542f63c225c177bfcc2d402c686e171cd6b76d34b6bf45829416` |
| [Presenter pen](../../external_artifacts/ce_op_home_v2_20261118/hero_riser_hub/source/wireless_presenter_pen_v2/asset.usda) | 131.22 × 14.80 × 15.95 | 3 | `5180b54c6f1d92fb9e016d9119355bd8de6c64ad1a8a07287eb191e85d485ac3` |
| [Compact mouse](../../external_artifacts/ce_op_home_v2_20261118/hero_riser_hub/source/compact_desk_mouse_v2/asset.usda) | 60.00 × 94.00 × 34.00 | 3 | `5d0b1ae1f7ea6496a6c81c819b4a9164944c7e4fb6d779565e8bf4963defa11b` |

Each digest covers files sorted by relative path. Each entry contributes its UTF-8 path, a zero byte and the binary SHA-256 digest of its contents.

## Operating the hub

| Control | Travel | Effect |
|---|---:|---|
| `DrawerSlideJoint` | 154 mm toward −Y | The walnut drawer presents the divided tray and pen bay. Opening it at least 45 mm selects ORGANIZE DRAWER. A pen seated in its bay selects PEN STOWED. |
| `ChargingPadJoint` | 1.8 mm downward | A correctly seated mouse and at least 0.20 mm of pad compression select MOUSE CHARGING. |
| `CamPrivacySliderJoint` | 50 mm toward +X | The blade emerges from its pocket, covers the lens and exposes the orange-red PRIVACY LOCKED inscription. At 49 mm the OLED selects CAM LOCKED. |
| `SleepButtonJoint`, `WakeButtonJoint` | 2.8 mm downward each | Native Z springs use stiffness 260.0, damping 5.5 and a 25 N force limit. A fresh sleep press selects SLEEP. Wake restores the page for the current mechanical state. |
| `BrightnessDialJoint` | −60° to +60° | The dial adjusts OLED gain from 0.45 to 1.15. Its 36 flutes have contact geometry, static/dynamic friction of 0.95/0.85 and angular drive damping of 0.04 per degree. |

The pen's `pen_stow` frame mates with the drawer's frame of the same name. The mouse's `charge_contact` mates with `mouse_charge_seat` on the moving pad. The root exposes the rest transforms in both frame dictionaries. Its `ceop:frame:*` relationships resolve to frames on the corresponding rigid bodies.

The embedded physics-step controller reads both joint positions and relative workpiece poses. Its six pages also include DESK READY. A changed `device:resetEpoch` on the source or its wrapper clears the control latches and restores the idle optics. Held keys require release before another press. Subsequent steps sample the current physical poses. Blank-screen mode selects the separate dark matte card. Frozen-LED mode holds the idle tint while the OLED and controls continue responding.

## Verification

Both commands completed with exit code 0. The second reopened the final files in a fresh process.

```sh
/isaac-sim/python.sh external_artifacts/ce_op_home_v2_20261118/builders/build_aura_smart_riser_hub_v2.py
/isaac-sim/python.sh external_artifacts/ce_op_home_v2_20261118/builders/build_aura_smart_riser_hub_v2.py --verify-only
```

- OpenUSD 26.05 resolved all 21 PNG dependencies inside their own source folders. All three visual and collision envelopes reached the ground plane within 0.001 m. The builder checked closed-mesh winding, face normals, world-projected surface UVs, print UVs and mass properties. Rebuilding in a different directory produced 24 byte-identical source files. The clean-room scan found zero matches.
- The independent fixed-base checker passed all 25 checks, with one world anchor and 88 hub colliders. Static swept bounds cleared adjacent controls and the chassis. Endpoint projection checks placed the open blade behind its pocket and the closed blade in front of the full lens. The fit checks verified support, drawer clearance and access to the pen at full extension. [Fixed-base report](../../external_artifacts/ce_op_home_v2_20261118/hero_riser_hub/evidence/fixed_base.json)
- The serialized ScriptNode ran on a rotated reference mount with prescribed joint and body-pose samples. Its 34 observations in each of the three ablation modes covered all six pages, both reset locations, held keys, dial limits and rejection of misplaced or tilted workpieces. The sampled control state agreed across all three runs.
- Pillow measured a minimum luminance standard deviation of 57.0 on a 0–255 scale in the six downsampled headline regions. The blank card had uniform, dark pixels and zero emission. The two static inspection images show the closed hub and a prescribed open-drawer, locked-camera pose with both workpieces seated. [Closed view](../../external_artifacts/ce_op_home_v2_20261118/hero_riser_hub/evidence/inspection_closed.png), [open view](../../external_artifacts/ce_op_home_v2_20261118/hero_riser_hub/evidence/inspection_open.png)

Live physics travel, spring return, contact settling and robot operation remain unmeasured. The 12 acceptance-verifier unit tests passed. Repository-wide `make check` stopped in pytest with 44 failures and 25 errors, including missing historical workbench and robot-bundle fixtures.

The scene-authoring standards at `5bde2b4` cover this handoff. The interaction thresholds, geometry and UI are specific to the riser, so the shared standards and package contracts require no revision. [GEN-005/007/008](../standards/asset-generation.md#gen-005), [ART-005](../standards/articulation.md#art-005), [USD-002/008](../standards/usd-layout.md#usd-002), [MAT-002/003/004](../standards/materials-and-liquids.md#mat-002), [STATE-002/003](../standards/task-state.md#state-003), [VAL-001/003](../standards/validation-and-delivery.md#val-001)

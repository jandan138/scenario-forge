# AURA POWER · VOLTGUARD 240W

On 2026-11-19 the Home v2 source collection gained a fixed-base desktop station and an independent 245 g grounded plug. Both are original procedural designs. The station measures 234.4 × 167.8 × 95.2 mm with its cover closed. The landing shelf supports the plug at insertion height. The image shows the loose plug and closed cover on the left, then the seated plug, open cover and combined output on the right. [Static inspection views](../../external_artifacts/ce_op_home_v2_20261118/hero_power_station/inspection.png)

| Source | Rigid bodies | Colliders | PNGs | SHA-256 of source layer and dependencies |
|---|---:|---:|---:|---|
| [AuraGaNDesktopPowerStationV2](../../external_artifacts/ce_op_home_v2_20261118/hero_power_station/source/aura-gan-power-station-v2/asset.usda) | 7 | 34 | 23 | `a2b92d20219245a1de1de460c6e33b9267e3ffc546cdd71845666c017742286c` |
| [Three-pin plug](../../external_artifacts/ce_op_home_v2_20261118/hero_power_station/source/gan_three_pin_plug_v2/asset.usda) | 1 | 11 | 2 | `2955a8e0ce1d1b255a04b8dc96fc9d35d32f6df9d2fa07764a2c9b5a9f821115` |

## Operation

Align the plug's `plug_mate` frame with the receiver's `ac_socket` frame and insert along local +Y. The sixth joint, `AcSocketJoint`, gives the recessed carrier 2 mm of spring travel. Detection requires at least 0.65 mm of compression and alignment of the shoulder and all three pin tips. Each interaction frame belongs to its moving link and resolves from the root through a `ceop:frame:*` relationship.

Seating the plug changes **SAFE OFF** to **PLUG DETECTED**. Lift the transparent guard and tilt the red rocker to reach **SURGE PROTECTED**. The AC and PD keys toggle independently on a press and release. Their fictional loads are 100 W and 40 W. Enabling both shows **AC1+PD 140W OUTPUT**. The dial switches the principal reading between watts and volts. Power-off or removal of the plug clears both output channels.

Changing `device:resetEpoch` on either the station or its mounting prim clears the display and logical latches. A held switch, key or seated plug must be released before it can rearm. In `osd_blank` the matte blank page covers the display. In `led_freeze` the three status lamps keep their idle tints while the meter operates.

## Round 1 visual polish

The gold index has a pointed tip, clocked 180° on the selector crown. At zero it sights the front tick and the W / V legend. Across the full 90° travel its tip aligns with all seven ticks to within 0.001°. The two keycaps and two plug landing rails share a 1024 × 1024 directional slate texture with roughness 0.48. The texture's luminance standard deviation fell from 6.59 to 1.14 on an 8-bit scale. [Selector, keycap and rail comparisons](../../external_artifacts/ce_op_home_v2_20261118/hero_power_station/round1_polish/controls.png)

The glazed panels use a translucent preview surface with opacity 0.10, roughness 0.22, specular color 0.22 and IOR 1.56. A package-relative thin-wall optical shader supplies the RTX reflection and transmission. Only the clear panels suppress opaque shadow casting. In matched close-ups an independent reviewer could read both white markings on the red rocker through the closed lid in Cycles and RTX. The RTX silhouette is subtler. [Closed-cover comparison](../../external_artifacts/ce_op_home_v2_20261118/hero_power_station/round1_polish/breaker.png) · [Visual review](../../external_artifacts/ce_op_home_v2_20261118/hero_power_station/round1_polish/visual_review.json)

The standalone renderer from the Isaac Sim installation captured the RTX images with the physics timeline stopped. A comparison against the Round 1 source found byte-identical plug files and identical authored physics, named frames and controller properties. The studio renderer's `assets/source` copy now matches the revised source bundle. The original qualification reports and reactive strip describe the preceding source.

## Verification

Run from the repository root to regenerate the pair. Add `--verify-only` to reopen the published files. [Builder](../../external_artifacts/ce_op_home_v2_20261118/builders/build_aura_power_station_v2.py)

```sh
/isaac-sim/python.sh external_artifacts/ce_op_home_v2_20261118/builders/build_aura_power_station_v2.py
```

The revised build and a fresh-process reopen returned exit code 0. OpenUSD 26.05 resolved all 25 PNGs and the local polycarbonate material. Visual and collision bounds on each asset start at 0.000 m. Mesh checks covered outward winding, face normals, world-projected surface UVs and registered artwork UVs. A second build in a different directory reproduced all 28 source files byte for byte. The clean-room scanner found zero matches in the builder and sources.

The fixed-base checker found one world anchor and six moving joints. The offline clearance check sampled 95 insertion positions and 106 cover angles against the control envelopes. The embedded graph received 71 prescribed steps per mode on a relocated stage. Checks covered out-of-position plugs, independent button edges, held controls, both reset locations, visible materials and LED tints. Across twelve meter textures the minimum title or main-reading luminance standard deviation was 77.82 on a 0–255 scale at 480 pixels wide. The blank page was uniform and non-emissive. [Reopen report](../../external_artifacts/ce_op_home_v2_20261118/hero_power_station/verification.json) · [Fixed-base report](../../external_artifacts/ce_op_home_v2_20261118/hero_power_station/fixed_base_check.json)

On isolated copies, changing the dial damping to 0.25, replacing a relative texture path with an absolute path, and erasing a raster title each triggered its corresponding verification failure. The evidence covers static USD, a software-rendered inspection and prescribed controller inputs. Live PhysX sweep percentages, spring return under load and robot operation remain unmeasured.

At original source creation, the 12 acceptance-verifier unit tests, lint checks and both Scenario Forge smoke targets passed. Its repository-wide `make check` stopped in pytest with 44 failures and 25 errors in other suites, including missing historical workbench packages. During the visual polish, Trajectory Forge's `make ci-check` and `make check` both passed, including the 41-test run with the mounted packages.

The applicable standards at `5bde2b4` are GEN-005/007/008, ART-005, USD-002/008, MAT-002/004, STATE-002/003/005 and VAL-001/003. The socket stroke, control layout and display logic are specific to this fictional station and use the existing authoring and delivery contracts.

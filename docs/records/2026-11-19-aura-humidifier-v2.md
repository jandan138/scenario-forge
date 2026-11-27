# AURA AIR · HYDROPURE H6 source verification, 2026-11-19

The humidifier, bedside pour carafe and aroma tablet are independent, Z-up, metre-scale components. Each source uses `AssetRoot` as its default prim. The builder generates the geometry and printed artwork procedurally. [Source builder](../../external_artifacts/ce_op_home_v2_20261118/builders/build_aura_humidifier_v2.py)

| Component | Closed or resting W × D × H (mm) | PNGs | SHA-256 of source and textures |
|---|---:|---:|---|
| [Humidifier](../../external_artifacts/ce_op_home_v2_20261118/hero_humidifier/source/aura-ultrasonic-humidifier-v2/asset.usda) | 218.0 × 233.0 × 305.9 | 16 | `81ea7571374c02f3bfcfffa3e3aeccfffadae2f339553afbf7623fabf2d6e1b5` |
| [Carafe](../../external_artifacts/ce_op_home_v2_20261118/hero_humidifier/source/bedside_pour_carafe_v2/asset.usda) | 133.3 × 89.5 × 161.0 | 2 | `826dcb108e04979948e72f443ee8b375e0e5cec919994a1c22b8082024f88e7a` |
| [Tablet](../../external_artifacts/ce_op_home_v2_20261118/hero_humidifier/source/aroma_tablet_puck_v2/asset.usda) | 32.0 × 32.0 × 7.55 | 2 | `831134b72974c3032c41f9f1a6a92efa6595d970cabd30988fc5e2609be83e26` |

Each bundle digest includes the sorted relative path, a zero byte and the binary SHA-256 of the contents for each file.

## Interaction

`TopLidJoint` swings the lid through 108°. The sixth DOF, `LidRemovalJoint`, slides it 218 mm along the hinge pin until the entire cover clears the tank. Both motions are passive and gravity-neutral. The drawer extends 90 mm, bringing its tablet seat in front of the control deck. The dial spans −60° to +60° and selects 45%, 55% or 65% RH. Its 40 flute contacts and central barrel use 0.95 static and 0.85 dynamic friction. The two spring buttons have 2.8 mm of Z travel.

Opening the hinge at least 60° or sliding the lid at least 173 mm exposes the refill port. A carafe tipped toward its lip with the `pour_spout` frame over the port raises the level by one quarter of the gauge per second of physics time. Closing and reseating the lid enables mist at any positive level. Seating the tablet in the drawer and closing it adds the scented mist tint. The night button reduces plume height, and the UV button toggles the treatment display. Opening or unseating the lid interrupts mist and UV. The water, mist and UV are optical states. The task uses the measured relative poses of the two rigid workpieces for its pour and seat decisions. [Refill view](../../external_artifacts/ce_op_home_v2_20261118/hero_humidifier/evidence/refill.png) · [Operating view](../../external_artifacts/ce_op_home_v2_20261118/hero_humidifier/evidence/warm_mist.png)

## Offline evidence

Both commands exited 0 from the repository root.

```sh
/isaac-sim/python.sh external_artifacts/ce_op_home_v2_20261118/builders/build_aura_humidifier_v2.py
/isaac-sim/python.sh external_artifacts/ce_op_home_v2_20261118/builders/build_aura_humidifier_v2.py --verify-only
```

- OpenUSD 26.05 reopened all three published stages. All 20 texture dependencies resolved within their source directories. The visual and collision minima were within 0.001 mm of ground on all three components. The builder checked mesh winding, outward normals, metric UV projections, registered artwork UVs and material bindings. Rebuilding at a second path reproduced all 23 files byte for byte. The clean-room scan reported zero findings.
- The fixed-base checker passed all 25 checks. It found one world anchor, seven rigid links and 76 colliders. Separate reopened-stage checks covered the six movable joints, explicit mass and inertia, the 0.04 angular dial damping, button spring gains and collision material bindings. Geometry checks measured lid clearance, full drawer exposure, button access and gauge depth ordering. [Fixed-base report](../../external_artifacts/ce_op_home_v2_20261118/hero_humidifier/evidence/fixed_base.json)
- The embedded ScriptNode ran through setup, compute and cleanup on a rotated, referenced stage with prescribed physics inputs. The test compared 39 observations in each of `normal`, `osd_blank` and `led_freeze`. It covered rejected pours, gauge height, both lid interlocks, all three targets, tablet placement, button edges, repeated steps and resets on both the source and its wrapper. The six live pages and three RH overlays had a minimum text-region luminance standard deviation of 34.1/255 after threefold downsampling. The blank page was uniformly dark.
- The inspection images show prescribed refill and closed operating poses. Live PhysX joint sweeps, settling and robot operation remain unmeasured. The 12 hero acceptance-verifier unit tests passed. Repository-wide `make check` stopped in pytest with 44 failures and 25 errors in other suites, including missing historical workbench and robot-bundle fixtures.

The existing standards at `5bde2b4` cover this source handoff. The guided lid removal, sensor tolerances and gauge fill rate are specific to this device and require no shared rule or package contract change. [GEN-005/007/008](../standards/asset-generation.md#gen-005) · [ART-001/005](../standards/articulation.md#art-001) · [USD-002/008](../standards/usd-layout.md#usd-002) · [MAT-001–004](../standards/materials-and-liquids.md#mat-001) · [STATE-002/003](../standards/task-state.md#state-002) · [VAL-001–005](../standards/validation-and-delivery.md#val-001)

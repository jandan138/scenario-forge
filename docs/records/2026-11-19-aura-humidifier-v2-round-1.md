# AURA AIR · HYDROPURE H6 Round‑1 repair, 2026-11-19

The repaired humidifier has a closed envelope of 218.0 × 233.0 × 305.9 mm, including invisible geometry. The reservoir rim and the cover underside both measure 268.000 mm above the support plane. The generated hero layer has SHA-256 `bca030db16cfcb206a9e0ffc547c2410ca0ec7f109c93cdcb4c6bceb479821c9`. The carafe and tablet reproduced their previous source and texture bytes. [Builder](../../external_artifacts/ce_op_home_v2_20261118/builders/build_aura_humidifier_v2.py) · [Humidifier source](../../external_artifacts/ce_op_home_v2_20261118/hero_humidifier/source/aura-ultrasonic-humidifier-v2/asset.usda) · [First build](2026-11-19-aura-humidifier-v2.md)

## Rest and travel

On the first source, the three reported collider pairs intersected, the lid sat 1.5 mm above the rim and the hidden plume reached 426.8 mm. The Round‑1 runtime report recorded 0.077857 maximum joint drift over 120 steps and a removal sweep from 3.65 to 188.82 mm. [Original report](../../external_artifacts/ce_op_home_v2_20261118/evidence/aura-ultrasonic-humidifier-v2_ika_acceptance_report.json)

| Repaired collider pair | Rest clearance |
|---|---:|
| Base hinge pedestal and cantilever pin | 2.50 mm |
| Base hinge pedestal and left lid collider | 3.75 mm |
| Base sole and drawer face | 1.50 mm |

The cantilever pin and its bored knuckles sit inside the tank footprint. A fixed strip closes the rear of the tank behind the hinge. The cover stays 0.20 mm inside each sidewall during hinge-only motion. The passive removal slide has linear damping of 6.0 and zero stiffness. The reopened-stage verifier also checks each moving lid collider's swept volume over the continuous 218 mm removal stroke.

Two 60 Hz standalone CPU PhysX fixtures exercised the published layer. One used its authored fixed base. The other mounted the articulation on a wrapper and parked the three workpiece instances after the first step. The drift figures are the largest excursions from the initial measurement across all 120 sampled steps. [Native measurements](../../external_artifacts/ce_op_home_v2_20261118/hero_humidifier/evidence/round1_repair/rig.json) · [Reproduction script](../../external_artifacts/ce_op_home_v2_20261118/hero_humidifier/evidence/round1_repair/check_cpu_rig.py)

| Measurement | Authored root | Wrapper with workpieces |
|---|---:|---:|
| Base translation drift | 0 m | 0 m |
| Maximum joint drift | 0 | 2.36 × 10⁻⁷ |
| Removal stroke under +2 N and −2 N | 0 → 218 → 0 mm | 0 → 218 → 0 mm |
| Hinge stroke under −2 N·m and +2 N·m | 0 → −108 → 0° | 0 → −108 → 0° |
| Maximum link X displacement during hinge motion | 0 m | 0 m |

The fixed-base checker passed all 25 checks and mapped 77 colliders to seven rigid links. All three stages reopened. All 20 PNG dependencies resolved within their respective source directories. The clean-room scan found zero matches. [Fixed-base evidence](../../external_artifacts/ce_op_home_v2_20261118/hero_humidifier/evidence/round1_repair/fixed_base.json)

## Optical and surface changes

The dry column retracts below the sight-glass opening behind a neutral backing. A tilted carafe with its lip over the exposed refill port raises the blue column. During that transfer, a narrow water stream tracks the lip and terminates at the moving reservoir surface. Opening the drawer interrupts mist even with a full tank or the night setting selected. Both wisps collapse inside the hinge sleeve whenever mist is off. At closed rest their highest points are 275.139 mm and 275.111 mm. The source verifier also checks the parked geometry through the full hinge rotation. The operating wisps widen as they rise, with transparent edges and tips.

The tank and cover now have 48 segments per corner quadrant. The handle has 64 circumferential segments and 48 segments per bend. The status and humidity-target surfaces meet edge to edge in a machined display recess. Both share the bezel face plane at Y = −68.5 mm. The UV legend is printed directly on the cap's upper faces.

The first image-only review passed the mechanism and requested a visible transfer stream and a softer plume. After those revisions, a fresh blind reviewer passed both sheets with high confidence. The reviewer identified an empty gauge before the pour, a stream meeting the water surface, a blue level after filling and mist originating at the outlet in the operating state. The rear pin, seated cover, handle feet and controls were legible in the detail views. Both PNGs carry the reviewed USD layer's SHA-256 in their metadata. [Operating states and controls](../../external_artifacts/ce_op_home_v2_20261118/hero_humidifier/evidence/round1_repair/states.png) · [Hinge and closed lid](../../external_artifacts/ce_op_home_v2_20261118/hero_humidifier/evidence/round1_repair/mechanism.png)

The build and fresh `--verify-only` run both used `/isaac-sim/python.sh`. The serialized ScriptNode passed 46 observations per ablation mode on a mounted stage with prescribed inputs. The minimum downsampled text-region luminance standard deviation was 34.1/255. A second build reproduced all 23 source and texture files byte for byte. The native dynamics measurements used `ovphysx 0.4.13` on CPU. The earlier Isaac 4.1 runtime report is bound to the original source hash.

The 14 upstream acceptance-verifier tests and both Trajectory Forge make checks passed. The full Scenario Forge suite stopped in pytest with 44 failures and 25 errors in other suites, including missing historical fixtures. The repair applies existing articulation, material, state and validation rules to this asset and introduces no shared contract change. [ART-005](../standards/articulation.md#art-005) · [MAT-003](../standards/materials-and-liquids.md#mat-003) · [STATE-003](../standards/task-state.md#state-003) · [VAL-003](../standards/validation-and-delivery.md#val-003)

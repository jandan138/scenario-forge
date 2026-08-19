# Task 02 r10.2 four-fill glass upgrade

Date: 2026-08-19

## Outcome

Task 02's `fill20`, `fill40`, `fill60`, and `fill80` dual-consumer packages now
use the formally admitted webpage-standard glass materials. The graduated
cylinder consumes ConvertAsset's `glass_web_standard_v2`; the 325 mL beaker
consumes `glass_web_standard_v1`.

Scenario Forge composes each admitted visual-material layer as a stronger USD
reference over the existing GPU-PBD source/target package. The PBD dependency
trees remain byte-identical. No local collider, mesh conversion, mass, inertia,
particle, liquid, or vessel-geometry change was made.

The final archive is:

`outputs/scientific_workbench_task02_r10_2_fill_sweep_20260819/handoff/task02_r10_2_fill_sweep.zip`

SHA-256:

`6ac826d83b69bb6f57d7873e0e1746debe22f13d07d7cd18d82f96dd41c1a5bd`

## VR contract

All four VR exports have `/World` as their directly opened default prim, no
authored `/World/_scene`, a texture-free white DomeLight, direct `obj_*`
children, an exact `obj_prim_list`, and local XY randomization of +/- 0.01 m.
The loader remains responsible for the runtime `/World/_scene` mount. The
configs omit `set_robot_physics_material`, `set_robot_contact_offset`, and
`set_robot_rest_offset`.

## Runtime and visual evidence

All four variants passed Isaac Sim 4.1 GenManip construction, reset/recovery,
960 zero-action physics steps at 120 Hz, and VR direct-open smoke. Particle
counts remained 290 / 580 / 972 / 1327. All four fixed-camera render gates
passed; the archive includes close-up and room-overview four-panel comparisons.

Local human-style visual review found the cylinder connector no longer cyan,
both task vessels transparent, and all four fill levels distinguishable. The
admitted thick-wall OmniGlass appears darker than the previous material against
the navy worktop; this is a recorded non-blocking reflection/refraction
observation, not an independent blind review or missing-material fallback.

## Claim boundary

The release retains the existing producer claim for GPU-PBD dynamic loaded
start and prescribed-transfer feasibility. It does not add a robot-policy,
teleoperation, active liquid metric, benchmark-success, or real-physics
calibration claim.

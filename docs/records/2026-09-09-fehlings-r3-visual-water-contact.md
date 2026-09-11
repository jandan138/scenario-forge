# Fehling r3: collision-free visual water and sample-region contact

## Change and ownership

r3 derives from the retained r2 package. It removes the scene's PBD system,
particle set and dedicated material, plus the already disabled PBD-only beaker
proxy. Existing active wall/rim/spout colliders and explicit rigid mass/inertia
are retained. The physics audit excludes only those removed PBD helpers.
The standalone rigid-body GPU/SDF configuration remains; absence of scene PBD
components does not mean the entire engine runs without GPU physics support.

`obj_beaker/VisualWater` contains one body mesh, one flat surface and a
UsdPreviewSurface material. No collision, rigid body, mass or particle API is
applied under it. Its color is (.95,.98,1), opacity .12, IOR 1.333, roughness .02,
with zero emission and no shadow casting. The measured source cavity floor,
inner radii and lower rim define 80% usable-height fill, with .1 mm floor/radial
clearance. It is a height fraction, not 80% of a nominal printed capacity.

## Contact and timing

The initial sample-region axial profile is clipped to the original sample top
and represented as capped frusta. It continues to include the later sediment
region. Actual tube and beaker rigid poses place those frusta in beaker-local
coordinates. AABB overlap is only broadphase; GJK support mapping performs the
convex narrowphase against the water profile's frusta. The renderer uses 96-sided
rings for the same circular profile, so minor polygon discretization remains.

Partial, shallow, tilted and off-center lower-region contact accumulates normal
simulation delta time. There is no heating-angle, complete-immersion or mouth-
height requirement. No contact means pause, not reset; touching only upper tube
or the outside glass is not sufficient. Contact fraction does not scale rate.
The r2 30/45/60-second appearance/geometry policy, observation and completion
latch remain unchanged. Observation still requires withdrawal, near-upright
orientation, a 2-cm stability radius and 3 seconds. Thermal lag, residual heat,
spilling and dilution are not modeled.

The beaker owns `water:profile_m`. Relationships `fehlings:bath` and
`fehlings:bathWater` locate the rigid container and water after mounting.
`fehlings:bath_contact` is explicit telemetry; `fehlings:immersed` is its
compatibility alias and no longer means strict full immersion. The legacy world
water-height value is display telemetry, not the source of contact geometry.

The config removes `fluid_runtime` from randomization, PBD contact-budget/particle
count settings and strict immersion-depth hints. Finalization dispatches by
policy version and rejects unknown versions instead of silently restoring r1
or r2 instructions. The package guide documents the changed meaning and paths.

## Validation protocol

Pure tests cover positive/negative contacts and 400 seeded parallel-frustum
cases checked against an independent analytic radial/height criterion. They
also cover time pause/resume and unchanged completion behavior. Package tests
check absent PBD components, no physics APIs on water, retained active colliders,
unchanged beaker mass, measured water height and finalization/config consistency.

Runtime checks include dynamic downward velocity-guided insertion, bottom
support and a lateral wall-contact trial. The tube remains dynamic during these
collision checks. Prescribed kinematic poses subsequently isolate contact-rule
cases and the full reaction path; this is not proof of human/robot grasp success.
The 55-degree contact pose keeps the shaft clear of the rim while only the lower
sample region intersects water, avoiding an intentionally interpenetrating
kinematic fixture.

An initial free-fall diagnostic showed transient penetration followed by recovery
at the retained thin beaker bottom. It is retained outside delivery and does not
qualify unrestricted drop/impact robustness. The accepted insertion test uses a
low commanded descent velocity and checks actual sampled positions. Another
fixture correction uses actual observation telemetry rather than assuming one
World.step call equals one physics callback; the observed clock accumulation does not justify a fixed one-to-one mapping
between World.step calls and the requested nominal subdivision. Snapshot step
indices are fixture counters, not the timing authority.

Three fresh reports must bind to the final scene and distinct process IDs.
Render replay restores actual beaker/tube poses, material parameters and sample/
sediment geometry; it no longer requires particle arrays. No collision events
or physics trigger volumes are used for heating detection.

Output: `outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r3_20260909/`.
The original r2 output and input dependencies remain available. The active scene
has no PBD components; retained unused source/evidence files in dependencies are
not active liquid systems.

## Final result

Three distinct process cold starts pass on scene SHA
`8902bdc2062bc1a9d3d8fcace0ead2c7d86c2c45beae6848e4f702141bfb300b`.
No PBD components remain and the water subtree has no physics APIs. The three
active cup colliders remain. Accepted dynamic insertion samples reach about
2.975 mm above the beaker root while retaining bottom support; the lateral
trial is blocked by the cup wall. Positive/negative contact cases, 55-degree
tilt, moving-bath tracking, timing, observation and reset all pass.

`make check` passes with 956 tests and one skip; all 17 focused Fehling tests
pass. Fourteen state-replay renders show high fill, shallow/tilted contact,
clouding and final sediment. Local visual review accepts the result with the
retained glass-reflection and rigid-follow-liquid limitations; it is not an
independent review or a recording of human/robot operation.

The guide's read example was checked against the actual USD Stage. Closure,
ZIP CRC and SHA pass, and finalized config is rechecked for the r3 contact
policy with no PBD count or strict immersion-depth hint. The Fehling current
head advances to r3; prior task packages remain retained.

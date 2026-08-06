# Experimental PBD beaker pour handoff

Scenario Forge accepted the LabUtopia source-bound interactive scene handoff
`lab001_pbd_beaker_to_beaker_step600_v2` at producer revision
`4b9279d8368385eae0a29b8dbe93048e48af2c4f`. The admitted closure contains the
required hidden-cube collision overlay and three independently qualified
entrypoints. Isaac Sim 4.1 load/reset/step evidence records 3,600 finite PBD
particles for native and GenManip at 600 Hz and VR at 60 Hz. Each endpoint was
stepped eight times and reset back to the authored particle snapshot.

Handoff v0.2 also hash-binds the composed recovery state of both beakers and
the support table. The source table is centered near
`[0.242788, 0, 0] m`, uses the non-unit local scale
`[0.006, 0.005, 0.00400000006]`, and has a qualified world AABB of roughly
`2.345 x 2.645 x 1.172 m`, with tabletop top at `z=0.772761 m`.

The temporary Scenario Forge task is
`experimental_lab001_pbd_beaker_to_beaker_pour`. It registers the producer-owned
table, `beaker2` source and `beaker1` target as embedded scene prims. Scenario
Forge does not re-instance them or author collider, rigid-body, mass, material
or PhysX-warning suppression opinions. Its reset metadata repeats the
producer-declared composed poses and scales so unmodified GenManip recovery is
idempotent. The GenManip facade keeps
the shared `/World/_scene` namespace and the VR facade uses the task-named
namespace.

The static authored snapshot has all 3,600 particle positions inside the visual
AABB of `beaker2` and none inside `beaker1`. This is an initial-layout witness,
not a containment or transfer metric. The source is the known unsuccessful
contact-grasp diagnostic, so the task package deliberately does not claim grasp
stability, release, liquid transfer, policy success or benchmark success.

The earlier Scenario Forge r3 task is superseded. It incorrectly wrote an
identity table pose and scale into GenManip reset metadata; unmodified
`recovery_scene()` therefore enlarged and moved the producer table. Its all-zero
Lift2 state also placed open grippers around the vessels, making the initial
image look like a beaker was already held.

The r4 task records a 16-value Lift2 initial state. CuRobo solved the left tool
to `[0.295, 0.075, 1.02] m` above the filled source and the right tool to
`[0.25, -0.45, 1.00] m` away from both vessels, with both grippers open. This is
an initialization witness only, not a grasp or policy result.

Downstream GenManip visual smoke uses the unmodified GenManip revision. It initializes Lift2 R5a, resets
the producer scene, takes eight zero-action physics steps, then updates cameras
without further physics advancement. Material-log scanning has no blocking
missing-MDL or missing-texture signal. The evidence gate checks scene structure,
hashes and camera composition only; human visual review remains a separate
judgment.

The final Scenario Forge VR wrapper was also opened directly in Isaac Sim 4.1.
Its task config parses, its task-named scene resolves 3,600 particles, and
`/physicsScene` reports 60 steps per second. This is wrapper load evidence only,
not VR controller or operator evidence.

The r4 structural visual gate passes. Its recovered table extent differs from
the producer AABB only at float precision. The empty target is unchanged over
the eight-step warmup. The filled source settles about `7.14 mm` downward onto
the tabletop, with `0.43 deg` root tilt and a final support gap below `0.1 mm`;
both extent and support gates pass.

Local human-style visual QA (not an independent blind review) rates the r4
workspace and object views `PASS` for initial-layout inspection: both transparent
beakers and blue particle fill are visible, neither gripper encloses a vessel,
and there is no visible spill or fallen vessel. The wide overview is useful for
confirming the full source table but is not a room-background presentation view.
These images remain non-policy evidence.

The package is internal and non-redistributable under the recorded
CC-BY-NC-4.0 source boundary.

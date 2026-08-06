# Experimental PBD beaker pour handoff

Scenario Forge accepted the LabUtopia source-bound interactive scene handoff
`lab001_pbd_beaker_to_beaker_step600_v1` at producer revision
`d465d9362f822479ede87700dc0b3493a25a1fd8`. The admitted closure contains the
required hidden-cube collision overlay and three independently qualified
entrypoints. Isaac Sim 4.1 load/reset/step evidence records 3,600 finite PBD
particles for native and GenManip at 600 Hz and VR at 60 Hz. Each endpoint was
stepped eight times and reset back to the authored particle snapshot.

The temporary Scenario Forge task is
`experimental_lab001_pbd_beaker_to_beaker_pour`. It registers the producer-owned
table, `beaker2` source and `beaker1` target as embedded scene prims. Scenario
Forge does not re-instance them or author local pose, collider, rigid-body,
mass, material or PhysX-warning suppression opinions. The GenManip facade keeps
the shared `/World/_scene` namespace and the VR facade uses the task-named
namespace.

The static authored snapshot has all 3,600 particle positions inside the visual
AABB of `beaker2` and none inside `beaker1`. This is an initial-layout witness,
not a containment or transfer metric. The source is the known unsuccessful
contact-grasp diagnostic, so the task package deliberately does not claim grasp
stability, release, liquid transfer, policy success or benchmark success.

Downstream GenManip visual smoke uses the unmodified GenManip revision
`6ff55ed7c7bd441825d56f1016a30e03b524ebea`. It initializes Lift2 R5a, resets
the producer scene, takes eight zero-action physics steps, then updates cameras
without further physics advancement. Material-log scanning has no blocking
missing-MDL or missing-texture signal. The evidence gate checks scene structure,
hashes and camera composition only; human visual review remains a separate
judgment.

The final Scenario Forge VR wrapper was also opened directly in Isaac Sim 4.1.
Its task config parses, its task-named scene resolves 3,600 particles, and
`/physicsScene` reports 60 steps per second. This is wrapper load evidence only,
not VR controller or operator evidence.

Local human-style visual QA (not an independent blind review) rates the final
three-view set `WARN`: both transparent beakers, the blue particle fill and the
Lift2 workcell are identifiable, and no spill or fallen vessel is visible after
the eight-step window. The largely white, sparse diagnostic background and the
known unstable source grasp limit these images to initial-state inspection; they
are not presentation-quality room evidence or manipulation evidence.

The package is internal and non-redistributable under the recorded
CC-BY-NC-4.0 source boundary.

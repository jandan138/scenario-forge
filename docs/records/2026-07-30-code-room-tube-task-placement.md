# 2026-07-30 Code-as-Room tube-task placement

## Outcome: task 7 output rejected

Both task 7 and task 11 ScenarioSpecs now select the admitted
`scientific_environment_code_room_example4_v1` background at the source-bound
`center_open_floor` pose. The complete eBench workcell is centered in the open
floor; no room Zone is deactivated.

The first task 7 candidate was compiled at:

```text
outputs/scientific_workbench_tube_tasks_code_room_center_20260730/
  wetlab_centrifuge_tube_load_start_no_wait/
```

Its portable structure passed `package check --require-asset-lock`, and Isaac Sim
4.1 produced both preview images. Those structural results are superseded by a
geometry and visual rejection: the composed centrifuge is approximately
`2.000 x 1.291 x 1.836 m`, rather than the producer-admitted
`0.321 x 0.350 x 0.226 m`, and is oriented/placed incorrectly. The retained
output is regression evidence only and carries `evidence/rejection.yaml`;
it must not be handed to eBench.

## Root cause

The r7 package entry prim `/World/Centrifuge` has a non-identity composed root
transform: scale `0.175`, a 90-degree axis conversion, and a Z translation. The
GenManip task wrapper correctly owns the task pose on that same prim. USD
composition therefore replaces the source root transform instead of multiplying
it, removing the canonicalization that made the isolated package correctly sized.
This is an input-contract incompatibility, not a large Code-as-Room room and not a
camera-only problem.

Scenario Forge now admits task-interactive `rigid_object` and
`articulated_object` packages only when the producer-recorded entry matrix is
identity within `1e-6`. It also carries the producer scope bound into the
collected package. The initial-scene gate compares the post-warmup runtime extent
to that bound, requires tabletop XY containment, and allows at most 1 cm of
support gap or penetration.

The exact producer return is
[`../operations/scientific-workbench-centrifuge-identity-root-requalification-request.yaml`](../operations/scientific-workbench-centrifuge-identity-root-requalification-request.yaml).
After that r8 delivery is accepted, task 7 will be rebuilt under
`outputs/scientific_workbench_tube_tasks_code_room_center_identity_root_r8_20260730/`.

## Preview compatibility fix

The unmodified GenManip `recovery_scene` treats articulation part IDs absent from
an episode layout as removable ordinary objects. For the centrifuge this
deactivated a moving-part collider and invalidated the PhysX tensor view before
the articulation pose could be restored.

Scenario Forge's evidence-only renderer now adds the already-loaded articulation
part IDs to a copied recovery layout as `articulation_part` preservation entries.
It also resolves camera anchors from `scene.articulation_list` when the
articulation root is intentionally absent from `scene.object_list`. No GenManip
checkout, asset USD, joint, drive, collider, mass, or inertia was modified.

## Remaining task 11 producer gate

The current rack candidate is not task-ready. Its interaction contract blocks
`gripper_collision_gate` and `open_top`, so the rigid-object handoff loader
rejects it as intended. The requested producer return is recorded in
`docs/operations/scientific-workbench-tube-rack-final-qualification-request.yaml`.

The promoted r7 runtime report references
`uniform_scale_k0365/test_tube/package`, while a later human summary says
`k=0.565`. Scenario Forge binds the hash-recorded runtime evidence and does not
invent a local scale correction; ConvertAsset must resolve that naming/value
discrepancy when returning the rack.

## Claim boundary

This record proves why the retained r7-derived task package is invalid and how
future composition is gated. It does not claim that an identity-root r8 package
has been delivered, task 7 is eBench-ready, robot-policy execution succeeds,
task 11 is ready, or physical parameters match the real device.

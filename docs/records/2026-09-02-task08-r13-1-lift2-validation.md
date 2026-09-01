# Task 08 r13.1 Lift2 Validation

## Outcome

Task08 r13.1 adds a GenManip/Lift2 adapter and instance-aware assisted-thread
controller.  The adapter loads under `/World/_scene`, preserves 120 Hz physics,
and does not add robot material/contact preprocessors to the VR config.

Lift2 reachability passed after using a 0.28 m lift-column position for the low
cap pickup and a shared assembly point at `(-0.10, -0.30, 0.84)` m.  Physical
grasp qualification did not pass: cap lift was inconsistent between cold starts
(`+36.46` mm and `-2.52` mm), and the target tube lift was effectively zero.
The three-segment twist and complete episode were therefore not run.

## Asset/controller changes

ConvertAsset r2 supplies a pickup-only cap grasp box and a persistent tube grasp
box.  The cap starts with only the flat box collider enabled; on `capture`, the
USD-contained OmniGraph disables it and enables the smooth shell colliders for
thread assistance.  Scenario Forge owns only the state switch and adapter.

## Claim boundary

The existing r13 non-robot one-turn qualification remains valid.  r13.1 proves
GenManip loading and waypoint reachability only.  Robot grasp, core assisted
twist, full Task08, policy, and benchmark success remain false.

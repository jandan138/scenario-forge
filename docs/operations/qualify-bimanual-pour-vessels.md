# Qualify the Bimanual Pour Vessel Assets

The current LabUtopia flask and graduated-cylinder prims are visually usable but
not task-ready in the GenManip contract. This handoff defines the minimum upstream
work needed before the EOS five-stage oracle can run meaningfully.

## ConvertAsset delivery request

Produce two independent source-bound dynamic packages without modifying the
original LabUtopia USD:

- `/World/conical_bottle03` as the Erlenmeyer-flask package;
- `/World/graduated_cylinder_03` as the graduated-cylinder package.

For each package, the runtime identity prim consumed by GenManip must be the same
prim whose pose is advanced by physics. It must have a valid nonzero mass, inertia,
center of mass, collision representation, and stable support behavior. Avoid a
wrapper tracked by the evaluator while an independently moving child is the actual
rigid body. Preserve render geometry and materials, and declare any provisional
mass or collision approximation in the producer profile.

The delivery manifest must bind the exact LabUtopia source hash, source prim scope,
package closure, physics profile, producer revision, license, and Isaac Sim 4.1
validation evidence. In addition to the normal scoped PhysX-warning gate, report:

- post-warmup stable pose on the task table;
- gripper-appropriate collision around the flask neck and cylinder shaft;
- the selected rigid-root prim and every collider prim;
- root pose delta versus rigid-body pose delta after a physical move of at least
  5 cm, with disagreement below 1 mm and 0.5 degrees.

## GenManip adapter request

Bind each object UID and metric lookup to the qualified rigid-root prim. Add a
frame-aware predicate that reads source and target opening frames and checks:

- opening-center horizontal error below 2 cm;
- source opening 2–5 cm above the target rim before tilt;
- source opening-normal tilt in the declared 40–80 degree interval;
- full source return pose against the post-warmup physical baseline.

The native root-range metric may remain as diagnostic compatibility output, but it
must not be the evidence for opening alignment. The rollout trace must separately
record gripper contact and the target-hold invariant because pose metrics cannot
prove grasping.

GenManip currently removes colliders recursively under the `room` prim. That is a
separate context-policy issue: the retained DryingBox is visible during this task
but cannot be described as collision-active in this adapter until that policy is
changed. It does not block the vessel-only oracle.

## Scenario Forge follow-up

Scenario Forge will consume the two packages and manifests through asset-source
bindings, regenerate the package, verify the rigid-root contract in the exported
scene, and freeze a new complete-tree digest. The EOS/GenManip rollout runner,
trajectory planner, and episode evidence remain downstream; they are not added to
this repository.

# Qualify the Bimanual Pour Vessel Assets

The current LabUtopia flask and graduated-cylinder prims are visually usable but
not task-ready in the GenManip contract. This handoff defines the minimum upstream
work needed before the EOS five-stage oracle can run meaningfully.

## Existing LabUtopia work to reuse

This request is not a request to invent a new consumer pipeline. The retained
GenManip branch `labutopia-aan-consumer` at
`ee0bcfee95860873dd201d5422dc4597220f1c42` already contains AAN intake, mount,
no-local-repair, runtime-wrapper, and smoke patterns for DryingBox, MuffleFurnace,
and Beaker_01. The retained `labutopia-stage5-eval-readback` branch at
`9e940cb35c74781077c84a41b96b659e18aacf98` contains native action-path and
score-capable oracle-runner patterns. Reuse or port the relevant small pieces into
the maintained downstream branch; do not recreate them in Scenario Forge.

LabUtopia also has a closed Isaac Sim 4.1 delivery at
`outputs/usd_asset_packages/lab_001_level1_pour_interndata_liquid_v1_20260714`.
Its initial USD hash is
`ab9f5eb1d3bc387e13ccb23655454d9357833b261f346fd93d974b86e1f83139`.
That package moves the source beaker's RigidBodyAPI to `/World/beaker2`, disables
the nested mesh rigid body, and supplies open inner-wall collision proxies. It is
useful as a topology and collision reference, but it is not a direct solution:
it covers beaker1/beaker2, drives the source kinematically, and contains no
robot-grasp qualification for the selected flask and cylinder.

## ConvertAsset delivery request

Produce two independent source-bound dynamic packages without modifying the
original LabUtopia USD:

- `/World/conical_bottle03` as the Erlenmeyer-flask package;
- `/World/graduated_cylinder_03` as the graduated-cylinder package.

Bind both deliveries to LabUtopia source USD SHA-256
`b3861b5a17945abe401062a04125969c3a63b0f8a0a5ce0026a461dbdfc935f2`.

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

Bind each object UID and metric lookup to the qualified rigid-root prim. Consume
`episode_metadata.task_data.scenario_forge_runtime_contract`, which Scenario Forge
now exports as a normalized, transport-only mapping. The evaluator must explicitly
make that mapping available to the frame-aware runtime metric; current GenManip
only sends `task_data.goal` to its metrics manager. The following values are
proposed acceptance gates and are not yet declared product thresholds:

- opening-center horizontal error below 2 cm;
- source opening 2–5 cm above the target rim before tilt;
- source opening-normal tilt from the declared 40-degree minimum to a proposed
  80-degree maximum;
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

Scenario Forge has completed the named-frame transport: the embedded runtime
contract includes runtime UID/state-prim mappings, named frames, actor bindings,
steps, invariants, and the existing success predicates. It deliberately reports
`frame_aware_metric_active: false` and does not invent the proposed thresholds.

After the two asset packages arrive, Scenario Forge will consume them through
source bindings, regenerate the package, verify the rigid-root contract in the
exported scene, and freeze a new complete-tree digest. If the proposed thresholds
are accepted, they must enter as an explicit ScenarioSpec predicate rather than an
adapter-only reinterpretation. GenManip owns the runtime metric that consumes this
handoff. EOS owns rollout execution and episode evidence. The runner and trajectory
planner are not added to this repository.

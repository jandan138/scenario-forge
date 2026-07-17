# ScenarioSpec and GenManip Export

`ScenarioSpec` is the small authoring contract between a task description and a
portable scenario package. It records asset/prim bindings, object poses, embodiment
actors, ordered task steps, cross-step invariants, and success predicates. It does
not contain a runner, policy, planner, controller, or simulator SDK object.

The dependency direction is intentionally one-way:

```text
ScenarioSpec
  -> portable scenario-package/v0.2
  -> EBench/GenManip collected-package export
```

The portable compiler owns `scenario.yaml`, the layered USD scene, task graph,
invariants, predicates, robot profile reference, asset lock, and provenance. It does
not use GenManip names such as `obj_table` or emit `evaluation_configs`.
The layered scene applies `scene.pose` to the source root, deactivates declared
source prims, resets world-anchored prims, and authors object poses with a reset
transform stack so object world poses do not inherit the room-alignment transform.

The GenManip adapter consumes the compiled package and emits its wire format:

```text
adapters/ebench/genmanip/
  tasks/config.yaml
  tasks/<task_name>/000/episode_metadata.json
    task_data.scenario_forge_runtime_contract
  tasks/<task_name>/000/meta_info.pkl
  cameras/fixed_camera_lift2.yml
  assets/scene_usds/scenario_forge/<scenario_id>/scene.usda
  package_manifest.json
```

The adapter scene has one child below `/World`, immediate `obj_*` wrappers, and an
`obj_table`. The Lift2 robot is injected by GenManip and is not authored into the
environment USD. `episode_metadata.json` is the authoritative episode description;
the pickle is a deterministic compatibility encoding of the same JSON-safe data.
Scenario Forge never loads an external pickle.

The embedded runtime contract is the semantic handoff for downstream code that
needs more than GenManip's native goal projection. The legacy v0.1, exact v0.2,
and target-frame-relative v0.3 forms all carry:

- the real GenManip runtime UID and state prim path for every scenario object,
  including the table's special all-zero layout UID;
- object-local named-frame poses in meters with `wxyz` quaternions, expressed as
  `state_prim_from_named_frame` and never silently normalized;
- the Lift2 actor-to-end-effector mapping;
- the normalized ScenarioSpec steps, invariants, and success contract.

`package_manifest.json.semantic_contract` locates this one authoritative copy by
episode-metadata path and JSON Pointer. There is no duplicate sidecar. In v0.1 the
native `task_data.goal` is the only executable path and no frame-aware metric is
activated. In v0.2 and v0.3, qualified ConvertAsset objects and an exact ordered
three-stage success contract allow the maintained GenManip consumer to register
and activate `manip/default/scenario_forge_runtime_predicate`; the native goal
remains an explicitly labelled diagnostic projection. All versions keep
`process_invariants_evaluated: false`: pose scoring does not prove target hold or
contact. The legacy manifest `success_contract` field is only a validated
projection for old readers, not a second semantic authority.

The room keeps the complete source `/World` reference so backgrounds and the shared
`Looks` scope remain intact. Task objects are referenced into GenManip wrappers and
their declared material bindings are rebound to that shared scope; this avoids the
out-of-scope material targets produced by narrow USD references.

`scene.pose` can align a source environment cluster with the EBench workspace, and
`scene.inactive_prim_paths` can suppress source prims that would duplicate task
objects. `scene.world_anchored_prim_paths` is deliberately narrow: it lets an
existing source light or ground prim whose authored transform uses the standard
`xformOp:translate`, `xformOp:orient`, `xformOp:scale` order keep that local
transform as its world transform while the rest of the environment inherits
`scene.pose`. Other transform stacks are outside this v0.1 contract. This is not a
general scene-editing pipeline.

## Task-ready context curation

The golden bimanual-pour scenario uses `scene.inactive_prim_paths` as a
non-destructive task overlay. It keeps the complete source bundle and source
layout intact, but deactivates whole top-level subtrees for unrelated loose
glassware, platforms, cabinets, and articulated appliances in both the portable
scene and the GenManip room reference. This prevents their descendant joints,
rigid bodies, and colliders from entering the task runtime without teaching the
compiler any LabUtopia-specific prim names.

`DryingBox_03` is intentionally retained as the single visible laboratory-context
device in this scenario. Its portable USD still composes the source-bound
articulation/physics APIs; Scenario Forge does not strip them. Current GenManip
initialization separately removes colliders recursively below the `room` prim, so
the post-initialization adapter runtime cannot claim DB03 is collision-active. A
future task that manipulates an appliance must export it through an interaction
path outside that room policy and qualify the relevant affordances.

## Initial-scene visual evidence

The GenManip export includes an evidence-only render request. The one-shot adapter
runtime performs the normal GenManip scene construction, reset, and recovery, takes
no policy action, then creates temporary QA cameras for:

- `workspace_closeup`: task objects, both Lift2 end effectors, and the work surface;
- `scene_overview`: the whole worktable, Lift2 robot, task objects, and surrounding
  scene context.

The images, runtime manifest, runtime log, and `visual_ready_gate.yaml` live below
`adapters/ebench/genmanip/evidence/initial_scene/`. Input hashes and the render-request
hash bind the evidence to the exported task config, episode metadata, scene USD,
the complete source USD/MDL/texture bundle, package manifest, policy camera config,
and QA camera policy. Validation re-derives those inputs from the current package
instead of trusting paths saved in an old request. The final parent process also
hash-binds the combined runtime log into the render manifest and gate. QA cameras
never enter the policy-observation camera file. Required
runtime IDs mean that their prims are present and active, not that an algorithm has
proved they are visible or unobstructed in the RGB image. The parent process appends
the renderer's stdout and stderr to the runtime log and scans the combined log for a
declared set of known blocking material signals. The gate therefore establishes
only that the expected render artifacts are current and structurally valid; a
clean-room visual review still decides whether composition and asset appearance are
acceptable.

## Pour claim boundary

The first bimanual-pour task is a `kinematic_proxy`. Its authoritative success
contract has three ordered predicates: a position-aligned pre-pour pose, a deeper
pour pose, and return against the post-warmup physical pose. v0.3 uses the same
generic `named_frames_relative_pose_reached` predicate for the first two stages and
binds them by `sequence_index`, so consumers must not collapse predicates by type.

For each relative-pose stage, `target_frame_from_source_frame_nominal_pose` is the
nominal transform `T_target_source`: the source opening frame expressed in the
target opening frame. `source_origin_in_target_frame_range_m` bounds that same
translation direction. The source opening +Z axis is expressed in the target frame
and measured as polar angle from target +Z and azimuth `atan2(n_y, n_x)`.

The current canonical pre-pour envelope is X `[-5, 5]` mm, Y `[15, 20]` mm, Z
`[35, 50]` mm, polar `[55, 60]` degrees, and azimuth `[-95, -85]` degrees. Its
nominal target is `(0, 17.5, 42.5)` mm with polar 58 degrees and azimuth -90
degrees. The pour envelope retains the same opening-position bounds and azimuth,
with polar `[70, 80]` degrees and a nominal 75-degree pose. Both are absolute
target-frame poses; the pour angle is not added on top of the pre-pour angle.

The return tolerance remains 6 cm / 15 degrees. This evaluates a motion contract;
it does not prove particle transfer, transferred volume, absence of spills, or
collision-free execution. A downstream oracle must separately establish that its
held-object representation covers the active source collider, retains the target,
table, environment, and opposite arm as obstacles, and checks the complete path.

Each exact predicate carries an explicit `diagnostic_compatibility_projection` for
the legacy GenManip root-range/axis metrics. The exporter never derives that
approximation implicitly and never labels it exact. The embedded v0.3 runtime
contract remains `transport_only` with `frame_aware_metric_active: false`; the
downstream GenManip environment explicitly accepts and activates it and records
that fact in runtime evidence. Qualified ConvertAsset
objects additionally disable local collider, rigid-body, and mass authoring in the
GenManip handoff so recovery cannot overwrite the producer-owned physics package.
If an enabled collider in that qualified interaction contract reports `sdf` as its
observed approximation, the task config enables GenManip GPU dynamics, as required
by PhysX for rigid SDF actors.

## Progress rubric transport (v0.4)

`scenario-spec/v0.4` carries an optional `success.progress_rubric` next to the
exact predicates; see [Progress Rubric](progress-rubric.md). The runtime contract
becomes `scenario-forge-genmanip-runtime-contract/v0.4` and transports the rubric
inside `success` unchanged. Because the native GenManip goals evaluate only the
diagnostic projections of the exact predicates, every rubric item is declared
under `execution.progress_rubric.unevaluated_metric_ids` with
`scored_here: false`; `contract_status` remains `transport_only`. Capability-gated
items (for example the two inactive liquid-transfer items) are transported with
their `requires` and `active: false` flags so the downstream environment can
feature-gate scoring explicitly rather than silently computing a different
denominator.

## Asset boundary

The compiler accepts an already usable USD bundle and copies it into a fat package.
It does not localize, repair, or convert USD, MDL, meshes, or textures. Those remain
ConvertAsset/upstream asset-preparation responsibilities. Source paths are build
inputs, while committed provenance uses a portable source URI.

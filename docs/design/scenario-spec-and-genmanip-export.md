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

The first bimanual-pour task is a `kinematic_proxy`. Its sequential GenManip metrics
check that the source reaches a relative pour pose and is subsequently returned to
its initial region. This evaluates the motion contract; it does not prove particle
transfer, transferred volume, or absence of spills. A later fluid evaluator can
replace the adapter mapping without changing the task graph or asset bindings.
For the selected conical flask and graduated cylinder, local `y` is the physical
upright axis, so the tilt and return metrics compare `y` rather than assuming `z`.

## Asset boundary

The compiler accepts an already usable USD bundle and copies it into a fat package.
It does not localize, repair, or convert USD, MDL, meshes, or textures. Those remain
ConvertAsset/upstream asset-preparation responsibilities. Source paths are build
inputs, while committed provenance uses a portable source URI.

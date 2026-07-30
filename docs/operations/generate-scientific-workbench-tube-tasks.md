# Generate Scientific Workbench Tube Tasks 7 and 11

This workflow builds two independent packages:

- task 7, `wetlab_centrifuge_tube_load_start_no_wait`;
- task 11, `wetlab_bimanual_hold_rack_insert_tube`.

Both use the admitted Code-as-Room `center_open_floor` background, the eBench
dual-arm robot, and the existing static worktable. The complete fixed workcell is
centered in the room and all four producer Zones remain active. Task 7 uses the
selected HCI centrifuge. Task 11 uses the selected tube rack.

## Current gate

The admitted task inputs are the centrifuge r9 and tube-rack r4 source-bound
packages. The centrifuge has an identity asset-entry prim, six passing
articulation gates including `benchtop_stability`, and a final
`aan.articulated_mounting.v1` declaration. The rack has the four passing
interaction gates plus its hash-bound `tube_insertion` task qualification.

The fixed-base mounting contract is verified across the packaged device
profile, runtime report, and final manifest. It supplies the runtime-root support
offset, support-plane-to-root pose, reset positions, and qualified warmup/final
extents. Details are recorded in
[`../records/2026-07-31-articulated-fixed-base-mounting-consumer.md`](../records/2026-07-31-articulated-fixed-base-mounting-consumer.md).

Scenario Forge must not add centrifuge-, tube-, or rack-specific colliders,
mass, inertia, joint drives, scale fixes, or PhysX-warning suppression.

## Source bindings

Bind centrifuge r9 as `articulated_object`, rack r4 and the test tube as
`rigid_object`, and use their final package manifests. Do not point a task to a
raw USD, an intermediate candidate, or a runtime report in place of the final
package.

The generator reads producer-measured socket, insertion-target, and grasp frames
from the hash-bound contracts. It replaces the human-readable template values
and derives GenManip's world-axis relative ranges using the materialized object
pose. A fixed-base device is mounted flush: the task-authored Z yaw is composed
with the producer mount rotation, while dynamic objects retain the existing
10 mm settle clearance.

## Static Compile After Delivery

Run with the accepted five-asset binding file:

```bash
PYTHONPATH=src python scripts/generate_scientific_workbench_tube_tasks.py \
  --bindings <accepted-five-asset-bindings.yaml> \
  --task all \
  --out <output-root> \
  --static-only
```

The generator creates one portable package and one GenManip collected package
under each selected scenario ID. It uses the documented GenManip checkout's
supported v0.1 transport path for execution while retaining the complete v0.5
contract at `task_data.scenario_forge_runtime_contract_v05`; the collected-package
manifest points to the latter as semantic authority. It does not run an episode
or claim task success. A repository test loads the exact documented GenManip
consumer and checks that both generated tasks parse on its native-goal v0.1 path;
this does not modify that checkout.

## Isaac 4.1 Initial-Scene Previews After Delivery

```bash
PYTHONPATH=src python scripts/generate_scientific_workbench_tube_tasks.py \
  --bindings <accepted-five-asset-bindings.yaml> \
  --task all \
  --out <output-root> \
  --isaac-python /cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-isaacsim41-genmanip-py310/bin/python \
  --genmanip-root /cpfs/user/zhuzihou/dev/worktrees/genmanip-runtime-contract-20260714
```

For each task, review:

```text
<scenario-id>/adapters/ebench/genmanip/evidence/initial_scene/scene_overview.png
```

The render gate checks package/input hashes, runtime prims, tabletop XY
containment, support position, and producer-vs-runtime extent. Fixed-base
articulations use the producer-qualified warmup and final reset extents as two
separate expectations without relaxing the five-percent threshold; dynamic
objects continue to use their admitted package bounds. The gate does not infer
visual quality from pixels. A clean-room visual review must separately pass on
the package-matching renders before an eBench-ready claim.

## Claim boundary

An initial-scene render proves composition and visual placement only. Static
compilation, loader acceptance, and a preview do not prove a robot task succeeds.
The next downstream step is an EOS/GenManip rollout that evaluates insertion, lid
state, button state, and rack displacement. Scenario Forge does not contain that
runner.

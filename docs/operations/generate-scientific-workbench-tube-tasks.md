# Generate Scientific Workbench Tube Tasks 7 and 11

This workflow builds two independent packages:

- task 7, `wetlab_centrifuge_tube_load_start_no_wait`;
- task 11, `wetlab_bimanual_hold_rack_insert_tube`.

Both use the admitted Code-as-Room `center_open_floor` background, the eBench
dual-arm robot, and the existing static worktable. The complete fixed workcell is
centered in the room and all four producer Zones remain active. Task 7 uses the
selected HCI centrifuge. Task 11 uses the selected tube rack.

## Current gate

The centrifuge r7 delivery passed its isolated asset articulation gates: its
parent-local proxy repair, measured profile, passing runtime report, promotion
receipt, and original loader smoke are recorded in
[`../records/2026-07-30-centrifuge-proxy-parent-local-requalification.md`](../records/2026-07-30-centrifuge-proxy-parent-local-requalification.md).
It is nevertheless rejected for task composition because `/World/Centrifuge`
has a non-identity root transform. The task wrapper replaces that transform,
producing a roughly 2 m device with the wrong axes. The retained wrong output is
marked by `evidence/rejection.yaml`; do not deliver it to eBench.

Task 7 is blocked only on the identity-root r8 producer return specified in
[`scientific-workbench-centrifuge-identity-root-requalification-request.yaml`](scientific-workbench-centrifuge-identity-root-requalification-request.yaml).
The current rack candidate for task 11 still blocks gripper-collision and
open-top insertion; its independent return request is
[`scientific-workbench-tube-rack-final-qualification-request.yaml`](scientific-workbench-tube-rack-final-qualification-request.yaml).
Scenario Forge must not add centrifuge-, tube-, or rack-specific colliders, mass,
inertia, joint drives, scale fixes, or PhysX-warning suppression.

## Source bindings

There is no approved task 7 binding while the centrifuge r8 delivery is absent.
After it passes, bind that identity-root package as `articulated_object` and the
already qualified test tube as `rigid_object`. Task 11 remains separate and
must not be generated from the blocked rack candidate. Do not point either task
to a raw USD or a runtime-report input.

The generator reads producer-measured socket, insertion-target, and grasp frames
from the hash-bound contracts. It replaces the human-readable template values
and derives GenManip's world-axis relative ranges using the authored object pose.

## Static Compile After Delivery

Run only after the tube and rack are accepted:

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

The render gate checks package/input hashes, runtime prims, producer-vs-runtime
extent, tabletop XY containment, and a 1 cm support tolerance. It does not infer
visual quality from pixels. A clean-room visual review must separately pass on
the package-matching renders before an eBench-ready claim.

## Claim boundary

An initial-scene render proves composition and visual placement only. Static
compilation, loader acceptance, and a preview do not prove a robot task succeeds.
The next downstream step is an EOS/GenManip rollout that evaluates insertion, lid
state, button state, and rack displacement. Scenario Forge does not contain that
runner.

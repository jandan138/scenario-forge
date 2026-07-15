# 2026-07-13 Task-ready Bimanual Pour Runtime Canary

## Decision

The curated `scientific_workbench_bimanual_pour` package passed a fresh exact-package
GenManip / Isaac Sim Canary driven by the EOS EBench client:

```text
private exact-package copy
  -> GenManip package discovery
  -> Isaac worker and curated scene construction
  -> reset and finite Lift2 observation
  -> one legal arm-hold + near-open-gripper neutral action
  -> one native physics/metric step
  -> finalize, result files, and EOS trace
```

This is the current r5 runtime record. The earlier r4 record remains historical
evidence for the uncurated full-context scene; its package and image hashes must not
be reused for this task-ready package. The compact machine-readable record is
[`runtime_canary.yaml`](https://github.com/jandan138/scenario-forge/blob/main/docs/records/evidence/2026-07-13-scientific-workbench-bimanual-pour-task-ready-canary/runtime_canary.yaml).

## 2026-07-14 runtime clarification

Later inspection of the frozen GenManip revision found that scene initialization
recursively removes colliders below `/World/<uuid>/room`. The statement below that
DB03 physics “remain active” describes the authored/static USD composition, not a
post-initialization collision-active guarantee. This canary proves load/reset and
visual presence; it must not be used as door-contact or appliance-interaction
evidence.

## What changed from the full-context scene

The source `lab_001.usd` and its closed source bundle remain untouched. The scenario
overlay now deactivates 16 unrelated top-level subtrees: loose glassware, target
platforms, the lounge table, cabinets, the muffle furnace, and three of the four
drying boxes. Deactivating the whole subtree also removes its descendant rigid
bodies, colliders, joints, and articulations from this task runtime.

`DryingBox_03` is the sole retained laboratory-context device. Its authored USD
retains the original articulation and physics APIs, which accounts for four known
door/handle negative-mass warnings during scene construction. As clarified above,
GenManip later removes room-subtree colliders, so the runtime claim is visual
context and reset coverage rather than collision-active interaction.

## Frozen package and initial images

The generated package and its private runtime copy matched before and after the
Canary. The collected trees each contain 61 files and 31,273,506 bytes, with this
normalized sorted `sha256sum`-stream digest:

```text
ec09d519cab41970d24bde1d0cd88e57c73698616933aab309f57eab66c1021d
```

The portable package contains 123 files and 61,656,201 bytes, with digest
`e5151c1801266312fd6215fb975f33db00fb24367bdbe657e3f6d02cee7de702`.
Both portable and GenManip USD entry layers opened successfully with `pxr.Usd`.

The final camera policy is `scenario-forge/task-anchor-fit-v4`. The close-up and
overview are post-reset, pre-action evidence only. The request, all current package
inputs, complete source bundle, runtime log, two images, manifest, and gate are
hash-bound. The structural visual-ready gate passed.

An independent image-only reviewer rated the pair **usable with warnings**. Together
the views show the full Lift2 robot, full table, conical flask, cylinder, and exactly
one peripheral drying box, with no extra loose clutter or obvious broken mesh. The
close-up crops the table, while the overview makes the task objects relatively
small; white robot parts and transparent glass also have weak contrast. This is an
honest initial-scene inspection result, not a claim of polished rendering or task
success.

## Exact r5 execution

The accepted run was:

```text
run_id:
  scenario_forge_bimanual_pour_canary_20260713T103405Z_r5

episode_id:
  scientific_workbench_bimanual_pour/
  scenario_forge_bimanual_pour_canary_20260713T103405Z_r5/
  scenario_forge/scientific_workbench_bimanual_pour/000

robot_id:
  manip/lift2/R5a
```

GenManip reset the curated scene in 25.4257 seconds. EOS received the package's
Chinese instruction, 12 joints, four gripper values, a three-value base state, two
end-effector poses, and an overlook-camera frame. All numeric robot state values
were finite.

The wire action contained 16 values plus separate three-value base motion. Each arm
received six zero relative joint deltas, each gripper received two absolute `0.04`
targets, and base motion was `[0, 0, 0]`. GenManip accepted it, executed exactly one
native step, finalized the episode, wrote both result files, and EOS wrote a
two-record trace (reset record plus action record). The result was `score=0.0`,
`sr=0.0`, which is expected for a one-step neutral action.

One earlier preflight run completed the simulator episode but was rejected as final
evidence because the current EOS `TraceStore` did not create nested parent
directories for an episode ID containing slashes. No EOS source was patched. The
accepted run pre-created that output parent, used a fresh run ID, and completed with
client exit code zero. The reset polling timeout was raised in process memory to
600 seconds; source files and Conda environments were not modified.

## Warning reduction and remaining debt

The r4 and r5 runtime used the same frozen GenManip commit and Isaac environment.
This is a directional before/after comparison rather than a controlled benchmark,
because the EOS client revision also changed. EBench was only probed for metadata
and was not the package runtime. The strongest direct signal is that no r5 warning
names any deactivated context prim.

| Isaac worker stdout | Full-context r4 | Task-ready r5 |
| --- | ---: | ---: |
| Warning lines | 113 | 44 |
| Negative mass/inertia | 41 | 7 |
| Unsupported `ScaleOrientation` | 9 | 0 |
| USD Imaging coding warnings | 9 | 0 |
| Duplicate articulation-link warnings | 14 | 0 |
| Warnings naming deactivated context prims | present | 0 |

The seven remaining negative-mass lines are four from `DryingBox_03` and three from
Lift2 dummy-base links. There is no error or traceback line in Isaac stdout. The
worker pool also logged a cold-start memory-snapshot timeout and an unfinished-state
bookkeeping retry; later memory snapshots, finalize, results, and trace all
completed. Four structured worker-log `ERROR` records are tqdm progress bars routed
through stderr, not failed operations.

## Isolation and claim boundary

No Conda environment was created or changed. GenManip commit
`6ff55ed7c7bd441825d56f1016a30e03b524ebea` was exported into
`/tmp/sfgm-final-0713-d`. The collected package was a real private copy. Only the
base asset directories were linked from the shared EBench dataset and used
read-only by this workflow. The server shut down cleanly, port 18090 became
rebindable, and no matching process remained.

This Canary establishes exact-package discovery, curated scene construction, reset,
finite Lift2 state delivery, legal action acceptance, one native step, metric and
finalize execution, result persistence, and EOS trace persistence. It does not
establish grasping, alignment, pouring, return-to-start, fluid transfer,
long-horizon stability, cuRobo planning, model quality, official EBench
reproduction, or leaderboard comparability.

The next meaningful experiment belongs in EOS/GenManip: either accept the retained
drying box's four warnings as context debt or supply an upstream task-ready static
overlay, then implement a scripted/oracle five-stage rollout. Scenario Forge should
remain the compiler and evidence-contract owner, not grow an episode runner.

# 2026-07-13 Scientific Workbench Bimanual Pour Runtime Canary

> Historical full-context r4 record. The current task-ready scene and its new
> exact-package evidence are documented in the
> [r5 runtime Canary](2026-07-13-scientific-workbench-bimanual-pour-task-ready-runtime-canary.md).
> The hashes below remain valid only for the earlier uncurated package.

## Decision

The exact generated `scientific_workbench_bimanual_pour` collected package passed a
real GenManip / Isaac Sim technical Canary driven by an EOS-owned client:

```text
private exact-package copy
  -> GenManip package discovery
  -> Isaac worker and scene construction
  -> reset and finite Lift2 observation
  -> one legal arm-hold + near-open-gripper neutral action
  -> one native physics/metric step
  -> aggregate and episode result files
```

This closes package discovery, reset, action-contract, one-step, and result-path
integration for the frozen package tree. It does not establish that the robot
performed the five-step pour task.

The compact evidence record is
[`runtime_canary.yaml`](https://github.com/jandan138/scenario-forge/blob/main/docs/records/evidence/2026-07-13-scientific-workbench-bimanual-pour-canary/runtime_canary.yaml).

## Frozen package and initial images

The private runtime copy was compared file-by-file with the generated collected
package. Both contain 61 files and 31,444,430 bytes, with the same sorted
`sha256sum`-stream digest after normalizing each entry name to a package-relative
path without a leading `./`:

```text
75cbb02ea80c504b72277466214872c1a29ca2a0174eb854c0d64665264892f0
```

Key frozen inputs are:

| Artifact | SHA256 |
| --- | --- |
| portable `manifest.yaml` | `fe352d908cd0c2d6fb7140df1092bd31209b6d5071439ce55c120bbc545937ee` |
| portable `scene/main.usda` | `aacbde1b0777f1e07e651d7e3c81c5df0439361c931a5cb02101710dac603732` |
| GenManip `package_manifest.json` | `1de01eb240a7842180346a61a0a4a21fc7bb8890c8528f27a35bd35f37d8a0bd` |
| `tasks/config.yaml` | `6d6a75836a49506a38da9435761edba488870b9e38742fcf8dc797dcce1f1e97` |
| episode metadata | `a5788816bee3b0b5cb9fb8abe374c1e7e9a8d10a2a1a63ba26ff314309d5be23` |
| compatibility pickle | `5b0c8248419f0f4f1fccc53abefa40fb488a607dfddfdf0a284f1af0892cf540` |
| GenManip scene USDA | `92eedcc0f1b62ddffb32216cf514343ac95191493e828ed2e66af82a926e0186` |

Both USD entry layers opened successfully with `pxr.Usd.Stage.Open`. The portable
layer also preserved the source world transforms of the declared standard-TRS
light and ground anchors.

The package contains 1280x720 post-reset, pre-action close-up and overview images.
The render request and input digest bind the manifest, current scene inputs,
complete source USD/MDL/texture bundle, and camera policy. The later render manifest
and gate bind both that request's hash and the combined runtime-log hash, so changing
any of those invalidates stale evidence. The structural gate and the declared known
material signal scan passed. A separate image-only visual review rated the images
**usable with warnings**, not a visual-quality pass: both vessels, the full robot,
worktable, and laboratory context are present, but cylinder markings are not
legible, transparent glass has weak contrast, and some arm/appliance occlusion
remains. These images establish initial-scene inspectability only.

## Isolation and environments

No conda environment was created and no package was installed or changed. The run
reused the existing EOS Isaac Sim 4.1 / GenManip environment and the existing EOS
client environment.

GenManip commit `6ff55ed7c7bd441825d56f1016a30e03b524ebea` was cloned into the private runtime
root:

```text
/tmp/sfgm-final-0713-c
```

The checkout was clean at launch. The collected package was a real copy under the
private `saved/assets/collected_packages`; only base asset directories were linked
from the shared EBench dataset and were used read-only by this workflow. The shared
GenManip `saved/assets` location was never used as a writable package install.

The EOS runner came from commit
`4096906e396651e674300448409e02f89a39b484` in a dirty development worktree, so the
three executed package/trace components are frozen by individual hashes in the YAML
record. The dirty genmanip-client `eval_client.py` is frozen the same way. The
server was shut down gracefully; port 18089 became rebindable and no matching
runtime process remained.

## Exact execution

The successful run used:

```text
run_id:
  scenario_forge_bimanual_pour_canary_20260713T080757Z_r4

episode_id:
  scientific_workbench_bimanual_pour/
  scenario_forge_bimanual_pour_canary_20260713T080757Z_r4/
  scenario_forge/scientific_workbench_bimanual_pour/000

robot_id:
  manip/lift2/R5a
```

GenManip completed scene initialization and reset. EOS received the package's
Chinese instruction, 12 arm joints, four gripper values, a three-value base state,
and two end-effector poses; every numeric value was finite.

The wire action was not a 16-value all-zero hold. Each arm received six zero
relative joint deltas, each gripper received two absolute `0.04` targets, and the
separate base motion was `[0, 0, 0]`. Reset gripper values were approximately
`0.044`, so the precise description is an arm-hold plus near-open-gripper neutral
action. GenManip accepted `action[16] + base_motion[3]`, executed exactly one
requested native step, finalized the episode, and saved both result files.

The result was `score=0.0`, `sr=0.0`. That is expected for a one-step neutral action
and is not a failed technical Canary. The terminal worker envelope contains
`obs=null`, so this run cannot claim post-step robot stability.

## Runtime debt exposed

- Isaac stdout contains 113 warning lines: 41 negative mass/inertia warnings, nine
  unsupported `ScaleOrientation` warnings, nine USD Imaging coding warnings, and 14
  duplicate articulation-link warnings. There is no `[Error]` or traceback line.
- Four `[ERROR]` records in the structured worker log are tqdm progress bars routed
  through stderr, not failed operations.
- The worker pool briefly logged an unfinished-episode bookkeeping retry, then
  finalized and saved the result normally.
- EOS still emits legacy top-level labels: `task_id=ebench/config`,
  `external_task_id=config`, and `scenario_pack=home_manipulation`. Native episode
  ID and frozen package hashes provide the correct linkage.
- The trace records EBench commit `884a949...`; EBench was not the package runtime,
  while GenManip was a frozen clean checkout and the dirty client file was
  hash-frozen.
- The generated package manifest correctly remains a static declaration with
  `validation_scope.simulator_smoke=false`; external evidence is recorded here
  instead of mutating the generated package after the run.
- The formal policy camera file still exposes only the overlook camera. Temporary
  QA cameras do not establish wrist-camera or model-input compatibility.
- The registered predicates cover the flask's pour pose and return pose; they do
  not prove the auxiliary-arm hold, five semantic phases, or fluid transfer.
- This neutral step does not call cuRobo IK, motion generation, or collision
  avoidance.

## Claim boundary and next action

This Canary establishes exact-package discovery, scene construction, reset, finite
Lift2 state delivery, legal action acceptance, one native step, metric/finalize
execution, and result persistence.

It does not establish grasping, alignment, pouring, return-to-start success, liquid
transfer, long-horizon physical stability, model quality, official EBench
reproduction, or leaderboard comparability.

The next meaningful slice belongs in EOS/GenManip: clean the task-facing physics and
transparent-asset presentation, then add a scripted/oracle five-step rollout with
post-action observations and evidence. Scenario Forge should remain the package
compiler and evidence-contract owner; it should not grow an episode runner.

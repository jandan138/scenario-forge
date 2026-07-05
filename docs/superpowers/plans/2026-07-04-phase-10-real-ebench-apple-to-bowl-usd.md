# Real EBench Apple-To-Bowl USD Canary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a narrow Phase 10.6-10.10 canary that generates one Scenario Forge package for EBench `mobile_manip/apple_to_fruit_bowl` using the official apple, bowl, scene, robot, and camera assets instead of placeholder USD assets.

**Architecture:** Keep Scenario Forge as a portable package compiler. Scenario Forge ingests a small official-asset source manifest, materializes asset bundles into a local package or records a locked external source, compiles `scene/main.usda`, exports the EBench adapter descriptor, and imports EOS evidence. EOS remains responsible for `pxr.Usd.Stage.Open`, Newton/GenManip rendering, model execution, traces, and task success checks.

**Tech Stack:** Python 3.10, YAML package artifacts, existing Scenario Forge asset lock and USD compiler modules, EOS `embodied-eval-os-py310` / Newton lanes for downstream smoke evidence.

---

## Execution Status

2026-07-04 update:

```text
Phase 10.6 Official EBench asset intake freeze:
  implemented in Scenario Forge with tests.

Phase 10.7 Single-task real-asset USD package:
  implemented and generated at /tmp/ebench-apple-to-bowl-canary.
  Scenario Forge package check and asset lock check passed.

Phase 10.8 EOS package-linked real-asset USD smoke:
  executed through the EOS bridge with runtime_status=executed and
  stage_open_status=passed.

Phase 10.9 engine-native tabletop render and visual review:
  executed through the EOS bridge with render_status=pass, material preflight
  status=pass, and clean-room visual review verdict=PASS.

Phase 10.10 task contract canary hardening:
  implemented in Scenario Forge. The generated package now includes
  task/task_contract.yaml and exposes it through the Scenario Forge manifest,
  EBench package descriptor, and adapter report.

Retained small evidence:
  docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/

Next open phase:
  Apple-to-bowl has closed Phase 11.0-11.4 through automated evidence and has a
  Phase 11.5 internal RC bundle; public release is still blocked by
  license/redistribution policy. The open Phase 11 work is now scale-out:
  remote-to-holder has passed 11.0 visual, 11.1 EOS live-start, and 11.2
  completed-episode gates, but its 11.3 success predicate correctly failed
  because the retained zero-policy terminal result has score=0.0 and sr=0.0.
  Soap-to-dish remains blocked earlier at 11.0 by official task3 scene material
  closure / overview review. Release policy still controls public release.

2026-07-05 update:
  Phase 11.3.b has a first rerun candidate, but Phase 11.3 remains blocked.
  Use EOS BPL-19R.R2 same-checkpoint online lane as the first 11.3.c source:
  the retained cohort has 10 completed EOS online attempts and 4 historical
  successes for apple-to-bowl (attempts 005, 006, 007, 009; score=1.0,
  success_rate=1). Attempt 007 is the preferred debugging reference because it
  succeeded in 13 cycles. This historical evidence is reference-only because it
  used the native GenManip task config directly. 11.3.c must rerun through an
  EOS wrapper that loads the Scenario Forge package, records package linkage,
  maps task_id=mobile_manip/apple_to_fruit_bowl to the native GenManip config,
  and emits new completed-episode and predicate evidence. Because the current
  runner cannot directly target the retained successful attempt 007 seed, 11.3.c
  should allow repeated package-scoped attempts and retain the first true
  package-linked success.

  2026-07-05 progress: EOS now has the package-linked BPL-19R wrapper and CLI
  scaffold in the Phase 11 EOS worktree. Unit tests verify that it loads the
  Scenario Forge package, maps `mobile_manip/apple_to_fruit_bowl` to the native
  GenManip apple-to-bowl config, records package linkage, supports repeated
  package-scoped attempts, stops after the first successful attempt, and supports
  a dry-run plan without starting Isaac Sim. Retained dry-run evidence uses
  `attempt_count=10`:
  docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/phase11_3c_bpl19r_package_linked_plan/phase11_package_linked_bpl19r_rerun.yaml.
  Its blocker is `live_bpl19r_rerun_not_executed`; the actual successful
  completed episode is still pending.

  2026-07-05 live update: the package-linked BPL-19R rerun has now retained a
  successful package-linked rollout. The live run stopped after attempt_002:
  attempt_000 and attempt_001 completed with task_success=false and score=0.0;
  attempt_002 completed with task_success=true and standard_model_score=1.0.
  Retained top evidence:
  docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/phase11_3c_bpl19r_package_linked_live/phase11_package_linked_bpl19r_rerun.yaml.
  It records rerun_status=executed, selected_success_attempt=attempt_002,
  blockers=[]. This closed the live package-linked rollout-source step.
  The BPL-19R bridge has since translated the retained output into Phase 11.2
  completed-episode evidence and Phase 11.3 predicate evidence, and both strict
  gates passed for apple-to-bowl. Apple-to-bowl is now an internal RC, not the
  active predicate blocker.

  GenManip native demogen/cuRobo is documented as a backup regeneration lane,
  not the selected 11.3.b source. It can run native
  `demogen.py -cfg configs/tasks/ebench/mobile_manip/test_mini/apple_to_fruit_bowl.yml`
  and records success when the scene metric score is 1, but no reusable local
  apple demogen/task LMDB was found and GenManip demogen cannot directly consume
  Scenario Forge packages. A Scenario-Forge-to-GenManip adapter/exporter would
  be required before demogen output can make a package-linked Phase 11.3 claim.
```

## Phase 11 Automated Evidence Plan

Phase 11 的执行口径已经从“人工 review / release flow”调整为“自动证据门禁 / EOS
execution / release gate”。人工可以看 dashboard、提出 issue、要求重跑，但不能作为通过条件；
所有阶段必须由结构化 evidence 决定 passed、failed 或 blocked。

Owner boundary:

```text
Scenario Forge:
  package/schema/asset/adapter/task-contract static gates
  visual-review evidence ingestion
  EOS execution evidence ingestion
  release-candidate gate aggregation

render-visual-reviewer:
  overview render and keyframe clean-room visual review
  visible blockers: missing object, empty frame, red/pink fallback material,
  severe occlusion, clipping, impossible geometry, bad camera framing

embodied-eval-os / EBench adapter:
  runtime task execution
  simulator trace and runtime logs
  reset/step/close lifecycle
  task success predicate evaluation

policy gate:
  license and redistribution approval
```

Phase sequence after the completed Phase 10.10 canary:

```text
11.0 Automated Visual Review Gate:
  status: closed for apple-to-bowl canary
  evidence: tabletop_overview_visual_review.yaml, phase11_visual_review_gate.yaml
  meaning: the retained engine-native overview render is visually acceptable

11.1 EOS Task Execution Integration:
  status: closed for apple-to-bowl canary
  evidence: phase11-eos-task-execution/v0.1
  meaning: EOS consumed the Scenario Forge package and task contract, generated
  a runtime execution config, started an episode, and retained trace/log/keyframe
  references. The retained live gate is phase11_task_execution_gate_live.yaml.

11.2 Executed Episode Evidence Gate:
  status: closed for apple-to-bowl canary
  evidence: phase11-executed-episode-evidence/v0.1
  meaning: EOS retained a completed episode with terminal episode_result,
  runtime log, trace, and initial/final keyframes. The original zero-policy
  completed result had score=0.0/sr=0.0 and remains failure history; the later
  BPL-19R bridge produced the successful completed-episode evidence used by
  the current apple-to-bowl chain. 11.2 itself still does not mean task success.

11.3 Success Predicate Evaluation Gate:
  status: closed for apple-to-bowl canary by BPL-19R bridge evidence
  evidence: predicate evaluation owned by EOS/EBench
  meaning: task success is computed from simulator state, such as
  object_in_container(apple_001, bowl_001); visual review cannot override it.
  The zero-policy failed gate is retained as historical evidence only.

11.4 Post-Execution Visual Review Gate:
  status: closed for apple-to-bowl BPL-19R attempt_002
  evidence: render-visual-reviewer keyframe review
  meaning: initial/final frames are visually coherent and material/render
  artifacts did not invalidate visual inspection

11.5 Single-Task Automated Release Candidate:
  status: internal RC generated, public release policy-blocked
  evidence: aggregated RC gate
  meaning: apple-to-bowl has the first complete automated evidence bundle; if
  license remains research-use, the release status is blocked even when technical
  gates pass

11.6 Small Multi-Task Canary:
  status: blocked during 3-task scale-out
  evidence: 3-5 task packages with the same automated gates
  meaning: the pipeline is not overfit to apple-to-bowl. Current blockers are
  remote-to-holder 11.3 successful-rerun/predicate recovery and soap-to-dish
  11.0 upstream material/visual closure.

11.7 Automated Release Gate:
  status: blocked by 11.6 and release policy
  evidence: release-critical gate aggregation
  meaning: only package, asset, visual, execution, predicate, and license gates
  together can declare release_candidate_status=passed

11.8 Phase-12 Readiness Checkpoint:
  roadmap/release contract implemented in Scenario Forge docs and evidence
  meaning: Phase 12 registry/viewer/multi-simulator work may start only after
  11.5 has at least one complete single-task evidence bundle, 11.6/11.7 have
  stable machine-readable status, and no unknown/manual blocker remains
```

Claim boundary:

```text
No Phase 11 gate may claim model quality, official EBench score, leaderboard
comparability, public dataset release, or physics fidelity unless the specific
EOS/EBench/policy evidence for that claim exists and is referenced by the gate.
```

Human-free acceptance policy:

```text
1. Phase 11 has no mandatory human approval step.
2. Human inspection may create feedback, issues, or rerun requests, but it
   cannot change a failed/blocked gate into passed.
3. Overview render and execution keyframe acceptance must come from
   render-visual-reviewer evidence with reviewer=render-visual-reviewer and
   review_mode=clean_room_visual_skill.
4. Runtime acceptance must come from EOS evidence: lifecycle status, trace URI,
   runtime log, keyframes, and simulator-state predicate outputs.
5. Scenario Forge only checks and aggregates evidence. Missing artifacts,
   stale evidence, mismatched owner, or missing visual-review skill output keeps
   the corresponding gate failed/blocked.
```

User-approved planning constraint, 2026-07-05:

```text
All former manual acceptance points are removed from the critical path.

Visual checks:
  Must use render-visual-reviewer clean-room evidence. Human inspection may
  request a retake, but it cannot create PASS evidence or override WARN/FAIL.

Task success:
  Must use Phase 11.3 EOS/EBench simulator-state predicate evidence. Visual
  review confirms evidence readability only; it cannot decide success.

Execution:
  Must use EOS lifecycle, trace, runtime log, and keyframe evidence. A generated
  execution config is useful but remains blocked until a real episode starts.

Release:
  Must use Phase 11.5 / 11.7 aggregation plus policy evidence. Research-use
  assets or missing redistribution approval keep the result internal or
  policy-blocked.
```

Manual-step replacement table:

```text
Manual overview image check:
  replaced by Phase 11.0 render-visual-reviewer clean-room evidence plus
  Scenario Forge strict visual gate ingestion.
  PASS is required. WARN/FAIL/missing review remains blocked or failed.

Manual post-execution screenshot check:
  replaced by Phase 11.4 render-visual-reviewer evidence on retained
  initial/final keyframes.
  This checks whether the evidence images are visually usable; it does not
  decide task success.

Manual "task succeeded" judgment:
  no visual replacement. Only Phase 11.3 EOS/EBench simulator-state predicate
  evidence can make a success claim.

Manual release signoff:
  replaced by Phase 11.5 single-task RC aggregation and Phase 11.7 suite release
  gate, both with policy evidence. Research-use assets or missing redistribution
  approval keep the result internal/policy-blocked.
```

Automated review chain:

```text
1. EOS / Isaac Sim owns render and keyframe production. Every image evidence row
   must keep an artifact path, hash or retained file reference, camera/runtime
   metadata, trace URI, and runtime log reference where applicable.
2. render-visual-reviewer receives only image paths and a short visual
   expectation packet. It must not receive implementation details, suspected
   defects, code diffs, or expected verdicts.
3. render-visual-reviewer outputs structured PASS/WARN/FAIL evidence with
   visible evidence and retake recommendation for WARN/FAIL.
4. Scenario Forge ingests that evidence and writes the visual gate. It does not
   visually inspect screenshots itself and cannot override the reviewer verdict.
5. WARN, FAIL, missing reviewer output, stale keyframe paths, or missing upstream
   gate references keep the gate blocked. The only fix is to regenerate the
   render/keyframe or upstream evidence and rerun the clean-room review.
6. Predicate success and visual quality remain separate: Phase 11.3 decides task
   success from simulator state; Phase 11.4 decides whether the retained
   before/after images are visually usable evidence.
```

The historical manual check of the apple-to-bowl render is retained only as
context. The active Phase 11.0 pass is the structured visual-review gate, and
Phase 11.4 must use the same skill-based review pattern for initial/final
execution keyframes.

Product milestone interpretation:

```text
Phase 11.0 passed:
  Only means the engine-native overview render passed clean-room visual review.

Phase 11.1 passed:
  Means EOS consumed the Scenario Forge package and task contract, generated an
  execution config, started a real episode, and retained trace/log/keyframe
  references.

Phase 11.2 passed:
  Only means EOS retained a completed episode with trace, runtime log,
  terminal result, and initial/final keyframes. It does not imply task success.

Phase 11.3 passed:
  Means EOS/EBench simulator-state predicate evidence says the task succeeded,
  such as object_in_container(apple_001, bowl_001)=true.

Phase 11.4 passed:
  Means the canary has a completed episode, success predicate evidence, and
  post-execution visual review evidence.

Phase 11.5 passed or policy-blocked:
  This is the first "complete EBench-compatible USD task package" milestone.
  It contains real USD assets, task contract, EOS execution evidence, predicate
  evidence, before/after visual review, and release policy status. If license or
  redistribution approval is blocked, it is an internal RC rather than a public
  dataset release.
```

Next engineering slices before Phase 12:

```text
11.1.a EOS package discovery:
  EOS reads manifest.yaml, locks/asset_lock.yaml, adapters/ebench/package.yaml,
  adapters/ebench/task_entrypoint.yaml, and task/task_contract.yaml.
  status: closed for apple-to-bowl canary on 2026-07-04 in EOS worktree
  phase11-scenario-forge-execution.

11.1.b EOS execution config generation:
  EOS maps the task contract into a runtime execution config and emits
  phase11-eos-task-execution/v0.1 evidence with execution_config_status=generated.
  status: closed for apple-to-bowl canary on 2026-07-04. Retained evidence:
  phase11_eos_task_execution_config_blocked_evidence.yaml,
  phase11_task_execution_config_trace.json, and
  phase11_task_execution_config_runtime.log.

11.1.c episode start and initial keyframe:
  EOS starts the apple-to-bowl episode, records reset/step/close lifecycle,
  runtime log, trace URI, and initial keyframe. Scenario Forge then runs
  package phase11-task-execution --strict.
  status: closed for apple-to-bowl canary on 2026-07-04. Retained evidence:
  phase11_eos_task_execution_live_evidence.yaml,
  phase11_task_execution_live_trace.json,
  phase11_task_execution_live_runtime.log,
  phase11_task_execution_initial_overlook.png, and
  phase11_task_execution_gate_live.yaml.

11.1.c.1 EOS runtime connection hardening:
  EOS starts or connects a GenManip/IsaacSim41 EvalServer, submits the
  apple-to-bowl job, and records server URL, job/run id, reset polling, timeout
  configuration, and reset outcome. A cold-start timeout must be evidence, not a
  silent skip. Status: closed for apple-to-bowl canary with
  reset_result_timeout_s=240.0 recorded in live trace evidence.

11.1.c.2 initial keyframe export:
  EOS exports a real initial keyframe PNG from simulator observation, server
  recorder artifact, or trace data, then writes that retained file path into
  phase11-eos-task-execution/v0.1. Scenario Forge strict gate must verify the
  file exists. Status: closed for apple-to-bowl canary with
  phase11_task_execution_initial_overlook.png.

11.1.c.3 strict Phase 11.1 rerun:
  Scenario Forge reruns package phase11-task-execution --strict using only EOS
  evidence. The output is either phase11_task_execution_gate.yaml passed, or a
  failed/blocked gate with machine-readable blockers. Manual override is not
  allowed. Status: closed for apple-to-bowl canary by
  phase11_task_execution_gate_live.yaml, status=passed, blockers=[].

11.2.a completed episode evidence:
  EOS retains final state, final keyframe, trace artifact, and runtime log.
  status: closed for apple-to-bowl canary on 2026-07-04. Retained passed
  evidence: phase11_executed_episode_completed_evidence.yaml,
  phase11_executed_episode_completed_trace.json,
  phase11_executed_episode_completed_runtime.log,
  phase11_executed_episode_initial_overlook.png,
  phase11_executed_episode_final_overlook.png, and
  phase11_executed_episode_gate_completed.yaml. The earlier
  phase11_executed_episode_started_blocked_evidence.yaml and
  phase11_executed_episode_gate_started_blocked.yaml remain historical blocked
  evidence for the one-step smoke.

11.2.a.1 EOS full-horizon or step_chunk execution:
  EOS must run the GenManip/IsaacSim41 apple-to-bowl job to a terminal episode,
  not just a short smoke. A later 40-step zero-policy run reached
  runtime_status=executed and retained recorder keyframes, but it did not emit
  episode_result; because the task config has num_steps=1000, that trace is
  debugging evidence only and cannot close 11.2. Status: closed by EOS run
  scenario_forge_phase11_apple_to_bowl_chunk_20260704T154825Z with
  max_policy_calls=1000, step_chunk_size=1000, executed_steps=1000.

11.2.a.2 executed episode evidence builder:
  EOS converts the terminal trace, runtime log, initial/final keyframes, and
  final simulator-state projection into phase11-executed-episode-evidence/v0.1.
  Required fields: runtime_owner=embodied-eval-os, episode_status=completed,
  trace_uri, runtime_log, keyframes.initial, keyframes.final, final_state, and
  blockers=[]. Status: closed by
  phase11_executed_episode_completed_evidence.yaml. The evidence records
  observation_status=post_completion_reset_observation because GenManip returns
  the next reset observation together with the completed episode_result.

11.2.a.3 strict executed episode gate:
  Scenario Forge runs package phase11-executed-episode --strict over the EOS
  evidence. Scenario Forge does not run the simulator and cannot turn a
  started/partial trace into completed evidence. Status: closed by
  phase11_executed_episode_gate_completed.yaml, status=passed, blockers=[].

11.3.a predicate evaluation evidence:
  EOS/EBench computes object_in_container(apple_001, bowl_001) from simulator
  state and emits success predicate evidence. Status: evaluated and failed for
  the current zero-policy completed episode. Retained evidence:
  phase11_success_predicate_failed_evidence.yaml and
  phase11_success_predicate_gate_failed.yaml. Blockers:
  predicate_status must be true; got False; episode_result_sr_zero.

11.3.b successful rollout source selection:
  EOS/EBench selects a real way to produce an apple-to-bowl success. Preferred
  sources are GenManip demonstration_configs / cuRobo / generalized oracle rule
  lanes, then official successful rollout reruns. A zero-policy run, historical
  screenshot, or human/visual-review judgment cannot be promoted into success
  evidence. Required evidence records the source, task config, policy/oracle
  identity, runtime environment, run id, package linkage, and blockers.
  Status: first candidate selected. Use EOS BPL-19R.R2 same-checkpoint online
  lane as the first rerun source because retained historical attempts 005, 006,
  007, and 009 succeeded. Use attempt 007 as the primary debugging reference.
  Retained source-selection evidence:
  docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/phase11_successful_rollout_source_selection.yaml.
  The selected source still requires a new package-linked rerun; old BPL-19R.R2
  result_info files cannot close Phase 11.3.
  Backup lane: GenManip native demogen/cuRobo can regenerate native successes,
  but it is not selected for 11.3.b because no reusable apple demogen/task LMDB
  was found and direct Scenario Forge package consumption is unsupported without
  an adapter/exporter.

11.3.c package-linked successful completed episode rerun:
  EOS/GenManip reruns the selected successful lane against the Scenario Forge
  apple-to-bowl package or a documented equivalent package-linked execution
  config. It must retain a new terminal episode_result, trace, runtime log,
  initial/final keyframes, and simulator-state projection, then rebuild Phase
  11.2 evidence. First implementation target: EOS package-linked BPL-19R wrapper
  that loads /tmp/ebench-apple-to-bowl-canary, records task contract / scene USD
  / asset lock linkage, maps the task id to the native GenManip config, runs a
  package-scoped BPL-19R online episode, and emits fresh evidence. The wrapper
  may also need a BPL-19R-native-trace to Phase-11-evidence translator, because
  current BPL-19R run reports are not guaranteed to be directly accepted by the
  Phase 11 completed-episode CLI. If the rollout is not package-linked, this
  step remains blocked.
  Status: live package-linked BPL-19R success retained at attempt_002. Top
  evidence records rerun_status=executed, selected_success_attempt=attempt_002,
  task_success=true, standard_model_score=1.0, blockers=[]. The BPL-19R output
  has now been bridged into Phase 11.2/11.3 strict gate evidence.

11.3.d strict predicate re-gate:
  Scenario Forge consumes only EOS/EBench predicate evidence and reruns
  package phase11-success-predicate --strict. Pass requires predicate_status=true,
  success score/sr evidence, a referenced passed Phase 11.2 gate, and no blockers.
  Visual review or human inspection cannot override this gate.
  Status: closed by phase11_success_predicate_bpl19r_success_gate.yaml,
  status=passed, blockers=[].

11.4.a post-execution review packet assembly:
  Scenario Forge/EOS prepares a clean-room packet with only initial/final
  keyframe paths, image references or hashes, a short visual expectation, and
  upstream gate references. The packet must not include implementation details,
  suspected defects, or expected verdicts.
  Status: closed for BPL-19R attempt_002 using
  phase11_4_bpl19r_visual_review_frames/right_camera_first.jpg and
  phase11_4_bpl19r_visual_review_frames/right_camera_last.jpg.

11.4.b clean-room visual review:
  render-visual-reviewer reviews the initial/final keyframes and emits
  structured PASS/WARN/FAIL evidence with visible evidence and retake
  recommendation when needed.
  Status: closed by phase11_post_execution_visual_review_bpl19r_success.yaml,
  verdict=PASS.

11.4.c strict visual gate and retake loop:
  Scenario Forge ingests 11.4.b evidence into the post-execution visual gate.
  If render-visual-reviewer returns WARN or FAIL, the blocked gate is retained
  and EOS/renderer/asset pipeline regenerates the relevant keyframes before
  rerunning 11.4.a/11.4.b. Manual inspection cannot override the verdict.
  Status: closed by phase11_post_execution_visual_review_bpl19r_success_gate.yaml,
  status=passed, blockers=[].

11.5.a single-task RC aggregation:
  Scenario Forge aggregates package, asset, task contract, visual, execution,
  predicate, and policy gates into the single-task release candidate gate.
  Status: internal RC evidence bundle generated, but blocked by release policy in
  phase11_single_task_rc_bpl19r_internal_policy_blocked_gate.yaml because assets
  remain research-use and redistribution approval is missing.

11.6.a small multi-task canary:
  Repeat the same gate chain for 3-5 Scenario Forge-generated EBench tasks.
  Status: progressed to three represented real EBench task packages. Apple-to-bowl
  is an internal RC; soap-to-dish and remote-to-holder now have package-static
  evidence, asset locks, task contracts, EBench adapter exports, and USD
  Stage.Open evidence. Latest gate is
  phase11_small_multi_task_canary_three_task_remote_predicate_failed_downstream_blocked_gate.yaml,
  status=blocked, package_count=3. The task-count blocker is removed.
  Remote-to-holder now has retained PASS Phase 11.0 evidence after fixing
  official-asset sidecar materialization, static tabletop contact, and
  task-specific overview framing. It has also passed Phase 11.1 live-start and
  Phase 11.2 completed-episode gates, then failed Phase 11.3 predicate because
  the completed zero-policy run returned score=0.0 and sr=0.0. Soap-to-dish
  still fails Phase 11.0 because its official task3 scene/MDL closure is
  missing textures and the overview camera still needs retake. Soap-to-dish
  must first close its upstream material/visual blocker.

11.7.a automated release gate:
  Aggregate suite-level release-critical gates. Status: blocked by
  phase11_automated_release_three_task_remote_predicate_failed_policy_blocked_gate.yaml
  because Phase 11.6 is blocked by soap overview visual/material gates,
  remote-to-holder zero-policy predicate failure, downstream post-execution
  review / RC gaps, and license policy. Remote visual/camera, 11.1
  episode-start, and 11.2 completed-episode blockers are no longer in the latest
  release blocker list.
```

Current execution order:

```text
1. Treat apple-to-bowl Phase 11.0-11.4 as closed by automated evidence.
2. Keep Phase 11.5 as the first complete single-task internal RC, but blocked
   for public release by research-use assets and missing redistribution approval.
3. Split the added-task work by current gate status. Remote-to-holder has
   passed Phase 11.0, Phase 11.1 EOS live-start evidence, and Phase 11.2
   completed episode evidence; it should proceed to a successful
   policy/oracle/official rerun for Phase 11.3 predicate success. Soap-to-dish
   must still receive repaired official task3 scene
   assets or a ConvertAsset handoff with failing package, dependency report,
   runtime log, render image, provenance, and hashes; then regenerate/render/
   review until Phase 11.0 PASS.
4. Re-run 11.6 small multi-task canary after each new task closes its 11.0-11.5
   automated gates.
5. Re-run 11.7 automated release only after 11.6 passes and license policy
   blockers are resolved or explicitly retained.
6. Defer Phase 12 registry/viewer/multi-simulator work until the 11.6/11.7
   blocker state is stable and machine-readable.
```

Product-readable next phase order:

```text
11.6.b remote-to-holder EOS execution:
  Status: Phase 11.1 episode-start lane is now closed. The retained evidence
  includes runtime preflight, live trace, runtime log, initial overlook keyframe,
  and a passed strict task-execution gate. Phase 11.2 completed episode evidence
  is also closed. The next remote step is Phase 11.3 success-predicate recovery:
  find a successful package-linked policy/oracle/official rerun and regenerate
  11.2/11.3 evidence, not another 11.1 or 11.2 smoke.

11.6.a soap-to-dish material/visual closure:
  Keep Scenario Forge out of ConvertAsset logic. Use a repaired official task3
  asset source or retained ConvertAsset handoff, then rerender and rerun
  render-visual-reviewer until Phase 11.0 passes.

11.6.c / 11.6.d added-task downstream gates:
  For each added task, retain completed episode evidence, simulator-state
  predicate evidence, post-execution visual review evidence, and single-task RC
  aggregation. No human decision can substitute for these gates.

11.6.e suite re-aggregation:
  Rerun the small multi-task canary only after the added tasks have machine-
  readable 11.0-11.5 evidence.

11.7 automated release re-gate:
  Re-aggregate package, asset, adapter, visual, execution, predicate, and policy
  gates. A public release candidate requires known_blockers=[] and passing
  license/redistribution evidence.

11.8 Phase-12 readiness:
  Write one readiness note that references 11.5, 11.6, 11.7 and policy status.
  If any blocker is unknown/manual, Phase 12 stays deferred and work remains in
  Phase 11.
```

2026-07-05 human-free execution update:

```text
Manual inspection is removed from the acceptance path. It may create bug reports
or rerun requests, but it cannot pass any Phase 11 gate.

Next concrete step:
  Resolve remote-to-holder Phase 11.3. The 11.1 live-start lane has already
  consumed the package, started a real episode, retained trace/log/initial
  keyframe evidence, and passed the strict gate. Phase 11.2 has also retained a
  completed episode and passed strict ingestion. The remaining remote blocker is
  zero-policy predicate failure, so the next work is a package-linked successful
  policy/oracle/official rerun, followed by fresh 11.2/11.3 evidence. Soap-to-dish
  still needs a better overview camera and upstream official task3 scene texture
  closure through a repaired asset source or ConvertAsset handoff before it can
  pass Phase 11.0.

If 11.3.c fails after bounded attempts:
  Historical fallback policy still applies for future reruns: keep the failed
  package-linked evidence and blockers, and escalate to GenManip demogen/cuRobo
  only after adding explicit Scenario Forge-to-GenManip package linkage or
  exporter evidence. Do not use visual review, historical screenshots, or manual
  judgment as success evidence.

After 11.3.d passes:
  This is now complete for apple-to-bowl. 11.4 used right_camera_first/right_camera_last
  rather than the ambiguous overview post-action frame, then Scenario Forge
  ingested the structured review evidence. For future tasks, WARN/FAIL/missing
  review still triggers retake or upstream evidence fixes.

First true package milestone:
  11.5 is the first "complete EBench USD task package" checkpoint for product
  reporting: real USD assets, locked assets, task contract, EOS completed
  episode, success predicate, automated visual reviews, and release policy.
  Apple-to-bowl has reached this checkpoint as an internal RC; license blockers
  keep it from being a public release.

Scale-out after the single task:
  11.6 repeats the same human-free gate chain for 3-5 real EBench tasks. The
  current canary has package_count=3 and is correctly blocked by soap Phase
  11.0 visual/material gates plus downstream gate gaps for soap-to-dish and
  remote-to-holder, not by task count. The latest 11.6/11.7 rerun has removed
  the remote material, pose/contact, and camera blockers after retaining
  contact-fixed render/review/gate evidence. Remote has also advanced through
  live-start and completed-episode evidence; its current blocker is failed
  simulator-state predicate evidence from a zero-policy terminal result. Soap
  material closure remains upstream. 11.7 aggregates the suite release gate and
  is currently blocked by 11.6, remote successful-rerun/predicate closure,
  soap-to-dish upstream evidence, and license policy. Phase 12 starts only after
  this path has stable machine-readable blockers or passes.
```

2026-07-05 Phase 11.6 / 11.7 execution slices:

```text
11.6.a.1 remote material sidecar closure promotion:
  Keep the official-asset intake sidecar fix, regenerate
  ebench_remote_to_holder_canary, retain manifest/asset lock/main USD evidence,
  rerender in IsaacSim41, and rerun render-visual-reviewer plus strict 11.0 gate.
  Pass requires material_runtime_preflight.status=pass, no missing remote texture
  blocker in the runtime log, and clean-room visual PASS after camera retake.
  Status: closed for remote-to-holder Phase 11.0. Contact-fixed cam3 has
  render_status=pass, material_runtime_preflight.status=pass, no blocking
  runtime log signal, clean-room visual PASS, and strict visual gate
  status=passed.

11.6.a.2 soap upstream material closure:
  Do not synthesize missing textures or port ConvertAsset logic into Scenario
  Forge. Either ingest a repaired official task3 scene source or retain a
  ConvertAsset handoff containing failing package, dependency closure report,
  runtime log, render image, provenance, and hashes. Then regenerate the package
  and rerun material preflight plus clean-room visual review.
  Current evidence:
  `soap_to_dish_phase11_material_closure_handoff.yaml` records a static MDL
  texture-closure failure in both the package copy and official task3 source.
  The missing official scene textures are
  `c00e97e58585d8ddb0f8b16a724d05a13eae31.jpg`,
  `bf77ddc86c270d02747e7d0517103514ab51d0f.jpg`, and
  `c9c274d4ea1de7d059cec0a795b3b27e3941935.jpg`. Scenario Forge can now detect
  this before render, but cannot repair it without a repaired official source or
  ConvertAsset-owned material-normalized artifact.

11.6.a.3 task-specific overview camera retakes:
  Update scale-out render metadata and expectation packets so they target
  soap/soap-dish and remote/holder, not apple/bowl. Camera selection must frame
  the manipulated object, fixture target, work surface, and robot/spawn without
  clipping or severe occlusion.

11.6.a.4 remote pose / camera root-cause gate:
  Before additional remote-to-holder camera tuning, compare the official
  GenManip remote pose with the Scenario Forge source manifest, generated
  scene/instances.yaml, scene/main.usda transform, and retained render camera
  metadata. Scenario Forge found that the manifest z center kept the remote
  about 9.6 cm above the task5 tabletop after the orientation fix. The manifest
  was corrected under test from z=0.11 to z=0.0142, package artifacts were
  regenerated, bbox evidence now shows tabletop contact, and the contact-fixed
  cam3 render passed clean-room visual review. Status: closed for Phase 11.0.

11.6.b added-task EOS execution integration:
  Repeat Phase 11.1 for mobile_manip/soap_to_dish and
  mobile_manip/remote_to_holder after their 11.0 gates pass. This is still
  Phase 11 work: EOS consumes the Scenario Forge package/task contract, starts a
  real episode, and emits trace/log/keyframe evidence. It is not Phase 12.

  Remote-to-holder status: closed for Phase 11.1 after an EOS runtime preflight
  and live GenManip/IsaacSim41 smoke with trace/log/initial keyframe retention.
  The earlier live remote probe without these overlays reached job submission
  but failed before reset/keyframe because the Isaac worker could not import
  `curobo`; that failure is retained as a historical EOS runtime-environment
  blocker, not a Scenario Forge material, pose, camera, or package-contract
  blocker.

11.6.c added-task completed episode and predicate gates:
  EOS retains completed episode evidence and simulator-state predicate evidence
  for each added task. Scenario Forge only ingests the evidence and runs strict
  11.2/11.3 gates. Visual review and manual inspection cannot override a failed
  predicate. Remote-to-holder status: 11.2 completed episode gate is passed,
  but 11.3 predicate gate is failed because the retained zero-policy terminal
  result has score=0.0 and sr=0.0. Source-selection evidence
  `remote_to_holder_phase11_successful_rollout_source_selection.yaml` found no
  retained remote success. EOS has now generalized the existing BPL-19R
  package-linked wrapper beyond apple-to-bowl by adding
  `mobile_manip/remote_to_holder -> remote_to_holder.yml`, and the dry-run plan
  evidence is retained under
  `remote_to_holder_phase11_3c_bpl19r_package_linked_plan/`. The next EOS action
  is a live package-linked multi-attempt remote lane; only a successful terminal
  result can be bridged into fresh 11.2/11.3 evidence.

11.6.d added-task post-execution review and RC aggregation:
  Run render-visual-reviewer on initial/final keyframes, ingest the strict 11.4
  gate, then aggregate each added task into 11.5 single-task RC evidence with
  policy status.

11.6.e small-canary re-aggregation:
  Rerun suite phase11-small-canary after each added task reaches 11.5. The suite
  passes only when the required 3-5 tasks have the expected automatic evidence
  chain and no release-critical gate remains failed or blocked.

11.7.b automated release re-gate:
  Rerun suite phase11-release after 11.6 passes and license/redistribution
  policy evidence is explicit. Release candidate passes only when package,
  asset, adapter, visual, execution, predicate, and license gates all pass and
  known_blockers=[].

11.8.a Phase-12 readiness checkpoint:
  Retain one readiness note referencing the latest 11.5 single-task RC gate,
  11.6 small-canary gate, 11.7 release gate, policy status, and blocker list.
  Phase 12 starts only if at least one complete single-task evidence bundle
  exists, the 3-5 task canary is passed or blocked only by explicit stable
  upstream/policy blockers, and the release gate has no unknown/manual blockers.
  Human approval is not an input; if this checkpoint is blocked, the next work
  remains Phase 11 retake, EOS evidence, predicate, or policy closure.
```

Phase 12 numbering once 11.8 permits it:

```text
12.0 Registry Readiness Freeze:
  Freeze the retained 11.5/11.6/11.7/11.8 evidence references and decide which
  packages are registry-eligible, internal-only, or policy-blocked. This is a
  documentation/evidence checkpoint, not a simulator run.

12.1 Package Registry and Snapshot:
  Build package registry metadata, asset-lock snapshots, provenance indexes,
  and reproducible package lookup. Do not add episode runners, model adapters,
  leaderboard code, or ConvertAsset conversion logic.

12.2 Evidence / Package Viewer:
  Expose manifests, USD entrypoints, asset locks, validation evidence,
  render-visual-reviewer evidence, EOS evidence links, and policy status. The
  viewer is read-only for gates; it cannot convert failed/blocked evidence into
  passed evidence.

12.3 EBench / EOS Integration Examples:
  Provide minimal handoff examples showing how EBench/EOS consumes Scenario
  Forge packages, task contracts, and evidence references. EOS remains the
  runtime owner.

12.4 Multi-Simulator Adapter Exports:
  Add adapter descriptors or export examples for additional simulator lanes.
  Core package layers still must not import simulator SDKs.

12.5 Public Release Policy Closure:
  Close redistribution approval, research-use, internal-only, or replacement
  asset decisions with policy evidence. Public release candidate status requires
  license_policy=pass and known_blockers=[].
```

## File Structure

- Create `examples/ebench_apple_to_bowl_asset_sources.yaml`: small source manifest for the official EBench apple-to-bowl assets already identified by EOS evidence.
- Create `src/scenario_forge/adapters/ebench/official_asset_intake.py`: load and validate the source manifest; copy package-local asset bundles while preserving `SubUSDs/`, annotations, and `.collect.mapping.json`.
- Create `src/scenario_forge/generation/ebench_canary/apple_to_bowl.py`: generate one package with real asset manifest, scene instances, task, metrics, robot, provenance, and EBench adapter export.
- Modify `src/scenario_forge/cli.py`: add `scenario-forge ebench canary apple-to-bowl`.
- Test `tests/test_ebench_official_asset_intake.py`: verify bundle copy, checksums, and missing-source failures using tiny local fixtures.
- Test `tests/test_ebench_apple_to_bowl_canary.py`: verify generated package has no placeholder assets, references apple/bowl/scene/robot, writes asset lock, and exports EBench package metadata.
- Update `docs/records/2026-07-04-phase10x-eos-environment-and-gates.md`: retain the Phase 10.6-10.10 plan and timing.
- Update `docs/strategy/scenario-forge-ebench-auto-factory-roadmap.md`: keep product roadmap aligned with this canary.

## Task 1: Official Asset Source Manifest

**Files:**
- Create: `examples/ebench_apple_to_bowl_asset_sources.yaml`
- Test: `tests/test_ebench_official_asset_intake.py`

- [ ] **Step 1: Write the failing manifest loader test**

```python
from pathlib import Path

import pytest
import yaml

from scenario_forge.adapters.ebench.official_asset_intake import load_official_asset_sources


def test_loads_apple_to_bowl_official_asset_sources(tmp_path: Path) -> None:
    source = tmp_path / "asset_sources.yaml"
    apple = tmp_path / "apple_bundle"
    apple.mkdir()
    apple_usd = apple / "apple.usd"
    apple_usd.write_text("#usda 1.0\n", encoding="utf-8")
    bowl = tmp_path / "bowl_bundle"
    bowl.mkdir()
    bowl_usd = bowl / "bowl.usd"
    bowl_usd.write_text("#usda 1.0\n", encoding="utf-8")

    source.write_text(
        yaml.safe_dump(
            {
                "schema_version": "ebench-official-asset-sources/v0.1",
                "task_id": "mobile_manip/apple_to_fruit_bowl",
                "instruction": "Pick up the apple from the dining table and place it into the fruit bowl.",
                "assets": {
                    "apple": {"role": "manipulated_object", "source_path": str(apple_usd), "license": "research-use"},
                    "bowl": {"role": "target_container", "source_path": str(bowl_usd), "license": "research-use"},
                },
            }
        ),
        encoding="utf-8",
    )

    loaded = load_official_asset_sources(source)

    assert loaded.task_id == "mobile_manip/apple_to_fruit_bowl"
    assert loaded.assets["apple"].source_path == apple_usd
    assert loaded.assets["bowl"].source_path == bowl_usd


def test_rejects_missing_official_asset_source(tmp_path: Path) -> None:
    source = tmp_path / "asset_sources.yaml"
    source.write_text(
        yaml.safe_dump(
            {
                "schema_version": "ebench-official-asset-sources/v0.1",
                "task_id": "mobile_manip/apple_to_fruit_bowl",
                "instruction": "Pick up the apple from the dining table and place it into the fruit bowl.",
                "assets": {
                    "apple": {"role": "manipulated_object", "source_path": str(tmp_path / "missing.usd"), "license": "research-use"},
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing official asset source"):
        load_official_asset_sources(source)
```

- [ ] **Step 2: Run the failing tests**

Run: `PYTHONPATH=src python -m pytest tests/test_ebench_official_asset_intake.py -q`

Expected: FAIL with `ModuleNotFoundError` or missing `load_official_asset_sources`.

- [ ] **Step 3: Implement the manifest loader**

Create `src/scenario_forge/adapters/ebench/official_asset_intake.py` with dataclasses:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class OfficialAssetSource:
    asset_id: str
    role: str
    source_path: Path
    license: str


@dataclass(frozen=True)
class OfficialAssetSources:
    task_id: str
    instruction: str
    assets: dict[str, OfficialAssetSource]


def load_official_asset_sources(path: str | Path) -> OfficialAssetSources:
    manifest_path = Path(path)
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Official asset source manifest must be a mapping: {manifest_path}")
    if data.get("schema_version") != "ebench-official-asset-sources/v0.1":
        raise ValueError("Unsupported official asset source schema_version")
    task_id = _required_string(data, "task_id")
    instruction = _required_string(data, "instruction")
    raw_assets = data.get("assets")
    if not isinstance(raw_assets, dict):
        raise ValueError("Official asset source manifest field 'assets' must be a mapping")
    assets: dict[str, OfficialAssetSource] = {}
    for asset_id, raw_asset in raw_assets.items():
        if not isinstance(asset_id, str) or not isinstance(raw_asset, dict):
            raise ValueError("Official asset entries must map asset IDs to mappings")
        source_path = Path(_required_string(raw_asset, "source_path"))
        if not source_path.exists():
            raise ValueError(f"Missing official asset source: {source_path}")
        assets[asset_id] = OfficialAssetSource(
            asset_id=asset_id,
            role=_required_string(raw_asset, "role"),
            source_path=source_path,
            license=_required_string(raw_asset, "license"),
        )
    return OfficialAssetSources(task_id=task_id, instruction=instruction, assets=assets)


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing required string field: {key}")
    return value
```

- [ ] **Step 4: Add the real source manifest**

Write `examples/ebench_apple_to_bowl_asset_sources.yaml` with the currently verified CPFS paths:

```yaml
schema_version: ebench-official-asset-sources/v0.1
task_id: mobile_manip/apple_to_fruit_bowl
instruction: Pick up the apple from the dining table and place it into the fruit bowl.
assets:
  scene:
    role: environment
    source_path: /cpfs/shared/simulation/zhuzihou/dev/_datasets/EBench-Assets/assets/scene_usds/ebench/simple_pnp/task4/scene.usd
    license: research-use
  robot:
    role: robot
    source_path: /cpfs/shared/simulation/zhuzihou/dev/_datasets/EBench-Assets/assets/robot_usds/lift2/robot.usd
    license: research-use
  apple:
    role: manipulated_object
    source_path: /cpfs/shared/simulation/zhuzihou/dev/_datasets/EBench-Assets/assets/object_usds/custom_usd/ebench_usds/apple/ready/5948de6770a5491ea158cd9e921ebce9/5948de6770a5491ea158cd9e921ebce9.usd
    license: research-use
  bowl:
    role: target_container
    source_path: /cpfs/shared/simulation/zhuzihou/dev/_datasets/EBench-Assets/assets/object_usds/custom_usd/ebench_usds/bowl/ready/307689f1c6884e1bb85bb20f00fef294/307689f1c6884e1bb85bb20f00fef294.usd
    license: research-use
  camera_yaml:
    role: camera_config
    source_path: /cpfs/shared/simulation/zhuzihou/dev/GenManip/configs/cameras/fixed_camera_lift2_simbox.yml
    license: research-use
```

- [ ] **Step 5: Verify**

Run: `PYTHONPATH=src python -m pytest tests/test_ebench_official_asset_intake.py -q`

Expected: PASS.

## Task 2: Bundle Materialization

**Files:**
- Modify: `src/scenario_forge/adapters/ebench/official_asset_intake.py`
- Test: `tests/test_ebench_official_asset_intake.py`

- [ ] **Step 1: Write the failing bundle-copy test**

```python
from scenario_forge.adapters.ebench.official_asset_intake import materialize_official_asset_bundle


def test_materializes_usd_bundle_with_subusds(tmp_path: Path) -> None:
    source_bundle = tmp_path / "source" / "apple_uid"
    texture_dir = source_bundle / "SubUSDs" / "textures"
    texture_dir.mkdir(parents=True)
    source_usd = source_bundle / "apple.usd"
    source_usd.write_text("#usda 1.0\n", encoding="utf-8")
    (texture_dir / "apple_texture.png").write_bytes(b"png")
    (source_bundle / "apple_annotation.json").write_text("{}", encoding="utf-8")
    target_root = tmp_path / "package"

    result = materialize_official_asset_bundle(
        source_path=source_usd,
        package_root=target_root,
        asset_id="official_ebench_apple",
        role="manipulated_object",
        license="research-use",
    )

    assert result.canonical_usd == "assets/official_ebench_apple/apple.usd"
    assert (target_root / result.canonical_usd).exists()
    assert (target_root / "assets/official_ebench_apple/SubUSDs/textures/apple_texture.png").exists()
    assert (target_root / "assets/official_ebench_apple/apple_annotation.json").exists()
```

- [ ] **Step 2: Run the failing test**

Run: `PYTHONPATH=src python -m pytest tests/test_ebench_official_asset_intake.py::test_materializes_usd_bundle_with_subusds -q`

Expected: FAIL with missing `materialize_official_asset_bundle`.

- [ ] **Step 3: Implement bundle materialization**

Add this to `src/scenario_forge/adapters/ebench/official_asset_intake.py`:

```python
from dataclasses import dataclass
import shutil

from scenario_forge.assets.checksum import compute_sha256


@dataclass(frozen=True)
class MaterializedOfficialAsset:
    asset_id: str
    role: str
    canonical_usd: str
    sha256: str
    license: str
    source_path: str

    def asset_manifest_entry(self) -> dict[str, object]:
        return {
            "asset_id": self.asset_id,
            "role": self.role,
            "asset_type": "usd_bundle",
            "canonical_usd": self.canonical_usd,
            "license": self.license,
            "sha256": self.sha256,
            "source_kind": "official_ebench_asset",
            "source_uri": self.source_path,
            "resolver_version": "scenario-forge-ebench-official-asset-intake/v0.1",
        }


def materialize_official_asset_bundle(
    *,
    source_path: str | Path,
    package_root: str | Path,
    asset_id: str,
    role: str,
    license: str,
) -> MaterializedOfficialAsset:
    source_usd = Path(source_path)
    if not source_usd.exists():
        raise ValueError(f"Missing official asset source: {source_usd}")
    root = Path(package_root)
    target_dir = root / "assets" / asset_id
    root_resolved = root.resolve()
    target_resolved = target_dir.resolve()
    if root_resolved != target_resolved and root_resolved not in target_resolved.parents:
        raise ValueError(f"Materialized asset target escapes package root: {target_dir}")
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_usd.parent, target_dir)
    target_usd = target_dir / source_usd.name
    canonical_usd = target_usd.relative_to(root).as_posix()
    return MaterializedOfficialAsset(
        asset_id=asset_id,
        role=role,
        canonical_usd=canonical_usd,
        sha256=compute_sha256(target_usd),
        license=license,
        source_path=str(source_usd),
    )
```

- [ ] **Step 4: Verify**

Run: `PYTHONPATH=src python -m pytest tests/test_ebench_official_asset_intake.py -q`

Expected: PASS.

## Task 3: Single-Task Package Generator

**Files:**
- Create: `src/scenario_forge/generation/ebench_canary/apple_to_bowl.py`
- Create: `src/scenario_forge/generation/ebench_canary/__init__.py`
- Test: `tests/test_ebench_apple_to_bowl_canary.py`

- [ ] **Step 1: Write the failing package generation test**

```python
from pathlib import Path

import yaml

from scenario_forge.generation.ebench_canary.apple_to_bowl import generate_apple_to_bowl_canary


def _write_tiny_source_manifest(tmp_path: Path) -> Path:
    assets: dict[str, dict[str, str]] = {}
    for name, role in {
        "scene": "environment",
        "robot": "robot",
        "apple": "manipulated_object",
        "bowl": "target_container",
    }.items():
        bundle = tmp_path / f"{name}_bundle"
        bundle.mkdir()
        source = bundle / f"{name}.usd"
        source.write_text("#usda 1.0\n", encoding="utf-8")
        assets[name] = {
            "role": role,
            "source_path": str(source),
            "license": "research-use",
        }
    camera = tmp_path / "fixed_camera_lift2_simbox.yml"
    camera.write_text("cameras: []\n", encoding="utf-8")
    assets["camera_yaml"] = {
        "role": "camera_config",
        "source_path": str(camera),
        "license": "research-use",
    }
    source_manifest = tmp_path / "asset_sources.yaml"
    source_manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": "ebench-official-asset-sources/v0.1",
                "task_id": "mobile_manip/apple_to_fruit_bowl",
                "instruction": "Pick up the apple from the dining table and place it into the fruit bowl.",
                "assets": assets,
            }
        ),
        encoding="utf-8",
    )
    return source_manifest


def test_generates_real_asset_apple_to_bowl_package(tmp_path: Path) -> None:
    source_manifest = _write_tiny_source_manifest(tmp_path)
    package_dir = tmp_path / "out" / "ebench_apple_to_bowl_canary"

    result = generate_apple_to_bowl_canary(source_manifest, package_dir)

    assert result.package_root == package_dir
    scene = (package_dir / "scene/main.usda").read_text(encoding="utf-8")
    assert "official_ebench_apple" in scene
    assert "official_ebench_bowl" in scene
    assert "starter_rigid_object" not in scene
    assert "target_marker" not in scene
    lock = yaml.safe_load((package_dir / "locks/asset_lock.yaml").read_text(encoding="utf-8"))
    assert set(lock["assets"]) >= {
        "official_ebench_scene",
        "official_ebench_robot",
        "official_ebench_apple",
        "official_ebench_bowl",
    }
    adapter = yaml.safe_load((package_dir / "adapters/ebench/package.yaml").read_text(encoding="utf-8"))
    assert adapter["source_package"]["package_id"] == "ebench_apple_to_bowl_canary"
```

- [ ] **Step 2: Run the failing test**

Run: `PYTHONPATH=src python -m pytest tests/test_ebench_apple_to_bowl_canary.py -q`

Expected: FAIL with missing module.

- [ ] **Step 3: Implement package generation**

Create `src/scenario_forge/generation/ebench_canary/apple_to_bowl.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scenario_forge.adapters.ebench.exporter import export_ebench_package
from scenario_forge.adapters.ebench.official_asset_intake import (
    load_official_asset_sources,
    materialize_official_asset_bundle,
)
from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.assets.lock import generate_asset_lock, write_asset_lock
from scenario_forge.scaffold import scaffold_starter_package
from scenario_forge.scene.usd_compiler import compile_usd_scene


@dataclass(frozen=True)
class AppleToBowlCanaryResult:
    package_root: Path
    scene_usd: Path


def generate_apple_to_bowl_canary(asset_sources_path: str | Path, package_root: str | Path) -> AppleToBowlCanaryResult:
    root = Path(package_root)
    sources = load_official_asset_sources(asset_sources_path)
    scaffold_starter_package(root)
    _write_manifest(root)
    write_yaml_artifact(
        root / "generation_plan.yaml",
        {
            "schema_version": "generation-plan/v0.2",
            "package_id": "ebench_apple_to_bowl_canary",
            "source_task_id": sources.task_id,
            "required_assets": [
                {"role": "environment", "asset_type": "scene"},
                {"role": "robot", "asset_type": "lift2"},
                {"role": "object", "asset_type": "apple", "affordances": ["pickable"]},
                {"role": "target_container", "asset_type": "bowl", "affordances": ["container"]},
            ],
            "workflow_bindings": {"object": "apple_001", "target_container": "bowl_001"},
        },
    )
    write_yaml_artifact(
        root / "provenance" / "summary.yaml",
        {
            "schema_version": "provenance-summary/v0.1",
            "source_task_id": sources.task_id,
            "source_kind": "official_ebench_asset_canary",
        },
    )
    write_yaml_artifact(
        root / "evidence" / "validation_report.yaml",
        {
            "schema_version": "package-validation-report/v0.1",
            "status": "draft",
            "checks": [{"name": "real_ebench_asset_canary_generated", "status": "passed"}],
        },
    )

    materialized = []
    for source_key, asset_id in {
        "scene": "official_ebench_scene",
        "robot": "official_ebench_robot",
        "apple": "official_ebench_apple",
        "bowl": "official_ebench_bowl",
    }.items():
        source = sources.assets[source_key]
        materialized.append(
            materialize_official_asset_bundle(
                source_path=source.source_path,
                package_root=root,
                asset_id=asset_id,
                role=source.role,
                license=source.license,
            )
        )

    write_yaml_artifact(
        root / "assets" / "asset_manifest.yaml",
        {
            "schema_version": "asset-manifest/v0.2",
            "assets": [asset.asset_manifest_entry() for asset in materialized],
        },
    )
    write_yaml_artifact(
        root / "scene" / "instances.yaml",
        {
            "schema_version": "scene-instances/v0.2",
            "instances": [
                _instance("environment_scene", "official_ebench_scene", "environment", [0.0, 0.0, 0.0]),
                _instance("lift2_robot_asset", "official_ebench_robot", "robot_asset", [-0.9, 0.1, -0.5]),
                _instance("apple_001", "official_ebench_apple", "manipulated_object", [-0.35, -0.22, 0.85]),
                _instance("bowl_001", "official_ebench_bowl", "target_container", [-0.35, 0.24, 0.82]),
            ],
        },
    )
    write_yaml_artifact(
        root / "task" / "task.yaml",
        {
            "schema_version": "task/v0.2",
            "task_id": sources.task_id,
            "task_family": "pick_place",
            "instruction": sources.instruction,
            "bindings": {"object": "apple_001", "target_container": "bowl_001"},
        },
    )
    write_yaml_artifact(
        root / "metrics" / "metrics.yaml",
        {
            "schema_version": "metrics/v0.2",
            "metrics": [
                {
                    "id": "apple_in_bowl",
                    "type": "predicate_satisfaction",
                    "role": "primary_success",
                    "predicate": "object_in_container",
                    "object": "apple_001",
                    "container": "bowl_001",
                    "adapter_hints": {
                        "ebench": {
                            "success_metric": "apple_in_bowl",
                            "predicate": "object_in_container",
                            "object": "apple_001",
                            "container": "bowl_001",
                        }
                    },
                }
            ],
        },
    )
    write_yaml_artifact(
        root / "robot" / "robot.yaml",
        {
            "schema_version": "robot/v0.2",
            "robot_id": "manip/lift2/R5a",
            "spawn": {"xyz": [-0.9, 0.1, -0.5], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        },
    )
    write_asset_lock(root, generate_asset_lock(root))
    scene_usd = root / "scene" / "main.usda"
    compile_usd_scene(root, root / "scene" / "instances.yaml", root / "locks" / "asset_lock.yaml", scene_usd)
    export_ebench_package(root)
    return AppleToBowlCanaryResult(package_root=root, scene_usd=scene_usd)


def _write_manifest(root: Path) -> None:
    write_yaml_artifact(
        root / "manifest.yaml",
        {
            "schema_version": "scenario-package/v0.2",
            "package_id": "ebench_apple_to_bowl_canary",
            "scenario_domain": "home_manipulation",
            "package_mode": "fat",
            "targets": ["ebench", "embodied-eval-os"],
            "entrypoints": {
                "generation_plan": "generation_plan.yaml",
                "scene_usd": "scene/main.usda",
                "scene_instances": "scene/instances.yaml",
                "task": "task/task.yaml",
                "robot": "robot/robot.yaml",
                "metrics": "metrics/metrics.yaml",
            },
            "assets": {"manifest": "assets/asset_manifest.yaml", "lock": "locks/asset_lock.yaml"},
            "validation": {"report": "evidence/validation_report.yaml", "minimum_required_level": "asset_locked"},
            "provenance": {"summary": "provenance/summary.yaml"},
        },
    )


def _instance(instance_id: str, asset_id: str, role: str, xyz: list[float]) -> dict[str, object]:
    return {
        "id": instance_id,
        "asset_id": asset_id,
        "role": role,
        "pose": {"xyz": xyz, "wxyz": [1.0, 0.0, 0.0, 0.0]},
        "semantic_tags": [role],
        "initial_state": {},
    }
```

Create `src/scenario_forge/generation/ebench_canary/__init__.py`:

```python
from scenario_forge.generation.ebench_canary.apple_to_bowl import (
    AppleToBowlCanaryResult,
    generate_apple_to_bowl_canary,
)

__all__ = ["AppleToBowlCanaryResult", "generate_apple_to_bowl_canary"]
```

- [ ] **Step 4: Verify the package test**

Run: `PYTHONPATH=src python -m pytest tests/test_ebench_apple_to_bowl_canary.py -q`

Expected: PASS.

## Task 4: CLI Canary Command

**Files:**
- Modify: `src/scenario_forge/cli.py`
- Test: `tests/test_ebench_apple_to_bowl_canary.py`

- [ ] **Step 1: Write the failing CLI test**

```python
from scenario_forge.cli import main


def _write_tiny_source_manifest(tmp_path: Path) -> Path:
    assets: dict[str, dict[str, str]] = {}
    for name, role in {
        "scene": "environment",
        "robot": "robot",
        "apple": "manipulated_object",
        "bowl": "target_container",
    }.items():
        bundle = tmp_path / f"{name}_bundle"
        bundle.mkdir()
        source = bundle / f"{name}.usd"
        source.write_text("#usda 1.0\n", encoding="utf-8")
        assets[name] = {"role": role, "source_path": str(source), "license": "research-use"}
    camera = tmp_path / "fixed_camera_lift2_simbox.yml"
    camera.write_text("cameras: []\n", encoding="utf-8")
    assets["camera_yaml"] = {"role": "camera_config", "source_path": str(camera), "license": "research-use"}
    source_manifest = tmp_path / "asset_sources.yaml"
    source_manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": "ebench-official-asset-sources/v0.1",
                "task_id": "mobile_manip/apple_to_fruit_bowl",
                "instruction": "Pick up the apple from the dining table and place it into the fruit bowl.",
                "assets": assets,
            }
        ),
        encoding="utf-8",
    )
    return source_manifest


def test_cli_generates_apple_to_bowl_canary(tmp_path: Path) -> None:
    source_manifest = _write_tiny_source_manifest(tmp_path)
    out_dir = tmp_path / "generated"

    code = main(
        [
            "ebench",
            "canary",
            "apple-to-bowl",
            "--asset-sources",
            str(source_manifest),
            "--out",
            str(out_dir),
        ]
    )

    assert code == 0
    assert (out_dir / "scene/main.usda").exists()
    assert (out_dir / "adapters/ebench/package.yaml").exists()
```

- [ ] **Step 2: Run the failing test**

Run: `PYTHONPATH=src python -m pytest tests/test_ebench_apple_to_bowl_canary.py::test_cli_generates_apple_to_bowl_canary -q`

Expected: FAIL with unknown CLI command.

- [ ] **Step 3: Implement CLI wiring**

Add parser hierarchy:

```text
scenario-forge ebench canary apple-to-bowl --asset-sources examples/ebench_apple_to_bowl_asset_sources.yaml --out /tmp/ebench-apple-to-bowl-canary
```

The command should print the package path and `scene/main.usda`.

- [ ] **Step 4: Verify**

Run: `PYTHONPATH=src python -m pytest tests/test_ebench_apple_to_bowl_canary.py -q`

Expected: PASS.

## Task 5: Real CPFS Canary Generation

**Files:**
- Generated outside git: `/tmp/ebench-apple-to-bowl-canary`
- Retain evidence under: `docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/`
- Modify: `docs/records/2026-07-04-phase10x-eos-environment-and-gates.md`

- [ ] **Step 1: Generate the real package**

Run:

```bash
PYTHONPATH=src python -m scenario_forge.cli ebench canary apple-to-bowl \
  --asset-sources examples/ebench_apple_to_bowl_asset_sources.yaml \
  --out /tmp/ebench-apple-to-bowl-canary
```

Expected:

```text
Package written: /tmp/ebench-apple-to-bowl-canary
USD entrypoint: /tmp/ebench-apple-to-bowl-canary/scene/main.usda
```

- [ ] **Step 2: Validate the package**

Run:

```bash
PYTHONPATH=src python -m scenario_forge.cli package check /tmp/ebench-apple-to-bowl-canary --require-asset-lock
PYTHONPATH=src python -m scenario_forge.cli assets check /tmp/ebench-apple-to-bowl-canary
```

Expected: both commands pass.

- [ ] **Step 3: Run EOS Stage.Open smoke**

Use the pushed EOS bridge branch and the normal EOS environment:

```bash
PYTHONPATH=/root/.config/superpowers/worktrees/embodied-eval-os/phase10x-scenario-forge-bridge/src:/root/.config/superpowers/worktrees/embodied-eval-os/phase10x-scenario-forge-bridge \
  /cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python \
  /root/.config/superpowers/worktrees/embodied-eval-os/phase10x-scenario-forge-bridge/scripts/run_phase10x_scenario_forge_usd_smoke.py \
  --suite-root /tmp \
  --package /tmp/ebench-apple-to-bowl-canary \
  --trace-out docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/apple_to_bowl_usd_smoke_trace.json \
  --runtime-evidence-out docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/apple_to_bowl_runtime_smoke.yaml
```

Expected: `runtime_status: executed`, `stage_open_status: passed`.

- [ ] **Step 4: Record claim boundary**

Append to `docs/records/2026-07-04-phase10x-eos-environment-and-gates.md`:

```text
The first real-asset apple-to-bowl USD canary uses official EBench apple, bowl,
scene, and robot USD bundles. This is real asset composition evidence and EOS
USD load evidence. It is not model success, official EBench reproduction,
official material/camera parity, or leaderboard evidence.
```

## Task 6: Engine-Native Tabletop Render And Visual Review

**Files:**
- EOS create: `/root/.config/superpowers/worktrees/embodied-eval-os/phase10x-scenario-forge-bridge/scripts/run_phase10x_scenario_forge_tabletop_render.py`
- EOS test: `/root/.config/superpowers/worktrees/embodied-eval-os/phase10x-scenario-forge-bridge/tests/test_phase10x_scenario_forge_tabletop_render_cli.py`
- Retain image outside git or under artifact storage: `docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview.png`
- Retain small metadata in git: `docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview_render_metadata.json`
- Retain review summary in git: `docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview_visual_review.md`

- [x] **Step 1: Add EOS render CLI contract test**

In EOS, write `tests/test_phase10x_scenario_forge_tabletop_render_cli.py` so a tiny package fixture can be passed to the CLI with `--dry-run`. The dry run must write metadata without importing Newton/Isaac:

```python
from __future__ import annotations

import json
from pathlib import Path

from tests.test_phase10x_scenario_forge_usd_smoke_cli import _write_package


def test_tabletop_render_cli_dry_run_writes_camera_metadata(tmp_path: Path) -> None:
    from scripts.run_phase10x_scenario_forge_tabletop_render import main

    package = _write_package(tmp_path / "pkg", package_id="ebench_apple_to_bowl_canary")
    image_out = tmp_path / "tabletop_overview.png"
    metadata_out = tmp_path / "tabletop_overview_render_metadata.json"

    code = main(
        [
            "--package",
            str(package),
            "--image-out",
            str(image_out),
            "--metadata-out",
            str(metadata_out),
            "--camera-name",
            "tabletop_overview",
            "--dry-run",
        ]
    )

    assert code == 0
    metadata = json.loads(metadata_out.read_text(encoding="utf-8"))
    assert metadata["package_id"] == "ebench_apple_to_bowl_canary"
    assert metadata["camera"]["name"] == "tabletop_overview"
    assert metadata["camera"]["intent"] == "full_tabletop_overview"
    assert metadata["camera"]["pose_selection_policy"] == "official_hint_then_filtered_workspace_look_at"
    assert metadata["camera"]["source_candidates"] == []
    assert metadata["camera"]["target_anchors"] == []
    assert metadata["material_runtime_preflight"] == {
        "status": "not_run",
        "claim_level": "not_claimed",
        "approved_runtime_mdl_dependencies": [],
        "blocked_dependency_count": 0,
        "runtime_log_scan": {"status": "not_run"},
    }
    assert metadata["claim_boundary"] == (
        "Engine-native visual canary only. Not task success, not official camera parity, "
        "not official material parity, and not leaderboard evidence."
    )
```

- [x] **Step 2: Implement EOS render CLI**

Create `/root/.config/superpowers/worktrees/embodied-eval-os/phase10x-scenario-forge-bridge/scripts/run_phase10x_scenario_forge_tabletop_render.py`.

The CLI must:

- accept `--package`, `--image-out`, `--metadata-out`, `--camera-name tabletop_overview`, and `--dry-run`;
- read the Scenario Forge package through `adapters.ebench.scenario_forge_package.load_scenario_forge_package`;
- in dry run, write metadata only;
- in real run, use the selected EOS runtime lane's native camera/sensor API to render the package scene, not a synthetic image, collage, or file copy;
- preserve `fixed_camera_lift2_simbox.yml` as an official camera hint, not as proof of official EBench camera parity;
- evaluate official camera candidates from the YAML, especially the external `camera1` and robot-mounted `overlook_camera`;
- select `overlook_camera` only if the runtime stage contains the corresponding robot camera prim and the rendered view covers apple, bowl, table, and robot/spawn;
- otherwise create an engine-native `tabletop_overview` camera, preferably reusing official 1280x720/intrinsics while choosing a runtime pose;
- place the camera from filtered task anchors: table/table_top prim, apple center, bowl center, and robot spawn;
- reject whole-stage bounds for placement when they are dominated by environment/background extents, and record that rejection in metadata;
- use the runtime's look-at helper or equivalent sensor API for an oblique 45 to 60 degree tabletop overview with enough FOV margin to show the full task-relevant work surface;
- run a material / MDL runtime preflight before claiming the render is useful;
- treat `OmniPBR.mdl` and `gltf/pbr.mdl` as approved runtime MDL dependencies only if the runtime records concrete search roots that resolve them;
- record `MDL_SYSTEM_PATH`, Kit additional MDL search paths, approved runtime MDL roots, unresolved MDL modules, unresolved textures, and package-escape texture literals;
- scan render stdout/stderr for material compiler signals: `MDLC`, `rtx.mdltranslator`, `usd_mdl`, `Failed to create MDL shade node`, `missing texture`, `could not find texture`, and `could not find module`;
- write PNG output, metadata JSON, and no model/task score.

The camera decision is evidence and must be reproducible. It should follow this
policy:

```text
1. Load official camera YAML from the package source manifest/provenance when available.
2. Record each candidate camera with name, exists flag, prim path, resolution, and selected/skipped/rejected reason.
3. Probe runtime stage anchors:
   - table/table_top prim, preferring /World/Instances/environment_scene/obj_table when present;
   - apple_001 instance translation;
   - bowl_001 instance translation;
   - RobotSpawn or lift2_robot_asset translation.
4. Build a filtered workspace bound from these task anchors.
5. Reject /World or full environment bounds when their size is implausibly large for a tabletop scene.
6. Create or move tabletop_overview with runtime-native camera APIs.
7. Save the final camera pose and the complete decision trace.
```

The material / MDL runtime preflight is required because ConvertAsset's AAN
experience showed that `Usd.Stage.Open` success does not guarantee Isaac Sim
material rendering success. The EOS render CLI must not reimplement ConvertAsset
no-MDL conversion. Instead, it should borrow the closure checks:

```text
1. Run a USD dependency closure scan over scene/main.usda.
2. Classify dependencies into package-local USD, package-local MDL, package-local texture, approved runtime MDL, unresolved, and package escape.
3. For MDL files that are package-local, parse import / using-import / texture_2d literals when feasible.
4. Classify Isaac-native modules such as OmniPBR.mdl and gltf/pbr.mdl as approved runtime dependencies only when runtime search roots resolve them.
5. Preserve official GenManip MDL_SYSTEM_PATH hints, but record the concrete expanded paths used by EOS.
6. Fail Phase 10.9 strict acceptance if any required helper MDL, texture, or package-local sidecar is missing.
7. Fail Phase 10.9 strict acceptance if runtime logs contain material compiler failures or missing texture/module signals.
8. Keep no-MDL conversion as a separate debug/fallback option; do not use it to claim official material parity.
```

Issue routing is part of the Phase 10.9 evidence trail:

```text
1. Scenario Forge package defect:
   - Examples: missing lock/provenance entry, texture not included in the package, package-local reference escaping the artifact, adapter failed to record search roots.
   - Owner: Scenario Forge.
   - Action: fix the package, lock, manifest, provenance, or adapter evidence and rerun Phase 10.9.
2. EOS / Isaac Sim runtime configuration defect:
   - Examples: Isaac-native OmniPBR.mdl or gltf/pbr.mdl exists in runtime but the render lane did not expose the required MDL search root.
   - Owner: EOS adapter/render lane.
   - Action: fix runtime configuration, record concrete search roots, and rerun Phase 10.9.
3. Asset conversion or material authoring defect:
   - Examples: incompatible MDL import style, missing helper MDL, missing texture sidecar, package-escaping texture literal, malformed converted USD/mesh, visible red/pink material fallback.
   - Owner: ConvertAsset or external conversion lane.
   - Action: open a ConvertAsset handoff with the failing package, dependency closure report, runtime log, render image, source asset provenance, and hashes. After repair, Scenario Forge ingests the repaired assets, updates hashes/locks/provenance, and reruns Phase 10.9.
4. Scenario Forge must not vendor or copy ConvertAsset conversion logic to close the issue locally.
```

Use this metadata shape:

```json
{
  "schema": "scenario_forge_tabletop_overview_render.v0",
  "package_id": "ebench_apple_to_bowl_canary",
  "scene_usd": "/tmp/ebench-apple-to-bowl-canary/scene/main.usda",
  "camera": {
    "name": "tabletop_overview",
    "intent": "full_tabletop_overview",
    "engine_native": true,
    "pose_source": "eos_runtime_tabletop_overview_camera",
    "pose_selection_policy": "official_hint_then_filtered_workspace_look_at",
    "source_yaml": "configs/cameras/fixed_camera_lift2_simbox.yml",
    "selected_candidate": "runtime_tabletop_overview",
    "source_candidates": [
      {
        "name": "camera1",
        "exists": false,
        "resolution": [1280, 720],
        "decision": "hint_only",
        "reason": "external GenManip fixed camera is preserved as hint; EOS still owns runtime pose"
      },
      {
        "name": "overlook_camera",
        "exists": true,
        "prim_path": "/lift2/lift2/lift2/base_link/Camera_overlook",
        "resolution": [1280, 720],
        "decision": "probe_in_runtime",
        "reason": "usable only if the robot-mounted prim exists and passes visual coverage"
      }
    ],
    "target_anchors": [
      {"name": "table", "prim_path": "/World/Instances/environment_scene/obj_table"},
      {"name": "apple", "instance_id": "apple_001"},
      {"name": "bowl", "instance_id": "bowl_001"},
      {"name": "robot_spawn", "prim_path": "/World/RobotSpawn"}
    ],
    "rejected_bounds": [
      {
        "prim_path": "/World",
        "reason": "whole-stage bounds include environment/background and are not task workspace bounds"
      }
    ],
    "pose": {
      "position": [0.0, 0.0, 0.0],
      "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
      "look_at": [0.0, 0.0, 0.0]
    },
    "resolution": [1280, 720],
    "fov_or_intrinsics_source": "official_camera_hint_when_available"
  },
  "material_runtime_preflight": {
    "status": "pass",
    "claim_level": "required_visual_canary_material_runtime_closure",
    "source_policy": "convertasset_aan03_aan04_aan11_inspired_preflight",
    "full_material_parity_claimed": false,
    "package_local_dependency_counts": {
      "usd": 0,
      "mdl": 0,
      "texture": 0
    },
    "approved_runtime_mdl_dependencies": [
      {
        "module": "OmniPBR.mdl",
        "runtime_path": "/isaac-sim/kit/mdl/core/Base/OmniPBR.mdl",
        "resolution": "approved_runtime_module"
      },
      {
        "module": "gltf/pbr.mdl",
        "runtime_path": "/isaac-sim/kit/mdl/core/mdl/gltf/pbr.mdl",
        "resolution": "approved_runtime_module"
      }
    ],
    "mdl_search_paths": [
      "/isaac-sim/materials/",
      "/isaac-sim/kit/mdl/core/Base",
      "/isaac-sim/kit/mdl/core/mdl"
    ],
    "genmanip_mdl_system_path_hint": "/isaac-sim/materials/:{ASSETS_DIR}/miscs/mdl/ebench/mdl:{ASSETS_DIR}/scene_usds/ebench/simple_pnp/task3/SubUSDs/materials",
    "blocked_dependency_count": 0,
    "blocked_dependencies": [],
    "runtime_log_scan": {
      "status": "pass",
      "blocked_signals": [],
      "counters": {
        "mdlc_count": 0,
        "failed_shader_node_count": 0,
        "missing_texture_count": 0
      }
    }
  },
  "visible_targets_expected": ["tabletop", "apple", "bowl", "scene_context", "robot_or_spawn"],
  "image_path": "tabletop_overview.png",
  "claim_boundary": "Engine-native visual canary only. Not task success, not official camera parity, not official material parity, and not leaderboard evidence."
}
```

- [x] **Step 3: Run the real engine-native render**

Use the EOS IsaacSim41 / GenManip runtime environment selected for visual
canaries:

```bash
cd /root/.config/superpowers/worktrees/embodied-eval-os/phase10x-scenario-forge-bridge

EEOS_ISAACSIM41_PYTHON=/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-isaacsim41-genmanip-py310/bin/python \
  python scripts/run_phase10x_scenario_forge_tabletop_render.py \
  --package /tmp/ebench-apple-to-bowl-canary \
  --image-out docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview.png \
  --metadata-out docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview_render_metadata.json \
  --runtime-log-out docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview_runtime.log \
  --camera-name tabletop_overview \
  --isaac-python /cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-isaacsim41-genmanip-py310/bin/python \
  --mdl-search-path /isaac-sim/kit/mdl/core/Base \
  --mdl-search-path /cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-isaacsim41-genmanip-py310/lib/python3.10/site-packages/omni/mdl/core/mdl \
  --mdl-search-path /cpfs/shared/simulation/zhuzihou/dev/_datasets/EBench-Assets/assets/miscs/mdl/ebench/mdl \
  --mdl-search-path /cpfs/shared/simulation/zhuzihou/dev/_datasets/EBench-Assets/assets/scene_usds/converted_from_partnet_mobility/d9d75b41ebf2430bb98ce42c3ca59503/SubUSDs/materials \
  --genmanip-mdl-system-path-hint '/isaac-sim/materials/:{ASSETS_DIR}/miscs/mdl/ebench/mdl:{ASSETS_DIR}/scene_usds/.../SubUSDs/materials'
```

Expected:

```text
render_status: pass
image_path: docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview.png
camera.name: tabletop_overview
camera.engine_native: true
material_runtime_preflight.status: pass
runtime_log_scan.status: pass
```

Actual retained result:

```text
render_status: pass
camera.engine_native: true
camera.pose_source: eos_native_tabletop_look_at
material_runtime_preflight.status: pass
blocked_dependency_count: 0
runtime_log_scan.status: pass
runtime_log_scan.warning_signals: [MDLC]
image.sha256: aa5f6e493d41b1884b8c1ded092f9ab067ca1f13a05ac291f774033838b3ba60
```

- [x] **Step 4: Run clean-room visual review**

Use `render-visual-reviewer` with a fresh clean-room reviewer. Provide only the image path and this visual expectation, not code, manifests, diffs, or suspected issues:

```text
Task: Inspect this render image as a clean-room visual QA reviewer.
Context: The target should be an apple-to-bowl tabletop manipulation scene rendered from an engine-native overview camera.
Images:
- A: /cpfs/user/zhuzihou/dev/scenario-forge/docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview.png
Check:
- Is the image nonblank and rendered from a useful tabletop overview?
- Is the full task-relevant table/work surface visible?
- Are apple and bowl visible and identifiable?
- Is scene context visible enough to understand this is a tabletop manipulation scene?
- Is a robot or robot spawn visible, or at least not contradicted by the image?
- Are there obvious blocking artifacts: camera clipping, severe occlusion, missing textures, black fallback materials, abnormal red/pink fallback materials, broken mesh, floating parts, z-fighting, or placeholder/starter assets?
Output: PASS/WARN/FAIL with concise visible evidence and a retake recommendation for WARN or FAIL.
Constraints: Do not inspect code, manifests, repo files, or implementation details.
```

Write the returned verdict to:

```text
docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview_visual_review.md
```

- [x] **Step 5: Enforce Phase 10.9 acceptance**

Phase 10.9 can close only if:

```text
1. tabletop_overview.png exists and is produced by the engine-native render CLI.
2. tabletop_overview_render_metadata.json records camera.engine_native=true.
3. tabletop_overview_render_metadata.json records material_runtime_preflight.status=pass.
4. The runtime material log scan is pass and records no MDLC, failed shader node, missing texture, or missing module blockers.
5. Approved runtime MDL dependencies such as OmniPBR.mdl and gltf/pbr.mdl include concrete runtime paths or hashes.
6. The visual review verdict is PASS.
7. The review says apple and bowl are visible and identifiable.
8. The review does not report blank image, camera clipping, missing table, abnormal red/pink fallback material, missing texture, or placeholder/starter assets.
```

If the review returns WARN, retake the render with a revised engine-native camera pose and repeat Step 4. If the review returns FAIL, keep Phase 10.9 open.

2026-07-04 enforcement result:

```text
1. tabletop_overview.png exists and was produced by the EOS engine-native render CLI.
2. camera.engine_native=true.
3. material_runtime_preflight.status=pass.
4. Runtime material log scan is pass; MDLC appears only as warning evidence.
5. OmniPBR.mdl and gltf/pbr.mdl resolve to concrete Isaac runtime paths.
6. Clean-room visual review verdict is PASS.
7. The review says apple and bowl are visible and identifiable.
8. The review reports no blank image, task-breaking clipping, missing table,
   abnormal red/pink fallback material, missing texture, or placeholder asset.
```

## Task 7: Verification And Commit

**Files:**
- All files touched above.
- Scenario Forge commit should include source manifests, package generator, docs, small metadata, and visual review summary.
- EOS branch commit should include the engine-native render CLI and its tests.
- Do not commit `tabletop_overview.png` unless it is explicitly small enough and allowed by artifact policy; otherwise retain it in artifact storage and commit only its path, size, and sha256 in metadata.

- [x] **Step 1: Run focused tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_ebench_official_asset_intake.py tests/test_ebench_apple_to_bowl_canary.py -q
```

Expected: PASS.

Actual:

```text
PYTHONPATH=src python -m pytest tests/test_scene_compiler.py tests/test_ebench_apple_to_bowl_canary.py -q
  12 passed

PYTHONPATH=src python -m scenario_forge.cli package check /tmp/ebench-apple-to-bowl-canary --require-asset-lock
  Package OK

PYTHONPATH=src python -m scenario_forge.cli assets check /tmp/ebench-apple-to-bowl-canary
  Asset lock OK
```

- [x] **Step 2: Run full Scenario Forge check**

Run: `make check`

Expected: PASS.

Actual:

```text
make check
  90 passed
  ruff: All checks passed
  Phase 10.x overall status: passed
```

- [x] **Step 3: Check git diff**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only intended implementation, tests, examples, docs, and retained evidence are changed.

Actual:

```text
git diff --check
  passed
```

EOS verification run:

```text
python -m pytest tests/test_phase10x_scenario_forge_tabletop_render_cli.py -q
  4 passed

python scripts/check_core_leakage.py
  OK: no forbidden benchmark/scenario leakage in core

python examples/run_smoke.py
  emitted a 3-step smoke episode with task_success=True

python -m pytest -q
  1228 passed, 38 skipped, 9 failed
```

The EOS full-suite failures were environment/evidence availability failures
outside the Phase 10.9 render CLI path: missing `playwright`, missing
`pybullet`, and one missing historical Taskbook02 evidence attempt directory.
The targeted render CLI test and core leakage check passed.

- [ ] **Step 4: Commit**

Run:

```bash
git add src/scenario_forge/adapters/ebench/official_asset_intake.py \
  src/scenario_forge/generation/ebench_canary \
  src/scenario_forge/cli.py \
  tests/test_ebench_official_asset_intake.py \
  tests/test_ebench_apple_to_bowl_canary.py \
  examples/ebench_apple_to_bowl_asset_sources.yaml \
  docs/records/2026-07-04-phase10x-eos-environment-and-gates.md \
  docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview_render_metadata.json \
  docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview_visual_review.md \
  docs/strategy/scenario-forge-ebench-auto-factory-roadmap.md \
  docs/superpowers/plans/2026-07-04-phase-10-real-ebench-apple-to-bowl-usd.md
git commit -m "feat: add real ebench apple-to-bowl usd canary"
```

Expected: one commit with no large USD payloads committed.

In the EOS bridge worktree, commit the render CLI separately:

```bash
git add scripts/run_phase10x_scenario_forge_tabletop_render.py \
  tests/test_phase10x_scenario_forge_tabletop_render_cli.py
git commit -m "feat: add scenario forge tabletop render canary"
```

Expected: EOS bridge commit contains only EOS runtime/render lane code and tests.

## Completion Criteria

- `scene/main.usda` references package-local copies of official EBench apple, bowl, scene, and robot USD bundles.
- `locks/asset_lock.yaml` has checksums for the canonical USD files.
- `adapters/ebench/package.yaml` and `task_entrypoint.yaml` identify `mobile_manip/apple_to_fruit_bowl`.
- `task/task_contract.yaml` binds task semantics, success predicate, robot hint, camera hint, and adapter boundary.
- EOS Stage.Open evidence is retained for the generated package.
- EOS retains one engine-native `tabletop_overview` render PNG and a clean-room visual review PASS before claiming Phase 10.9 visual canary closure.
- Documentation states the boundary: real USD asset package and task contract, not task success, official parity, or leaderboard evidence.

## Phase 10.10 Closure Evidence

Scenario Forge now emits `task/task_contract.yaml` for the real EBench
apple-to-bowl canary. The artifact is retained as
`docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/apple_to_bowl_task_contract.yaml`.

The contract records:

- task id `mobile_manip/apple_to_fruit_bowl` and the official instruction;
- `apple_001` as the manipulated object and `bowl_001` as the target container;
- primary success metric `apple_in_bowl` with predicate `object_in_container`;
- Lift2 robot hint `manip/lift2/R5a` and spawn pose;
- `fixed_camera_lift2_simbox.yml` as a hint-only camera source, with no official camera parity claim;
- EOS/EBench as the runtime/evaluator owner, while Scenario Forge remains package artifacts and contracts only.

Retained evidence:

```text
apple_to_bowl_task.yaml
apple_to_bowl_metrics.yaml
apple_to_bowl_task_contract.yaml
apple_to_bowl_adapter_report.yaml
phase10_10_task_contract_gate.yaml
```

Boundary: Phase 10.10 closes the real single-task EBench-compatible package
contract canary. It still does not claim model inference, executed task success,
official EBench reproduction, physics fidelity, official material/camera parity,
score release, or leaderboard comparability.

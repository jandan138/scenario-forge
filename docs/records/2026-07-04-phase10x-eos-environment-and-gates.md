# 2026-07-04 Phase 10.x EOS Environment and Gates

## Question

Before Phase 11 starts, identify which Phase 10.x gates should close the gap
between Scenario Forge's static suite factory and a complete USD task package
that EBench / embodied-eval-os can consume.

Also confirm which conda environment EOS uses.

## EOS Environment Evidence

Read-only inspection of `/cpfs/user/zhuzihou/dev/embodied-eval-os` found:

- `AGENTS.md:122-127` declares the project-owned EOS environment:
  `/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310`.
- `README.md:185-191` instructs DSW users to export `EEOS_ENV_ROOT`,
  `EEOS_PYTHON`, and `CHECK_PYTHON` to the same environment.
- `docs/reference/environment.md:21-26` states that `EEOS_PYTHON` is the
  interpreter path used for direct checks.
- `AGENTS.md:169-184` separates IsaacSim41 runtime work from the normal
  project environment.
- `scripts/run_taskbook03b_r2_p2_newton_runtime_capability_probe.py:38-43`
  defaults Newton / EBench runtime probing to the shared experimental runtime
  environment.

Local executable checks on 2026-07-04:

```text
/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python
  Python 3.10.20

/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-isaacsim41-py310/bin/python
  Python 3.10.20

/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-newton-ebench-experimental-py310/bin/python
  Python 3.10.20

/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-sidecar-openpi-ebench-py311/bin/python
  Python 3.11.15
```

Decision:

- Use `EEOS_PYTHON` from `embodied-eval-os-py310` for EOS static import gates.
- Use backend-specific runtime environments only for runtime smoke gates.
- Treat OpenPI sidecars as model-lane dependencies, not as the global EOS check
  environment.

## Phase 10.x Plan

Phase 10 is complete for suite construction-quality evidence. The pre-Phase-11
work should be tracked as:

```text
10.1 Golden USD Task Pack Freeze
10.2 Asset / External Input Hardening
10.3 EOS Static Import Contract Gate
10.4 Runtime Smoke Evidence Gate
10.5 Release Candidate Gate
```

The purpose is to prove that a small USD-bearing task package can be generated,
checked, exported, statically imported by EOS, and smoke-tested in at least one
backend lane before building UI surfaces or automated release gates.

The gates must preserve Scenario Forge's hard boundary: no episode runners,
model adapters, simulator SDK imports, leaderboards, or benchmark reports in
this repo.

## Runtime Smoke Audit

On 2026-07-04, a live EOS / GenManip smoke was run from the EOS repository to
separate backend readiness from Scenario Forge package consumption.

Environment:

```text
EOS repo:
  /cpfs/user/zhuzihou/dev/embodied-eval-os

EOS static/check Python:
  /cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python

GenManip / IsaacSim runtime Python:
  /cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-isaacsim41-genmanip-py310/bin/python

GenManip root:
  /cpfs/shared/simulation/zhuzihou/dev/GenManip

Task config:
  /cpfs/shared/simulation/zhuzihou/dev/GenManip/configs/tasks/ebench/mobile_manip/test_mini/apple_to_fruit_bowl.yml
```

Findings:

```text
1. Stock adapters.ebench.smoke_run reached /docs but failed /reset with HTTP 500.
   Root cause: GenManip requires /start_new_job before /reset.

2. After manual /start_new_job, stock adapters.ebench.smoke_run reached /reset
   and /reset_result but returned a structured skip.
   Root cause: the adapter has RESET_RESULT_POLL_TIMEOUT_S=30.0, while cold
   IsaacSim / GenManip reset needs a longer window. Existing EOS live-runner
   records use 900 seconds for this path.

3. A one-off call using the same EOS adapter module, manual /start_new_job,
   and RESET_RESULT_POLL_TIMEOUT_S=900.0 executed a live native GenManip smoke.
   It produced runtime_status=executed with two trace steps.

4. The executed trace initially exposed a TraceStore path issue because the
   native GenManip episode_id contains slash separators. The retained evidence
   was saved with a safe filename; the trace content keeps the original
   episode_id.
```

Retained evidence:

```text
docs/records/evidence/2026-07-04-phase10x-eos-native-smoke/eos_genmanip_native_smoke_trace.json

episode_id:
  ebench/scenario_forge_phase10x_smoke_20260704_r4_job/ebench/mobile_manip/apple_to_fruit_bowl_test_mini/000

runtime_status:
  executed

steps:
  2

asset_provenance:
  genmanip_runtime
```

Boundary:

This is positive evidence that the EOS / GenManip backend lane can execute a
native EBench task in the local runtime environment. It is not yet Phase 10.4
completion evidence for Scenario Forge, because the retained trace says
`asset_provenance=genmanip_runtime` and the task came from a GenManip native
config, not from a Scenario Forge-generated USD task package.

## Package-Linked RC Evidence

The package-linked bridge was then implemented in EOS under
`adapters/ebench/`, keeping runtime/package consumption outside Scenario Forge.
The retained Scenario Forge evidence is:

```text
docs/records/evidence/2026-07-04-phase10x-package-linked-runtime-smoke/
  phase10x_source_golden_task_pack.yaml
  phase10x_rc_imported_golden_task_pack.yaml
  phase10x_rc_external_input_hardening.yaml
  phase10x_rc_eos_static_import.yaml
  phase10x_rc_runtime_smoke.yaml
  phase10x_rc_imported_runtime_smoke.yaml
  phase10x_rc_usd_smoke_trace.json
  phase10x_rc_gate.yaml
```

Observed result:

```text
suite_id:
  phase10x_rc_suite

package_count:
  50

source golden evidence:
  phase10x_golden_suite, package_count=10, status=passed

runtime lane:
  eos_usd_stage_open_smoke

package consumed by EOS:
  phase10x_rc_suite_000

runtime_status:
  executed

stage_open_status:
  passed

Phase 10.x strict result:
  passed
```

Boundary:

This closes the Phase 10.4 / 10.5 package-handoff gate for a package-linked USD
load smoke. It proves that EOS can read a Scenario Forge package descriptor,
resolve the package's `scene/main.usda`, `locks/asset_lock.yaml`,
`adapters/ebench/package.yaml`, and `adapters/ebench/task_entrypoint.yaml`,
open the USD stage, and feed the resulting package-linked evidence back into a
50-task Phase 10.5 RC gate.

It still does not prove model quality, task success, physics fidelity, official
EBench reproduction, leaderboard comparability, or runtime-grade robot/control
bindings.

## Next: Phase 10.6-10.10 Real EBench Apple-To-Bowl USD Canary

The next pre-Phase-11 slice should not broaden to many tasks. It should use one
specific EBench task, `mobile_manip/apple_to_fruit_bowl`, to prove that Scenario
Forge can generate a package whose USD entrypoint references real official EBench
assets instead of placeholder USD stubs.

Evidence already available in EOS:

```text
source evidence:
  /cpfs/user/zhuzihou/dev/embodied-eval-os/docs/records/evidence/2026-07-03-taskbook03b-r2-real-newton-ebench-apple-to-bowl/newton_task_asset_manifest.json

task:
  mobile_manip/apple_to_fruit_bowl

instruction:
  Pick up the apple from the dining table and place it into the fruit bowl.

official assets resolved:
  scene: /cpfs/shared/simulation/zhuzihou/dev/_datasets/EBench-Assets/assets/scene_usds/ebench/simple_pnp/task4/scene.usd
  robot: /cpfs/shared/simulation/zhuzihou/dev/_datasets/EBench-Assets/assets/robot_usds/lift2/robot.usd
  apple: /cpfs/shared/simulation/zhuzihou/dev/_datasets/EBench-Assets/assets/object_usds/custom_usd/ebench_usds/apple/ready/5948de6770a5491ea158cd9e921ebce9/5948de6770a5491ea158cd9e921ebce9.usd
  bowl: /cpfs/shared/simulation/zhuzihou/dev/_datasets/EBench-Assets/assets/object_usds/custom_usd/ebench_usds/bowl/ready/307689f1c6884e1bb85bb20f00fef294/307689f1c6884e1bb85bb20f00fef294.usd
  camera: /cpfs/shared/simulation/zhuzihou/dev/GenManip/configs/cameras/fixed_camera_lift2_simbox.yml
```

Planned gates:

```text
10.6 Official EBench asset intake freeze:
  write a small source manifest with paths, hashes, roles, license/use
  restrictions, and provenance. Do not commit USD payloads.

10.7 Single-task real-asset USD package:
  generate /tmp/ebench-apple-to-bowl-canary with package-local materialized
  official asset bundles and scene/main.usda references to scene, robot, apple,
  and bowl. This is the first point where a real apple-to-bowl USD should exist.

10.8 EOS package-linked real-asset USD smoke:
  run the EOS bridge against the generated package and retain Stage.Open evidence
  with the real official asset hashes.

10.9 Newton / EBench visual canary:
  produce a downstream runtime visual or scene-inspection evidence record proving
  the runtime lane sees the real asset geometry. This is still not task success.
  Acceptance should prefer an engine-native `tabletop_overview` camera / sensor
  placed by the EOS runtime lane, not a synthetic collage or code-only check. The
  retained PNG should show the full tabletop work surface with apple, bowl, scene
  context, and robot / robot spawn visible. Retain camera pose, engine/runtime,
  package id, scene USD, and asset hashes beside the image, then run a clean-room
  visual review over only the image and visual expectation. Phase 10.9 strict
  pass requires the visual review verdict to be PASS.

  Phase 10.9 camera placement should be decided by a recorded selection policy,
  not by an untracked manual pose. The policy starts from the official GenManip
  `fixed_camera_lift2_simbox.yml` camera hints, then lets the EOS runtime place
  an engine-native `tabletop_overview` camera if those hints do not directly
  provide a useful product overview.

  Local research on 2026-07-04 found these constraints:
  - `fixed_camera_lift2_simbox.yml` contains an external `camera1`
    (`exists: false`, 1280x720, position approximately
    `[0.2807, -0.0233, 1.6858]`) plus robot-mounted `left_camera`,
    `right_camera`, `top_camera`, and `overlook_camera` entries
    (`exists: true`). `overlook_camera` is a useful named candidate, but it is
    attached to the Lift2 robot prim path, so EOS must only reuse it when that
    prim exists in the runtime stage.
  - GenManip creates `exists: true` cameras under `/World/<uuid><prim_path>` and
    `exists: false` cameras as external fixed cameras. Therefore Scenario Forge
    should preserve the YAML as a camera hint, while EOS owns the runtime camera
    creation and final pose.
  - The apple-to-bowl task config uses the same camera YAML, robot base
    `[-0.9, 0.1, -0.5]`, and task layout ranges around the table. Earlier
    provisional Scenario Forge canary instances used hand-entered object
    heights, but the current canary derives the object poses from official USD
    bboxes and the GenManip tabletop convention: apple center
    `[-0.35, -0.22, 0.046444]`, bowl center `[-0.35, 0.24, 0.050375]`,
    object orientation `[0.5, 0.5, 0.5, 0.5]`, and relative scale `0.8`.
  - A USD BBoxCache pass over `/tmp/ebench-apple-to-bowl-canary/scene/main.usda`
    showed that whole-stage bounds are not suitable for camera placement: the
    environment scene expands `/World` to roughly a 516 m cube, while the task
    table prim `/World/Instances/environment_scene/obj_table` is roughly
    0.9 m by 1.6 m. Object bounds can also be misleading if an asset has unusual
    origin or scale metadata, so object instance translations are safer semantic
    anchors than raw object extents.

  The Phase 10.9 render CLI should therefore use this order:
  1. Record all official camera candidates from `fixed_camera_lift2_simbox.yml`
     and mark whether each candidate was selected, skipped, or rejected.
  2. Prefer `overlook_camera` only when the runtime stage contains its robot
     camera prim and it can see apple, bowl, table, and robot/spawn.
  3. Otherwise create an EOS-native `tabletop_overview` camera, reusing the
     official 1280x720 overview-style resolution and camera intrinsics when
     possible, but using a new engine-native pose.
  4. Build the camera target from filtered task anchors: table top/table prim if
     present, apple center, bowl center, and robot spawn. Exclude whole-stage
     background bounds and reject any candidate workspace bound with implausible
     size, invalid range, or no task anchors.
  5. Use the runtime's native look-at camera helper, or equivalent sensor API, to
     place the camera at an oblique 45 to 60 degree tabletop overview with enough
     distance and field-of-view margin to keep the full task-relevant work
     surface visible. The exact pose is evidence, not a hidden constant.
  6. If visual review reports WARN or FAIL for clipping, missing apple/bowl,
     missing table, severe occlusion, or placeholder assets, retake with a
     revised engine-native pose and keep Phase 10.9 open until the review passes.

  The render metadata must include camera name, source YAML, selected candidate,
  skipped/rejected candidate reasons, target anchors, final pose, FOV or
  intrinsics, resolution, engine/runtime, package id, scene USD, asset hashes, and
  the boundary that this is a visual canary only. It must not claim official
  EBench camera parity.

  Phase 10.9 must also include a material / MDL runtime preflight before the
  visual review. ConvertAsset's AAN experience shows that USD composition
  success is not enough for Isaac Sim rendering: `Usd.Stage.Open` can pass while
  MDL helper modules, texture literals, or shader compiler paths still fail at
  render time and produce fallback red/pink materials.

  The 2026-07-04 ConvertAsset research relevant to this gate:
  - AAN-03 treats USD, MDL, texture, reference, payload, sublayer, variant, clip,
    and property asset dependencies as a closure problem, with missing local
    files and remote/package-escape references recorded as blockers.
  - AAN-04 records material closure at the `UsdShade` level, including bound
    material prims, source MDL assets, texture paths, channel extraction, fallback
    modes, and residual MDL evidence.
  - AAN-11 parses MDL `import`, `using ... import`, and `texture_2d(...)`
    literals. Missing helper MDL modules, package-escaping texture paths, missing
    textures, and second-order MDL dependencies are blocking unless mirrored,
    classified as approved runtime modules, or explicitly waived.
  - ConvertAsset runtime log parsing records `MDLC`, `rtx.mdltranslator`,
    `usd_mdl`, `Failed to create MDL shade node`, `missing texture`,
    `could not find texture`, and `could not find module` signals. For Phase
    10.9, plain `MDLC` compiler warnings such as `C183 unused parameter` are
    warning evidence rather than automatic blockers; MDL compiler errors,
    missing textures/modules, failed shader-node creation, or visible fallback
    red/pink materials are blockers. Prior `KooPbr` repair work shows that even
    MDL import style can break module lookup in Isaac runtimes.
  - ConvertAsset's render helpers configure MDL search paths from CLI arguments
    and `MDL_SYSTEM_PATH`, so the effective renderer environment is evidence,
    not an implicit assumption.

  A local dependency probe of the current canary found all ordinary PNG texture
  assets package-local, but `UsdUtils.ComputeAllDependencies` still reports
  unresolved `OmniPBR.mdl` and `gltf/pbr.mdl`. These are available in the Isaac
  Sim runtime (`/isaac-sim/kit/mdl/core/Base/OmniPBR.mdl` and
  `/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-isaacsim41-genmanip-py310/lib/python3.10/site-packages/omni/mdl/core/mdl/gltf/pbr.mdl`)
  rather than in the package. This matches the official GenManip task pattern,
  which sets `MDL_SYSTEM_PATH` with `/isaac-sim/materials/`,
  `{ASSETS_DIR}/miscs/mdl/ebench/mdl`, and the task scene's
  `SubUSDs/materials` directory.

  Therefore Phase 10.9 should treat `OmniPBR.mdl` and `gltf/pbr.mdl` as approved
  runtime MDL dependencies only when the EOS render lane records the concrete
  search roots that resolve them. Missing helper MDL modules, missing textures,
  package-escape texture literals, MDL compiler errors, or visible fallback
  red/pink materials keep Phase 10.9 open. This is still not an instruction to
  run ConvertAsset no-MDL conversion inside Scenario Forge; no-MDL is a separate
  debug/fallback path and cannot be used to claim official material parity.
  The resulting ownership rule is: Scenario Forge fixes package/evidence
  defects, EOS fixes runtime search-path configuration defects, and ConvertAsset
  or an external conversion lane fixes asset conversion / MDL authoring defects.
  A ConvertAsset handoff should include the failing package, dependency closure
  report, runtime material log, render image, source provenance, and asset
  hashes. Scenario Forge then consumes the repaired asset output, updates
  hashes/locks/provenance, and reruns the Phase 10.9 preflight/render/review
  rather than copying conversion logic into this repo.

  Phase 10.9 execution evidence retained on 2026-07-04:
  - EOS render CLI:
    `/root/.config/superpowers/worktrees/embodied-eval-os/phase10x-scenario-forge-bridge/scripts/run_phase10x_scenario_forge_tabletop_render.py`
  - EOS CLI tests:
    `/root/.config/superpowers/worktrees/embodied-eval-os/phase10x-scenario-forge-bridge/tests/test_phase10x_scenario_forge_tabletop_render_cli.py`
  - Final render:
    `docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview.png`
  - Render metadata:
    `docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview_render_metadata.json`
  - Runtime material log:
    `docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview_runtime.log`
  - Clean-room visual review:
    `docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview_visual_review.md`

  The retained metadata records `render_status=pass`,
  `camera.engine_native=true`, `camera.pose_source=eos_native_tabletop_look_at`,
  `material_runtime_preflight.status=pass`, approved runtime MDL dependencies
  for `OmniPBR.mdl` and `gltf/pbr.mdl`, `blocked_dependency_count=0`, no runtime
  material blockers, and `MDLC` warning evidence only. The final PNG sha256 is
  `aa5f6e493d41b1884b8c1ded092f9ab067ca1f13a05ac291f774033838b3ba60`. The
  clean-room review verdict is PASS with apple, bowl, tabletop, scene context,
  and robot/spawn visible.

10.10 EBench task contract canary:
  bind the package to the apple-to-bowl task semantics, success predicate, robot
  and camera hints, and adapter contract so it can serve as the first real task
  sample for Phase 11 review.
```

Timing:

```text
If work continues from 2026-07-04 and the CPFS EBench asset mount remains
available, Phase 10.7 should be able to produce the first real-asset
scene/main.usda on 2026-07-04 or 2026-07-05.

The safer milestone for product demonstration is Phase 10.8, targeted for
2026-07-05 to 2026-07-06, because it includes EOS package-linked Stage.Open
evidence.

The first visually useful product screenshot should be Phase 10.9, targeted
around 2026-07-06. It should be a renderer-native tabletop overview image and
must pass visual review before being used as evidence that real apple-to-bowl
assets are visibly present.

The earliest honest claim for a real single-task EBench-compatible package
canary is Phase 10.10, targeted for 2026-07-06 to 2026-07-07, assuming license
and artifact-storage constraints allow either locked or controlled fat-package
delivery.
```

Boundary:

The Phase 10.7 artifact can be called a real-asset USD canary for
apple-to-bowl. It must not be described as model success, official EBench
reproduction, official material/camera parity, physics-fidelity evidence, score
release, or leaderboard-comparable output.

The Phase 10.9 render can be called a visual canary only if the image is produced
by the runtime engine from the Scenario Forge package and passes clean-room visual
review. It still must not be described as official material parity, official
camera parity, task success, or score evidence.

## Phase 10.6-10.8 Execution Update

On 2026-07-04, Phase 10.6-10.8 were implemented for the single-task
`mobile_manip/apple_to_fruit_bowl` canary.

Scenario Forge implementation:

```text
asset source manifest:
  examples/ebench_apple_to_bowl_asset_sources.yaml

asset intake module:
  src/scenario_forge/adapters/ebench/official_asset_intake.py

package generator:
  src/scenario_forge/generation/ebench_canary/apple_to_bowl.py

CLI:
  scenario-forge ebench canary apple-to-bowl
```

Generated package:

```text
package root:
  /tmp/ebench-apple-to-bowl-canary

package_id:
  ebench_apple_to_bowl_canary

task_id:
  mobile_manip/apple_to_fruit_bowl

USD entrypoint:
  /tmp/ebench-apple-to-bowl-canary/scene/main.usda
```

The generated `scene/main.usda` references package-local copies of the official
EBench scene, Lift2 robot, apple, and bowl USD assets:

```text
assets/official_ebench_scene/scene.usd
assets/official_ebench_robot/robot.usd
assets/official_ebench_apple/5948de6770a5491ea158cd9e921ebce9.usd
assets/official_ebench_bowl/307689f1c6884e1bb85bb20f00fef294.usd
```

The retained small evidence bundle is:

```text
docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/
  apple_to_bowl_package_manifest.yaml
  apple_to_bowl_main.usda
  apple_to_bowl_asset_manifest.yaml
  apple_to_bowl_asset_lock.yaml
  apple_to_bowl_ebench_package.yaml
  apple_to_bowl_task_entrypoint.yaml
  apple_to_bowl_task.yaml
  apple_to_bowl_metrics.yaml
  apple_to_bowl_task_contract.yaml
  apple_to_bowl_adapter_report.yaml
  apple_to_bowl_usd_smoke_trace.json
  apple_to_bowl_runtime_smoke.yaml
  phase10_10_task_contract_gate.yaml
  phase11_canary_human_review_gate.yaml
  phase11_task_execution_blocked_evidence.yaml
  phase11_task_execution_blocked_runtime.log
  phase11_task_execution_gate_blocked.yaml
  phase11_visual_review_gate.yaml
  tabletop_overview.png
  tabletop_overview_render_metadata.json
  tabletop_overview_runtime.log
  tabletop_overview_visual_review.md
  tabletop_overview_visual_review.yaml
```

Verification:

```text
PYTHONPATH=src python -m pytest tests/test_ebench_official_asset_intake.py tests/test_ebench_apple_to_bowl_canary.py -q
  7 passed

PYTHONPATH=src python -m pytest tests/test_ebench_apple_to_bowl_canary.py tests/test_ebench_adapter.py tests/test_asset_schemas.py -q
  14 passed

make check
  90 passed
  ruff: All checks passed
  Phase 10.x overall status: passed

PYTHONPATH=src python -m scenario_forge.cli package check /tmp/ebench-apple-to-bowl-canary --require-asset-lock
  Package OK

PYTHONPATH=src python -m scenario_forge.cli assets check /tmp/ebench-apple-to-bowl-canary
  Asset lock OK

EOS bridge Stage.Open smoke:
  runtime_status: executed
  stage_open_status: passed
  lane: eos_usd_stage_open_smoke
```

Phase 10.10 contract evidence:

```text
  apple_to_bowl_task.yaml
  apple_to_bowl_metrics.yaml
  apple_to_bowl_task_contract.yaml
  apple_to_bowl_adapter_report.yaml
  phase10_10_task_contract_gate.yaml
```

The Phase 10.10 task contract binds `mobile_manip/apple_to_fruit_bowl` to the
official instruction, `apple_001` as the manipulated object, `bowl_001` as the
target container, `apple_in_bowl` / `object_in_container` as the primary success
predicate, the Lift2 robot hint, the `fixed_camera_lift2_simbox.yml` camera
hint, and the EBench/EOS adapter boundary. The EBench package descriptor now
advertises `entrypoints.task_contract: ../../task/task_contract.yaml`, and the
adapter report records `task_contract: task/task_contract.yaml`.

Phase 11 canary review evidence (historical):

```text
  phase11_canary_human_review_gate.yaml
```

The user manually inspected `tabletop_overview.png` and reported no issue. The
remaining review checks are judged by Scenario Forge evidence: the task contract
is complete, the EBench adapter exposes it, package and asset checks pass, EOS
Stage.Open evidence is retained, and Scenario Forge boundaries are preserved.
This passes the apple-to-bowl canary for internal Phase 11 continuation into EOS
task execution integration. It does not approve public dataset release because
the retained asset license is `research-use`, explicit redistribution approval
is still required, and executed task success has not been retained as evidence.

Superseding plan: future Phase 11 gates remove mandatory manual review. Render
and keyframe inspection must be performed by the `render-visual-reviewer`
clean-room visual review skill; package, contract, license, execution, and
predicate checks must be decided by machine-readable evidence gates.

Decision record:

```text
1. Manual observation is allowed only as product feedback or issue discovery.
   It is not a release-critical gate and cannot convert a blocked/failed gate
   into a passed gate.
2. Scenario Forge owns static package evidence and gate aggregation, but does
   not own episode runners, model adapters, simulator SDK calls, task success
   predicates, or leaderboard evidence.
3. EOS owns task execution evidence, lifecycle status, traces, logs, keyframes,
   and success predicate evaluation.
4. `render-visual-reviewer` owns visual review for overview renders and
   execution keyframes. Its output is evidence, not a substitute for EOS state
   predicates or license policy.
5. Missing evidence, mismatched owner, missing artifact path, or stale input
   keeps the corresponding Phase 11 gate blocked.
```

Phase 11.0 automated visual review gate:

```text
  tabletop_overview_visual_review.yaml
  phase11_visual_review_gate.yaml
```

The structured `phase11-visual-review/v0.1` evidence records
`reviewer=render-visual-reviewer`, `review_mode=clean_room_visual_skill`,
`verdict=PASS`, and the retained `tabletop_overview.png` image. The generated
`phase11-visual-review-gate/v0.1` evidence records `status=passed`, no blockers,
and `next_stage=eos_task_execution_integration`. This replaces mandatory manual
visual review for the apple-to-bowl canary.

Phase 11.1 EOS task execution gate contract:

```text
  src/scenario_forge/evaluation/phase11_gates.py
  src/scenario_forge/schemas/jsonschema/phase11-eos-task-execution-v0.1.schema.json
  src/scenario_forge/schemas/jsonschema/phase11-task-execution-gate-v0.1.schema.json
  scenario-forge package phase11-task-execution \
    --package <package-dir> \
    --execution-evidence <phase11-eos-task-execution.yaml> \
    --strict
```

Scenario Forge can now ingest `phase11-eos-task-execution/v0.1` evidence emitted
by EOS and write `evidence/phase11_task_execution_gate.yaml`. The gate passes
only when EOS is the recorded runtime owner, the package and task IDs match the
Scenario Forge package, the task contract was consumed, the execution config was
generated, an episode started or completed, reset/step/close lifecycle states
passed, and trace/log/initial-keyframe references exist.

This was a package-side evidence contract, not live execution evidence. At this
point in the run log, the real apple-to-bowl Phase 11.1 canary remained open
until EOS emitted matching task execution evidence for
`/tmp/ebench-apple-to-bowl-canary` or a regenerated equivalent package.

Current real canary status:

```text
  phase11_task_execution_blocked_evidence.yaml
  phase11_task_execution_blocked_runtime.log
  phase11_task_execution_gate_blocked.yaml
  phase11_eos_task_execution_config_blocked_evidence.yaml
  phase11_task_execution_config_trace.json
  phase11_task_execution_config_runtime.log
  phase11_task_execution_gate_config_blocked.yaml
  phase11_genmanip_server_probe_skipped_trace.json
  phase11_eos_task_execution_live_evidence.yaml
  phase11_task_execution_live_trace.json
  phase11_task_execution_live_runtime.log
  phase11_task_execution_initial_overlook.png
  phase11_task_execution_gate_live.yaml
```

On 2026-07-04, Scenario Forge ran the Phase 11.1 strict gate against explicit
blocked evidence for `/tmp/ebench-apple-to-bowl-canary`. The generated gate has
`status=failed`, `next_stage=blocked`, and blockers for `contract_consumed=false`,
`execution_config_status=blocked`, `episode_status=blocked`, reset/step/close
not passed, missing initial keyframe, and missing real EOS package execution
evidence. This is the retained go/no-go state before EOS implements or runs the
Scenario Forge package execution lane.

EOS package-consumption update:

On 2026-07-04, EOS isolated worktree
`/root/.config/superpowers/worktrees/embodied-eval-os/phase11-scenario-forge-execution`
implemented the first package execution evidence lane on branch
`phase11-scenario-forge-execution`, based on the earlier
`phase10x-scenario-forge-bridge` branch. The new EOS lane consumes
`manifest.yaml`, `adapters/ebench/package.yaml`,
`adapters/ebench/task_entrypoint.yaml`, `locks/asset_lock.yaml`, and
`task/task_contract.yaml`; it writes a `phase11-eos-task-execution/v0.1`
evidence file, runtime log, and trace JSON.

Executed command:

```bash
/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python \
  scripts/run_phase11_scenario_forge_task_execution.py \
  --package /tmp/ebench-apple-to-bowl-canary \
  --evidence-out /tmp/ebench-apple-to-bowl-canary/evidence/phase11_eos_task_execution.yaml \
  --trace-out /tmp/ebench-apple-to-bowl-canary/evidence/phase11_task_execution_trace.json \
  --runtime-log-out /tmp/ebench-apple-to-bowl-canary/evidence/phase11_task_execution_runtime.log
```

The command intentionally exited with code 1 because no real simulator episode
was started. Its evidence now records `contract_consumed=true` and
`execution_config_status=generated`, with the generated execution config binding
the apple-to-bowl instruction, `object_in_container(apple_001, bowl_001)`, scene
USD, asset lock, task entrypoint, robot hints, camera hints, and runtime hints.

Scenario Forge then ingested that evidence with:

```bash
PYTHONPATH=src python -m scenario_forge.cli package phase11-task-execution \
  --package /tmp/ebench-apple-to-bowl-canary \
  --execution-evidence /tmp/ebench-apple-to-bowl-canary/evidence/phase11_eos_task_execution.yaml \
  --strict
```

The strict gate still failed, as it should. The remaining blockers are now
limited to `episode_status=blocked`, reset/step/close lifecycle blocked, missing
initial keyframe, and the explicit EOS blockers
`eos_episode_start_not_run_for_scenario_forge_package` and
`no_scenario_forge_package_episode_runner_available_in_this_eos_lane`.

This closes Phase 11.1.a package discovery and Phase 11.1.b execution config
generation for the apple-to-bowl canary. The remaining open item at this point
was Phase 11.1.c: EOS still needed to start a real simulator episode, retain
reset/step/close lifecycle evidence, runtime log, trace URI, and an initial
keyframe before Scenario Forge could mark Phase 11.1 passed.

EOS runtime probe for Phase 11.1.c:

The existing EOS `adapters.ebench.smoke_run` path can connect to an already
running GenManip EvalServer and perform reset/step, but it does not start the
server itself. On 2026-07-04, a local probe against `http://127.0.0.1:8087`
failed with connection refused and the smoke path wrote
`phase11_genmanip_server_probe_skipped_trace.json`.

Executed command:

```bash
/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python \
  -m adapters.ebench.smoke_run \
  --task-config /cpfs/shared/simulation/zhuzihou/dev/GenManip/configs/tasks/ebench/mobile_manip/test_mini/apple_to_fruit_bowl.yml \
  --server-url http://127.0.0.1:8087 \
  --worker-id 0 \
  --trace-dir /tmp/scenario-forge-phase11-genmanip-smoke \
  --max-policy-calls 1
```

The skipped trace records `runtime_status=skipped`, `runtime_attempted=true`,
`server_connection_attempted=true`, and the reason:

```text
GenManip protocol failed after probe readiness: ConnectionError ... 127.0.0.1:8087 ... Connection refused
```

Therefore the next Phase 11.1.c task is not another Scenario Forge schema task.
It is an EOS runtime task: start or connect a real GenManip/IsaacSim41 EvalServer
with the required cuRobo/CUDA overlays, submit or bind the apple-to-bowl job,
then run reset/step/close and retain the initial keyframe.

Phase 11.1.c live evidence update:

Later on 2026-07-04, EOS worktree
`/root/.config/superpowers/worktrees/embodied-eval-os/phase11-scenario-forge-execution`
closed Phase 11.1.c for the apple-to-bowl canary. Two EOS-side fixes were needed:
`adapters.ebench.smoke_run` now accepts `--reset-result-timeout-s` and records it
in trace metadata, and `TraceStore.save_json` now creates parent directories for
external episode ids containing `/`.

Executed command:

```bash
/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python \
  -m adapters.ebench.smoke_run \
  --task-config /cpfs/shared/simulation/zhuzihou/dev/GenManip/configs/tasks/ebench/mobile_manip/test_mini/apple_to_fruit_bowl.yml \
  --server-url http://127.0.0.1:8087 \
  --worker-id 0 \
  --trace-dir /tmp/scenario-forge-phase11-genmanip-smoke-tracefix \
  --max-policy-calls 1 \
  --reset-result-timeout-s 240
```

The command completed with `runtime_status=executed` and retained:

```text
phase11_eos_task_execution_live_evidence.yaml
phase11_task_execution_live_trace.json
phase11_task_execution_live_runtime.log
phase11_task_execution_initial_overlook.png
phase11_task_execution_gate_live.yaml
```

The live trace records episode id
`ebench/scenario_forge_phase11_apple_to_bowl_tracefix_20260704T151344Z/ebench/mobile_manip/apple_to_fruit_bowl_test_mini/000`,
`runtime_status=executed`, `reset_result_timeout_s=240.0`, and two steps
including reset and one zero-policy step. The GenManip recorder retained an
initial `overlook_camera/00000.png`, copied here as
`phase11_task_execution_initial_overlook.png`.

Scenario Forge strict verification:

```bash
PYTHONPATH=src python -m scenario_forge.cli package phase11-task-execution \
  --package /tmp/ebench-apple-to-bowl-canary \
  --execution-evidence docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/phase11_eos_task_execution_live_evidence.yaml \
  --strict
```

Result:

```text
Phase 11.1 task execution gate status: passed
phase11_task_execution_gate_live.yaml: status=passed, blockers=[]
```

This closes Phase 11.1 for the apple-to-bowl canary. It does not close Phase
11.2, because Phase 11.2 requires completed episode evidence with final state,
final keyframe, trace artifact, and runtime log. It also does not claim task
success, model quality, official EBench score, physics fidelity, or release
approval.

Planning update: Phase 11 has no remaining manual acceptance gate. Human review
can still create issues, debugging notes, or rerun requests, but it cannot
convert failed/blocked evidence into a pass. Visual acceptance for both overview
renders and execution keyframes must come from `render-visual-reviewer`
clean-room evidence. Runtime acceptance must come from EOS evidence: lifecycle
status, trace URI, runtime log, keyframe paths, and simulator-state predicate
outputs. Scenario Forge remains the evidence ingester and gate aggregator.

Automated visual-review policy now written into the roadmap:

```text
1. EOS / Isaac Sim produces render/keyframe artifacts and keeps paths, hashes,
   camera/runtime metadata, trace URI, and runtime logs.
2. `render-visual-reviewer` receives only image paths and a short visual
   expectation packet. It must not receive code context, implementation notes,
   suspected defects, or expected verdicts.
3. `render-visual-reviewer` outputs PASS/WARN/FAIL evidence with visible
   evidence and retake recommendation when needed.
4. Scenario Forge ingests the structured evidence and writes the visual gate.
   It does not override the verdict by manual observation.
5. WARN, FAIL, missing reviewer output, stale image paths, or missing upstream
   gate references keep the corresponding Phase 11 visual gate blocked.
6. The fix path is to regenerate the render/keyframes or upstream evidence and
   rerun clean-room visual review; manual approval is never a replacement.
```

The Phase 11.1.c work was split into three concrete tasks, all now closed for
the apple-to-bowl canary:

```text
11.1.c.1 EOS runtime connection hardening:
  start or connect GenManip/IsaacSim41 EvalServer, submit the apple-to-bowl job,
  record server URL, job/run id, reset polling, timeout configuration, and reset
  outcome. Status: closed with reset_result_timeout_s=240.0 retained in trace.

11.1.c.2 initial keyframe export:
  export a real initial keyframe PNG from simulator observation, server recorder
  artifact, or trace data, and retain the file path in
  phase11-eos-task-execution/v0.1 evidence. Status: closed with
  phase11_task_execution_initial_overlook.png.

11.1.c.3 strict Phase 11.1 rerun:
  run Scenario Forge package phase11-task-execution --strict over EOS evidence.
  The result must be passed or failed/blocked with machine-readable blockers;
  no manual override is allowed. Status: closed with
  phase11_task_execution_gate_live.yaml passed.
```

Phase 11.2 executed episode gate contract:

```text
  src/scenario_forge/evaluation/phase11_gates.py
  src/scenario_forge/schemas/jsonschema/phase11-executed-episode-evidence-v0.1.schema.json
  src/scenario_forge/schemas/jsonschema/phase11-executed-episode-gate-v0.1.schema.json
  scenario-forge package phase11-executed-episode \
    --package <package-dir> \
    --episode-evidence <phase11-executed-episode-evidence.yaml> \
    --strict
```

Scenario Forge can now ingest completed EOS episode evidence and write
`evidence/phase11_executed_episode_gate.yaml`. This gate is stricter than
Phase 11.1: `episode_status=started` is not enough. It requires
`episode_status=completed`, matching package/task IDs, EOS runtime ownership,
trace artifact reference, runtime log, initial and final keyframes, and a
non-empty final state.

This was also a package-side evidence contract, not live execution evidence. At
this point in the run log, the real apple-to-bowl Phase 11.2 canary remained open
until EOS emitted a completed episode evidence record for the Scenario Forge
package.

Phase 11.2 current blocked evidence:

The Phase 11.1 live smoke trace was intentionally not promoted to a completed
episode. It contains reset plus one zero-policy step, but it does not retain a
completed episode final state. Scenario Forge therefore recorded explicit Phase
11.2 blocked evidence:

```text
phase11_executed_episode_started_blocked_evidence.yaml
phase11_task_execution_step1_overlook.png
phase11_executed_episode_gate_started_blocked.yaml
```

Strict verification:

```bash
PYTHONPATH=src python -m scenario_forge.cli package phase11-executed-episode \
  --package /tmp/ebench-apple-to-bowl-canary \
  --episode-evidence docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/phase11_executed_episode_started_blocked_evidence.yaml \
  --strict
```

Result:

```text
Phase 11.2 executed episode gate status: failed
blockers:
  - executed episode_status must be completed; got started
  - eos_completed_episode_not_retained_for_scenario_forge_package
  - one_step_smoke_is_not_phase11_2_completed_episode
```

This historical blocked evidence remains useful because it proves one-step
smoke evidence cannot close Phase 11.2.

Phase 11.2 completed evidence:

EOS then added a chunked full-horizon execution path in the Phase 11 EOS worktree
and ran the same apple-to-bowl canary with:

```text
run_id: scenario_forge_phase11_apple_to_bowl_chunk_20260704T154825Z
max_policy_calls: 1000
step_chunk_size: 1000
executed_steps: 1000
task_config num_steps: 1000
```

The resulting trace contains a terminal `episode_result`:

```text
episode_status: completed
score: 0.0
sr: 0.0
```

Retained completed evidence:

```text
phase11_executed_episode_completed_trace.json
phase11_executed_episode_completed_runtime.log
phase11_executed_episode_result_info.json
phase11_executed_episode_completed_evidence.yaml
phase11_executed_episode_initial_overlook.png
phase11_executed_episode_final_overlook.png
phase11_executed_episode_gate_completed.yaml
```

The keyframes were extracted from the engine-native GenManip recorder artifact
`overlook_camera.mp4` because GenManip consolidates per-frame PNGs into mp4 at
episode finalization. The source mp4 is retained locally in the evidence
directory but is not release-critical for the Scenario Forge gate.

Strict verification:

```bash
PYTHONPATH=src python -m scenario_forge.cli package phase11-executed-episode \
  --package /tmp/ebench-apple-to-bowl-canary \
  --episode-evidence docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/phase11_executed_episode_completed_evidence.yaml \
  --strict
```

Result:

```text
Phase 11.2 executed episode gate status: passed
blockers: []
next_stage: success_predicate_evaluation_gate
```

Important boundary: Phase 11.2 is now closed for apple-to-bowl, but this is not
task success. The completed episode result records `score=0.0` and `sr=0.0`.
Phase 11.3 must ingest EOS/EBench predicate evidence and is expected to record
predicate failure unless simulator-state evidence says otherwise.

GenManip terminal response note:

After completing episode 000, GenManip immediately reset worker 0 to episode
001. The executed episode evidence therefore records
`observation_status=post_completion_reset_observation`: the terminal
`episode_result` and final keyframe are the authoritative completed-episode
artifacts, while the returned observation belongs to the next reset.

Phase 11.3 predicate evaluation result:

Scenario Forge then ingested EOS/EBench predicate evidence derived from the
completed episode result:

```text
phase11_success_predicate_failed_evidence.yaml
phase11_success_predicate_gate_failed.yaml
```

Strict verification:

```bash
PYTHONPATH=src python -m scenario_forge.cli package phase11-success-predicate \
  --package /tmp/ebench-apple-to-bowl-canary \
  --predicate-evidence docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/phase11_success_predicate_failed_evidence.yaml \
  --strict
```

Result:

```text
Phase 11.3 success predicate gate status: failed
blockers:
  - predicate_status must be true; got False
  - episode_result_sr_zero
```

This is the correct automated outcome for the retained zero-policy run. It means
Phase 11.2 is closed, but Phase 11.3 is not passed. No human inspection or
visual-review output can override this predicate failure. The next EOS-side
requirement is a successful apple-to-bowl policy/adapter or official successful
rollout that can produce a new completed episode and predicate_status=true
evidence.

Planning update: Phase 11 remains fully human-free. Manual inspection can create
issues or rerun requests, but it is never an acceptance signal. The active
recovery path is now split into three Phase 11.3 slices:

```text
11.3.b successful rollout source selection:
  EOS/EBench investigates GenManip demonstration_configs / cuRobo /
  generalized-oracle lanes first, and official successful rollout reruns second.
  The selected source must record policy/oracle identity, task config, run id,
  runtime environment, package linkage, and blockers. A zero-policy run,
  historical screenshot, or visual review verdict cannot become success evidence.

11.3.c package-linked successful completed episode rerun:
  EOS/GenManip reruns a successful apple-to-bowl episode against the Scenario
  Forge package or a documented equivalent package-linked execution config. It
  must retain terminal episode_result, trace, runtime log, initial/final
  keyframes, and simulator-state projection, then rebuild Phase 11.2 evidence.

11.3.d strict predicate re-gate:
  Scenario Forge consumes only EOS/EBench predicate evidence and reruns
  phase11-success-predicate --strict. Pass requires predicate_status=true,
  success score/sr evidence, a referenced passed Phase 11.2 gate, and no blockers.
```

2026-07-05 source-selection update: 11.3.b now has a first rerun candidate:
EOS BPL-19R.R2 same-checkpoint online lane. The retained BPL-19R.R2 cohort used
`pi05-ebench-generalist`, `pi05_ebench_all`, and the native GenManip
`apple_to_fruit_bowl.yml` task config. It retained 10 completed EOS online
attempts, with attempts 005, 006, 007, and 009 showing `score=1.0` and
`success_rate=1` in GenManip result_info files.

At source-selection time, this did not close Phase 11.3. The BPL-19R.R2
successes were reference evidence for choosing the next lane, not Scenario Forge
package success evidence. 11.3.c therefore had to rerun that lane through an EOS
package-linked wrapper that loads
`/tmp/ebench-apple-to-bowl-canary`, records `package_id`,
`task/task_contract.yaml`, `adapters/ebench/package.yaml`, `scene/main.usda`,
`locks/asset_lock.yaml`, the task-id-to-native-config mapping, policy/checkpoint
identity, run id, and runtime env. The retained source-selection note is:

```text
docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/phase11_successful_rollout_source_selection.yaml
```

Implementation detail for 11.3.c: derive the package-linked runner from the
BPL-19R.R1 single-attempt online path, because that is the per-attempt runner
used by the successful R2 cohort. Use retained attempt 007 as the preferred
debugging reference (`task_success=true`, `score=1.0`, `sr=1.0`, 13 cycles),
but do not assume it can be exactly replayed: the current CLI cannot directly
target retained attempt 007. The rerun path should therefore support repeated
package-scoped attempts and retain the first successful package-linked episode.
If BPL-19R native run reports are not directly consumable by Scenario Forge's
Phase 11 completed-episode evidence gate, EOS must add a small translator that
links BPL-19R output refs, terminal episode_result, keyframes, and package
metadata into Phase 11.2/11.3 evidence.

2026-07-05 implementation update: EOS now has a package-linked BPL-19R wrapper
and CLI in the Phase 11 worktree. The wrapper loads the Scenario Forge package,
validates `mobile_manip/apple_to_fruit_bowl`, records package descriptor,
task contract, scene USD, asset lock, mapping source, checkpoint/policy identity,
and maps the task to the native GenManip apple-to-bowl config before invoking
the BPL-19R.R1 runner. It supports repeated package-scoped attempts and stops
after the first successful attempt, matching the BPL-19R.R2 lesson that a single
rerun is not guaranteed to succeed. A dry-run plan with `attempt_count=10` has
been retained at:

```text
docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/phase11_3c_bpl19r_package_linked_plan/phase11_package_linked_bpl19r_rerun.yaml
```

This evidence has `rerun_status=planned` and blocker
`live_bpl19r_rerun_not_executed`. It proves package linkage and runner selection,
multi-attempt intent, but it does not close 11.3.c because no live completed
BPL-19R episode has run through this package-linked wrapper yet.

Live package-linked update:

The live 11.3.c BPL-19R package-linked rerun has now retained a successful
attempt. EOS loaded `/tmp/ebench-apple-to-bowl-canary`, recorded package linkage,
mapped `mobile_manip/apple_to_fruit_bowl` to the native GenManip apple-to-bowl
config, and ran package-scoped BPL-19R attempts. attempt_000 and attempt_001
completed with `task_success=false` and `score=0.0`; attempt_002 completed with
`task_success=true` and `standard_model_score=1.0`.

Retained live evidence:

```text
docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/phase11_3c_bpl19r_package_linked_live/phase11_package_linked_bpl19r_rerun.yaml
docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/phase11_3c_bpl19r_package_linked_live/phase11_package_linked_bpl19r_runtime.log
docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/phase11_3c_bpl19r_package_linked_live/bpl19r_rerun/attempt_002/run_report.json
```

The top evidence records `rerun_status=executed`,
`selected_success_attempt=attempt_002`, and `blockers=[]`. This closes the
package-linked successful rollout-source evidence step for 11.3.c. At this point
the remaining requirement was to translate or bridge the retained BPL-19R output
into Phase 11.2 completed episode evidence and Phase 11.3 predicate evidence,
then rerun the strict gates.

Bridge and strict gate update:

EOS now has a BPL-19R-to-Phase-11 bridge that projects the retained successful
attempt into Scenario Forge gate evidence without adding any simulator runner to
this repo. The bridge produced:

```text
docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/phase11_executed_episode_bpl19r_success_evidence.yaml
docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/phase11_success_predicate_bpl19r_success_evidence.yaml
```

Scenario Forge strict gate results:

```text
phase11_executed_episode_bpl19r_success_gate.yaml      status=passed
phase11_success_predicate_bpl19r_success_gate.yaml     status=passed
```

This closes 11.3.d for the apple-to-bowl canary. The success claim is
package-linked internal evidence, not public release, official EBench score
release, or leaderboard comparability.

The first live-server probe for the package-linked rerun found no GenManip server
on `http://127.0.0.1:8087/docs` (`curl` exit code 7, connection refused). Retained
probe evidence:

```text
docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/phase11_3c_bpl19r_live_server_probe.yaml
```

This is only a server-availability probe. The next execution step is to start
`ray_eval_server.py` with the package-scoped run id and then invoke
`run_phase11_scenario_forge_bpl19r_rerun.py --attempt-count 10` without
`--dry-run`. That historical probe is now superseded by the retained live
package-linked rerun and the BPL-19R bridge evidence above.

GenManip native demogen/cuRobo remains a backup regeneration lane. It can run
`demogen.py -cfg configs/tasks/ebench/mobile_manip/test_mini/apple_to_fruit_bowl.yml`
or the `--eval` variant from the GenManip root and record success when the scene
metric score is 1. However, no reusable apple demogen/task LMDB was found locally,
and native GenManip demogen expects GenManip-shaped assets/configs rather than a
Scenario Forge package. Therefore demogen/cuRobo cannot close 11.3 unless EOS or
an adapter layer first records explicit Scenario Forge package linkage or exports
the Scenario Forge package into a GenManip-shaped task package.

Only after 11.3.d passes can Phase 11.4 run the `render-visual-reviewer`
post-execution keyframe review. Phase 11.4 remains a visual-evidence quality gate;
it cannot rescue a failed simulator-state predicate. That condition is now met
for the package-linked BPL-19R attempt_002 path, so the post-execution visual
review was run as the next gate.

Phase 11.3 success predicate gate contract:

```text
  src/scenario_forge/evaluation/phase11_gates.py
  src/scenario_forge/schemas/jsonschema/phase11-success-predicate-evaluation-v0.1.schema.json
  src/scenario_forge/schemas/jsonschema/phase11-success-predicate-gate-v0.1.schema.json
  scenario-forge package phase11-success-predicate \
    --package <package-dir> \
    --predicate-evidence <phase11-success-predicate-evaluation.yaml> \
    --strict
```

Scenario Forge can now ingest EOS/EBench predicate evidence and write
`evidence/phase11_success_predicate_gate.yaml`. The gate requires
`evaluator_owner=embodied-eval-os-ebench-adapter`, matching package/task IDs,
non-empty predicate fields, `predicate_status=true`, non-empty measurement
evidence, and a referenced Phase 11.2 executed episode gate whose status is
`passed`.

This is not a predicate evaluator implementation. The original zero-policy
completed episode remains a failed predicate example, but the BPL-19R
package-linked attempt_002 path now has matching predicate evidence and a passed
strict gate:

```text
phase11_success_predicate_bpl19r_success_evidence.yaml
phase11_success_predicate_bpl19r_success_gate.yaml
```

Phase 11.4 post-execution visual review gate contract:

```text
  src/scenario_forge/evaluation/phase11_gates.py
  src/scenario_forge/schemas/jsonschema/phase11-post-execution-visual-review-v0.1.schema.json
  src/scenario_forge/schemas/jsonschema/phase11-post-execution-visual-review-gate-v0.1.schema.json
  scenario-forge package phase11-post-execution-visual-review \
    --package <package-dir> \
    --visual-review <phase11-post-execution-visual-review.yaml> \
    --strict
```

Scenario Forge can now ingest clean-room post-execution visual review evidence
from `render-visual-reviewer` and write
`evidence/phase11_post_execution_visual_review_gate.yaml`. The gate requires
the reviewer identity and review mode, PASS verdict, existing initial and final
keyframe images, visible evidence, and a referenced Phase 11.3 success predicate
gate whose status is `passed`.

This visual gate supports inspection only. It does not replace the EOS/EBench
predicate or release policy. The BPL-19R attempt_002 review used retained
right-camera keyframes because the overview post-action frame did not clearly
show the apple-in-bowl outcome:

```text
phase11_4_bpl19r_visual_review_frames/right_camera_first.jpg
phase11_4_bpl19r_visual_review_frames/right_camera_last.jpg
phase11_post_execution_visual_review_bpl19r_success.yaml
phase11_post_execution_visual_review_bpl19r_success_gate.yaml   status=passed
```

Manual inspection did not pass this gate; it is retained only as debugging
context when choosing which keyframes to send to visual review.

Phase 11.5 single-task automated release candidate gate contract:

```text
  src/scenario_forge/evaluation/phase11_gates.py
  src/scenario_forge/schemas/jsonschema/phase11-release-policy-v0.1.schema.json
  src/scenario_forge/schemas/jsonschema/phase11-single-task-release-candidate-gate-v0.1.schema.json
  scenario-forge package phase11-single-task-rc \
    --package <package-dir> \
    --release-policy <phase11-release-policy.yaml> \
    --strict
```

Scenario Forge can now aggregate the single-task Phase 11 gates into
`evidence/phase11_single_task_release_candidate_gate.yaml`. The gate requires a
valid package, asset lock, task contract, passed gates for Phase 11.0 through
11.4, and `phase11-release-policy/v0.1` evidence with
`release_policy_status=pass` and `redistribution_approval=true`.

If the asset policy remains `research-use`, the release-candidate gate is
`blocked` even when all technical gates pass. This preserves the distinction
between an internal complete task package and a public dataset or official score
release.

Current apple-to-bowl result:

```text
phase11_release_policy_bpl19r_internal_rc_blocked.yaml
phase11_single_task_rc_bpl19r_internal_policy_blocked_gate.yaml  status=blocked
```

The package has a complete internal single-task evidence bundle, but public
release remains blocked by `ebench_assets_research_use_only` and
`redistribution_approval_missing`.

Phase 11.6 small multi-task canary gate contract:

```text
  src/scenario_forge/evaluation/phase11_gates.py
  src/scenario_forge/schemas/jsonschema/phase11-small-multi-task-canary-v0.1.schema.json
  src/scenario_forge/schemas/jsonschema/phase11-small-multi-task-canary-gate-v0.1.schema.json
  scenario-forge suite phase11-small-canary \
    --suite <suite-dir> \
    --canary-evidence <phase11-small-multi-task-canary.yaml> \
    --strict
```

Scenario Forge can now aggregate 3-5 task rows into
`evidence/phase11_small_multi_task_canary_gate.yaml`. The gate requires a
matching suite id, each task row to reference a single-task RC gate, real asset
package and task-contract markers, passed overview visual review, execution
lane status, predicate evidence status or structured blocker, and at least one
task whose execution lane started or completed.

This gate checks breadth of the automated process, not public release or
leaderboard comparability. The real small multi-task canary remains open until
EOS emits evidence for 3-5 Scenario Forge-generated EBench tasks.

Current breadth result:

```text
phase11_small_multi_task_canary_underfilled_blocked.yaml
phase11_small_multi_task_canary_underfilled_blocked_gate.yaml    status=blocked
```

The blocker is structural and machine-readable: the current canary has one real
EBench task, while Phase 11.6 requires 3-5 tasks.

2026-07-05 breadth update:

Scenario Forge added a second real EBench USD-bearing task package:
`ebench_soap_to_dish_canary`. This task covers the common EBench pattern where
the manipulated object is materialized as a package-local USD asset and the
target container is an environment fixture already present in the scene USD.
For soap-to-dish, the target fixture is `/root/obj__01` / source uid `_01` in the
official task3 scene, represented as `soap_dish_fixture` in the task contract.

Retained package-static evidence:

```text
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/soap_to_dish_package_generation_evidence.yaml
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/soap_to_dish_package_manifest.yaml
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/soap_to_dish_main.usda
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/soap_to_dish_asset_lock.yaml
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/soap_to_dish_task_contract.yaml
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/soap_to_dish_ebench_package.yaml
```

Verification retained in the evidence:

```text
package check: passed
asset lock check: passed
USD Stage.Open: passed
checked prims: /World/Instances/environment_scene, /World/Instances/lift2_robot_asset, /World/Instances/soap_001
```

Latest Phase 11.6 gate:

```text
phase11_small_multi_task_canary_two_task_underfilled_blocked.yaml
phase11_small_multi_task_canary_two_task_underfilled_blocked_gate.yaml    status=blocked
package_count=2
```

The current blocker is still structural and machine-readable: Phase 11.6 requires
3-5 tasks; soap-to-dish also still needs overview visual review, EOS execution,
predicate evaluation, and single-task RC evidence.

2026-07-05 three-task breadth update:

Scenario Forge added a third real EBench USD-bearing task package:
`ebench_remote_to_holder_canary`. This task covers the same package-static
fixture pattern as soap-to-dish: the manipulated remote control is materialized
as a package-local USD asset and the target remote holder is an environment
fixture already present in the scene USD. For remote-to-holder, the target
fixture is `/root/obj__00` / source uid `_00` in the official task5 scene,
represented as `remote_holder_fixture` in the task contract.

Retained package-static evidence:

```text
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_package_generation_evidence.yaml
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_package_manifest.yaml
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_main.usda
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_asset_lock.yaml
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_task_contract.yaml
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_ebench_package.yaml
```

Verification retained in the evidence:

```text
package check: passed
asset lock check: passed
USD Stage.Open: passed
checked prims: /World/Instances/environment_scene, /World/Instances/lift2_robot_asset, /World/Instances/remote_001
```

Latest Phase 11.6 gate:

```text
phase11_small_multi_task_canary_three_task_downstream_blocked.yaml
phase11_small_multi_task_canary_three_task_downstream_blocked_gate.yaml    status=blocked
package_count=3
```

The task-count blocker is removed. The current blockers are now downstream
automated gates: soap-to-dish and remote-to-holder still need overview visual
review, EOS execution, predicate evaluation, and single-task RC evidence.

2026-07-05 visual-review update:

Scenario Forge then ran engine-native tabletop overview renders and clean-room
visual review for soap-to-dish and remote-to-holder. This advanced both tasks
from `overview_visual_review_not_run` to explicit Phase 11.0 failed gates:

```text
soap_to_dish_tabletop_overview.png
soap_to_dish_tabletop_overview_render_metadata.json
soap_to_dish_tabletop_overview_runtime.log
soap_to_dish_tabletop_overview_visual_review.yaml
soap_to_dish_phase11_visual_review_gate_failed.yaml   status=failed

remote_to_holder_tabletop_overview.png
remote_to_holder_tabletop_overview_render_metadata.json
remote_to_holder_tabletop_overview_runtime.log
remote_to_holder_tabletop_overview_visual_review.yaml
remote_to_holder_phase11_visual_review_gate_failed.yaml   status=failed
```

Blocker classes:

```text
1. Both overview camera frames failed clean-room visual review.
2. Soap-to-dish material runtime preflight failed because the official task3
   scene references missing textures through MDL files.
3. Remote-to-holder runtime log reports a missing remote asset texture reference.
```

Scenario Forge also tightened Phase 11.0 gate aggregation: a visual PASS is not
enough when render metadata or runtime logs show material/texture closure
blockers. The latest Phase 11.6 gate is now:

```text
phase11_small_multi_task_canary_three_task_visual_failed_downstream_blocked.yaml
phase11_small_multi_task_canary_three_task_visual_failed_downstream_blocked_gate.yaml    status=blocked
package_count=3
```

Phase 11.7 automated release gate contract:

```text
  src/scenario_forge/evaluation/phase11_gates.py
  src/scenario_forge/schemas/jsonschema/phase11-automated-release-evidence-v0.1.schema.json
  src/scenario_forge/schemas/jsonschema/phase11-automated-release-gate-v0.1.schema.json
  scenario-forge suite phase11-release \
    --suite <suite-dir> \
    --release-evidence <phase11-automated-release-evidence.yaml> \
    --strict
```

Scenario Forge can now aggregate release-critical gate status into
`evidence/phase11_automated_release_gate.yaml`. The gate requires a passed
Phase 11.6 small multi-task canary gate, `pass` status for package check, asset
lock check, adapter contract, visual review, episode execution, predicate
evaluation, and license policy, plus an empty `known_blockers` list.

This is the final automated release-candidate gate contract. It does not grant
official leaderboard comparability or public dataset publication without the
corresponding external approval and policy evidence. The real Phase 11.7 release
remains open until the upstream EOS/EBench and policy evidence exists.

Initial one-task release-gate result:

```text
phase11_automated_release_underfilled_policy_blocked_evidence.yaml
phase11_automated_release_underfilled_policy_blocked_gate.yaml   status=blocked
```

At that one-task point, the blockers were Phase 11.6 underfilled breadth plus
license policy. No manual approval path can override either blocker.

2026-07-05 release-gate update:

The automated release gate has been rerun against the two-task underfilled
canary. It remains blocked, now with more specific blockers for soap-to-dish:

```text
phase11_automated_release_two_task_underfilled_policy_blocked_evidence.yaml
phase11_automated_release_two_task_underfilled_policy_blocked_gate.yaml   status=blocked
```

Blocker classes:

```text
1. At that two-task point, Phase 11.6 gate was still blocked because package_count=2.
2. At that two-task point, soap-to-dish visual review / EOS execution / predicate / RC gates were not run.
3. license_policy remains blocked by research-use assets and missing redistribution approval.
```

2026-07-05 three-task release-gate update:

The automated release gate has been rerun against the three-task canary:

```text
phase11_automated_release_three_task_downstream_policy_blocked_evidence.yaml
phase11_automated_release_three_task_downstream_policy_blocked_gate.yaml   status=blocked
```

Blocker classes:

```text
1. Phase 11.6 gate is still blocked, but no longer because of package_count.
2. At that three-task point, soap-to-dish and remote-to-holder visual review / EOS execution / predicate / RC gates were not run.
3. license_policy remains blocked by research-use assets and missing redistribution approval.
```

2026-07-05 visual-failed release-gate update:

The automated release gate has been rerun against the visual-failed three-task
canary:

```text
phase11_automated_release_three_task_visual_failed_policy_blocked_evidence.yaml
phase11_automated_release_three_task_visual_failed_policy_blocked_gate.yaml   status=blocked
```

Blocker classes:

```text
1. Phase 11.6 gate is blocked by failed Phase 11.0 visual/material gates.
2. soap-to-dish and remote-to-holder EOS execution / predicate / RC gates are not run.
3. license_policy remains blocked by research-use assets and missing redistribution approval.
```

Boundary:

This closes Phase 10.6-10.10 for a real-asset apple-to-bowl canary package. It
proves official EBench asset intake, Scenario Forge package composition, asset
locking, EBench adapter export, package validation, asset validation, EOS USD
Stage.Open smoke, and one EOS/IsaacSim41 engine-native tabletop visual canary
with clean-room visual review PASS. Phase 10.10 additionally proves that the
package contains a reviewable task contract.

2026-07-05 addendum: for the apple-to-bowl canary, Phase 11.0-11.4 now also
prove package-linked EOS execution, completed BPL-19R success evidence,
EOS/EBench predicate success evidence, and post-execution visual review PASS.
Phase 11.5 proves an internal single-task RC bundle but remains policy-blocked
for public release. Phase 11.6 and 11.7 remain blocked, but the breadth blocker
has progressed from one represented task to three represented tasks:
apple-to-bowl, soap-to-dish, and remote-to-holder. The task-count blocker is
removed. Soap-to-dish and remote-to-holder are beyond package-static now:
engine-native overview renders and clean-room visual reviews were attempted, but
both Phase 11.0 gates failed and need camera retakes plus material/texture
closure fixes before EOS execution, predicate evaluation, and single-task RC
evidence. Official material
parity, physics fidelity, public score release, and leaderboard comparability
are still outside the current evidence claim.

2026-07-05 remote material-closure addendum:

The remote-to-holder material blocker was narrowed and resolved on the Scenario
Forge side. Root cause: the official remote_control `ready/remote0` USD depends
on a sibling sidecar texture bundle under the same `remote_control` collection
root. The first materialization copied only the ready bundle and missed that
sibling dependency. Scenario Forge now preserves collection-relative sibling
sidecar roots for official asset bundles when USD dependency analysis shows they
are required.

Retained fixed evidence:

```text
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_tabletop_overview_material_fixed.png
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_tabletop_overview_material_fixed_render_metadata.json
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_tabletop_overview_material_fixed_runtime.log
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_tabletop_overview_material_fixed_visual_review.yaml
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_visual_review_gate_material_fixed_warn.yaml
```

The fixed render metadata records `render_status=pass`,
`material_runtime_preflight.status=pass`, `blocked_dependency_count=0`, and
runtime log scan status `pass`. The retained runtime log no longer contains the
old missing remote texture signal.

Clean-room visual review over the fixed image returned WARN, not PASS: the
remote and holder are visible but weakly identifiable because the camera remains
too high/far. The strict Phase 11.0 gate therefore still fails, but only with:

```text
visual review verdict must be PASS; got WARN
```

Scenario Forge reran the Phase 11.6 and Phase 11.7 gates after this update:

```text
phase11_small_multi_task_canary_three_task_visual_failed_downstream_blocked_gate.yaml   status=blocked
remote row material_runtime_closure: passed

phase11_automated_release_three_task_visual_failed_policy_blocked_gate.yaml   status=blocked
known_blockers must be empty; got 13
```

The remote `material_runtime_log_missing_remote_texture` blocker is removed from
the latest suite and release gates. The remaining remote blockers are visual
camera retake, EOS execution not run, predicate not evaluated, and single-task
RC not run. Soap-to-dish still needs upstream official scene texture closure or
ConvertAsset handoff, plus its own camera retake.

2026-07-05 remote pose/contact/camera superseding addendum:

Remote-to-holder Phase 11.0 has since closed. Scenario Forge retained
root-cause evidence showing the generated remote visual package had a tabletop
contact issue after the orientation fix; the manifest z center was corrected
under test, package artifacts were regenerated, and the contact-fixed cam3
engine render passed clean-room visual review. Latest retained evidence:

```text
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_pose_camera_root_cause.yaml
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_tabletop_overview_contactfixed_cam3_render_metadata.json
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_tabletop_overview_contactfixed_cam3_visual_review.yaml
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_visual_review_gate_contactfixed_cam3_pass.yaml
```

The remaining remote blocker is now downstream Phase 11.1+ execution evidence,
not visual/material/camera evidence.

2026-07-05 remote Phase 11.1 runtime-preflight planning addendum:

The next remote-to-holder Phase 11.1 run must first prove the EOS
GenManip/IsaacSim41 runtime environment. A live probe against a GenManip
EvalServer started without the required cuRobo/CUDA overlays accepted the remote
task job, but the Isaac worker died before reset with:

```text
ModuleNotFoundError: No module named 'curobo'
```

The secondary `/reset_result` HTTP 500/no-pending-reset symptom is therefore not
a Scenario Forge package, layout, material, or camera issue. The planning rule is:
EOS must retain runtime preflight evidence with the selected IsaacSim41 conda
env, cuRobo source path, CUDA/torch library overlays, import-check output,
EvalServer launch command/run id, and log path before the remote 11.1 gate can
claim a real episode-start attempt. If the preflight fails, the correct blocker
is `eos_runtime_environment_preflight_failed`; if it passes, EOS reruns
`mobile_manip/remote_to_holder` and must retain trace/log/lifecycle evidence plus
an initial keyframe for Scenario Forge to ingest.

2026-07-05 remote Phase 11.1 live evidence addendum:

EOS reran `mobile_manip/remote_to_holder` with the required cuRobo/CUDA overlays
and closed remote Phase 11.1. The runtime preflight imported
`curobo.types.state.JointState` and `curobo.curobolib.kinematics_fused_cu` from
`/cpfs/shared/simulation/mamengchen/curobo-wbc-backup/src`, then launched
GenManip EvalServer on `http://127.0.0.1:18348` with run id
`scenario_forge_phase11_remote_to_holder_envfix_20260704T195141Z`.

Retained evidence:

```text
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_runtime_preflight_envfix.yaml
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_eos_task_execution_live_evidence.yaml
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_task_execution_live_trace.json
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_task_execution_live_runtime.log
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_task_execution_initial_overlook.png
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_task_execution_gate_live.yaml
```

The strict gate result is `status=passed`, with `episode_status=started`,
`lifecycle.reset=passed`, `lifecycle.step=passed`, `lifecycle.close=passed`, and
`blockers=[]`. This closes remote-to-holder Phase 11.1 only. It does not claim
completed episode, task success, predicate success, model quality, release
approval, official EBench score, or leaderboard comparability.

Scenario Forge reran the suite gates after this update:

```text
phase11_small_multi_task_canary_three_task_remote_live_started_downstream_blocked_gate.yaml   status=blocked
remote row execution_lane_status: started
remote blockers:
  - remote_to_holder_phase11_2_completed_episode_not_run
  - remote_to_holder_success_predicate_not_evaluated
  - remote_to_holder_post_execution_visual_review_not_run
  - remote_to_holder_single_task_rc_blocked

phase11_automated_release_three_task_remote_live_started_policy_blocked_gate.yaml   status=blocked
```

2026-07-05 remote Phase 11.2 / 11.3 evidence addendum:

EOS then ran `mobile_manip/remote_to_holder` to a terminal episode on the same
GenManip/IsaacSim41 EvalServer run id
`scenario_forge_phase11_remote_to_holder_envfix_20260704T195141Z`. Scenario Forge
retained completed trace, terminal episode result, runtime log, initial/final
overlook keyframes, and strict gate evidence.

Retained Phase 11.2 evidence:

```text
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_executed_episode_completed_evidence.yaml
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_executed_episode_completed_trace.json
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_executed_episode_result_info.json
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_executed_episode_completed_runtime.log
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_executed_episode_initial_overlook.png
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_executed_episode_final_overlook.png
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_executed_episode_gate_completed.yaml
```

The Phase 11.2 strict gate result is `status=passed`. This means remote-to-holder
has a completed episode evidence bundle with trace/log/keyframes and terminal
episode_result. It does not mean task success.

The terminal result for the retained zero-policy episode is:

```text
score=0.0
sr=0.0
```

Scenario Forge therefore evaluated Phase 11.3 and retained a failed success
predicate gate:

```text
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_success_predicate_failed_evidence.yaml
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_success_predicate_gate_failed.yaml
```

The Phase 11.3 strict gate result is `status=failed`, with blockers:

```text
predicate_status must be true; got False
episode_result_sr_zero
```

This is the correct automated outcome. Human visual inspection, overview renders,
or post-execution visual review cannot convert this failed simulator-state
predicate into a passed task-success claim. The next remote-to-holder step is a
package-linked successful policy/oracle/official rerun, followed by fresh 11.2
completed-episode evidence and 11.3 predicate evidence.

Scenario Forge reran suite gates again after the remote 11.2/11.3 update:

```text
phase11_small_multi_task_canary_three_task_remote_predicate_failed_downstream_blocked_gate.yaml   status=blocked
remote blockers:
  - remote_to_holder_success_predicate_failed_zero_policy
  - remote_to_holder_successful_policy_or_oracle_rerun_needed
  - remote_to_holder_post_execution_visual_review_not_run_because_predicate_failed
  - remote_to_holder_single_task_rc_blocked

phase11_automated_release_three_task_remote_predicate_failed_policy_blocked_gate.yaml   status=blocked
```

Soap-to-dish remains blocked at Phase 11.0 by official scene material/texture
closure and overview visual review. Release remains policy-blocked by
research-use assets and missing redistribution approval.

2026-07-05 remote 11.3.b source-selection and soap material-closure addendum:

Remote-to-holder source selection is now retained as structured evidence:

```text
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_successful_rollout_source_selection.yaml
```

The investigation found no retained remote-to-holder success artifact. The
available TaskBook/GenManip remote terminal results are all failures or zero
score, including the package-linked zero-policy Phase 11.3 run. The reusable path
is not a completed success lane; it is the EOS BPL-19R package-linked
wrapper/bridge pattern already proven for apple-to-bowl. EOS has now generalized
that wrapper for remote-to-holder and retained a package-linked dry-run plan:

```text
mobile_manip/remote_to_holder ->
/cpfs/shared/simulation/zhuzihou/dev/GenManip/configs/tasks/ebench/mobile_manip/test_mini/remote_to_holder.yml
```

```text
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_phase11_3c_bpl19r_package_linked_plan/phase11_package_linked_bpl19r_rerun.yaml
rerun_status=planned
attempt_count=10
package_linkage.task_id=mobile_manip/remote_to_holder
package_linkage.native_task_config_exists=true
blockers:
  - live_bpl19r_rerun_not_executed
```

Only after EOS produces a package-linked remote terminal result with
`task_success=true` / `sr=1` can Scenario Forge ingest new 11.2 and 11.3 evidence.

Soap-to-dish material closure is now retained as structured handoff evidence:

```text
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/soap_to_dish_phase11_material_closure_handoff.yaml
```

Scenario Forge added a static MDL `texture_2d(...)` closure audit in the official
asset intake boundary. The audit fails both the packaged copy and official task3
source because three JPG textures referenced by official MDLs are absent:

```text
SubUSDs/materials/MI_655dcc9a9237ad0001ba8197.mdl -> SubUSDs/textures/c00e97e58585d8ddb0f8b16a724d05a13eae31.jpg
SubUSDs/materials/MI_655dcc9ad6b50e000157727c.mdl -> SubUSDs/textures/bf77ddc86c270d02747e7d0517103514ab51d0f.jpg
SubUSDs/materials/MI_655dcc9ad6b50e000157727c.mdl -> SubUSDs/textures/c9c274d4ea1de7d059cec0a795b3b27e3941935.jpg
```

This confirms that soap-to-dish needs a repaired official task3 source or a
ConvertAsset-owned material-normalized/no-MDL artifact before Scenario Forge can
regenerate, rerender, and rerun the Phase 11.0 visual gate. The soap overview
camera also still needs a task-specific retake after material closure, because
the retained review could not identify the soap/dish or robot frame.

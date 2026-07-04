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
backend lane before building UI and human release workflows.

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
  apple_to_bowl_usd_smoke_trace.json
  apple_to_bowl_runtime_smoke.yaml
  tabletop_overview.png
  tabletop_overview_render_metadata.json
  tabletop_overview_runtime.log
  tabletop_overview_visual_review.md
```

Verification:

```text
PYTHONPATH=src python -m pytest tests/test_ebench_official_asset_intake.py tests/test_ebench_apple_to_bowl_canary.py -q
  5 passed

PYTHONPATH=src python -m scenario_forge.cli package check /tmp/ebench-apple-to-bowl-canary --require-asset-lock
  Package OK

PYTHONPATH=src python -m scenario_forge.cli assets check /tmp/ebench-apple-to-bowl-canary
  Asset lock OK

EOS bridge Stage.Open smoke:
  runtime_status: executed
  stage_open_status: passed
  lane: eos_usd_stage_open_smoke
```

Boundary:

This closes Phase 10.6-10.9 for a real-asset apple-to-bowl canary package. It
proves official EBench asset intake, Scenario Forge package composition, asset
locking, EBench adapter export, package validation, asset validation, EOS USD
Stage.Open smoke, and one EOS/IsaacSim41 engine-native tabletop visual canary
with clean-room visual review PASS. It still does not close Phase 10.10
task-contract hardening, model inference, task success, official EBench
reproduction, physics fidelity, official material/camera parity, score release,
or leaderboard comparability.

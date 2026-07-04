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

This closes Phase 10.6-10.8 for a real-asset apple-to-bowl canary package. It
proves official EBench asset intake, Scenario Forge package composition, asset
locking, EBench adapter export, package validation, asset validation, and EOS
USD Stage.Open smoke. It still does not close Phase 10.9 visual canary, Phase
10.10 task-contract hardening, model inference, task success, official EBench
reproduction, physics fidelity, official material/camera parity, score release,
or leaderboard comparability.

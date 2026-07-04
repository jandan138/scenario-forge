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

Phase 10.4 can close only when the runtime evidence explicitly links the live
trace to Scenario Forge package ids, USD entrypoints, asset locks, and adapter
descriptors. Phase 10.5 can close only after that evidence is attached to a
50-100 task RC suite, or the RC gate records the missing runtime package bridge
as a blocker.

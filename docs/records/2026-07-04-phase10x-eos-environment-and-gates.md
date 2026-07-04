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

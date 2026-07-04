# Development Checks

Install:

```bash
python -m pip install -e ".[dev]"
```

Run:

```bash
make check
```

The default check runs:

- unit and contract tests;
- Ruff linting;
- v0.2 starter package scaffold, workflow compose, layout plan, task compile,
  scene compile, EBench export, package check, suite generate, and suite quality smoke;
- `git diff --check`.

Phase 1 asset lock smoke commands:

```bash
scenario-forge assets lock ./pkg
scenario-forge assets check ./pkg
scenario-forge package check ./pkg --require-asset-lock
```

Phase 3 USD scene compiler smoke command:

```bash
scenario-forge scene compile \
  --instances ./pkg/scene/instances.yaml \
  --asset-lock ./pkg/locks/asset_lock.yaml \
  --out ./pkg/scene/main.usda
```

Phase 4 task compiler smoke command:

```bash
scenario-forge task compile --package ./pkg --family pick_place
```

Phase 5 EBench adapter smoke commands:

```bash
scenario-forge export ebench --package ./pkg
scenario-forge export ebench --suite ./suite
```

Phase 6 workflow generator smoke command:

```bash
scenario-forge workflow compose \
  --package ./pkg \
  --family pick_place \
  --binding object=object_001 \
  --binding target_zone=target_zone
```

Phase 7 layout generator smoke command:

```bash
scenario-forge layout plan --package ./pkg --difficulty easy
```

Phase 8 real2sim importer smoke commands:

```bash
scenario-forge real2sim import --result ./real2sim_result.yaml --out ./pkg
scenario-forge real2sim cousins --package ./pkg --plan ./cousin_plan.yaml --out ./suite
```

Phase 9/10 suite factory smoke commands:

```bash
scenario-forge suite generate --spec examples/suite_spec_smoke.yaml --out ./suite
scenario-forge suite quality --suite ./suite
```

Phase 10.x EOS handoff environment:

```bash
export EEOS_ENV_ROOT=/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310
export EEOS_PYTHON="$EEOS_ENV_ROOT/bin/python"
"$EEOS_PYTHON" --version
```

Use `EEOS_PYTHON` for EOS static import checks of Scenario Forge package and
suite artifacts. On 2026-07-04 this environment existed locally and reported
Python 3.10.20.

Runtime smoke checks are lane-specific and must not replace the global EOS
project environment:

```text
IsaacSim41 local runtime:
  /cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-isaacsim41-py310/bin/python

Newton / EBench experimental runtime:
  /cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-newton-ebench-experimental-py310/bin/python

OpenPI EBench model sidecar:
  /cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-sidecar-openpi-ebench-py311/bin/python
```

Phase 10.x handoff gate smoke:

```bash
scenario-forge suite generate \
  --spec examples/suite_spec_phase10x_golden.yaml \
  --out /tmp/scenario-forge-phase10x-suite
scenario-forge suite phase10x \
  --suite /tmp/scenario-forge-phase10x-suite \
  --eos-python "$EEOS_PYTHON" \
  --external-evidence examples/phase10x_external_evidence.yaml \
  --runtime-smoke examples/phase10x_runtime_smoke.yaml \
  --rc-min-packages 10 \
  --rc-max-packages 20 \
  --strict
```

The example uses the Phase 10.1 golden-pack size of 10-20 tasks so it can run
quickly in development. A formal Phase 10.5 release-candidate gate keeps the
default 50-100 task range by omitting the `--rc-min-packages` and
`--rc-max-packages` overrides.

Heavy simulator checks are not part of the bootstrap lane. Future simulator checks should be
separate targets and marked so pure package validation remains fast.

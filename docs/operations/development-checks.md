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
- v0.2 starter package scaffold, task compile, scene compile, EBench export,
  and package check smoke;
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

Heavy simulator checks are not part of the bootstrap lane. Future simulator checks should be
separate targets and marked so pure package validation remains fast.

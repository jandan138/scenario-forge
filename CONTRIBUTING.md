# Contributing

## Development Loop

```bash
python -m pip install -e ".[dev,usd]"
make ci-check
```

`make ci-check` matches GitHub's portable gate. Use `make check` in the managed
internal environment to include tests that require local generated artifacts.

Write tests before production behavior. Keep package validation and schema helpers runnable
without simulator SDKs.

## Boundaries

- Put portable contracts in `core/`, `schemas/`, `generation/`, `assets/`, `artifacts/`, and
  `evaluation/`.
- Put simulator or external tool code in `adapters/`.
- Do not import `pxr`, `omni`, Isaac Sim, Habitat, ManiSkill, or OmniGibson outside adapters.
- Do not commit large assets, videos, frames, simulator dumps, or model checkpoints.

## Generated Evidence

Commit small manifests, fixtures, and claim-bearing reports when they explain a decision.
Store large generated artifacts outside git and add an entry under `external_artifacts/`.

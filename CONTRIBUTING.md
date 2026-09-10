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

## Scene Authoring and Standards Maintenance

Read the [standards index](docs/standards/README.md) and applicable topics before
changing scenes. Record the relevant rule IDs and scope. After validation
appropriate to the change, update the affected canonical rules, design links,
operations instructions and evidence record together; explain when no general
rule needs changing. See the [workflow and templates](docs/standards/maintenance.md).

Unverified proposals stay in design documents. Core package/schema/API contracts
retain their existing design-document authority. Existing deliveries keep their
bytes and evidence; adoption happens in new work or a new revision. This workflow
adds neither a synchronization tool nor a CI/approval gate.

## Boundaries

- Put portable contracts in `core/`, `schemas/`, `generation/`, `assets/`, `artifacts/`, and
  `evaluation/`.
- Put simulator or external tool code in `adapters/`.
- Keep `pxr`, `omni`, Isaac Sim, Habitat, ManiSkill, and OmniGibson imports out of
  pure package layers. Simulator-specific adapters and tool/validation entrypoints
  own those integrations; they must not turn into dependencies of the pure layers.
- Do not commit large assets, videos, frames, simulator dumps, or model checkpoints.

## Generated Evidence

Commit small manifests, fixtures, and claim-bearing reports when they explain a decision.
Store large generated artifacts outside git and add an entry under `external_artifacts/`.

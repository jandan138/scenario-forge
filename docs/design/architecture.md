# Architecture

Scenario Forge is a portable scenario package compiler.

It owns the upstream preparation steps needed before an evaluator can run:

- asset references and licenses;
- scene instance manifests;
- task and robot specifications;
- portable metric and validation metadata;
- adapter export boundaries for simulator-specific artifacts.

It does not own episode execution, model serving, trace capture, evaluator runtime, or leaderboard
reporting. Those belong to downstream systems such as EBench and `embodied-eval-os`.

## Layers

```text
core/          simulator-neutral references and errors
schemas/       versioned package schema helpers and JSON Schema artifacts
generation/    deterministic package generation plans
assets/        asset references, hashes, licenses, and resolver boundaries
artifacts/     package layout and provenance helpers
evaluation/    portable metric and split references
adapters/      external tools and simulator exports
```

The pure layers must not import heavy simulator stacks. This is enforced by
`tests/test_architecture_boundaries.py`.

## External Tool Boundary

ConvertAsset owns USD/MDL/mesh/GLB processing. Scenario Forge may build command plans for
ConvertAsset public CLI entry points, but it must not import or reimplement conversion internals.

Isaac, Habitat, ManiSkill, OmniGibson, and future simulator integrations belong under
`src/scenario_forge/adapters/<name>/`.

## Downstream Contract

The durable output is a package directory with `manifest.yaml` plus referenced files. Downstream
systems should read the manifest and files, not infer package shape from simulator-specific
artifacts.

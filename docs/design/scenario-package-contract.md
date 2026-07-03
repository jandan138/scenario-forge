# Scenario Package Contract

The bootstrap schema version is `scenario-package/v0.1`.

Required files:

```text
manifest.yaml
scene.usda
scene_instances.yaml
task.yaml
robot.yaml
validation_report.yaml
```

`manifest.yaml` must declare:

- `schema_version`;
- `scenario_id`;
- `exports`, currently `ebench` and/or `embodied-eval-os`;
- `files`, mapping logical file roles to paths.

## Semantics

`scene.usda` is the portable scene entry point or placeholder for adapter export. It does not by
itself prove that a scenario is executable.

`scene_instances.yaml` describes instantiated objects, asset IDs, poses, semantic tags, and initial
state.

`task.yaml` describes instruction text, success predicates, and safety rules.

`robot.yaml` describes robot identity, embodiment, action space, and sensors.

`validation_report.yaml` records checks. `not_run` is never equivalent to `passed`.

## Future Schema Additions

Planned fields:

- content-addressed asset references;
- deterministic generation seeds;
- splits;
- metric specs;
- provenance and source dataset references;
- adapter export manifests under `adapters/<simulator>/`.

The v0.2 product contract draft is tracked in
[Scenario Package v0.2](package-v0.2.md). The current implementation still
supports the v0.1 bootstrap contract.

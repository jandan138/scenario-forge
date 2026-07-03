# Scenario Package Contract

Scenario Forge currently supports two package manifest versions:

- `scenario-package/v0.1`: bootstrap format, still readable for compatibility.
- `scenario-package/v0.2`: product format, used by the default scaffold and
  package validation path.

## v0.1 Bootstrap Contract

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
[Scenario Package v0.2](package-v0.2.md).

## v0.2 Product Contract

Required manifest fields:

- `schema_version: scenario-package/v0.2`;
- `package_id`;
- `scenario_domain`;
- `package_mode`, either `fat` or `locked`;
- `targets`, currently `ebench` and/or `embodied-eval-os`;
- `entrypoints`, including `generation_plan`, `scene_usd`,
  `scene_instances`, `task`, `robot`, and `metrics`;
- `assets.manifest` and `assets.lock`;
- `validation.report` and `validation.minimum_required_level`;
- `provenance.summary`.

`scenario-forge package scaffold` writes the v0.2 layout by default. `package
check` validates referenced v0.2 files and runs the asset-lock check because a
formal v0.2 package must carry `locks/asset_lock.yaml`.

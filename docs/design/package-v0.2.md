# Scenario Package v0.2

Status: Phase 5 package contract implemented for scaffold, manifest loading,
package validation, asset-lock validation, static USD compilation, `pick_place`
task/predicate/metric compilation, EBench static export, and JSON Schema
artifact scope. Broader nested semantic validation and runtime checks remain
future work.

`scenario-package/v0.1` is the bootstrap format. `scenario-package/v0.2` is the
product format for EBench-compatible task package generation. It is allowed to
change before v1.0, but each incompatible change must have a documented migration path.

## Purpose

The v0.2 package contract makes generation, assets, task semantics, validation,
and adapter export explicit enough for downstream evaluators to consume without
inferring meaning from simulator-specific artifacts.

Scenario Forge owns:

- package shape and schema;
- generation plans;
- asset manifests and locks;
- scene instance manifests and USD scene entry points;
- task, predicate, robot, and metric specifications;
- validation evidence and provenance;
- adapter export artifacts.

Scenario Forge does not own episode execution, model interfaces, simulator runtime,
trace capture, benchmark reports, or leaderboards.

## Standard Layout

```text
scenario_package/
  manifest.yaml
  generation_plan.yaml
  scene/
    main.usda
    layout.yaml
    instances.yaml
  task/
    task.yaml
    task_graph.yaml
    predicates.yaml
    safety_rules.yaml
  robot/
    robot.yaml
    robot_profile.yaml
  metrics/
    metrics.yaml
    splits.yaml
  assets/
    asset_manifest.yaml
    objects/
    robots/
    environments/
  locks/
    asset_lock.yaml
    generator_lock.yaml
    schema_lock.yaml
  evidence/
    validation_report.yaml
    static_checks.yaml
    asset_checks.yaml
    layout_checks.yaml
    adapter_checks.yaml
    runtime_smoke.yaml
  provenance/
    provenance.yaml
    source_refs.yaml
    generation_trace.jsonl
  adapters/
    ebench/
      package.yaml
      task_entrypoint.yaml
      adapter_report.yaml
    embodied-eval-os/
      package.yaml
      adapter_report.yaml
```

Small examples in git may omit heavy asset payloads. A formal v0.2 package must
always include an asset lock. `package_mode: fat` means assets are materialized
under `assets/` in addition to being locked. `package_mode: locked` means assets
may remain external if the lock and resolver can restore them.

## Manifest

`manifest.yaml` is the durable package index. Downstream systems should read this
manifest and referenced files instead of inferring package shape from directories.

Required top-level fields:

```yaml
schema_version: scenario-package/v0.2
package_id: workbench_pick_place_0001
scenario_domain: scientific_workbench
package_mode: fat
targets:
  - ebench
  - embodied-eval-os
entrypoints:
  generation_plan: generation_plan.yaml
  scene_usd: scene/main.usda
  scene_instances: scene/instances.yaml
  task: task/task.yaml
  robot: robot/robot.yaml
  metrics: metrics/metrics.yaml
assets:
  manifest: assets/asset_manifest.yaml
  lock: locks/asset_lock.yaml
validation:
  report: evidence/validation_report.yaml
  minimum_required_level: adapter_static_validated
provenance:
  summary: provenance/provenance.yaml
```

Rules:

- `schema_version` must be `scenario-package/v0.2`.
- `package_id` must be stable within a suite.
- `package_mode` must be `fat` or `locked`.
- `targets` must name downstream export targets, not simulator runtimes.
- `entrypoints.generation_plan`, `entrypoints.scene_usd`,
  `entrypoints.scene_instances`, `entrypoints.task`, `entrypoints.robot`, and
  `entrypoints.metrics` are required.
- `assets.manifest`, `assets.lock`, `validation.report`,
  `validation.minimum_required_level`, and `provenance.summary` are required.
- EBench-targeted packages must include `assets.lock`, `scene_usd`, `task`, `robot`,
  `metrics`, and `validation.report`.
- Adapter outputs must live under `adapters/<target>/` and must not mutate the
  portable manifest in place.

## Generation Plan

`generation_plan.yaml` is the auditable intermediate contract between requests and
compiled packages. It records task intent, seed, domain, target exports, package
mode, required assets, layout constraints, predicates, validation requirements,
and provenance.

Allowed producers include hand-authored plans, CLI commands, LLM planners,
protocol grounders, workflow composers, and real-to-sim ingestors. Scenario Forge
core only requires the plan to validate against schema before compilation.

## External Producer Contract

External systems may help produce package inputs, but the package contract stays
Scenario Forge-owned.

LabBuilder-style producers may contribute protocol steps, required assets,
layout constraints, safety rules, and layout validation evidence. SimFoundry-style
producers may contribute reconstructed assets, scene/object poses, physics
metadata, task-cousin proposals, source media references, and reconstruction
evidence.

Rules:

- External producers write Scenario Forge schemas. They do not place upstream
  pipeline schemas directly into the portable manifest.
- Producer name, version, prompts, source media, model/tool versions, and
  confidence reports are provenance/evidence, not package identity.
- Assets from external producers must be represented in `assets/asset_manifest.yaml`
  and `locks/asset_lock.yaml` before they can be referenced by `scene/main.usda`.
- External validation may raise confidence, but it must be recorded as evidence
  and must not claim runtime execution unless produced by an adapter or downstream
  runtime.
- The core package remains simulator-neutral even when an upstream producer used
  simulator-specific tools internally.

## Validation Ladder

v0.2 uses named validation levels:

```text
L0 generated
L1 package_schema_validated
L2 asset_locked
L3 usd_static_validated
L4 semantic_validated
L5 layout_static_validated
L6 adapter_static_validated
L7 simulator_smoke_validated
L8 runtime_evidence_validated
L9 benchmark_quality_validated
```

Minimum delivery targets:

- Single EBench package: at least `L6 adapter_static_validated`.
- Formal benchmark suite: at least `L7 simulator_smoke_validated`.
- Public high-quality benchmark suite: at least `L9 benchmark_quality_validated`.

`not_run` is not equivalent to `passed`. A package may report lower validation
levels honestly, but it must not claim release readiness without evidence.

## Implemented Scope

The Phase 2 implementation provides:

- default `scenario-forge package scaffold` output using the v0.2 layout;
- `load_package_manifest()` support for both `scenario-package/v0.1` and
  `scenario-package/v0.2`;
- v0.2 manifest validation for package ID, package mode, targets, entrypoints,
  asset manifest/lock references, validation level, and provenance summary;
- `package check` validation of v0.2 referenced files and `locks/asset_lock.yaml`;
- v0.2 scene entrypoint discovery for asset-lock USD reference checks;
- `src/scenario_forge/schemas/jsonschema/scenario-package-v0.2.schema.json`.

This scope fixes the package contract. It does not compile `scene/main.usda`,
generate EBench adapter outputs, migrate v0.1 packages, or validate nested
task/scene/robot/metric schemas beyond referenced-file presence.

## Migration

v0.1 remains the bootstrap format. v0.2 should not inherit v0.1 layout constraints
when they conflict with product needs. A future migration command should create a
new v0.2 package rather than rewriting the old package in place:

```bash
scenario-forge package migrate \
  --from scenario-package/v0.1 \
  --to scenario-package/v0.2 \
  --in old_package \
  --out new_package
```

## Phase 0 Decisions

- v0.2 is the product format and is not limited by v0.1.
- `generation_plan.yaml` is the standard generation entry point.
- `scene/main.usda` is the standard USD scene entry point.
- EBench is a first-class adapter target.
- Every formal v0.2 package must have `locks/asset_lock.yaml`.
- Fat packages materialize assets locally and still carry an asset lock.
- Simulator-specific files are derived artifacts under `adapters/<target>/`.
- Heavy generated assets stay out of git unless they are tiny fixtures.

## Future Work

- JSON Schema files for nested v0.2 contracts.
- v0.1 to v0.2 migration command.
- Package writer helpers for emitting full v0.2 packages from generation plans.
- Concrete EBench format mapping once the downstream schema is pinned.

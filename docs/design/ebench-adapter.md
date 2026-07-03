# EBench Adapter Design

Status: Phase 0 product contract draft. This document is normative for the
v0.2 EBench export direction, not evidence that EBench export is implemented.
The exact EBench wire format is provisional until the downstream schema is pinned.

The EBench adapter exports portable Scenario Forge packages into
EBench-compatible adapter artifacts. It is a downstream export adapter, not an
episode runner or evaluator runtime.

## Responsibilities

The adapter reads a Scenario Forge package and writes derived files under
`adapters/ebench/`.

It is responsible for:

- checking that `manifest.yaml` targets `ebench`;
- reading the package entry points declared by the manifest;
- validating the presence of scene USD, task, robot, metrics, asset lock, and
  validation report files;
- generating an EBench package descriptor;
- generating task entrypoint metadata and runtime hints;
- writing `adapter_report.yaml` with pass/fail status and blockers;
- exporting suite-level task indexes when given a suite manifest.

It is not responsible for:

- running episodes;
- serving models;
- recording traces;
- implementing EBench metrics runtime;
- publishing leaderboards or benchmark reports;
- mutating the portable package manifest in place.

## Package Export

The standard output directory is:

```text
scenario_package/
  adapters/
    ebench/
      package.yaml
      task_entrypoint.yaml
      adapter_report.yaml
```

Example `adapters/ebench/package.yaml`:

```yaml
schema_version: ebench-scenario-export/v0.1
source_package:
  package_id: workbench_pick_place_0001
  schema_version: scenario-package/v0.2
entrypoints:
  scene_usd: ../../scene/main.usda
  task: ../../task/task.yaml
  robot: ../../robot/robot.yaml
  metrics: ../../metrics/metrics.yaml
assets:
  asset_lock: ../../locks/asset_lock.yaml
runtime_hints:
  simulator: isaac_or_usd_capable
  reset_policy: deterministic
  max_episode_steps: 300
  success_metric: task_success
adapter_validation:
  status: passed
  report: adapter_report.yaml
```

## Export Gates

A package export should fail with structured blockers when:

- the source manifest does not target `ebench`;
- the package schema is unsupported;
- `scene/main.usda` is missing;
- `task/task.yaml` is missing;
- `robot/robot.yaml` is missing;
- `metrics/metrics.yaml` is missing;
- `locks/asset_lock.yaml` is missing for a formal EBench package;
- no primary success metric is declared;
- success predicates do not bind to scene instances;
- required validation level is not met.

The default single-package target is `L6 adapter_static_validated`. Runtime smoke
evidence can raise the package to `L7`, but the EBench adapter should not fake
runtime evidence.

## Suite Export

Suite export reads `suite_manifest.yaml` and writes:

```text
suite/
  adapters/
    ebench/
      suite_export.yaml
      task_index.yaml
      adapter_report.yaml
```

Suite export must preserve package-level entry points, split labels, difficulty
labels, task family labels, and asset lock references. It must not merge packages
in a way that hides package-level validation results.

## Format Volatility

The core Scenario Forge package contract must not be tightly coupled to EBench's
current wire format. If EBench changes its expected package shape, only the
adapter schema and exporter should need to change. The portable package remains
the source of truth.

## Phase 0 Decisions

- EBench is a first-class target.
- EBench export artifacts live under `adapters/ebench/`.
- Adapter export success is not model evaluation success.
- Missing asset locks, missing primary success metrics, or missing scene USD are
  hard blockers for formal EBench export.
- Adapter reports must record all entry points and blockers.

## Future Work

- Concrete `ebench-scenario-export/v0.1` JSON Schema.
- Single-package exporter implementation.
- Suite export task index implementation.
- Adapter report data model and blocker taxonomy.
- Validation integration for `L6 adapter_static_validated`.
- Updates when the downstream EBench wire format changes.

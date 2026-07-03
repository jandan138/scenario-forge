# EBench Adapter Design

Status: Phase 5 static EBench adapter v0 implemented. This document is
normative for the v0.2 EBench export contract and records the implemented
single-package and suite-index export scope. The exact downstream EBench wire
format remains provisional until a downstream schema is pinned.

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
  simulator: usd_capable
  reset_policy: deterministic
  max_episode_steps: 300
  success_metric: task_success
  success_predicate: object_in_zone
adapter_validation:
  status: passed
  report: adapter_report.yaml
```

Implemented command:

```bash
scenario-forge export ebench --package ./pkg
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
- Scenario Forge package validation reports blockers.

The package exporter is static adapter validation. It does not claim runtime
load, reset, physics, or model-evaluation evidence.

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

Implemented command:

```bash
scenario-forge export ebench --suite ./suite
```

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

- Updates when the downstream EBench wire format changes.
- richer adapter blocker taxonomy once EBench publishes a pinned schema;
- runtime smoke integration in downstream runtimes.

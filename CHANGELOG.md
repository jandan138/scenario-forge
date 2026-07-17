# Changelog

## Unreleased

- Add `success.progress_rubric` (scenario-spec/v0.4, task/v0.4, metrics/v0.3,
  GenManip runtime contract v0.4): weighted progress-score rubric transport with
  aggregation semantics, activation flags, capability requirements, temporal
  kinds, and pinned upstream source refs. Rubric items are transported, not
  runtime-evaluated (`transport_only`).
- Align the golden bimanual-pour spec with the upstream five-item Progress
  Score; liquid items declared inactive pending the liquid measurement adapter
  contract.
- Static EBench export resolves the primary metric via
  `aggregation.primary_metric_id` when no `primary_success` role exists.

## 0.1.0 - 2026-07-03

- Bootstrap Scenario Forge as a portable scenario package compiler.
- Add starter package scaffold and structural package validation.
- Add ConvertAsset command-plan adapter boundary.
- Add architecture tests preventing simulator imports in pure package layers.

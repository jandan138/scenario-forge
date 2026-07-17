# 2026-07-17 Progress Rubric v0.4 (M1, transport_only)

## Outcome

The scenario package can now carry the upstream weighted Progress Score rubric
from the wetlab task-design document. This is M1 of the rubric plan: schema and
transport only. No rubric item is evaluated by any runtime; M0 (EOS executes the
existing three predicates) and M2 (EOS weighted-score reconciliation) remain
downstream work.

## What changed

- Coordinated version bump: `scenario-spec/v0.4`, `task/v0.4`,
  `metrics/v0.3`, `scenario-forge-genmanip-runtime-contract/v0.4`.
  `predicates/v0.3` is unchanged and reused.
- `success.progress_rubric` is a parallel block next to the exact ordered
  predicates. The predicates stay the GenManip diagnostic-projection contract;
  the rubric is the scoring authority. See
  [the design doc](../design/progress-rubric.md).
- The golden bimanual-pour spec declares the five upstream items with their
  declared weights: `source_lifted` 0.20 (instant),
  `openings_aligned_while_grasped` 0.30 (sustained, align→pour window),
  `liquid_transfer_majority` 0.20 (terminal, inactive),
  `liquid_transfer_complete` 0.20 (terminal, inactive),
  `source_returned_released` 0.10 (terminal). Aggregation is
  `declared_sum + zero`, so the current achievable ceiling is 0.60 by design.
- Every rubric item carries a pinned `source_ref` (Feishu doc revision 1549,
  sheet revision 564, extracted 2026-07-17). Weights re-align in batches.
- The two liquid items are declared with
  `requires: [liquid_sim.contained_volume_ratio]` and `active: false`. The
  measurement semantics live in the
  [liquid measurement adapter contract](../design/liquid-measurement-adapter-contract.md);
  activation additionally requires per-vessel fluid-safe wrappers and a
  qualified runtime.
- The GenManip runtime contract transports the rubric and lists all five items
  under `execution.progress_rubric.unevaluated_metric_ids` with
  `scored_here: false`. `contract_status` stays `transport_only`.
- Static EBench export resolves its primary metric via
  `aggregation.primary_metric_id` (`openings_aligned_while_grasped`).

## Explicitly not claimed

- No rubric item has ever been evaluated in a runtime.
- The existing three predicates' thresholds are unchanged; M0 calibration is
  still pending.
- No liquid transfer is measurable on the current vessels.
- The other 17 upstream tasks' rubrics are not aligned.

## Evidence

- 353 tests pass (`make check`), including new coverage: rubric validation
  (weight sum, temporal kinds, window order, invariant duplication), metrics/v0.3
  derivation against its JSON schema, v0.4 runtime-contract transport against
  its JSON schema.

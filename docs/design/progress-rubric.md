# Progress Rubric (scenario-spec/v0.4)

`scenario-spec/v0.4` adds an optional `success.progress_rubric` alongside the
existing `success.predicates` contract. The two have different jobs:

- `success.predicates` (unchanged): the exact ordered bimanual contract that the
  GenManip adapter projects into native diagnostic goals.
- `success.progress_rubric` (new): the authoritative weighted scoring rubric,
  aligned with the upstream task-design Progress Score. It is transported, not
  natively evaluated, by the current adapter runtimes.

## Shape

```yaml
success:
  operator: all
  claim_scope: kinematic_proxy
  predicates: [...]
  progress_rubric:
    aggregation:
      type: weighted_progress_score
      normalization: declared_sum        # or active_subset_renormalize
      inactive_treatment: zero           # or exclude
      primary_metric_id: openings_aligned_while_grasped  # optional
    items:
      - id: source_lifted
        weight: 0.20                     # (0, 1]; all item weights sum to 1.0
        active: true                     # default true
        requires: []                     # capability names; empty = always measurable
        temporal:
          kind: instant                  # instant | sustained | terminal
          window:                        # sustained only
            from_step: align_openings
            through_step: tilt_pour
        condition:
          type: object_lifted
          parameters: {...}
        source_ref:                      # upstream traceability, pinned
          document_url: https://...
          document_revision: 1549
          extracted_on: "2026-07-17"
          item: 时序1
```

## Normalization semantics

`declared_sum + zero` (the golden bimanual-pour choice): the score denominator is
always the declared total 1.0, and inactive items score zero. Scores stay
comparable before and after a capability (for example liquid measurement) is
activated; the current achievable ceiling is the active subset sum (0.60 for the
golden task). `active_subset_renormalize + exclude` rescales over active items
only and must always be reported as a labelled secondary copy, never silently.

## Condition types

- `object_lifted` — object clears its support surface by `min_clearance_m`;
  optional `held_by` restricts the measurement to an actor-held lift.
- `pose_while_grasped` — compound condition: `grasp` (actor holds object) AND a
  nested pose predicate, over a `sustained` window.
- `object_released_on_support` — terminal composite AND: upright within
  `upright_max_tilt_deg`, inside absolute `region`, on `support_surface`, and
  gripper `released`. Uses absolute semantics; do not confuse with the relative
  `object_returned_to_post_warmup_pose` predicate.
- `liquid_transfer_ratio` — declared for capability-gated activation. See
  [Liquid Measurement Adapter Contract](liquid-measurement-adapter-contract.md).

## Validation rules (core)

- Item ids unique; each weight in (0, 1]; weights sum to 1.0 ± 1e-6.
- `sustained` items require a window over known, ordered steps; `window` is
  rejected for other temporal kinds.
- Object/frame/actor references must resolve, including nested pose predicates.
- A grasp condition that overlaps a `maintain_grasp` invariant on the same
  (actor, object, window) is rejected: a condition is a hard gate or a scored
  item, never both.
- `progress_rubric` requires `scenario-spec/v0.4`; the exact ordered bimanual
  predicate contract is still required and unchanged.

## Derived artifacts and transport

- `metrics/metrics.yaml` becomes `metrics/v0.3` with top-level `aggregation` and
  `role: progress_component` items when a rubric is present; otherwise the
  legacy `metrics/v0.2` derivation is unchanged.
- `task/task.yaml` becomes `task/v0.4` and embeds the full rubric.
- `task/predicates.yaml` stays `predicates/v0.3`.
- The GenManip runtime contract becomes
  `scenario-forge-genmanip-runtime-contract/v0.4`, transports the rubric inside
  `success`, and declares every rubric item under
  `execution.progress_rubric.unevaluated_metric_ids` with `scored_here: false`.
  `contract_status` remains `transport_only`: no rubric item is claimed to be
  evaluated by the current adapter runtime.
- Static EBench export resolves its primary metric through
  `aggregation.primary_metric_id` when no `primary_success` role exists.

## Source-of-truth and update policy

The rubric mirrors the upstream task-design Progress Score (see
[the generated reference copy](../reference/scientific-workbench-task-design.html)). Weights are
re-aligned in batches, not per upstream edit; every item carries a pinned
`source_ref` (document revision, sheet revision, extraction date).

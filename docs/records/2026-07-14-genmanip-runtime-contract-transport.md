# 2026-07-14 GenManip Runtime-contract Transport

## Outcome

Scenario Forge now transports its normalized task semantics inside every supported
GenManip episode at:

```text
episode_metadata.json
  -> task_data
  -> scenario_forge_runtime_contract
```

The JSON mapping is authoritative. `meta_info.pkl` remains only the fixed-protocol
compatibility encoding of that same episode mapping, so there is no independent
sidecar that can drift. `package_manifest.json.semantic_contract` records the
episode path and JSON Pointer needed to discover the contract. The legacy manifest
`success_contract` remains a labelled, validated projection for compatibility, not
a second authority.

The versioned `scenario-forge-genmanip-runtime-contract/v0.1` contains runtime
UID/state-prim mappings, initial poses, object-local named frames, the robot profile
and actor/end-effector bindings, ordered steps, invariants, and success predicates.
The table mapping preserves GenManip's real all-zero layout UID instead of
incorrectly conflating it with the `table_uid: table` configuration selector.

## Claim boundary

This delivery is intentionally `transport_only`:

- GenManip's native root-based goal remains a diagnostic compatibility projection.
- No new metric type is registered or added to `task_data.goal`.
- No opening-frame threshold is invented; 2 cm, 2–5 cm, and the 80-degree maximum
  remain proposed gates.
- Steps and invariants are preserved semantics, not proof that grasp, specified-arm
  use, contact, hold, or release occurred.
- The flask and cylinder wrapper/rigid-body identity blocker remains open.

Therefore this change does not supersede the historical frozen baseline, does not
make the task oracle-ready, and does not authorize a five-stage success claim.

## Downstream handoff

GenManip must explicitly pass the embedded contract to a frame-aware metric (or
project an accepted explicit frame predicate into a registered metric config).
Before activation, it must feature-gate the required metric capability and bind
each runtime UID to the qualified rigid root. EOS then owns rollout execution,
post-warmup baseline capture, per-stage contact/grasp evidence, and contract/package
hash preservation.

Once the vessel assets, accepted predicate thresholds, and GenManip consumer are
available, Scenario Forge will regenerate and refreeze a new exact package. The
previous `59d6024d...be4` tree digest remains historical preflight evidence only.

## Verification

Tests cover the exact dual-arm contract, table UID special case, JSON/pickle
equivalence, schema validation against the real export, tasks without named frames
or invariants, unknown frame references, invalid frame poses, deterministic export,
and the golden task's corrected opening frames and same-side actor assignment.

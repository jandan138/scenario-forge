# 2026-07-05 Phase 12 Registry / Viewer / Handoff / Policy Evidence

## Status

Phase 12.0-12.6 passed on the retained Phase 11 three-task canary.

Authoritative index:

```text
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/phase11_three_task_suite/evidence/phase12_current_gate_index.yaml
  overall_status: phase13_allowed
  phase13_allowed: true
  12.0-12.6: passed
```

Generation command:

```bash
PYTHONPATH=src python -m scenario_forge.cli suite phase12 \
  --suite docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/phase11_three_task_suite \
  --gate-index docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/phase11_current_gate_index.yaml \
  --strict
```

## Outputs

```text
registry/package_registry.yaml
registry/asset_registry.yaml
registry/registry_query_contract.yaml
registry/registry_snapshot.yaml
registry/resolver_snapshot.yaml
registry/snapshot_digest.txt
viewer/readonly_index.yaml
viewer/index.md
handoff/ebench_eos_handoff_examples.yaml
adapters/simulators/export_descriptors.yaml
registry/hosted_internal_registry_alpha.yaml
evidence/phase12_0_registry_readiness_freeze.yaml
evidence/phase12_1_registry_contract_gate.yaml
evidence/phase12_2_registry_snapshot_gate.yaml
evidence/phase12_3_readonly_viewer_gate.yaml
evidence/phase12_4_ebench_eos_handoff_gate.yaml
evidence/phase12_5_multi_simulator_export_gate.yaml
evidence/phase12_6_public_release_policy_closure_gate.yaml
```

Snapshot digest:

```text
sha256:7dbf22b2ea435cb6c2eba19ee58d5c9aaebf728bea9a303a359439d2e0132007
```

## Boundary

Phase 12 indexes retained package, asset, evidence, handoff, descriptor, and policy
metadata. It does not run EOS episodes, evaluate models, publish leaderboards, or
reimplement ConvertAsset material/MDL/mesh conversion.

The builder rejects mutable `/tmp` public snapshot refs and prefers retained evidence
artifacts. For final-pass variants it uses current gate filenames such as
`nomdl_relink` and `contactfixed` as artifact selection hints.

2026-07-05 closure hardening:

- Public registry, snapshot, viewer, and handoff outputs no longer expose local
  filesystem `source_uri` values such as `/tmp/...`, `/cpfs/...`, or `file://...`.
  They are replaced with `retained-artifact://...` references back to the retained
  asset manifest.
- The retained three-task Phase 12 suite was regenerated after this hardening and
  remains `overall_status=phase13_allowed` with 12.0-12.6 passed.

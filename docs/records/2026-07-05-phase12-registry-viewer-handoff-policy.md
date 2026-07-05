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
sha256:dd49ae0063d90e891b863a4ced8e8da7cea9c194113faa21a8195893028f2586
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

2026-07-05 asset-readiness metadata update:

- Asset registry entries now include `semantic_tags`, `affordances`,
  `role_suitability`, `material_closure`, `physics_readiness`, and
  `export_eligibility`.
- The material closure audit records MDL `texture_2d(...)` texture dependencies
  and text/binary USD `.mdl` dependencies. The retained official apple and bowl
  entries record package-local `gltf/pbr.mdl` refs plus approved runtime MDL
  evidence from retained render metadata.
- `phase13_allowed=true` remains a registry/readiness transition signal, not a
  claim that every asset can be selected by every Phase 13 request. Phase 13
  enforces selected-asset `material_closure.status=passed` and fails closed with
  `handoff/asset_intake_blockers.yaml` when a chosen asset is not material-ready.
  Runtime MDL modules only count as passed when retained material preflight
  evidence records status pass, no blocked dependencies, search roots, and a
  resolved runtime path.

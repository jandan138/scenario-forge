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

## 2026-07-06 S2D-12 Handoff Closure

ConvertAsset has completed the S2D-12 soap-to-dish clean asset handoff. The
handoff is now indexed by Phase 12 as external evidence, without copying
ConvertAsset conversion logic into Scenario Forge.

Handoff input:

```text
/cpfs/user/zhuzihou/assets/convertasset_research/experiments/ebench/official_asset_closure/soap_to_dish_e1cf0d5b4d76_20260705/evidence/s2d12_phase12_clean_registry_mapping.yaml
```

Clean asset entry:

```text
asset_uid: official_ebench_scene@e1cf0d5b4d76_native_phase12_clean
source_package_id: s2d12_native_mdl_phase12_clean
canonical_usd: asset.usda
content_sha256: sha256:1fedd44093435591458cf10c303bdf2e856e20b18608307ed7e7dc59b71f0673
material_closure.status: passed
material_closure.missing_material_refs: []
material_closure.missing_textures: []
```

Scenario Forge implements this as a Phase 12 asset-handoff overlay:

```bash
PYTHONPATH=src python -m scenario_forge.cli suite phase12 \
  --suite docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/phase11_three_task_suite \
  --gate-index docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/phase11_current_gate_index.yaml \
  --asset-handoff /cpfs/user/zhuzihou/assets/convertasset_research/experiments/ebench/official_asset_closure/soap_to_dish_e1cf0d5b4d76_20260705/evidence/s2d12_phase12_clean_registry_mapping.yaml \
  --strict
```

Regenerated outputs include `asset_registry.yaml`, `registry_snapshot.yaml`,
`resolver_snapshot.yaml`, `snapshot_digest.txt`, asset-level handoff metadata,
and refreshed Phase 12 gates. Public registry, resolver, snapshot, and handoff
example outputs redact local `/cpfs` and `/tmp` paths. The retained internal
handoff asset manifest/lock keep the real clean USD path for Phase 13
materialization. The old failed `official_ebench_scene@e1cf0d5b4d76` entry
remains traceable until a later policy explicitly removes superseded entries.

Closure evidence:

```text
registry/asset_registry.yaml:
  official_ebench_scene@e1cf0d5b4d76_native_phase12_clean
registry/resolver_snapshot.yaml:
  official_ebench_scene@e1cf0d5b4d76_native_phase12_clean
handoff/ebench_eos_handoff_examples.yaml:
  asset_handoffs[0].replacement_asset_uid
evidence/phase12_current_gate_index.yaml:
  overall_status=phase13_allowed
```

Detailed planning record:

```text
docs/records/2026-07-06-s2d12-soap-to-dish-phase12-phase13-plan.md
```

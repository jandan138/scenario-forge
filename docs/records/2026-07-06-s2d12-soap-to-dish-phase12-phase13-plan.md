# 2026-07-06 S2D-12 Soap-to-Dish Phase 12 / Phase 13 Plan

## Status

ConvertAsset has completed the S2D-12 soap-to-dish handoff at the asset-closure
boundary. Scenario Forge has now promoted the clean scene asset into the Phase
12 retained registry and regenerated a fresh Phase 13 soap-to-dish static
candidate using the clean scene UID and the real `official_ebench_soap` asset.
Scenario Forge has now promoted soap-to-dish into the passing Phase 13 batch.
The package has passed 13.6 overview visual review, 13.8 execution/predicate
canary ingestion, and the refreshed 13.9 batch quality gate.

Product status:

```text
ConvertAsset S2D-12 handoff: complete
Phase 12 registry promotion: complete
Phase 13 soap-to-dish compile: complete, non-smoke static candidate
Phase 13.6 overview visual: complete, engine-native render + visual PASS
Phase 13.8 execution/predicate: complete, package-matching EOS predicate PASS
Phase 13.9 batch inclusion: complete, soap-to-dish listed as formal-ready
```

Implemented Phase 12 evidence:

```text
registry/asset_registry.yaml:
  asset_uid=official_ebench_scene@e1cf0d5b4d76_native_phase12_clean
  source_package_id=s2d12_native_mdl_phase12_clean
  canonical_usd=asset.usda
  material_closure.status=passed

registry/resolver_snapshot.yaml:
  asset_uid=official_ebench_scene@e1cf0d5b4d76_native_phase12_clean
  asset_lock=handoff/asset_handoffs/official_ebench_scene_e1cf0d5b4d76_native_phase12_clean_asset_lock.yaml

handoff/ebench_eos_handoff_examples.yaml:
  asset_handoffs[0].replacement_asset_uid=official_ebench_scene@e1cf0d5b4d76_native_phase12_clean

evidence/phase12_current_gate_index.yaml:
  overall_status=phase13_allowed
```

Public registry, resolver, snapshot, and handoff example outputs redact local
`/cpfs` and `/tmp` paths. The retained internal handoff asset manifest/lock keep
the real clean USD path so Phase 13 can materialize the official asset.

Implemented Phase 13 static candidate evidence:

```text
external full package:
  /cpfs/user/zhuzihou/assets/scenario_forge_runs/phase13_s2d12_soap_to_dish_static_candidate_20260706/package

retained small evidence snapshot:
  docs/records/evidence/2026-07-05-phase13-image-grounded-task-factory/phase13_s2d12_soap_to_dish_static_candidate

package/evidence/phase13_current_gate_index.yaml:
  overall_status=phase13_formal_package_ready
  static_candidate_ready=true
  formal_package_ready=true
  overview_visual_ready=true
  execution_predicate_ready=true
  next_required_gate=13.9

package/task/task_contract.yaml:
  manipulated_object.asset_uid=official_ebench_soap@c147837fe9bd
  target_container.asset_uid=official_ebench_scene@e1cf0d5b4d76_native_phase12_clean
  target_container.semantic_label=soap_dish
  target_container.source_uid=_01
  target_container.fixture_kind=environment_fixture
```

## Handoff

ConvertAsset handoff:

```text
/cpfs/user/zhuzihou/assets/convertasset_research/experiments/ebench/official_asset_closure/soap_to_dish_e1cf0d5b4d76_20260705/evidence/s2d12_phase12_clean_registry_mapping.yaml
```

Replacement asset identity:

```text
asset_uid: official_ebench_scene@e1cf0d5b4d76_native_phase12_clean
source_package_id: s2d12_native_mdl_phase12_clean
canonical_usd: asset.usda
content_sha256: sha256:1fedd44093435591458cf10c303bdf2e856e20b18608307ed7e7dc59b71f0673
```

ConvertAsset reports the Phase12-facing material closure as:

```yaml
material_closure:
  status: passed
  missing_texture_count: 0
  missing_textures: []
  missing_material_ref_count: 0
  missing_material_refs: []
  package_local_missing_material_refs:
    - usd: asset.usda
      material: gltf/pbr.mdl
      resolved_path: gltf/pbr.mdl
  approved_runtime_mdl_dependencies:
    - module: gltf/pbr.mdl
      resolution: approved_runtime_module
      runtime_path: /isaac-sim/kit/mdl/core/mdl/gltf/pbr.mdl
```

The clean source USD is about 786 MB and must not be committed to Scenario Forge.
Scenario Forge should retain small handoff/projection/metadata evidence and keep
the large USD behind asset-lock / resolver references.

## Multi-Agent Review

Phase 12 review:

- Treat S2D-12 as an explicit asset handoff overlay, not a waiver and not a new
  core package pipeline.
- Add a Phase 12 CLI/API input such as repeated `--asset-handoff PATH`.
- Generate the normal registry first, then apply the external asset handoff
  before writing snapshot digest, resolver snapshot, viewer, and handoff outputs.
- Preserve the old failed `official_ebench_scene@e1cf0d5b4d76` entry for
  provenance unless a later policy explicitly removes superseded entries.
- Add the clean UID as a new asset entry and keep `content_sha256` authoritative.
- Avoid leaking absolute `/cpfs/...` paths into public registry fields; keep them
  as internal retained evidence refs or redacted resolver metadata.

Phase 13 / EOS review:

- Do not promote the old `/tmp/scenario-forge-phase13-batch-suite/.../soap_to_dish`
  package. It is stale pre-S2D-12 evidence blocked by `O.mdl` and missing textures.
- Do not use the ConvertAsset smoke package as formal evidence. It proves compile
  no longer fails on material closure, but it uses a smoke/minimal soap object and
  a placeholder snapshot.
- Fresh formal compile must use the clean S2D-12 scene entry and the intended
  real `official_ebench_soap` object from the Phase 12 registry.
- Preserve the old useful task semantics for EOS mapping:
  `semantic_label=soap_dish`, `source_uid=_01`, and
  `fixture_kind=environment_fixture`.
- 13.6 rendered the generated package, not just the source USD.
- 13.8 should use package-matching Phase 11 evidence generated inside or projected
  to the same Phase 13 package ID. Old soap gates for
  `ebench_soap_to_dish_canary` cannot be passed directly into 13.8 because the
  gate checks generated package ID equality.

Product / documentation review:

- Initially document S2D-12 as completed handoff evidence rather than claiming
  batch inclusion before 13.8/13.9. This blocker is now closed: soap-to-dish is
  included in the refreshed 13.9 passing batch.
- The product-visible milestone is now complete: soap-to-dish is formal-ready in
  the refreshed 13.9 batch. The retained batch keeps the duplicate apple/bowl
  retake as a regression row, so it has four passing request-level packages.

## Planned Work

### 1. Phase 12 Asset-Handoff Overlay

Implemented a Scenario Forge Phase 12 overlay input:

```bash
PYTHONPATH=src python -m scenario_forge.cli suite phase12 \
  --suite docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/phase11_three_task_suite \
  --gate-index docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/phase11_current_gate_index.yaml \
  --asset-handoff /cpfs/user/zhuzihou/assets/convertasset_research/experiments/ebench/official_asset_closure/soap_to_dish_e1cf0d5b4d76_20260705/evidence/s2d12_phase12_clean_registry_mapping.yaml \
  --strict
```

Implemented Phase 12 output:

- `registry/asset_registry.yaml` contains the clean S2D-12 asset entry.
- `registry/resolver_snapshot.yaml` contains the clean UID.
- `registry/registry_snapshot.yaml` and `snapshot_digest.txt` are regenerated.
- `handoff/ebench_eos_handoff_examples.yaml` records an asset-level handoff or
  replacement section.
- The old failed UID remains traceable.

Implemented tests:

- handoff overlay generates exact clean UID/source package/canonical USD/hash;
- material closure is passed with zero missing refs/textures and approved
  `gltf/pbr.mdl`;
- resolver snapshot includes the clean UID;
- duplicate `official_ebench_scene` entries remain disambiguable;
- negative handoff cases block when projection status is not passed, runtime
  approval is missing, or UID/source fields are inconsistent.

### 2. Phase 13 Fresh Soap Compile

Created a fresh non-smoke soap-to-dish image task result from the prior formal
soap probe semantics, changing the scene selected asset selectors:

```text
selected_asset_uid: official_ebench_scene@e1cf0d5b4d76_native_phase12_clean
selected_source_package_id: s2d12_native_mdl_phase12_clean
```

Keep:

```text
object asset: official_ebench_soap
target semantic_label: soap_dish
target source_uid: _01
target fixture_kind: environment_fixture
```

Implemented result:

```text
phase13_current_gate_index.overall_status=phase13_visual_candidate_ready
13.0-13.5 passed
13.7 passed
13.6 passed after engine-native overview render and clean-room visual review
13.8 subsequently passed with package-matching EOS predicate evidence
```

### 3. Phase 13.6 Overview Visual

Implemented by running the EOS/Isaac overview renderer against the generated
Phase 13 package. The render covers the generated package, not only the source
S2D-12 USD. The MDL search paths included Isaac runtime MDL roots.

Retained evidence:

```text
phase13_tabletop_overview.png
phase13_tabletop_overview_render_metadata.json
phase13_tabletop_overview_runtime.log
phase13_tabletop_overview_visual_review.yaml
phase13_6_factory_overview_visual_gate.yaml
```

Result:

```text
render_status=pass
material_runtime_preflight.status=pass
visual_review=PASS
phase13_6_factory_overview_visual_gate.status=passed
phase13_current_gate_index.overall_status=phase13_visual_candidate_ready
phase13_current_gate_index.next_required_gate=13.8
```

The clean-room reviewer judged the pink soap visible, the gray shallow dish or
tray-like target visible enough for the visual canary, and the countertop
overview framing usable. The review caveat is that the dish is somewhat small
and could read as a generic tray; this is non-blocking for 13.6 and must not be
treated as task success.

### 4. Phase 13.8 Execution / Predicate

Implemented package-matching retained Phase 11 evidence for the fresh Phase 13
soap package:

```text
phase11_task_execution_gate.yaml
phase11_executed_episode_gate.yaml
phase11_success_predicate_gate.yaml
phase11_post_execution_visual_review_gate.yaml
phase11_single_task_release_candidate_gate.yaml
```

Preferred path: rerun package-linked EOS/BPL19R against the generated package.
Fallback for an internal smoke must be explicitly labeled as projected evidence
and must not be promoted as final public-ready evidence.

Run:

```bash
PYTHONPATH=src python -m scenario_forge.cli image-task execution-predicate \
  --package <phase13-soap-package> \
  --single-task-rc-gate <phase13-soap-package>/evidence/phase11_single_task_release_candidate_gate.yaml \
  --strict
```

Result:

```text
selected_success_attempt=attempt_000
task_success=true
standard_model_score=1.0
phase11_task_execution_gate.status=passed
phase11_executed_episode_gate.status=passed
phase11_success_predicate_gate.status=passed
phase11_post_execution_visual_review_gate.status=passed
phase11_single_task_release_candidate_gate.status=passed
phase13_8_execution_predicate_canary_gate.status=passed
overall_status=phase13_formal_package_ready
formal_package_ready=true
execution_predicate_ready=true
next_required_gate=13.9
```

The first retained overlook final frame was not sufficient as visual evidence:
it showed the soap beside the dish from that camera angle. The post-execution
visual gate therefore uses the retained right-camera final confirmation frame,
where the soap is visibly seated in or on the gray soap dish. A clean-room
render-visual-reviewer pass is retained in
`phase11_post_execution_visual_review_bpl19r_success.yaml`.

### 5. Phase 13.9 Batch Refresh

Implemented a refreshed retained Phase 13 batch. The retained batch now has
four formal-ready request-level packages:

```text
apple_to_bowl
remote_to_holder
apple_to_bowl_retake
soap_to_dish
```

This keeps the apple/bowl retake for regression continuity and adds
soap-to-dish as the fourth formal-ready package.

Run:

```bash
PYTHONPATH=src python -m scenario_forge.cli image-task batch-quality \
  --suite <refreshed-suite-dir> \
  --quality-report <refreshed-suite-dir>/evidence/phase13_batch_factory_quality_report.yaml \
  --suite-quality-evidence <refreshed-suite-dir>/evidence/suite_quality_evidence.yaml \
  --strict
```

Result:

```text
phase13_9_batch_factory_quality_gate.status=passed
next_stage=phase13_batch_factory_ready
soap_to_dish no longer appears under blocked_probe_notes
request_count=4
formal_package_ready_count=4
```

## Boundaries

Scenario Forge may parse ConvertAsset handoff files as external evidence and may
index the resulting clean asset entry. It must not import ConvertAsset code or
copy USD/MDL/mesh/texture conversion logic.

Scenario Forge still does not run episode policies or report leaderboard results.
13.8 remains an ingestion gate over EOS/EBench-owned execution and predicate
evidence.

## Product Summary

ConvertAsset fixed the raw material problem, and Scenario Forge has now consumed
that fix end to end: registry promotion, package compile, engine-native render,
EOS predicate evidence, post-execution visual review, and 13.9 batch refresh.
Soap-to-dish is now a formal image-grounded task package in the passing batch,
not just a repaired asset.

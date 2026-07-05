# 2026-07-05 Phase 13 Image-Grounded Existing-Asset Factory Evidence

## Status

Phase 13 now has a static candidate compiler in Scenario Forge. The current
real official EBench apple/bowl probe reaches static candidate readiness after
retained runtime evidence classifies `gltf/pbr.mdl` as an approved Isaac Sim MDL
dependency. It is not a formal package release because 13.6 and 13.8 still need
fresh downstream evidence.

Implemented CLI:

```bash
PYTHONPATH=src python -m scenario_forge.cli image-task compile \
  --request image_task_request.yaml \
  --scene-result image_to_scene_result.yaml \
  --registry-snapshot registry_snapshot.yaml \
  --out /tmp/phase13_candidate \
  --strict
```

The compiler ingests `image-task-request/v0.1` and
`image-to-scene-result/v0.1`, selects only assets that exist in a Phase 12
registry snapshot, materializes retained USD bundles into a fat v0.2 package,
generates `scene/main.usda`, writes `asset_lock.yaml`, exports EBench static
adapter artifacts, and writes Phase 13 gate evidence.

The retained official apple/bowl assets expose `gltf/pbr.mdl` dependencies in
binary USD. The Phase 12 registry records the package-local unresolved ref plus
approved runtime MDL evidence from retained render metadata. Phase 13 strict
mode blocks selected assets whose `material_closure.status` is not `passed`.

## Local Completion Boundary

Local static completion means:

- 13.0-13.5 pass for scope, intake, image-result import, registry asset match,
  task contract, scene USD, asset lock, and materialization.
- 13.7 passes for package validation and EBench static export.
- `evidence/phase13_current_gate_index.yaml` records
  `overall_status=phase13_static_candidate_ready`.

This is not a formal EBench-compatible package release. The current index keeps
`formal_package_ready=false` until external gates pass:

- 13.6 engine-native overview render and render-visual-reviewer PASS.
- 13.8 EOS execution evidence, completed episode, simulator-state predicate
  success, and post-execution visual review PASS.

## Fail-Closed Evidence

Strict mode returns non-zero and writes blocked evidence when selected assets are
not in the Phase 12 registry, upstream confidence is too low, required metadata
is missing, material closure fails, source assets cannot be materialized, or task
bindings cannot be verified.

Blocked outputs include:

```text
provenance/summary.yaml
provenance/phase13_image_task_request.yaml
provenance/phase13_image_to_scene_result.yaml
handoff/asset_intake_blockers.yaml
evidence/phase13_*_gate.yaml
evidence/phase13_current_gate_index.yaml
```

They intentionally do not include `manifest.yaml`, so they cannot be mistaken
for public-ready packages.

Real apple/bowl probe result after material-closure hardening:

```text
PYTHONPATH=src python -m scenario_forge.cli image-task compile \
  --request /tmp/scenario-forge-phase13-real-probe/request.yaml \
  --scene-result /tmp/scenario-forge-phase13-real-probe/result.yaml \
  --registry-snapshot docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/phase11_three_task_suite/registry/registry_snapshot.yaml \
  --out /tmp/scenario-forge-phase13-real-probe/out \
  --strict
```

```text
Phase 13 status: phase13_static_candidate_ready
next_required_gate: 13.6
blockers:
- 13.6 engine-native overview render gate is required before formal package readiness
- 13.8 EOS execution/predicate canary gate is required before formal package readiness
```

The 13.5 gate records that apple and bowl both have
`package_local_missing_material_refs: gltf/pbr.mdl` and
`approved_runtime_mdl_dependencies: gltf/pbr.mdl`. USD dependency tooling still
prints unresolved `gltf/pbr.mdl` warnings during materialization, so 13.6 must
render the generated package and pass render-visual-reviewer before this can
move toward formal readiness.

## Tests

Focused regression:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_materials.py \
  tests/test_phase12_registry.py \
  tests/test_phase13_image_task_factory.py \
  tests/test_ebench_official_asset_intake.py \
  -q
```

Expected result:

```text
20 passed
```

Full project verification remains `make check`.

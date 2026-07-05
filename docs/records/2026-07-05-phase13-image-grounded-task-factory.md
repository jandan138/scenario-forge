# 2026-07-05 Phase 13 Image-Grounded Existing-Asset Factory Evidence

## Status

Phase 13 now has a static candidate compiler in Scenario Forge. The current
real official EBench apple/bowl probe reaches static candidate readiness after
retained runtime evidence classifies `gltf/pbr.mdl` as an approved Isaac Sim MDL
dependency. It now also has real 13.6 overview visual evidence from Isaac Sim
and render-visual-reviewer. It is not a formal package release because 13.8
still needs fresh execution and predicate evidence.

Implemented CLI:

```bash
PYTHONPATH=src python -m scenario_forge.cli image-task compile \
  --request image_task_request.yaml \
  --scene-result image_to_scene_result.yaml \
  --registry-snapshot registry_snapshot.yaml \
  --out /tmp/phase13_candidate \
  --strict
```

```bash
PYTHONPATH=src python -m scenario_forge.cli image-task overview-visual \
  --package /tmp/scenario-forge-phase13-real-probe/out \
  --visual-review /tmp/scenario-forge-phase13-real-probe/out/evidence/phase13_tabletop_overview_visual_review.yaml \
  --strict
```

```bash
PYTHONPATH=src python -m scenario_forge.cli image-task execution-predicate \
  --package /tmp/scenario-forge-phase13-real-probe/out \
  --single-task-rc-gate /tmp/scenario-forge-phase13-real-probe/out/evidence/phase11_single_task_release_candidate_gate.yaml \
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

- 13.8 EOS execution evidence, completed episode, simulator-state predicate
  success, and post-execution visual review PASS.

After 13.6 passes, the current index records
`overall_status=phase13_visual_candidate_ready`, `overview_visual_ready=true`,
and `next_required_gate=13.8`.

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

## Real 13.6 Overview Visual Evidence

The real apple/bowl probe was rendered with the EOS Isaac Sim overview renderer
and explicit MDL roots for `OmniPBR.mdl` and `gltf/pbr.mdl`:

```bash
OMNI_KIT_ACCEPT_EULA=yes \
/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-isaacsim41-py310/bin/python \
  /root/.config/superpowers/worktrees/embodied-eval-os/phase11-scenario-forge-execution/scripts/run_phase10x_scenario_forge_tabletop_render.py \
  --package /tmp/scenario-forge-phase13-real-probe/out \
  --image-out /tmp/scenario-forge-phase13-real-probe/out/evidence/phase13_tabletop_overview.png \
  --metadata-out /tmp/scenario-forge-phase13-real-probe/out/evidence/phase13_tabletop_overview_render_metadata.json \
  --runtime-log-out /tmp/scenario-forge-phase13-real-probe/out/evidence/phase13_tabletop_overview_runtime.log \
  --camera-name phase13_tabletop_overview \
  --isaac-python /cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-isaacsim41-py310/bin/python \
  --mdl-search-path /isaac-sim/kit/mdl/core/Base \
  --mdl-search-path /isaac-sim/kit/mdl/core/mdl \
  --camera-target -0.35 0.01 0.06 \
  --visible-target apple \
  --visible-target bowl \
  --visible-target scene_context
```

Retained evidence:

```text
docs/records/evidence/2026-07-05-phase13-image-grounded-task-factory/phase13_tabletop_overview.png
docs/records/evidence/2026-07-05-phase13-image-grounded-task-factory/phase13_tabletop_overview_render_metadata.json
docs/records/evidence/2026-07-05-phase13-image-grounded-task-factory/phase13_tabletop_overview_runtime.log
docs/records/evidence/2026-07-05-phase13-image-grounded-task-factory/phase13_tabletop_overview_visual_review.yaml
docs/records/evidence/2026-07-05-phase13-image-grounded-task-factory/phase13_6_factory_overview_visual_gate.yaml
docs/records/evidence/2026-07-05-phase13-image-grounded-task-factory/phase13_current_gate_index_after_13_6.yaml
```

13.6 result:

```text
render_status: pass
material_runtime_preflight.status: pass
blocked_dependency_count: 0
image_sha256: sha256:955f68cbabcd438409c6c44fd47eb15e30cbb28f47195882b8e0a5cdfbbb318c
visual_review: PASS
phase13_6_factory_overview_visual_gate: passed
phase13_current_gate_index.overall_status: phase13_visual_candidate_ready
next_required_gate: 13.8
```

The visual reviewer judged the apple and bowl visible and identifiable. The
review also noted wide framing and missing table/robot context as a non-blocking
readability caveat for this overview canary. The package is still not formal
because 13.8 execution/predicate evidence remains blocked.

## 13.8 Ingestion Status

Scenario Forge now has the 13.8 gate ingestion path. It is intentionally only an
evidence aggregator: it checks that the same generated package has passed Phase
11 task execution, executed episode, success predicate, post-execution visual
review, and single-task release-candidate gates. If those gates pass, 13.8 can
promote the current index to:

```text
overall_status: phase13_formal_package_ready
formal_package_ready: true
execution_predicate_ready: true
next_required_gate: 13.9
```

The real apple/bowl probe does not have that downstream evidence yet. EOS
currently has a Scenario Forge package task-execution CLI that consumes the
package and writes a config-level blocked evidence record, but that lane states
`no_scenario_forge_package_episode_runner_available_in_this_eos_lane`. Therefore
13.8 is not passed for the real Phase 13 probe.

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
23 passed
```

Full project verification remains `make check`.

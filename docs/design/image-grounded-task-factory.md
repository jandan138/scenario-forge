# Image-Grounded Task Factory Design

Status: Phase 13 static candidate compiler, 13.8 execution/predicate canary
ingestion, and 13.9 request-level batch quality gate are implemented. The real
official EBench apple/bowl package reaches formal package readiness, and a
retained three-request batch reaches `phase13_batch_factory_ready`. Soap-to-dish
remains a blocked probe until ConvertAsset/Phase 12 registry material closure is
fixed.

The image-grounded task factory turns a user-provided tabletop image request and
an external image-to-scene result into a Scenario Forge package candidate. It is
an importer and package compiler. It is not an image-understanding model, asset
converter, simulator runner, or benchmark reporter.

## Scope

Implemented commands:

```bash
scenario-forge image-task compile \
  --request image_task_request.yaml \
  --scene-result image_to_scene_result.yaml \
  --registry-snapshot registry_snapshot.yaml \
  --out ./phase13_candidate \
  --strict

scenario-forge image-task overview-visual \
  --package ./phase13_candidate \
  --visual-review ./phase13_candidate/evidence/phase13_tabletop_overview_visual_review.yaml \
  --strict

scenario-forge image-task execution-predicate \
  --package ./phase13_candidate \
  --single-task-rc-gate ./phase13_candidate/evidence/phase11_single_task_release_candidate_gate.yaml \
  --strict

scenario-forge image-task batch-quality \
  --suite ./phase13_batch_suite \
  --quality-report ./phase13_batch_suite/evidence/phase13_batch_factory_quality_report.yaml \
  --suite-quality-evidence ./phase13_batch_suite/evidence/suite_quality_evidence.yaml \
  --strict
```

Inputs:

- `image-task-request/v0.1`: source image URI/hash/rights, one-sentence goal,
  tabletop domain, robot profile, EBench target, fat package mode, and
  `allow_new_asset_reconstruction=false`.
- `image-to-scene-result/v0.1`: external producer identity, detections,
  task family, asset requirements, selected registry asset candidates, scene
  instances, task bindings, confidence summary, and upstream blockers.
- `registry-snapshot/v0.1`: Phase 12 asset registry snapshot used as the only
  allowed asset source.

When a registry snapshot contains multiple entries for the same `asset_id`,
`image-to-scene-result/v0.1` may provide `selected_asset_uid` or
`selected_source_package_id` on an asset candidate or scene instance. The
compiler uses that selector before release-readiness tie-breaks. Target
fixture metadata such as `semantic_label`, `source_uid`, and `fixture_kind` is
preserved in `task/task_contract.yaml` so EOS can map generated image-task IDs
to native EBench tasks without Scenario Forge owning the runner.

Outputs when local static gates pass:

```text
manifest.yaml
generation_plan.yaml
scene/instances.yaml
scene/main.usda
assets/asset_manifest.yaml
locks/asset_lock.yaml
task/task.yaml
task/task_contract.yaml
metrics/metrics.yaml
robot/robot.yaml
provenance/summary.yaml
provenance/phase13_image_task_request.yaml
provenance/phase13_image_to_scene_result.yaml
adapters/ebench/package.yaml
adapters/ebench/task_entrypoint.yaml
adapters/ebench/adapter_report.yaml
evidence/phase13_*_gate.yaml
evidence/phase13_current_gate_index.yaml
```

## Static Gates

The compiler writes Phase 13 gate evidence for:

- 13.0 scope freeze;
- 13.1 intake provenance;
- 13.2 image-understanding candidate import;
- 13.3 registry asset match;
- 13.4 goal-to-task contract;
- 13.5 scene USD / asset lock / materialization;
- 13.6 factory overview visual gate;
- 13.7 package adapter preflight;
- 13.8 execution predicate canary.

Passing 13.0-13.5 and 13.7 produces
`overall_status=phase13_static_candidate_ready`. The package is still not a
formal EBench-compatible task package because 13.6 and 13.8 are external gates.
The 13.6 ingestion command requires a render-visual-reviewer PASS, an existing
render image, render metadata with `render_status=pass`, and
`material_runtime_preflight.status=pass`. Passing 13.6 updates the current gate
index to `overall_status=phase13_visual_candidate_ready`,
`overview_visual_ready=true`, and `next_required_gate=13.8`. Formal readiness
still requires EOS execution evidence, completed episode, simulator-state
predicate success, and post-execution visual PASS.

The 13.8 ingestion command does not run a simulator. It only aggregates retained
Phase 11 gates for the same generated package: task execution, executed episode,
success predicate, post-execution visual review, and single-task release
candidate. Passing 13.8 updates the current gate index to
`overall_status=phase13_formal_package_ready`, `formal_package_ready=true`, and
`next_required_gate=13.9`. Phase 13 batch quality remains a separate 13.9 gate.

The 13.9 ingestion command is suite-level. It requires `suite_quality_evidence`
with `overall_status=passed`, a Phase 13 batch factory quality report, at least
three requests, formal-package-ready current gate indices for generated
packages, and blocker taxonomy for every failed or blocked request. It writes
`evidence/phase13_9_batch_factory_quality_gate.yaml` and does not report model
performance or leaderboard quality.

Retained 2026-07-05 evidence:

```text
docs/records/evidence/2026-07-05-phase13-image-grounded-task-factory/phase13_batch_rc_20260705/
```

That suite passes 13.9 with apple/bowl, remote/holder, and an apple/bowl retake
request. It proves request-level batch readiness, not broad task taxonomy
coverage. The retained soap-to-dish probe is blocked before package generation
because its selected scene asset has unresolved static material/texture closure
blockers.

If a selected registry asset has `material_closure.status != passed`, or if
post-materialization audit finds missing MDL/texture dependencies, the compiler
blocks before public-ready package generation. Runtime MDL modules such as
`gltf/pbr.mdl` are allowed only when the selected Phase 12 registry entry retains
approved runtime dependency evidence: material runtime preflight pass, no blocked
dependencies, concrete MDL search roots, and a resolved runtime path.

## Fail-Closed Behavior

The compiler writes blocked evidence and `handoff/asset_intake_blockers.yaml`
instead of a package manifest when it sees:

- unsupported request or result schema;
- missing image hash, rights, goal, producer, or robot profile;
- non-tabletop domain or target export other than EBench;
- `allow_new_asset_reconstruction` not set to false;
- upstream image-grounding blockers;
- low detection confidence or low asset match score;
- selected asset missing from the Phase 12 registry snapshot;
- missing selected asset digest, license, resolver version, retained provenance,
  material closure, physics readiness, or EBench export eligibility;
- selected registry asset `material_closure.status` not passed, including
  unresolved `.mdl` dependencies such as `gltf/pbr.mdl`;
- unmaterializable retained asset source;
- failed material/texture closure audit;
- invalid scene instance binding or package validation failure.

The fail-closed result is evidence and handoff, not a public-ready package.

## Boundaries

Scenario Forge owns the contracts, import checks, package artifacts, static USD
compile, asset lock, EBench static export, and retained evidence.

External systems own image grounding, detections, segmentation, depth, camera
pose, asset retrieval embeddings, model calls, 3D reconstruction, ConvertAsset
USD/MDL/mesh/texture conversion, simulator settling, EOS execution, policy
rollouts, and benchmark reports.

Scenario Forge may record material dependency blockers and hand off the failing
package, registry entry, dependency report, runtime log, and render evidence. It
must not synthesize replacement textures or reimplement ConvertAsset conversion
and material-normalization logic.

Perception confidence, visual review PASS, or human approval must not be used as
asset identity, binding correctness, predicate success, or release readiness.

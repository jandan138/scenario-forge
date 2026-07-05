# Image-Grounded Task Factory Design

Status: Phase 13 static candidate compiler implemented.

The image-grounded task factory turns a user-provided tabletop image request and
an external image-to-scene result into a Scenario Forge package candidate. It is
an importer and package compiler. It is not an image-understanding model, asset
converter, simulator runner, or benchmark reporter.

## Scope

Implemented command:

```bash
scenario-forge image-task compile \
  --request image_task_request.yaml \
  --scene-result image_to_scene_result.yaml \
  --registry-snapshot registry_snapshot.yaml \
  --out ./phase13_candidate \
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
They require an engine-native overview render, render-visual-reviewer PASS, EOS
execution evidence, completed episode, simulator-state predicate success, and
post-execution visual PASS.

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

Perception confidence, visual review PASS, or human approval must not be used as
asset identity, binding correctness, predicate success, or release readiness.

# Scenario Forge

> Generate evaluation-ready scenario packages for embodied agents.

Scenario Forge is a portable scenario package compiler. It prepares asset, scene, task,
robot, metric, and provenance artifacts that downstream evaluators can consume without
letting any one simulator define the core format.

The first-class downstream targets are:

- EBench-compatible package exports.
- `embodied-eval-os` scenario package exports.

Scenario Forge is not an episode runner, simulator facade, USD converter, benchmark
leaderboard, or model evaluation core.

## Positioning

```text
Scenario Forge
  owns: asset registry, package schema, generation plans, layout constraints,
        scenario manifests, package validation, adapter export boundaries

embodied-eval-os / EBench
  own: episode execution, model interfaces, trace capture, evaluator runtime,
       benchmark reports, leaderboards

ConvertAsset
  owns: USD/MDL/mesh/GLB conversion, material closure, runtime asset smoke checks,
       thumbnails, normalized asset packages
```

## Package Shape

Starter packages now use the v0.2 product layout:

```text
scenario_package/
  manifest.yaml
  generation_plan.yaml
  scene/main.usda
  scene/instances.yaml
  task/task.yaml
  robot/robot.yaml
  metrics/metrics.yaml
  assets/asset_manifest.yaml
  locks/asset_lock.yaml
  evidence/validation_report.yaml
  provenance/provenance.yaml
```

Simulator-specific exports live under `adapters/<target>/` and must not mutate the
portable manifest in place.

## Roadmap

The v0.1 package format remains readable as a bootstrap format. The v0.2 package
format is the active product contract for EBench-compatible task package generation.
It is built around generation plans, asset locks, USD scene entry points, explicit
task predicates and metrics, validation evidence, and adapter exports.

Design documents:

- [EBench Auto Factory Roadmap](docs/strategy/scenario-forge-ebench-auto-factory-roadmap.md)
- [Scenario Package v0.2](docs/design/package-v0.2.md)
- [Asset Lock Design](docs/design/asset-lock.md)
- [USD Scene Compiler Design](docs/design/usd-scene-compiler.md)
- [EBench Adapter Design](docs/design/ebench-adapter.md)
- [Workflow, Layout, Real2Sim, Suite Factory Design](docs/design/workflow-layout-suite-factory.md)

## Quick Start

```bash
python -m pip install -e ".[dev]"
scenario-forge package scaffold --out /tmp/scenario-forge-starter
scenario-forge workflow compose \
  --package /tmp/scenario-forge-starter \
  --family pick_place \
  --binding object=object_001 \
  --binding target_zone=target_zone
scenario-forge layout plan --package /tmp/scenario-forge-starter --difficulty easy
scenario-forge scene compile \
  --instances /tmp/scenario-forge-starter/scene/instances.yaml \
  --asset-lock /tmp/scenario-forge-starter/locks/asset_lock.yaml \
  --out /tmp/scenario-forge-starter/scene/main.usda
scenario-forge task compile --package /tmp/scenario-forge-starter --family pick_place
scenario-forge export ebench --package /tmp/scenario-forge-starter
scenario-forge package check /tmp/scenario-forge-starter
```

Suite smoke:

```bash
scenario-forge suite generate \
  --spec examples/suite_spec_smoke.yaml \
  --out /tmp/scenario-forge-suite
scenario-forge suite quality --suite /tmp/scenario-forge-suite
scenario-forge export ebench --suite /tmp/scenario-forge-suite
```

Developer checks:

```bash
make check
```

## Design Rules

- Core package validation must run without Isaac Sim, Omniverse, CUDA, Habitat, ManiSkill,
  OmniGibson, or simulator SDK imports.
- Simulator and asset-tool integration must use adapter modules.
- ConvertAsset integration shells out through its public CLI command boundary; Scenario Forge
  does not import or reimplement USD conversion internals.
- Heavy generated artifacts stay out of git. Commit manifests, schemas, tiny fixtures, and
  claim-bearing reports only.
- `not_run` validation checks are not passed checks. Do not use draft validation reports as
  evidence for runtime claims.

## Repository Layout

```text
src/scenario_forge/
  core/          simulator-neutral contracts
  schemas/       versioned package schema helpers
  generation/    portable generation plans and orchestration
  assets/        asset references, licenses, checksums, resolver boundaries
  artifacts/     package layout and provenance helpers
  evaluation/    portable metric and split references
  adapters/      external simulator/tool integration boundaries

configs/         default schema and adapter configuration
examples/        small packages and commands that run without heavy dependencies
docs/            design, operations, records, and reference material
scripts/         lightweight project maintenance commands
tests/           unit and contract tests
```

## Current Status

This repo is a narrow, testable foundation. It supports v0.1 package loading, v0.2
package scaffold/load/check behavior, asset manifests and locks, static USDA scene
compilation, workflow-grounded task artifacts, deterministic layout planning,
real2sim import/cousin packaging, suite generation, suite quality evidence, and
static EBench package/suite-index export. It does not run embodied evaluations or
produce model-performance benchmark reports.

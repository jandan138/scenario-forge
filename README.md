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

Starter packages use a small, portable layout:

```text
scenario_package/
  manifest.yaml
  scene.usda
  scene_instances.yaml
  task.yaml
  robot.yaml
  validation_report.yaml
```

Future simulator-specific exports live under `adapters/<simulator>/` and must not mutate the
portable manifest in place.

## Roadmap

The v0.1 package format is the bootstrap format. The v0.2 product direction is an
EBench-compatible task package factory built around generation plans, asset locks, USD scene
compilation, explicit task predicates and metrics, validation evidence, and adapter exports.

Phase 0 design documents:

- [EBench Auto Factory Roadmap](docs/strategy/scenario-forge-ebench-auto-factory-roadmap.md)
- [Scenario Package v0.2](docs/design/package-v0.2.md)
- [Asset Lock Design](docs/design/asset-lock.md)
- [USD Scene Compiler Design](docs/design/usd-scene-compiler.md)
- [EBench Adapter Design](docs/design/ebench-adapter.md)

## Quick Start

```bash
python -m pip install -e ".[dev]"
scenario-forge package scaffold --out /tmp/scenario-forge-starter
scenario-forge package check /tmp/scenario-forge-starter
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

This repo is bootstrapped as a narrow, testable foundation. It validates portable package
structure, scaffolds a starter package, records architecture constraints, and provides Phase 1
asset manifest / asset lock helpers with checksum, license, local file, and USD reference checks.
It does not yet generate full Isaac Sim USD scenes or run embodied evaluations.

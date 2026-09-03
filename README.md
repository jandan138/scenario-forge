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
- [ScenarioSpec and GenManip Export](docs/design/scenario-spec-and-genmanip-export.md)
- [Scenario Source Bindings](docs/design/scenario-source-bindings.md)
- [Task Catalog and Readiness](docs/design/task-catalog-and-readiness.md)

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

Scientific-workbench bimanual-pour example:

```bash
python scripts/generate_scientific_workbench_bimanual_pour.py \
  --scene1-source-usd /path/to/hard_task/Scene1_hard.usd \
  --table-source-usd /path/to/lab_001.usd \
  --source-vessel-source-usd /path/to/conical_bottle_identity/facade.usda \
  --target-vessel-source-usd /path/to/graduated_cylinder_identity/facade.usda \
  --scene1-environment-package /path/to/scene1_environment/package \
  --scene1-environment-manifest /path/to/scene1_environment/manifest.json \
  --table-package /path/to/ebench_table/package \
  --table-manifest /path/to/ebench_table/manifest.json \
  --source-vessel-package /path/to/conical_bottle03/package \
  --source-vessel-manifest /path/to/conical_bottle03/manifest.json \
  --target-vessel-package /path/to/graduated_cylinder_03/package \
  --target-vessel-manifest /path/to/graduated_cylinder_03/manifest.json \
  --scene1-environment-revision <convertasset-git-sha> \
  --table-revision <convertasset-git-sha> \
  --source-vessel-revision <source-vessel-convertasset-git-sha> \
  --target-vessel-revision <target-vessel-convertasset-git-sha> \
  --out outputs/scientific_workbench_bimanual_pour \
  --isaac-python "$ISAAC_ENV/bin/python" \
  --genmanip-root "$GENMANIP_ROOT"
```

New canonical builds require a ConvertAsset `static_support` table. The eBench
adapter explicitly disables GenManip collider authoring and consumes the qualified
package collider. Export the same recipe for VR collection with:

```bash
PYTHONPATH=src python scripts/export_vr_teleop_package.py \
  outputs/scientific_workbench_bimanual_pour_static_support_v1_20260806 \
  --out outputs/scientific_workbench_bimanual_pour_vr_r2_20260806
```

The VR directory is relocatable and contains `scene.usd`, `task_config.py`, its
relative `deps/` closure, and a parity manifest. The two adapters share the same
Isaac/PhysX and robot-contact profile; the declared exception is robot joint
initialization because the current VR config contract has no joint-position field.

For a static build, the same portable compiler is available for any ScenarioSpec
through a separate local source-binding file:

```bash
scenario-forge package compile \
  --spec examples/scientific_workbench/bimanual_pour/scenario.yaml \
  --source-bindings /path/to/scenario_source_bindings.yaml \
  --out outputs/scientific_workbench_bimanual_pour \
  --export-genmanip
```

The bindings file holds local USD and ConvertAsset delivery paths; those paths do
not become part of the ScenarioSpec or generated package provenance. This command
does not start Isaac Sim or execute a rollout.

The default build resets the exported task in GenManip and renders a tabletop
close-up plus a full Scene1_hard laboratory overview before accepting the package. Use
`--static-only` only when intentionally producing unrendered static artifacts.
This example evaluates a kinematic pour sequence; it does not claim real liquid
transfer. See the [generation runbook](docs/operations/generate-bimanual-pour-package.md).
The current v0.2 package, render, runtime-binding Canary, and EOS five-stage dry-run
are recorded in the
[package closure note](docs/records/2026-07-14-scientific-workbench-bimanual-pour-v02-package-closure.md).
The earlier [task-ready r5](docs/records/2026-07-13-scientific-workbench-bimanual-pour-task-ready-runtime-canary.md)
and [full-context r4](docs/records/2026-07-13-scientific-workbench-bimanual-pour-runtime-canary.md)
records are retained as historical evidence only.

Developer checks:

```bash
python -m pip install -e ".[dev,usd]"
make ci-check
```

The internal full gate is `make check`; it additionally runs tests marked
`local_artifacts` and therefore requires the declared `/cpfs` inputs.

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
static EBench package/suite-index export. It now also compiles simulator-neutral
`ScenarioSpec` inputs into portable packages, exports the EBench/GenManip collected
package wire format, and can request strict post-reset/pre-action Isaac Sim QA
renders as package evidence. `scenario-spec/v0.4` adds a weighted progress-score
rubric (aligned with the upstream wetlab task-design Progress Score) that is
transported with explicit activation and capability semantics — rubric items are
declared, not runtime-evaluated. It does not contain an episode runner, run embodied
evaluations, or produce model-performance benchmark reports.

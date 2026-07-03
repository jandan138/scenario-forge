# Workflow, Layout, Real2Sim, Suite Factory Design

## Status

Implemented for deterministic static package generation scope in Phases 6-10.

## Scope

Scenario Forge now has a portable package-factory lane that composes workflow-grounded task artifacts, plans deterministic scene layouts, imports upstream real2sim results, generates digital cousin variants, builds benchmark suites, and writes suite quality evidence.

This lane does not run episodes, import simulator SDKs, evaluate models, or create leaderboards. EBench and embodied-eval-os remain responsible for runtime execution and model-facing reporting.

## Components

- `configs/domain_packs/scientific_workbench/` defines atomic skills, workflow templates, layout constraints, and hazard spacing inputs.
- `scenario_forge.generation.workflows` composes task graphs, predicates, safety rules, metrics, and required asset declarations from task-family templates.
- `scenario_forge.generation.layout` turns required assets and bindings into deterministic `scene/layout.yaml`, `scene/instances.yaml`, layout checks, package-local placeholder assets, and asset locks.
- `scenario_forge.adapters.real2sim` imports `real2sim-result/v0.1` artifacts from upstream producers into v0.2 packages.
- `scenario_forge.generation.cousins` creates digital cousin packages while preserving task predicates and recording variation axes.
- `scenario_forge.generation.suite` builds suites from `suite-spec/v0.2`, exports each package to EBench, and writes suite manifests, coverage, validation, and suite asset-lock summaries.
- `scenario_forge.evaluation.suite_quality_evidence` reports construction evidence such as distribution, duplicate scenes/instructions, split leakage, and asset reproducibility completeness.

## Contracts

All outputs are ordinary package or suite artifacts: YAML manifests, scene instances, USD entrypoints, asset manifests/locks, provenance, evidence, and EBench adapter descriptors. External systems can produce real2sim results or alternative layout plans, but they must enter through importer/adapter contracts and cannot bypass package validation.

## Commands

```bash
scenario-forge workflow compose --package ./pkg --family pick_place --binding object=object_001 --binding target_zone=target_zone
scenario-forge layout plan --package ./pkg --difficulty easy
scenario-forge real2sim import --result ./real2sim_result.yaml --out ./pkg
scenario-forge real2sim cousins --package ./pkg --plan ./cousin_plan.yaml --out ./suite
scenario-forge suite generate --spec examples/suite_spec_smoke.yaml --out ./suite
scenario-forge suite quality --suite ./suite
```

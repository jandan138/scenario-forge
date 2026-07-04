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

## Phase 10.x Pre-Phase-11 Gates

Phases 6-10 produce static packages and suite construction evidence. Before Phase 11 adds UI and human review flows, the factory needs a downstream handoff gate:

- `10.1 Golden USD Task Pack Freeze`: freeze a small 10-20 task suite that covers the main scientific-workbench families, split labels, difficulty labels, USD entrypoints, package-local asset locks, and EBench adapter descriptors.
- `10.2 Asset / External Input Hardening`: compare Scenario Forge's deterministic layout output with LabBuilder-style layout imports and SimFoundry-style real2sim/cousin imports using package validity, asset-lock coverage, predicate binding, layout checks, and EBench export readiness.
- `10.3 EOS Static Import Contract Gate`: in EOS's normal project environment, statically load the Scenario Forge suite/package outputs and verify that downstream code can resolve `suite_manifest.yaml`, `adapters/ebench/package.yaml`, `task_entrypoint.yaml`, `scene/main.usda`, and `locks/asset_lock.yaml`.
- `10.4 Runtime Smoke Evidence Gate`: in a backend-specific EOS runtime lane, run the smallest non-model smoke needed to prove that selected Scenario Forge USD packages can be accepted by a real runtime and produce evidence. Native GenManip task smoke is useful backend-readiness evidence, but it is not sufficient unless the trace links back to Scenario Forge package ids, USD entrypoints, task entrypoints, adapter descriptors, and asset locks.
- `10.5 Release Candidate Gate`: scale to a 50-100 task RC suite and attach quality evidence, EOS static import evidence, package-linked runtime smoke evidence, and known blockers before Phase 11 starts.

These gates are evidence handoff steps, not new ownership. Scenario Forge remains responsible for portable package construction and validation; EOS / EBench remain responsible for episode execution, model-facing traces, and benchmark reports.

Implemented command:

```bash
scenario-forge suite phase10x \
  --suite ./suite \
  --eos-python "$EEOS_PYTHON" \
  --external-evidence examples/phase10x_external_evidence.yaml \
  --runtime-smoke examples/phase10x_runtime_smoke.yaml \
  --strict
```

This command writes `golden_task_pack.yaml`, `external_input_hardening.yaml`,
`eos_static_import.yaml`, `runtime_smoke.yaml`, and `phase10x_rc_gate.yaml`
under `suite/evidence/`. Runtime smoke is imported from downstream evidence; it
is not executed by Scenario Forge. The imported evidence must not merely show
that EOS / GenManip can run a native task. For a passing Phase 10.4 package gate,
it must identify which Scenario Forge package ids and USD entrypoints were
accepted by the downstream runtime.

Runtime evidence uses `packages_tested` for the covered package ids and
`package_artifacts` for package-linked proof. Each `package_artifacts` item must
include `package_id`, `usd_entrypoint`, `asset_lock`, `adapter_descriptor`,
`task_entrypoint`, and `trace_uri`. The package artifact paths are
suite-relative and must resolve to the expected files inside the referenced
package.

## Commands

```bash
scenario-forge workflow compose --package ./pkg --family pick_place --binding object=object_001 --binding target_zone=target_zone
scenario-forge layout plan --package ./pkg --difficulty easy
scenario-forge real2sim import --result ./real2sim_result.yaml --out ./pkg
scenario-forge real2sim cousins --package ./pkg --plan ./cousin_plan.yaml --out ./suite
scenario-forge suite generate --spec examples/suite_spec_smoke.yaml --out ./suite
scenario-forge suite quality --suite ./suite
scenario-forge suite phase10x --suite ./suite
```

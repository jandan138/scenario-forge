# Scenario Forge Documentation

- [玻璃器皿材质准入标准](glass-material-guide/)

Scenario Forge compiles portable embodied scenario packages for downstream evaluators.

## Strategy

- [Strategy Documents](strategy/README.md)
- [EBench Auto Factory Roadmap](strategy/scenario-forge-ebench-auto-factory-roadmap.md)

## Design

- [Architecture](design/architecture.md)
- [Scenario Package Contract](design/scenario-package-contract.md)
- [Adapter Boundaries](design/adapter-boundaries.md)
- [Scenario Package v0.2](design/package-v0.2.md)
- [Asset Lock Design](design/asset-lock.md)
- [USD Scene Compiler Design](design/usd-scene-compiler.md)
- [EBench Adapter Design](design/ebench-adapter.md)
- [Workflow, Layout, Real2Sim, Suite Factory Design](design/workflow-layout-suite-factory.md)
- [Image-Grounded Task Factory Design](design/image-grounded-task-factory.md)
- [ScenarioSpec and GenManip Export](design/scenario-spec-and-genmanip-export.md)
- [Scene Asset Overlays](design/scene-asset-overlays.md)
- [Scenario Source Bindings](design/scenario-source-bindings.md)
- [Task Catalog and Readiness](design/task-catalog-and-readiness.md)
- [Scientific Workbench Tabletop Placement](design/scientific-workbench-tabletop-placement.md)
- [Scientific Workbench Task Coverage Factory](design/task-coverage-factory.md)
- [Progress Rubric (scenario-spec/v0.4)](design/progress-rubric.md)
- [Liquid Measurement Adapter Contract](design/liquid-measurement-adapter-contract.md)
- [Liquid Autofill Contract](design/liquid-autofill-contract.md)

## Operations

- [Artifact Policy](operations/artifact-policy.md)
- [Scientific Workbench Task Directory](task-directory/)
- [量筒 GPU-PBD 液体修复教程](liquid-cylinder-tutorial/)
- [给任意合格容器加入初始液体](liquid-autofill/)
- [Liquid Autofill Runbook](operations/liquid-autofill.md)
- [Scientific Workbench Background Gallery](background-gallery/)
- [Build the Scientific Workbench Task Directory](operations/build-scientific-workbench-task-directory.md)
- [Generate Scientific Workbench Layout Prototypes](operations/generate-scientific-workbench-layout-prototypes.md)
- [Development Checks](operations/development-checks.md)
- [Generate the Bimanual Pour Package](operations/generate-bimanual-pour-package.md)
- [Qualify the Bimanual Pour Vessel Assets](operations/qualify-bimanual-pour-vessels.md)
- [Intake an External Visual Environment](operations/intake-external-environment.md)
- [Intake a Generated Blender Environment](operations/intake-generated-blender-environment.md)
- [Generate External-Room Zone Variants](operations/generate-external-room-zone-variants.md)
- [Generate Scientific Workbench Tube Prototypes](operations/generate-scientific-workbench-tube-prototypes.md)
- [Live Tasks 7, 10, and 11 ConvertAsset Request](operations/scientific-workbench-live-task-7-10-11-asset-admission-request.yaml)
- [Historical Tube-prototype ConvertAsset Request](operations/scientific-workbench-tube-prototype-asset-admission-request.yaml)
- [HCI 15 mL Closed Insert and Lid Demo ConvertAsset Request](operations/scientific-workbench-hci-15ml-closed-insert-lid-admission-request.yaml)

## Reference

- [Scientific Workbench Task Design](reference/scientific-workbench-task-design.md) — generated from the pinned Feishu `1. Task Design` snapshot
- [Scientific Workbench Task Design (self-contained HTML)](reference/scientific-workbench-task-design.html) — refresh via `python scripts/sync_scientific_workbench_task_catalog.py --write`

## Records

- [2026-08-20 Liquid Autofill Tool](records/2026-08-20-liquid-autofill-tool.md)

- [2026-08-19 Workbench Table Gray-top Package](records/2026-08-19-workbench-table-gray-top-package.md)
- [2026-08-18 HCI 15 mL Closed Insert and Lid Demo Admission](records/2026-08-18-hci-15ml-closed-insert-lid-admission.md)
- [2026-08-18 Task 05 / Task 09 r11.1 Prequalification](records/2026-08-18-scientific-workbench-r11-1-prequalification.md)
- [2026-08-17 r10.1 VR Root, Randomization, and Task 07 Rack](records/2026-08-17-r10-1-vr-root-randomization-and-task07-rack.md)
- [2026-08-16 Scientific Workbench r9 Rich Tabletop](records/2026-08-16-scientific-workbench-r9-rich-tabletop.md)
- [2026-08-16 Task 02 r8.7 Dynamic-loaded-start Package](records/2026-08-16-task02-r87-dynamic-loaded-start.md)
- [2026-08-16 Task 02 r8.5 40% Liquid Package](records/2026-08-16-task02-r85-40pct-liquid-package.md)
- [2026-08-15 Task 02 r8.4 World-baked PBD and Preloaded Support](records/2026-08-15-task02-r84-world-baked-pbd-and-preloaded-support.md)
- [2026-08-11 Cold-output OSS Archive](records/2026-08-11-cold-output-oss-archive.md)
- [2026-07-03 Bootstrap Decisions](records/2026-07-03-bootstrap-decisions.md)
- [2026-07-04 Phase 10.x EOS Environment and Gates](records/2026-07-04-phase10x-eos-environment-and-gates.md)
- [2026-07-05 Phase 12 Registry / Viewer / Handoff / Policy Evidence](records/2026-07-05-phase12-registry-viewer-handoff-policy.md)
- [2026-07-05 Phase 13 Image-Grounded Existing-Asset Factory Evidence](records/2026-07-05-phase13-image-grounded-task-factory.md)
- [2026-07-06 S2D-12 Soap-to-Dish Phase 12 / Phase 13 Plan](records/2026-07-06-s2d12-soap-to-dish-phase12-phase13-plan.md)
- [2026-07-13 Scientific Workbench Bimanual Pour Runtime Canary](records/2026-07-13-scientific-workbench-bimanual-pour-runtime-canary.md)
- [2026-07-13 Task-ready Bimanual Pour Runtime Canary](records/2026-07-13-scientific-workbench-bimanual-pour-task-ready-runtime-canary.md)
- [2026-07-14 DryingBox_03 Source-Bound Package Integration](records/2026-07-14-scientific-workbench-dryingbox-source-bound-integration.md)
- [2026-07-14 Scientific Workbench Task Catalog and Readiness](records/2026-07-14-scientific-workbench-task-catalog-readiness.md)
- [2026-07-14 Bimanual Pour Oracle Baseline](records/2026-07-14-scientific-workbench-bimanual-pour-oracle-baseline.md)
- [2026-07-14 Scientific Workbench Next-task Selection](records/2026-07-14-scientific-workbench-next-task-selection.md)
- [2026-07-14 GenManip Runtime-contract Transport](records/2026-07-14-genmanip-runtime-contract-transport.md)
- [2026-07-14 Bimanual Pour v0.2 Package Closure](records/2026-07-14-scientific-workbench-bimanual-pour-v02-package-closure.md)
- [2026-07-17 Progress Rubric v0.4 (M1, transport_only)](records/2026-07-17-progress-rubric-v04-m1.md)
- [2026-07-23 Scene1_hard Visual Context for EBench Bimanual Pour](records/2026-07-23-scene1-hard-ebench-bimanual-pour-context.md)
- [2026-07-27 External Room Zone-Background Implementation](records/2026-07-27-external-room-zone-background-implementation.md)
- [2026-07-29 Scientific Workbench Tube-task Foundation](records/2026-07-29-scientific-workbench-tube-task-foundation.md)
- [2026-07-30 Code-as-Room Generated Environment Integration](records/2026-07-30-code-as-room-generated-environment-integration.md)
- [2026-08-03 Three-view Background Package QA](records/2026-08-03-three-view-background-package-qa.md)
- [2026-08-03 Four Generated Laboratory Backgrounds](records/2026-08-03-four-generated-lab-backgrounds.md)
- [2026-07-30 Centrifuge Proxy Parent-Local Requalification](records/2026-07-30-centrifuge-proxy-parent-local-requalification.md)
- [2026-07-31 Task Design Authority Correction](records/2026-07-31-scientific-workbench-task-design-correction.md)
- [2026-08-01 Scientific Workbench Coverage Factory v1](records/2026-08-01-scientific-workbench-coverage-factory-v1.md)
- [2026-08-01 Scientific Workbench v4 Candidate Evidence](records/2026-08-01-scientific-workbench-v4-candidate-evidence.md)
- [2026-08-14 Graduated Cylinder GPU-PBD Container Handoff](records/2026-08-14-graduated-cylinder-gpu-pbd-container-handoff.md)
- [2026-07-06 Phase 13 S2D-12 Soap-to-Dish Static Candidate Evidence](https://github.com/jandan138/scenario-forge/blob/main/docs/records/evidence/2026-07-05-phase13-image-grounded-task-factory/phase13_s2d12_soap_to_dish_static_candidate/generated_package_summary.yaml)

# Phase 6-10 Factory Design

## Context

Scenario Forge is already a portable package compiler with asset locks, v0.2 packages, USD scene compilation, task artifacts, and static EBench export. Phase 6-10 extend that foundation from one static package to an automatic benchmark package factory.

## Design

Phase 6 adds a domain-pack driven workflow generator. It loads atomic skills and workflow templates, composes task graphs for supported task families, derives required asset roles, success predicates, and safety rules, and rejects robot profiles that lack required capabilities.

Phase 7 adds a deterministic layout baseline. It takes a generation plan or required asset list, applies difficulty profiles and spatial constraints, writes `scene/layout.yaml`, `scene/instances.yaml`, and `evidence/layout_checks.yaml`, and keeps all placements simulator-neutral.

Phase 8 adds importer-first real2sim support. External real-to-sim systems remain upstream producers; Scenario Forge imports their result contract, writes assets/provenance/evidence into package form, and can create cousin variants that preserve task semantics while recording variation axes.

Phase 9 adds suite generation. It reads `suite_spec.yaml`, generates multiple v0.2 packages, assigns splits/difficulties/task families, writes `suite_manifest.yaml`, suite-level locks/reports, and runs static EBench suite export.

Phase 10 adds suite quality evidence. It reports distribution, duplicate/leakage checks, asset/license/checksum completeness, and suite construction findings. It does not report model performance and does not create a leaderboard.

## Boundaries

All implementation stays in package generation, artifacts, evaluation, and adapter layers. Core package layers do not import simulator SDKs. Real2sim and LabBuilder-style outputs enter through contracts/importers, not as vendored runtime dependencies. EBench execution remains downstream.

## Verification

Each phase gets focused pytest coverage plus CLI coverage where user-facing commands are added. `make check` remains the final gate and must run package smoke through scaffold, workflow/layout/task/scene compilation, EBench export, and package check.

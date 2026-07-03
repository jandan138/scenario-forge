# Scenario Forge Design

## Goal

Create a new repo named `scenario-forge` that generates evaluation-ready scenario packages
compatible with EBench and `embodied-eval-os`, without using `lab` in the repo identity.

## Architecture

Scenario Forge is a portable package compiler. It keeps asset references, scene instances, task
specs, robot specs, validation reports, and provenance in a simulator-neutral package. External
simulator or asset-tool output lives behind adapters.

## Boundaries

- EBench and `embodied-eval-os` own runtime evaluation.
- ConvertAsset owns USD/MDL/mesh/GLB conversion.
- Scenario Forge owns package shape, generation orchestration, validation, and blocker reporting.

## Bootstrap Requirements

- Use a `src/` Python package layout.
- Provide a CLI to scaffold and check a starter package.
- Include tests that validate package behavior and architecture boundaries.
- Include docs for package contract, adapter boundaries, and artifact policy.
- Keep pure validation free of Isaac/Omniverse imports.

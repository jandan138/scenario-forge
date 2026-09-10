# Agent Guide

Scenario Forge is a portable scenario package compiler. Keep the repo narrow.

## Hard Boundaries

- Do not add episode runners, model adapters, leaderboards, or benchmark reporting here.
- Do not import simulator SDKs in pure package layers.
- Do not reimplement ConvertAsset USD/MDL/mesh conversion logic.
- Do not vendor, import, or expose LabBuilder/SimFoundry pipelines as core package
  layers; map their capabilities into Scenario Forge-owned contracts through
  adapters or generation-plan producers.
- Do not use `lab` in top-level repo naming or public package identity.

## Scene Authoring Standards

For scene-authoring work (assets, USD, articulation, materials/liquids, task
state, validation or delivery), start at [docs/standards/README.md](docs/standards/README.md)
and read the applicable topics before implementation. Use their rule IDs and
scope; do not generalize fixed-base or runtime-specific evidence to other cases.

After the appropriate validation, the same implementer must synchronize any
affected standards, design references, operations guidance and dated evidence
in the same change. If no general rule changes, explain why in the task record.
Follow [the maintenance workflow](docs/standards/maintenance.md). This is a work
responsibility, not an automatic synchronization service or a new approval gate.
Core package/schema/API contracts remain authoritative in their design documents;
historical task packages are not silently rewritten to adopt new standards.

## Expected Workflow

1. Write a failing test for package/schema/adapter behavior.
2. Implement the smallest code that passes.
3. Run `make check`.
4. Update docs when changing package shape, adapter contracts, or artifact policy.

## Directory Ownership

- `src/scenario_forge/core`: simulator-neutral contracts.
- `src/scenario_forge/schemas`: versioned schema helpers.
- `src/scenario_forge/generation`: package generation orchestration.
- `src/scenario_forge/assets`: asset refs, license, hash, resolver boundaries.
- `src/scenario_forge/artifacts`: package layout and provenance.
- `src/scenario_forge/evaluation`: portable metric and split references.
- `src/scenario_forge/adapters`: external tools and simulators.
- `docs/standards`: current scene-authoring rules, applicability and validation basis.
- `docs/design`: design rationale/proposals; core package/schema/API contracts.
- `docs/operations`: runbooks, checklists, handoff notes.
- `docs/records`: dated decisions and evidence summaries.

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
- `docs/design`: durable architecture decisions.
- `docs/operations`: runbooks, checklists, handoff notes.
- `docs/records`: dated decisions and evidence summaries.

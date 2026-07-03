# 2026-07-03 Bootstrap Decisions

## Name

The repo name is `scenario-forge`. It intentionally avoids `lab` so the project can cover
scientific workbenches, home manipulation, factories, warehouses, field robotics, and other
domains.

## Scope

Scenario Forge generates and validates portable scenario packages. EBench and `embodied-eval-os`
consume those packages and run evaluation.

## Agent Review Summary

Three independent review tracks informed the bootstrap:

- EOS alignment: keep core domain-agnostic, use scenario-pack style manifests, and avoid duplicating
  evaluator runtime or model adapters.
- ConvertAsset boundary: consume ConvertAsset public CLI/package manifests and do not import or
  reimplement USD conversion internals.
- Embodied project structure: keep simulator-specific exports behind adapters; make package
  validation work without simulator dependencies.

## Initial Cut

The first cut implements:

- starter package scaffold;
- structural package validation;
- ConvertAsset command-plan adapter;
- asset reference helper;
- architecture import boundary tests;
- docs, schema, config defaults, and a checked-in minimal example.

It does not claim full Isaac scene generation, real2sim reconstruction, or executable embodied
evaluation.

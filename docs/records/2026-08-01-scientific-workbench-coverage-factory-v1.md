# 2026-08-01 Scientific Workbench Coverage Factory v1

## Decision

Scenario Forge now treats the Feishu Scientific Workbench catalog as a
coverage queue. The near-term product goal is one canonical, immutable package
per asset-ready task, rather than claiming end-to-end task execution.

## Implemented Contract

- A task queues only when every required role has a source-bound asset with
  admitted status, a resolvable Scenario Forge binding, and an authored
  canonical recipe.
- Missing or unadmitted roles are deduplicated into a producer-facing
  ConvertAsset admission request. Original source remains immutable; Scenario
  Forge must not add asset-specific physics or scale repairs.
- Releases retain candidate evidence separately from `latest`. Automatic
  promotion requires self-contained package closure, runtime reset, tabletop
  placement, visual review, and fixed-base provisional IK.
- Package generation writes composed-bounding-box top-down IK requests for an
  external GenManip/CuRobo owner. An empty or absent composed bbox is recorded
  as a blocked candidate-generation reason; it never falls back to a USD
  origin-based grasp point.

## Initial Catalog Result

The pinned 18-row catalog currently has three queued canonical recipes:

1. graduated-cylinder to beaker pour;
2. funnel-assisted graduated-cylinder to flask pour;
3. two-sample mix in a beaker.

The other 15 rows remain blocked by their exact missing asset/admission and/or
missing canonical-recipe reasons. The three existing v3 packages are retained
as candidates with reset and tabletop evidence. They are intentionally not
promoted until self-contained closure, visual review, and external provisional
IK evidence are recorded.

## Claim Boundary

This change proves queue classification and evidence contract handling only.
It does not prove collision-free motion, grasp closure, lifting, dual-arm
coordination, articulated interaction, liquid transfer, policy success, or
benchmark success.

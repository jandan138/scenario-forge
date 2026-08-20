# Fluid-interaction asset tool v1

Scenario Forge now exposes a ConvertAsset-owned two-stage workflow for
`reservoir`, `conduit`, and `surface_guide` assets. The implementation keeps
USD geometry inspection, collision authoring and Isaac qualification in
ConvertAsset; Scenario Forge supplies strict subprocess, review, batch,
promotion, ZIP and handoff contracts.

The direct fast path applies normalized, r10.3-bounded SDF parameters to
reviewed source geometry. A blocked fast path can produce a second-review
package-local convex partition proposal. Raw USD input is closed through the
existing ConvertAsset dependency-closure producer before qualification.
Promoted packages contain no particles and claim no robot or benchmark result.

## Real-asset evidence

- Open 50 mL centrifuge-tube body: derived-partition package passed three
  process-isolated Isaac Sim 4.1 runs. Static retention and motion retention
  were 1.0 in all runs, structural leakage was zero, and pour outflow was
  0.8841 / 0.9275 / 0.9130. Package:
  `outputs/fluid_interaction_asset_v1_20260820/packages_partition_v4/centrifuge_tube_50ml/`.
- Funnel: the direct SDF closed the inlet. Derived partitions opened the
  geometry, but the 7.46 mm measured bore is smaller than the pinned Task02
  liquid's 18 mm effective particle diameter. Liquid remained above the tube;
  the package is blocked and must not be consumed. Latest diagnostics:
  `outputs/fluid_interaction_asset_v1_20260820/packages_partition_v6/funnel/`.
- Conical flask: both the source SDF fast path and the first measured partition
  profile failed retention. The candidate remains blocked; no qualified flask
  claim was emitted. Latest diagnostics:
  `outputs/fluid_interaction_asset_v1_20260820/packages_partition_v2/conical_flask/`.
- Glass rod: the three paired with-guide/without-guide cold runs measured zero
  receiver capture in both conditions. It is truthfully `not_applicable`, has
  no qualification claim, and is retained only as diagnostics:
  `outputs/fluid_interaction_asset_v1_20260820/packages_final5/glass_rod/`.

These results are asset-level liquid/contact evidence only. They do not claim a
robot policy, task metric, benchmark success, or a full-scene rollout.

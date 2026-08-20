# 2026-08-20 Simple-SDF multi-liquid tool

Scenario Forge now exposes a two-stage producer workflow for the deliberately
simple container route demonstrated by the colleague-authored reagent-bottle
and 15 mL tube scene. The first stage requests a reviewed visual-mesh SDF
collision package from ConvertAsset. The second stage requests producer-time
closed-mesh particle baking and validates the returned package before
promotion.

The handoff contract requires one independent `ParticleSet` and unique
`particleGroup` for every sampler mesh while all sets share one canonical
scene-level `ParticleSystem`. This preserves per-container identity and per-set
retention evidence without duplicating simulation systems.

## Golden regression

The qualified golden package is under
`outputs/simple_sdf_multi_liquid_golden_20260820/liquid_package_qualified/`.
It contains 50,000 reagent-bottle particles and 2,640 tube particles. All three
cold Isaac Sim 4.1 runs retained 100% of each set, observed zero below-floor
particles, and reported no hard errors. The result carries
`qualified_gpu_pbd_loaded_start`.

The regression also covers two composition failures found during development:
strongest-layer stage units must be preserved, and adding liquid to an existing
simple-SDF package must retain that package's collision overlay and approved
bottom plug.

Claim boundary: no robot, grasp, pour, liquid metric, or benchmark success is
claimed.

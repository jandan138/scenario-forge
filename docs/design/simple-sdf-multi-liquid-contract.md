# Simple-SDF multi-liquid contract

This route turns reviewed container geometry into a portable GPU-PBD loaded
start without putting USD, mesh, or PhysX authoring in Scenario Forge.

## Ownership

- Scenario Forge owns requests, subprocess orchestration, strict handoff
  validation, promotion, and deterministic ZIP delivery.
- ConvertAsset owns dependency closure, collider replacement, optional bottom
  plugs, particle baking, PhysX authoring, and Isaac Sim 4.1 validation.
- A consumer owns robot policy, pouring, metrics, and benchmark execution.

The workflow is intentionally split into two stages. Collision authoring must
be reviewed and built before initial liquid is added.

## Collision stage

`aan.simple_sdf_collision_spec.v1` names an exact container scope and an exact
visual `Mesh`. ConvertAsset disables prior colliders inside that scope and
authors `sdf` collision on the selected mesh. It does not edit the source USD.

A tiny invisible Cube may close a pointed container bottom only when the YAML
uses `mode: approved_cube`, contains explicit dimensions and a parent-local
translation, and sets `approved: true`. There is no inferred or automatic
bottom-plug promotion.

## Liquid stage

`aan.multi_liquid_sample_request.v1` maps every closed sampler mesh to exactly
one liquid identity:

- one shared `/__ScenarioForgeFluid/ParticleSystem` per scene;
- one `/__ScenarioForgeFluid/ParticleSets/<id>` per sampler mesh;
- a unique `particleGroup` and per-set particle count for every set;
- particles baked at producer time, with no runtime resampling.

If any set is marked `small_required`, the whole shared system uses the small
recipe: 1 mm spacing, 1.188 mm width, 1 mm contact offset, 5 mm effective rest
offset, 0.2 m/s maximum velocity, at most 50,000 particles per set, and 100,000
particles total. Otherwise the Task 02-compatible recipe is used.

## Evidence and claims

Quick validation is one cold Isaac Sim 4.1 process for three seconds and yields
only `provisional_gpu_pbd_loaded_start`. Qualified validation is three cold
processes for eight seconds each and yields
`qualified_gpu_pbd_loaded_start`. Every set must independently retain at least
99% of its particles, have zero particles below its declared initial floor,
and produce no hard runtime errors.

Neither claim implies robot success, pouring success, a liquid metric, or a
benchmark result. Failed production retains diagnostics and is never promoted
as a delivery package.

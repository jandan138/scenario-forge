# 2026-08-21 Automatic liquid sampler handoff

Scenario Forge now accepts ConvertAsset result schema
`aan.multi_liquid_sample_result.v2`. The adapter verifies package-relative
automatic sampler evidence, canonical sampler prim paths, supported modes,
target fill ratios, independent ParticleSets, the one shared ParticleSystem,
and the existing runtime report hash and claim boundary.

USD geometry analysis, closed-cylinder authoring, particle baking, and Isaac
Sim validation remain ConvertAsset responsibilities. Scenario Forge does not
reimplement them. Version 1 explicit sampler packages remain compatible.

The producer-side source-bound trials passed in Isaac Sim 4.1 at a requested
40% fill: the reagent bottle `mouth_drop` trial settled at 42.25%, and the
15 mL tube `inside_fill` trial settled at 43.62%; both retained every particle
with zero below-floor particles. These are liquid loaded-start claims only.

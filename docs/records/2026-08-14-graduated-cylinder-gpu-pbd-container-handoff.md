# Graduated Cylinder GPU-PBD Container Handoff

Date: 2026-08-14

> **Revoked on 2026-08-15.** The producer report read Isaac 4.1's authored
> `physxParticle:simulationPoints` rest-state buffer instead of live `points`.
> Corrected three-cold runs retain only 43--45 of 548 particles. Current
> Scenario Forge code rejects this historical package because each accepted
> run must explicitly bind `particle_readback_attribute: points`. See
> `2026-08-15-task02-r83-fluid-gate-blocked.md`.

Scenario Forge now has a narrow, fail-closed adapter for ConvertAsset's
qualified 250 mL graduated-cylinder GPU-PBD package. The adapter validates the
package-local manifest, profile, three-cold-run report, fixture, normalized
particle state, SHA-256 bindings, 548-particle count, source-derived
`convexDecomposition` strategy, `fluid=true`, `selfCollision=true`, retention,
support, runtime-error, and 40 FPS gates.

The loader is `load_gpu_pbd_static_container_handoff` in
`scenario_forge.adapters.convert_asset`. It maps the asset into the existing
portable `LocalUSDAssetSource` contract as a rigid object and records that
consumer physics patches are forbidden. Scenario Forge does not import Isaac
Sim or reproduce ConvertAsset mesh conversion.

The historically accepted, now revoked producer package is:

`/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/graduated_cylinder_250ml_gpu_pbd_remesh_20260814_v3/final_package/graduated_cylinder_250ml_gpu_pbd_static_r2_visual_bound`

This r2 handoff has the same historical collider and bound particle state as r1,
and additionally binds three reviewed 960 x 540 views rendered from the final
promoted package. It supersedes r1 for consumer handoff without mutating r1.

No current static-containment claim remains for this package. This record is
retained to explain the superseded decision and does not promote Task 02,
claim a successful pour, or add an episode runner.

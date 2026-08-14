# Graduated Cylinder GPU-PBD Container Handoff

Date: 2026-08-14

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

The accepted producer package is:

`/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/graduated_cylinder_250ml_gpu_pbd_remesh_20260814_v3/final_package/graduated_cylinder_250ml_gpu_pbd_static_r1`

The accepted claim remains static containment with the package-bound initial
particle state. This change does not promote Task 02, claim a successful pour,
or add an episode runner.

# ClearBorosilicate v2 six-asset handoff

Date: 2026-08-18

## Outcome

Scenario Forge publishes six independent ConvertAsset packages as a review ZIP:

- graduated cylinder 250 mL, including its outer hexagonal support base;
- beaker 325 mL;
- flat-bottom flask 250 mL, 29/42;
- dynamic beaker;
- reagent bottle 90x55; and
- Erlenmeyer flask 250 mL, 90x35.

The package binding is recorded in
`configs/source_bindings/scientific_workbench_glass_material_v2_20260818.yaml`.
The export entry point is
`scripts/export_scientific_workbench_glass_material_v2.py`.

This is an asset handoff, not a task revision. No scientific-workbench task
package, VR package, eBench config, or public material-guide page is changed by
this delivery.

## Consumer status

The six bindings deliberately use `local_usd` with role
`rigid_object_unqualified_task_instance`. ConvertAsset's static admission and
Isaac Sim 4.1 runtime smoke prove package load/render/step/reset behavior, but
do not satisfy Scenario Forge's task-interaction gates. A later task revision
must promote the selected asset only after its task-specific support, grasp,
open-top, robot-policy, and metric evidence is available.

## Visual recipe and geometry mode

The shared visual inputs are:

- `glass_color = (0.99, 0.998, 1.0)`;
- `reflection_color = (1.0, 1.0, 1.0)`;
- `frosting_roughness = 0.035`;
- `glass_ior = 1.47`; and
- `depth = 0.002`.

Thick-wall assets use `thin_walled = false`. Fixed-room Isaac 4.1 evidence
showed that the tall, narrow graduated-cylinder shell produced a near-black
axial reflection in that mode. The cylinder therefore uses the reviewed
geometry mode `thin_walled = true`; this is a renderer/geometry compatibility
switch, not a different glass color recipe. Its body becomes legible again and
the requested hexagonal base remains bound to the v2 glass material.

Ground-glass joints, stoppers, graduations, labels, and decals remain outside
the clear-body override. The glass rod is out of scope.

## Evidence boundary

The fixed-pose A/B renderer is
`scripts/ebench/render_scientific_workbench_glass_material_v2.py`. It uses the
same Isaac Sim 4.1 RayTracedLighting room, table, camera, exposure, and lights
for both variants. Its evidence does not claim physics correctness, robot
success, liquid-transfer success, task readiness, or benchmark performance.

The handoff archive contains complete package dependencies and ConvertAsset
manifests. Consumers should retain each package directory intact and open its
`asset.usd`; they should not copy only the root USD.

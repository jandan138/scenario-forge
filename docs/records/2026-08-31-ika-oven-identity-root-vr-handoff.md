# IKA OVEN 125 Identity-root VR Handoff

## Outcome

Scenario Forge now consumes the promoted ConvertAsset identity-root package
instead of applying the earlier direct-stage 0.755 m descendant bake.

The new handoff is:

`outputs/ika_oven_125_task0912_vr_identity_r2_20260831/handoff/ika_oven_125_task0912_vr_identity_r2.zip`

Inside `scene.usd`, the stage explicitly declares Z-up, meters, and 9.81 m/s²
gravity. The oven is referenced at `/World/obj_oven` with a single
root translation `z=0.755 m`. The standard table stays at its source transform;
no table, robot, joint, collider, or controller patch is authored by Scenario
Forge. VR Teleop mounts the scene default prim under `/World/_scene`, yielding
the runtime path `/World/_scene/obj_oven` declared by `task_config.py`.

## Contents

- `scene.usd`: standard VR source scene;
- `scene_open_preview.usd`: static 100-degree door preview;
- `task_config.py`: all operation objects in `obj_prim_list`, local XY
  randomization ±0.01 m, and no robot-material/contact-offset overrides;
- `deps/oven/`: the complete ConvertAsset package, qualification report, and
  promotion receipt;
- empty SDF-capable conical flask and beaker on the lower shelf;
- standard table and package-local lighting.

## Evidence and claim boundary

ConvertAsset passed identity-root composition under canonical, ordinary
`obj_oven`, and VR `_scene/obj_oven` namespaces in Isaac Sim 4.1. Task 09/12
door/button/mains controls passed in all three mounts. Promotion is deliberately
`relocatable_task_scoped`; `relocatable_full` remains false because additional
left-hinge and relocation-invariant full-appliance probes are not closed.

Scenario Forge tests verify 16 composed joints, 15 chassis-relative body0
bindings, SI stage metadata, unchanged table transform, package-local
dependencies, ZIP contents, and VR config paths. An r1 candidate omitted the
meters metadata and therefore experienced default centimeter-scale gravity;
r2 supersedes it. Robot-policy and benchmark success remain false.

The older direct-stage package remains available only as a fallback and
historical comparison. It is not the preferred VR integration path.

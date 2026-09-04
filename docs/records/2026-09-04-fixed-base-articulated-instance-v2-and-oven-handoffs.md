# Fixed-base articulated Instance v2 and oven handoffs

## Problem

Task09 r15 and Task12 r1 composed a promoted oven whose links and joints were
under `/World/obj_oven/Instance`, but the object root was not an articulation.
The oven body was kinematic, so adding an articulation root downstream produced
the PhysX kinematic-link error; making the body dynamic without a fixed-base
joint allowed the constrained parts to move away from their authored assembly.
The `Instance` prim was also a `Scope`, while VR post-processing requires a
transformable `Xform` boundary.

## Contract v2

Scenario Forge now has a strict final-scene validator for fixed-base articulated
objects. It requires:

- an enabled articulation root on `obj_*`;
- identity `Xform obj_*/Instance`;
- every rigid link below `Instance` and no kinematic links;
- a rigid `Instance/Body` base;
- `Instance/Joints/BaseFixed` from the object root to the base;
- valid internal joint targets, with only the fixed-base root anchor allowed
  outside `Instance`.

The v1 Scope validator remains available for historical immutable handoffs.
Scenario Forge does not author these physics properties; it checks and consumes
the promoted ConvertAsset package.

## New handoffs

- Task09 r16 consumes the OVEN 125 r16 fixed-base package. The task vessels stay
  on the main workbench. Its equipment cart uses scale `(1, 1, 0.7)` and the
  oven root is lowered to `z=0.5285 m`.
- Task12 r2 derives from Task09 r16 and preserves the completed-heat state and
  the beaker/conical-flask placement on the lower shelf. It uses the same cart
  and oven height.

All pre-existing oven link, joint, panel, button, knob, shelf, and runtime graph
paths remain unchanged. The only new oven prim path is
`obj_oven/Instance/Joints/BaseFixed`; the `Instance` path is unchanged and only
its prim type changes from Scope to Xform.

Task09's reusable evidence renderer now accepts `--oven-z-offset`. The r16
retake uses `-0.2265 m`, matching the reduced cart height, so the control-panel
view follows the lowered oven instead of cropping the panel below frame.

## Verification and boundary

Unit tests cover the v2 contract and both package generators. Final handoff
checks include Isaac Sim 4.1 static/device smoke, fixed evidence renders,
package dependency closure, and the ConvertAsset producer receipt. Isaac Sim
4.5 compatibility is inherited from the producer qualification. No robot
policy or benchmark success is claimed.

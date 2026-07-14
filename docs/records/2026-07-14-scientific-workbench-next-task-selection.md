# 2026-07-14 Scientific Workbench Next-task Selection

## Decision

After the current flask-to-cylinder task, the implementation order is:

1. `wetlab_tabletop_reagent_delivery` (`#6`);
2. `wetlab_two_sample_add_and_swirl` (`#4`);
3. `wetlab_dryingbox_beaker_load_start` (`#3`).

This is a dependency order, not a claim that any of the three is executable now.
No placeholder scenario package is published as task-ready.

## Why this order

Task `#6` reuses the qualified flask and only adds a Scenario Forge semantic target
region. Task `#4` then reuses the same flask package twice and adds one qualified
beaker, while expanding coverage from pick/place to ordered pour and shake. Task
`#3` reuses that beaker and adds articulation, button, and inside-volume semantics.

The first two are the intended small expansion set. The third is the next
interaction-heavy task after its appliance package exists. Contact-point
generalization (`#8b`) waits until both cylinder and beaker target classes are
qualified; a one-target variant would not establish generalization.

## Current blockers

- `#6`: the selected flask still lacks a source-bound rigid-root package and
  grasp/lift/place evidence.
- `#4`: the flask dependency above remains, and `lab_001#/World/beaker2` has no
  source-bound dynamic grasp/pour/shake handoff. Two instances must also prove
  independent UID and physics state.
- `#3`: use `DryingBox_01`, not the current context-only `DryingBox_03`. DB01 has
  the relevant door/button topology, but still needs an interaction-qualified
  source-bound bundle with door, handle, button, reset thresholds, and inside
  placement volume.

LabUtopia's historical `Beaker_01` AAN package passed generic reset/step/render/
metric/logging smoke, and the InternData-style beaker delivery demonstrates useful
rigid-root and open-inner-wall patterns. Neither proves robot grasp, shake, or
source binding for the selected `lab_001#/World/beaker2`, so neither is promoted to
task-ready status.

## Upstream grouping

Request two ConvertAsset deliveries rather than one ticket per failed rollout:

- a vessel-family bundle for `conical_bottle03`, `graduated_cylinder_03`, then
  `beaker2`, with rigid-root identity, mass/inertia, grasp/support/opening frames,
  open-top collision, multi-instance independence, and Isaac 4.1 interaction
  evidence;
- a `DryingBox_01` interactive bundle covering body, door, handle, button,
  articulation parameters, observable state thresholds, reset, and inside volume.

The detailed first-bundle acceptance contract is in
[`qualify-bimanual-pour-vessels.md`](../operations/qualify-bimanual-pour-vessels.md).

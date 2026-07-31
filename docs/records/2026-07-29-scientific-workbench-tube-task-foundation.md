# 2026-07-29 Scientific Workbench Tube-task Foundation

> Identity correction (2026-07-31): this dated record used obsolete PDF-derived
> task numbering. The two cases below are integration prototypes, not live
> Feishu task 7 or task 11. See
> [the correction record](2026-07-31-scientific-workbench-task-design-correction.md).

## Outcome

Scenario Forge now has compiler-side definitions for wetlab tasks 7 and 11:

- `wetlab_centrifuge_tube_load_start_no_wait`;
- `wetlab_bimanual_hold_rack_insert_tube`.

The implementation adds a general articulated-object handoff rather than a
centrifuge-specific branch. It consumes a hash-bound ConvertAsset device profile,
maps semantic joints to GenManip DOFs, explicitly converts revolute runtime values
to radians and prismatic values to metres, and exports native GenManip articulation
status goals. No GenManip checkout was modified.

## Selected assets and layout

Task 7 selects
`HCI955350812560602-1.usd`. Its source topology has one fixed joint and three
movable joints: lid, rotor, and start button. Two clean-room-reviewed source
renders show an open lid, an accessible rotor with empty holes, and a visible
front control. This is selection evidence only; the raw source is severely
mis-scaled in authored metric units and is not task-ready.

Task 11 selects the BlenderKit tube-rack-with-tubes source and a separate
Taoyuan10K test tube. Both tasks reuse the admitted
`scientific_environment_3fo4k5c9jd44` full-room package at the
`north_bench_pair_east` workspace and the existing visual-static eBench table.

## Contracts added

- `scenario-spec/v0.5` adds ordered
  `articulation_joint_state_reached` predicates while retaining the general
  relative-pose and initial-pose predicates needed by these tasks.
- `scenario-source-bindings/v0.2` accepts `usage: articulated_object`.
- The ConvertAsset adapter admits only a passed, source-bound articulation
  contract with one root, complete/contiguous DOF mapping, valid reset values,
  hash-bound semantic profile, Isaac-observed runtime DOF order, declared passing
  task gates, runtime qualification, and zero scoped warnings.
- The GenManip export writes native articulated object config, initial joint
  positions, semantic part paths, and ordered joint-state ranges. Raw USD degrees
  are never copied into GenManip runtime positions.
- The task generator selects an explicit v0.1 transport compatibility projection
  for the documented, unmodified GenManip checkout. Its native goals remain
  executable there, while the complete v0.5 semantic contract is retained beside
  the projection and remains the collected package's declared semantic authority.
- The task generator consumes producer-measured named frames and derives
  world-axis success ranges after applying each target object's pose. The checked-in
  coordinates are readable templates, not an authority that can override the
  admitted asset contract.

## Current readiness

The compiler foundation is complete. Final task packages and package-matching
Isaac 4.1 scene renders are not yet claimed because three producer-owned
normalized facades and their three source-bound packages are still required:

1. articulated HCI centrifuge;
2. rigid test tube;
3. rigid tube rack with one qualified empty socket.

The exact producer request is
[`../operations/scientific-workbench-tube-prototype-asset-admission-request.yaml`](../operations/scientific-workbench-tube-prototype-asset-admission-request.yaml).
After those packages pass, the two outputs can be generated with
[`../operations/generate-scientific-workbench-tube-prototypes.md`](../operations/generate-scientific-workbench-tube-prototypes.md).

This record does not claim robot rollout success, benchmark success, real-world
physical calibration, or a final task-package render.

# Scientific Workbench Task 09 r12 VR-first handoff

Task 09 r12 removes the freestanding eBench table and places the analog oven
and sample beaker on the floor of the Code-as-Room analytical-instrumentation
environment.  The room owns visible floor rendering.  A qualified static
support package keeps the compatibility object id `table` but its VR wrapper
is invisible, so there is no duplicate slab in the final view.

The sample beaker uses the glass-material-v1 package at a task-instance uniform
scale of 0.7.  The oven is placed at `(0.35, 0, 0)` and the beaker at
`(-0.35, -0.16, 0)`.  The two independent context props from r11 are absent.

The first ConvertAsset experiment requested convex decomposition on all twelve
oven link meshes.  Static admission passed, but Isaac Sim 4.1 did not finish
the first physics cook within 900 seconds.  The deliverable package therefore
uses convex decomposition only on the three Task 09 controls: the main door
(including its handle geometry), power rocker, and upper temperature dial.
Fixed and non-task links preserve their source collision approximation.  This
variant passed load/render/step/reset, the three task-control state cycles,
locked-joint stability, sample-shelf support, and floor-mounted fixed-base
stability.  The timed-out all-link facade remains ConvertAsset evidence and is
not a consumer entrypoint.

The VR handoff has `/World` as the direct-open default prim.  Runtime object
paths remain `/World/_scene/obj_oven` and
`/World/_scene/obj_sample_beaker`, because the VR collector mounts the scene
default prim beneath `_scene`.  Both objects use local XY randomization of
plus/minus 0.01 m.  The generated `task_config.py` intentionally omits all
three `set_robot_*` physics override fields requested by the collection team.

Isaac Sim 4.1 direct-open smoke passed with zero physics steps.  This release
does not claim VR teleoperation success, robot policy success, complete Task 09
success, benchmark score, or thermal behavior.  The 0.7-scale glass beaker
still requires task-specific robot interaction qualification.

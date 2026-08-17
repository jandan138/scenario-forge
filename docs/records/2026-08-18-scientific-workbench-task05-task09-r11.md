# Scientific Workbench Task 05 / Task 09 r11

## Outcome

Scenario Forge now publishes two formal dual-consumer packages:

- Task 05 removes a loose 29/42 stopper from a 250 mL flat-bottom flask and
  places it in a stopper rack;
- Task 09 opens an analog oven, loads a transparent beaker, closes the door,
  sets the upper temperature dial, and presses the power rocker.

Both packages use the 2.0 x 0.8 x 0.755 m eBench table, the eBench dual-arm
robot contract, a Code-as-Room background, exact Feishu progress weights, an
eBench/GenManip export, and a VR export.  Final artifacts are under
`outputs/scientific_workbench_task05_task09_r11_20260817/`.

## Asset boundary

The flat-bottom flask and analog oven are consumed through ConvertAsset
source-bound packages from revision `dc77e45`.  Scenario Forge does not add an
asset-specific collider, scale, mass, inertia, joint drive, or warning
suppression.  The oven's door, upper dial, rocker, locked non-task joints, and
sample shelf are taken from its passed articulation profile.

The oven package owns its Y-up to Z-up mount.  The scenario pose names the
support-plane location on the table.  The eBench adapter composes that support
pose with `aan.articulated_mounting.v1.support_plane_to_root_mount_pose` when it
writes GenManip's articulation initial state.  This keeps the directly opened
USD upright while also preventing the articulation from reverting to its raw
Y-up pose after reset.

## Placement and reset findings

The fixed oven uses its declared 0.875 x 0.693 m support footprint for the
table-edge gate, while its 0.875 x 0.770 x 0.9332 m visual envelope remains
visible in evidence.  Its minimum support-footprint edge clearance is 5.35 cm;
after the VR contract's worst-case 1 cm XY offset, 4.35 cm remains.

The loose stopper initially settled 14.9 mm below the measured joint-entry
frame during a zero-action Isaac 4.1 warmup.  The task therefore starts at that
observed physical rest position and records the offset from the authoritative
`obj_flask.closure_seat` frame.  No hidden constraint or relaxed support gate
was added.

## Runtime evidence

Each eBench package passed the initial-scene load/reset, zero-action runtime
geometry, camera composition, and visual-ready gate.  Each VR package passed
the Isaac Sim 4.1 direct-open contract: `/World` defaultPrim, no authored
`/World/_scene`, direct room/table/light/`obj_*` children, exact `obj_prim_list`,
and local XY randomization of +/- 0.01 m with fixed yaw.

The final archive is:

`outputs/scientific_workbench_task05_task09_r11_20260817/handoff/scientific_workbench_task05_task09_r11.zip`

## Claim boundary

`visual_ready` and `asset_interaction_ready` are true.  `task_interaction_ready`
and `robot_policy_success` remain false.  The evidence does not claim a complete
robot rollout, benchmark success, real thermal behavior, or real-world physical
calibration.

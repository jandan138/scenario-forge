# Experimental PBD workbench variants

The previous PBD beaker-to-beaker package placed Lift2 at the world origin,
inside the source workbench. The visible intersection was a layout-contract
failure, not a renderer defect. The prior handoff also left the beakers at a
world-space layout that was no longer appropriate once the robot moved.

LabUtopia handoff v0.3 now owns two deterministic variants. The recommended
`source_workbench` variant preserves the original wide workbench. The
`ebench_workbench` variant consumes the hash-bound ConvertAsset static-support
table package. In each variant the source beaker, target beaker, and all 3,600
PBD points share one translation, while Lift2 moves to the table's `x_min`
side. The robot-to-task relative layout is identical across the two variants.

Scenario Forge validates rather than repairs the producer scene. Its new
adapter gate checks:

- exact agreement with the producer-declared Lift2 profile and spawn;
- circular robot-base clearance from the producer-qualified table AABB;
- at least 0.10 m clearance from every table edge for both beaker AABBs;
- placement in the half of the tabletop facing the robot.

The two 2026-08-07 packages pass with approximately 0.329 m robot-table
clearance. The target beaker is the limiting tabletop object at approximately
0.105 m from the robot-facing edge. Both GenManip initial-scene previews pass
in Isaac Sim 4.1 with three 1280x720 views. Local visual review finds the robot
outside the table in both variants, both vessels supported and visible, and no
obvious robot/table or vessel/table penetration.

The renderer needed the documented external CuRobo source and a process-local
mesh cache because the shared cache filesystem returned `ENOSPC`. A clean,
detached GenManip code copy at revision
`6ff55ed7c7bd441825d56f1016a30e03b524ebea` was used; GenManip code and the
managed Isaac environment were not changed.

Claim boundary: this record establishes package structure, producer handoff
qualification, initial layout geometry, and initial-scene rendering only. It
does not establish inverse-kinematics reachability, stable contact grasp,
liquid transfer, policy success, or benchmark success.

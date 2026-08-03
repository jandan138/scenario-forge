# GenManip full-room preview contract v0.3

Scenario Forge keeps ordinary tabletop packages on the compact v0.2 three-view
preview contract. A collected package upgrades to v0.3 only when its manifest
contains a source asset whose producer role is `visual_static_environment`.

The v0.3 contract requires seven 1920 × 1080 evidence images:

1. `workspace_closeup`
2. `scene_overview`
3. `task_object_closeup`
4. `room_topdown`
5. `room_corner_a`
6. `room_corner_b`
7. `room_entrance_eye_level`

All four room views contain the recovered eBench robot, table, and task objects
in the same frame as the actual runtime room. The top-down camera uses composed
world north-up. The corner cameras use opposite high-angle diagonals. The
entrance camera is placed inside the largest authored wall opening at a nominal
eye height of 1.65 m and looks toward the recovered workcell.

Corner views may temporarily set complete `Wall_*` Xform roots on the two
camera-nearest sides to invisible. This is an evidence-only stage override. The
renderer records every runtime prim path and restores its prior visibility.
Top-down and entrance views may not hide room prims. Source USD, package
composition, task state, and physics are never changed.

The automatic camera gate records projected room and workcell bounds. Top-down
and corner views must fully frame the room and workcell with useful room image
occupancy. The entrance view must fully frame the workcell. A failed v0.3 gate
retains the package and images but writes a failed visual-ready receipt; the
package must not be published in the gallery until reviewed.

ConvertAsset workspace-zone profiles may optionally provide a source-bound
`room_survey` override with reviewed camera positions, targets, and complete
wall roots. Scenario Forge maps those source-composed coordinates through the
room instance placement. Automatic runtime placement remains the default.

This contract is visual evidence only. It does not add a benchmark runner or
claim reachability, collision-free motion, manipulation success, liquid
transfer, policy success, or benchmark success.

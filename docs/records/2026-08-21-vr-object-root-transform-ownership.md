# 2026-08-21 VR object-root transform ownership

> Superseded on 2026-08-23 by
> `2026-08-23-vr-object-materialization-and-transform-correction.md`. The
> explicit complete-TRS and scenario-pose equality rule below was based on an
> incorrect interpretation of the downstream requirement and is no longer an
> export gate.

Future VR exports now enforce a single task-pose owner for every object listed in
`task_config.py:obj_prim_list`. Each corresponding source root must be a matching
`obj_*` Xform with an explicit reset stack and canonical translate, orient, and
scale operations. Its local pose must equal the canonical scenario object pose
within `1e-6`.

The rule applies to task objects and randomizable tabletop context props. It does
not rename or constrain the room, table, robot, lights, PBD helper prims, or
asset-internal child transforms. A scene where the root remains identity while a
child prim alone carries the task placement is blocked. Scenario Forge does not
attempt automatic transform lifting because that could change articulation,
collision, or asset-local semantics.

Every passed export contains `transform_ownership.json`, and the parity manifest
records its SHA-256. Both ordinary referenced-asset scenes and producer-entrypoint
scenes pass through the same composed-USD gate before the staging directory is
atomically promoted. Historical output packages are not rewritten.

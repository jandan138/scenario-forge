# Task-interactive support frame and preview stability

Date: 2026-07-30

## Decision

Scenario Forge no longer treats a package-wide aligned bounding-box minimum as
the tabletop contact witness for task-interactive assets. A validated
ConvertAsset handoff now emits
`scenario-forge-task-interactive-geometry/v0.1` with:

- the producer's authoritative, root-local `support` frame as a USD/Gf
  row-vector `support_frame_local_matrix`;
- `support_frame_source_sha256`, equal to the validated interaction-contract
  payload hash for rigid objects or the validated device-profile hash for
  articulated objects; and
- the existing identity entry transform and package bound.

Rigid and articulated handoffs fail closed if the validated producer contract
does not contain an authoritative `support` frame parented directly to the
asset entry prim. This is adapter metadata carried by the package manifest; it
is not duplicated in the GenManip runtime contract.

Optional producer `manifest.task_qualifications` entries are also verified and
propagated. Every entry must be a unique, passing qualification with a
package-local report whose SHA-256 matches. The rack-insertion task requires a
`tube_insertion` qualification. This is an affordance admission requirement,
not consumer-side physics authoring.

## Placement and preview evidence

The tube-task generator places each task object with:

`root_z = table_top_z + 0.01 m - rotated_support_frame_offset_z`

Task-level scale must remain identity. No asset-specific collider, mass,
inertia, or scale repair is introduced.

The Isaac/GenManip evidence process records task-object state immediately
after recovery and again after the existing 50-step zero-action warmup. Each
qualified object record contains:

- root world pose;
- authoritative support-frame world point; and
- world bound and extent.

The structural preview gate requires:

- producer extent agreement within 5% at both warmup boundaries;
- post-warmup tabletop XY containment with 10 mm tolerance;
- root up-axis tilt no greater than 10 degrees; and
- post-warmup support-frame/tabletop gap within 10 mm.

The overall AABB minimum remains in the gate output only as a diagnostic. It
cannot make a package pass the support check.

## Boundary and runtime follow-up

Pure package layers do not import simulator SDKs. USD/Isaac inspection remains
inside the one-shot preview renderer process. GenManip is not modified.

Unit coverage proves that missing support frames and unbound task
qualifications fail closed, a collider-inflated AABB cannot spoof support, a
tipped root is rejected, and support-based placement is generic. Final r9/r4
packages still require an Isaac Sim 4.1 preview run to confirm the producer
support frames, composed root poses, and live PhysX settle behavior agree with
these contracts.

The rejected predecessor behavior was also checked directly:

- centrifuge r8 has no profile frame named `support` and is rejected at
  handoff; and
- tube-rack r3 has a root-local support frame but no bound `tube_insertion`
  task qualification. Its package bound extends 13.5 mm below that support
  frame, so the new placement/gate path cannot be made to pass by the inflated
  proxy AABB.

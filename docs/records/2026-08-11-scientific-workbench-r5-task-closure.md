# Scientific workbench r5 task closure

Date: 2026-08-11

## Result

The unified asset-expansion generator now produces ten Feishu-aligned tasks and
fourteen scene packages. Task 7 is emitted against five interchangeable room
backgrounds; the other tasks use their reviewed semantic room class.

Available task numbers: `1, 2, 4, 5, 7, 8, 13, 14, 15, 16`.

All packages use the same source-bound LabUtopia visual table with exact outer
dimensions `2.000 × 0.800 × 0.755 m`, an identity table prim, and the shared
Lift2 spawn at the center of the near long edge. Task objects follow the
near-side placement policy while retaining edge clearance.

Tasks 1, 13, and 16 use the newly qualified 250 mL 29/42 conical flask. The
older `conical_bottle03` package tipped during the shared preview warmup, so it
is not used in the r5 review set; no consumer-side rotation or physics patch was
added.

## Rendering corrections

The GenManip evidence renderer retains seven 1920×1080 views but allocates only
one RTX RenderProduct at a time. Physics is advanced once during the declared
zero-action warmup, then frozen while the seven cameras record the same scene
moment. The entrance camera stands outside the reviewed doorway so it frames
more of the room and workcell.

The runtime geometry gate compares exact sorted axis extents at warmup start.
After physics starts it uses the longest AABB axis when no producer-qualified
post-warmup extent exists, because small rigid rotations change an axis-aligned
box without changing asset scale. Explicit producer-qualified per-sample
extents remain strict. Tabletop bounds, support gap, and root tilt remain
separate blocking gates.

## Honest release tiers

- full semantic candidates: Tasks 4, 5, and 7;
- candidate with a declared threaded-closure gap: Task 8;
- liquid/interaction prototypes with partial portable scoring: Tasks 1, 2, 13,
  14, and 16;
- layout-only prototype: Task 15.

The incoming rigid-asset archive contains seven raw reagent-bottle candidates,
but none has a qualified interaction package yet. Their presence is therefore
recorded as source inventory only and does not promote Task 3 or Task 15.

These labels do not claim policy success, robot reachability, grasp retention,
liquid-transfer success, or benchmark success. Provisional IK remains not run.

## Handoff shape

The review handoff is derived from the VR adapter and deliberately contains no
robot model. Each task directory contains `scene.usd`, `task_config.py`,
`parity_manifest.json`, and its package-relative `deps/` closure. Task 1 is
distributed separately from the nine regular tasks.

## Verification

- `make check`: 618 tests passed; lint, package smoke, Phase 10.x strict smoke,
  and diff check passed.
- All fourteen overview renders were inspected after a single shared physics
  warmup; the three tasks that had reused the tipping legacy flask were rebuilt
  with the qualified 29/42 flask.
- The directory page was reviewed in Chromium at `1440×1000`, `834×1112`, and
  `390×844`; all ten evidence images returned HTTP 200.
- Both ZIP archives passed `unzip -t`; their `scene.usd` files contain neither
  robot references nor absolute USD asset paths.

## Remaining work

Robot reachability, policy rollouts, threaded closure, real liquid transfer,
and interactive weighing remain downstream qualifications. They are not
silently implemented in this repository.

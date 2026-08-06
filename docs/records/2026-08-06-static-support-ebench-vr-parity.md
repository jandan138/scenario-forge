# Static-support and eBench/VR parity closure — 2026-08-06

## Outcome

The canonical bimanual-pour recipe now consumes a source-bound ConvertAsset
`static_support` table instead of asking GenManip to synthesize a generic table
collider. Scenario Forge source bindings v0.3 carry that role explicitly. The
eBench and VR adapters consume the same canonical asset identities, poses, table
physics contract, robot model/base pose, and Isaac/PhysX contact profile.

Canonical outputs:

- eBench package: `outputs/scientific_workbench_bimanual_pour_static_support_v1_20260806`
- VR handoff: `outputs/scientific_workbench_bimanual_pour_vr_r2_20260806`
- background variants: `outputs/scientific_workbench_background_gallery_v5_20260806`

## Producer evidence

The table package is ConvertAsset
`outputs/labutopia_lab001_table_static_support_r2`, revision
`77600fc529446eeea0a6abc8de04da4c484dbae8`. Its manifest reports pass with no
blockers. The support profile owns the collider and physical material and passes
six Isaac 4.1 probes: centre, four edges, and side impact. Scenario Forge adds no
table-specific collider, mass, inertia, or warning suppression.
The friction/restitution values are provisional and unmeasured; the pass certifies
the recorded probes, not real-material calibration or leg/cabinet collision.

The source and target vessels use the identity-root deliveries at ConvertAsset
revision `db71fde4e97fa2698926b23a2a86af663eda6177`. Consequently the canonical
task poses and named opening frames are Z-up identity transforms rather than
consumer-side corrections.

## Runtime and visual evidence

The canonical GenManip package completed the Isaac 4.1 initial-scene gate. Local
clean-room visual review of `scene_overview.png`, `workspace_closeup.png`, and
`task_object_closeup.png` passed: the complete laboratory is visible; the table,
Lift2, flask, and cylinder have plausible relative scale; both transparent vessels
are upright and supported; and no floating or grossly displaced task object is
visible. The workspace crop intentionally contains less room context and is not a
separate background-quality claim.

The geometry gate measured the table top at approximately `z=0.772761 m`; support
gaps for the two task vessels were below `1e-5 m`, tilt stayed below `0.016°`, and
both objects remained within the tabletop footprint. This is initial-state and
composition evidence, not a rollout.

All five Code-as-Room variants were regenerated from this canonical package under
`scientific_workbench_background_gallery_v5_20260806`; all five v0.3 seven-view
preview gates passed. The published background gallery was refreshed from those
artifacts. A real Chromium audit at 1440×1000, 820×1000, and 390×844 found 40/40
images loaded, five room cards present, no failed requests or console/page errors,
and no document-level horizontal overflow. Visual inspection found no recurrence
of the previously reported floating bioclean bottle group.

## Parity boundary

The shared runtime profile is `manip/lift2/R5a_isaac41_vr600_v1`, derived from
Feishu contract `IWsNwtFX1iilwHkz5OGcnGyZnRd@600`. VR exports include one declared
exception: robot joint initialization, because that config contract exposes a
robot base pose but no joint-vector field. There is no exception for collision,
materials, object poses, task semantics, or PhysX settings.

The VR plugin code was not available for an end-to-end runtime launch. Therefore
the VR evidence proves portable USD/config generation and parity closure only. It
does not prove headset/controller operation, a successful bimanual policy, liquid
transfer, or benchmark success.

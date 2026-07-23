# Scene1_hard Visual Context for EBench Bimanual Pour

Date: 2026-07-23

## Decision

The target scene is a two-layer composition:

1. `Scene1_hard.usd:/World/lab_015` is the complete visual laboratory under the
   GenManip `room` prim.
2. `lab_001.usd:/World/table` is the existing EBench-compatible static table.

The Lift2 dual-arm robot and the qualified flask/cylinder packages remain on their
existing EBench coordinate protocol. Scenario Forge does not consume
`Scene1_hard:/World/table_hard`, add local asset repairs, or modify GenManip.

## Why the room must retain parent composition

`lab_015.usd` is a payload of `Scene1_hard.usd`, not a portable replacement for
the parent scope. A direct USD audit showed:

| Input | Stage metres-per-unit | Authored room scale | Resulting room size |
| --- | ---: | ---: | ---: |
| `Scene1_hard.usd:/World/lab_015` | 1 | 0.001 | about 8.055 m × 21.554 m × 4.153 m |
| direct `SubUSDs/lab_015.usd:/World` | 0.001 | 0.001 | about 0.008 m × 0.022 m × 0.004 m |

The parent also contributes approximately `(0.007898, 0.270606, 0)` translation
and a 180-degree Z rotation. Therefore a direct payload package would render a
1000-times-too-small room and is explicitly rejected as a product input. The
correct ConvertAsset delivery is source-bound to the parent `Scene1_hard.usd`
scope and must preserve its composed metrics and transform.

## Historical producer blockers

The direct-payload ConvertAsset probe was useful only as a diagnostic. It proved
that its material closure and visual-static admissions work, but it is not a
consumer delivery:

- source SHA-256: `4cab00a66cfd0007f733e0f2b91bfb955d9a8b0dc91331bee695878b1fd3b1ad`;
- `physics_closure`, `output_role_admission`, visual fingerprint, cold load,
  render readback, physics step, and warning gate passed;
- reset alone blocked because `scope_rigid_bodies=[]` was evaluated by the dynamic
  rigid-body reset subgate, although the scope transform itself reset exactly.

A fresh context-independent visual review of that probe's render plus three material
views failed: all four images showed a small pale/translucent isolated object on a
dark background, with no visible room, bench, instruments, or floor. There was no
obvious pink fallback material, but the images are not usable evidence of a complete
laboratory. This independently confirms that the direct-payload route must not be
promoted.

The same AAN-06 issue historically blocked the otherwise valid
`lab_001:/World/table` `visual_static` delivery. It was a ConvertAsset regression,
not a table-asset or Scenario Forge defect.

The first correct parent-scope probe, `Scene1_hard.usd:/World/lab_015`, also
blocked at AAN-03 because ConvertAsset admitted dependencies from the whole root
layer before pruning the requested scope. The unrelated root-level `table_hard`
has unresolved material dependencies including `Map #1461`, three
`lounge_booth_table_texture*` files, and `Steel_Stainless_BaseColor.png`. The
historical LFS object that was said to repair this table returns HTTP 404 here, so
Scenario Forge must not reconstruct it.

## Delivered ConvertAsset resolution

ConvertAsset shipped both fixes in
`main@73a84d3c2cfc8378cd5c255cf2282a20da017b8f`:

1. Scope reset passes for `visual_static` assets with no rigid bodies; the
   rigid-body reset subgate is recorded as `not_applicable`. Dynamic assets keep
   the strict rigid-body reset check.
2. Dependency admission is scope-first. The selected scope retains its bound
   materials, parent USD composition, stage metrics, and authored transform while
   unrelated root assets remain evidence-only out-of-scope dependencies.

Delivered packages:

| Delivery | Package | Manifest SHA-256 | Root USD SHA-256 |
| --- | --- | --- | --- |
| Scene1 room | `outputs/convertasset-scene1-hard-lab015-room-20260723` | `1dfd59e67f6380d8737e5ae9ad6b27fbb53d1ab897680b5f0e0da819f8b47f84` | `70bd34e570595ba03f4a1b084dd70128c5f01033e57c9b150fd3ce03dc62b652` |
| EBench table | `outputs/convertasset-lab001-table-visual-static-20260723` | `ab192c2678482ceca5b65bfa22564e1700a707f4f43713afe31aa02542a8051d` | `dd3cde5a1d764b6367e93f01e938cd29e8973996bc8b7863a7f922b509bd1e88` |

The corresponding immutable source SHA-256 values are
`1611dd3621bb30091d53c6f9d9e818d341085a102b2603756dc06c103f52f1b4`
for `Scene1_hard.usd` and
`b3861b5a17945abe401062a04125969c3a63b0f8a0a5ce0026a461dbdfc935f2`
for `lab_001.usd`. ConvertAsset reports both sources unchanged.

Both manifests report `overall_status: pass`, seven passing stage gates, no
blocked reasons, zero active physics residue, passing
load/render/step/scope-reset evidence, and zero scoped or unattributed PhysX
warning events. Scenario Forge's current handoff loader accepted both exact
packages without an adapter exception or local repair.

The room claim remains limited to `/World/lab_015`. `table_hard` is still
out-of-scope and unqualified; that is evidence, not a waiver, and future use
requires a repaired source plus a separate admission. Both packages remain
`visual_static`; neither is a dynamic or task-ready asset.

## Scenario Forge implementation now in place

- Source bindings accept the explicit `visual_static_environment` and
  `visual_static_object` ConvertAsset usages, with strict source, scope, runtime,
  warning, visual-fingerprint, and no-physics-residue validation.
- The bimanual-pour generator expects the parent Scene1 room delivery and the
  separate EBench table delivery, while retaining the existing dynamic vessel
  packages.
- The overview renderer includes `room`, Lift2, table, and task objects; the
  workspace renderer stays focused on the two vessels and both end effectors.
- In the EBench adapter a `visual_static_object` is currently allowed only as the
  declared table. This makes GenManip's existing static-table collider policy
  explicit and prevents a non-table visual asset from silently taking GenManip's
  generic rigid-body default.

The final full Scenario Forge check passed after the runtime-entry change
(`360 passed` plus lint, package smoke, suite smoke, and Phase 10.x strict checks).

## Runtime integration result

The first two private candidates exposed consumer-side composition defects and
were rejected rather than promoted:

1. With the table pre-embedded in `scene.usda`, GenManip recovery saw an existing
   `obj_table` and therefore never executed the requested `add_colliders: true`.
   The narrow `/World/table` reference also left two material bindings targeting
   sibling `/World/Looks` prims outside the reference scope. The vessels fell
   through during the evidence warmup.
2. Loading the raw ConvertAsset root through GenManip recovery fixed material
   scope and executed `CollisionAPI applied`, but retained the source table's
   internal transform below the episode wrapper. That compounded transform made
   the support surface only a few millimetres across, so the vessels still fell.

The accepted adapter contract leaves the visual-static table out of the initial
scene and emits
`source_bundle/scenario_forge_runtime/table.usd`. This thin layer references the
unchanged ConvertAsset root `/World`, retains its complete material closure, and
clears only the effective `xformOpOrder` at the reference root and declared table
scope. The episode wrapper remains the sole effective pose/scale owner. A USD
composition check showed the resulting table bounds exactly match the previous
correct direct-scope bounds (approximately
`1.17247 m × 1.85130 m × 1.17248 m`) while both material bindings resolve below
the runtime wrapper.

The promoted package is
`outputs/scientific_workbench_bimanual_pour`. Its private canary used
GenManip `014bf5435a373df9b3bcf5a69aa7fe22d17f613d` and recorded:

- GenManip native table preload and `CollisionAPI applied`;
- both vessels stable on the dark-blue table after the zero-action warmup;
- zero known blocking material signals;
- passing package validation with the asset lock required;
- passing structural preview-evidence validation;
- an independent clean-room visual `PASS` with no blocking defects.

Evidence hashes:

| Artifact | SHA-256 |
| --- | --- |
| `workspace_closeup.png` | `dd109c94da6f17da6ff2cb34fc226e9a4eebce74c495dd80cad0d51f0cb381fa` |
| `scene_overview.png` | `8b469eb2c9a9b64a5d910661b3fbacdc2976e6efbe47a3b93d034be7e60e7c02` |
| runtime `table.usd` | `ebdf23e0506c591c940fe81d363185ab7e68d5aec831030887edf3385aee6ced` |

The overview's wide gray margin is optional camera polish, not a composition
blocker. This evidence covers a correctly composed, post-reset initial scene. It
does not claim a grasp, five-stage oracle rollout, complete pour, liquid transfer,
policy success, warning-free whole runtime, or calibrated real-world physics.

## Exit criteria

Run the documented generator, inspect both initial-scene images in a clean-room
review, and only then promote the candidate. That establishes the paper-style
visual context plus eBench dual-arm task composition. It does not by itself
establish grasp success, a full pour, liquid transfer, or an oracle rollout.

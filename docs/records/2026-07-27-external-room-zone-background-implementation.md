# 2026-07-27 External Room Zone-Background Implementation

Scenario Forge now supports one admitted external visual-static environment
asset with multiple source-bound workspace zones. The public background asset
identity is `scientific_environment_3fo4k5c9jd44`; individual task packages
are addressed as `<asset-id>__<zone-id>`.

The implementation keeps the portable ScenarioSpec unchanged. Every zone uses
the same background `scene.asset_id`, while only the visual room instance pose,
reviewed inactive source assembly roots, composition yaw, and scenario ID vary.
The fixed eBench table, robot, vessels, steps, invariants, and success
predicate remain byte-equivalent to the baseline task.

The external source snapshot is extracted and intake-bound, and it has now
passed ConvertAsset admission through a producer-owned consumer facade. The
verified archive SHA-256 is
`396608472548b545ffe1cf0c4d403a125590ac7398b669d1a6cd3436a6972e25`; the
extracted tree has SHA-256
`a3bea79c8a25cb4b3f8ed9715ee9a63e91c291924462c14c86e33121debc8346`, and
`world.usda` has SHA-256
`03aa64f29a20517e33e47c75620cd4326f70e39963b8880750a36f6988de45bd`.

Source inspection changed the admission contract: raw `world.usda` has three
top-level namespaces, `/world`, `/Root`, and `/Render`. `/world` is the default
prim and holds Looks/ground data; room geometry and lighting are under `/Root`,
with absolute material bindings back to `/world/Looks`. Scenario Forge's fixed
eBench composition expects one consumer scope `/World`, so directly consuming
the raw default prim would either omit the room or break the fixed object
namespace. The producer-owned gate therefore required a source-bound
ConvertAsset `visual_static_environment` package with a complete `/World`
consumer facade, full material/HDR closure, package-side facade-transform
evidence, and v0.2 zone profiles written against that facade. ConvertAsset
delivered it at `outputs/external_environment_3fo4k5c9jd44/package/`: seven
gates pass, `asset.usd` is package-local with 1,223 local dependencies, and
facade provenance records `/world → /World/world`, `/Root → /World/Root`, and
`/Render → /World/Render`.

The raw room hash remains
`03aa64f29a20517e33e47c75620cd4326f70e39963b8880750a36f6988de45bd`, while
the producer facade hash is
`48770c5be9100266336663b67a7554455218f4ee24df5d5e33dbb96f672d5503`.
Scenario Forge now verifies both: restricted intake and workspace zones bind
the raw source, while ConvertAsset package handoff binds the facade. It does
not treat these different hashes as an inconsistency.

The producer returned three profiled complete-room workcells:
`north_bench_pair_east`, `north_bench_pair_west`, and `south_table_b`.
`east_bench` remains `not_applicable`: its narrow bench and retained
neighbouring furniture cannot host the fixed eBench footprint without
destroying readable room context.

ConvertAsset zone-profile v0.3 closed the north-profile contract gap. Both
`north_bench_pair_east` and `north_bench_pair_west` now declare the standard
`usd_z_up_right_handed_ccw` convention and a reviewed yaw of `-90` degrees.
That sign puts the unchanged Lift2 base in the south-side aisle rather than
beyond the north wall. The producer also supplied source-composed evidence
camera poses and source-side Isaac 4.1 overlay images. `east_bench` remains
`not_applicable`; its measured clearance cannot host the fixed workcell without
removing unreadable amounts of retained room context.

The source-room evidence camera is retained as provenance in each generated
package, but is not assumed to be the eBench camera. It does not include the
final recovered Lift2 geometry, so a source-valid ray can still be blocked by
the real robot. The consumer uses a narrow evidence-only v10 policy instead:
GenManip first fits `workspace_closeup` from the post-reset robot, table, and
vessels; `scene_overview` reuses that exact look-at direction at 1.15 times the
distance while restoring the room. Neither the robot, worktable, task objects,
USD assets, nor task state is moved. The preview validator requires the
overview to record room-visible composition and verifies the requested
camera-reference relation before emitting the structural gate.

The current candidate is
`outputs/scientific_workbench_external_room_zone_variants_20260728_v03_runtime_camera_candidate/`.
It contains three eligible packages: `north_bench_pair_east`,
`north_bench_pair_west`, and `south_table_b`; the aggregate manifest explicitly
excludes only `east_bench`. Every package passes asset-lock `package check` and
the post-reset Isaac Sim 4.1/GenManip preview validator. Independent image-only
review is recorded in `visual_review.yaml` at the candidate root and rates all
three contextual overviews `pass`. The east north-bench view gives the richest
room context; the other two are also usable. High-key lighting and a large
foreground worktable remain non-blocking presentation caveats.

The exact producer request is versioned at
[`external-room-facade-admission-request.yaml`](../operations/external-room-facade-admission-request.yaml).

External intake records are restricted and non-redistributable. They bind the
archive/source hashes without copying signed URLs or absolute staging paths into
Scenario Forge artifacts.

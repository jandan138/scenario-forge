# Source-bound native EBench intervention suites

Status: task-specific native adapter prototype. This is not the portable
`scenario-package/v0.2` contract and does not provide episode execution.

## Boundaries and inputs

`scenario_forge.adapters.ebench.intervention_suite` owns compilation of four
native dish intervention cells and geometry-only source-task variants. ConvertAsset owns geometry, materials and
physics overlays; EEOS owns experiment execution and model analysis. The
adapter reads JSON and YAML and writes a native USD composition plus GenManip
metadata. It never imports simulator SDKs or loads external pickle data.

Build schema: `ebench-native-intervention-build/v1`.

| Field | Meaning |
|---|---|
| `source_layout` | JSON exported from a source demonstration, including `task_data`, object first/last poses and metadata/database path+SHA references |
| `source_task_config` | Native YAML containing exactly one `evaluation_configs` entry |
| `base_scene`, `base_scene_sha256` | Retained source content layer and its expected hash; sibling `.usda` is the native wrapper |
| `overlays` | Exactly `control` and `wide`, each with producer-owned path and SHA256 |
| `task_prefix` | Optional identifier matching `[A-Za-z][A-Za-z0-9_]*`, default `dish` |
| `preplaced_instruction` | Optional nonempty instruction used only in preplaced conditions |

Source layout must declare `source_kind=source_demonstration_not_model_rollout`.
The adapter verifies the declared metadata/database, base and overlay hashes.
For preplacement, the big basket's first/last position, quaternion components
and scale must agree within 1e-6 and match the initial layout. The first poses
of dish1/dish2/dish3/glass must also match that layout; only these four objects
receive their recorded final poses. Spoon, baskets and other objects retain
their initial states. This is a conservative component comparison, not a
general moving-frame transform or quaternion-equivalence solver.

## API and outputs

- `preplaced_layout(source)` returns a copied layout with the four allowed changes.
- `compile_suite(config, output)` creates a new directory; existing output is rejected.
- `install_suite(output, genmanip_root)` registers checked cells under
  `eeos_evolution/<prefix>_<geometry>_<progress>` in the supplied runtime root.

Each geometry (`control` / `wide`) is paired with both progress conditions
(`full` / `preplaced`). Native goal predicates remain identical. Optional shortened
instruction changes both `task_data.instruction` and `language_instruction` only
for preplaced cells, with source/compiled text and a changed flag in the record.
Full cells retain the original instruction. `wide` is a cell label: the matched
inertia configuration explicitly describes which producer overlay it means.

Per-cell artifacts are `scene/main.usd`, the retained wrapper as `main.usda`,
`task_config.yml`, `tasks/<task_name>/000/episode_metadata.json`, and a protocol-4
`meta_info.pkl` encoding generated exclusively from that JSON-compatible data.
The wrapper retains its source text except for the one `@./<base filename>@`
payload rewritten to `@./main.usd@`. Scene sublayers use absolute producer/base
paths: this prototype intentionally remains source-bound and nonportable.

Suite schema: `ebench-native-intervention-suite/v1`, status
`compiled_not_runtime_verified`, closure `external_source_bound_prototype`.
`suite.json` binds source/layout/config/content/wrapper/overlay hashes and each
cell's scene/metadata/pickle identity. `build_config.json` retains build inputs.
No compiled result becomes runtime-validated merely by installing it.

## Geometry-only source-task variants

Build schema `ebench-native-scene-variants-build/v1` uses the same source bindings,
artifact layout, installer and output schema. It creates only `full` cells and
preserves all source `task_data`, including instruction, goals and initial poses.
It never calls the dish preplacement logic or requires basket/dish object IDs.

- `task_prefix` is required; identifiers follow the rule above.
- `base_default_prim` is required and must be a valid single USD identifier.
  The producer/source defines its value; the downstream composed-stage check
  verifies that the named prim exists. This pure adapter does not import USD.
- `overlays` contains `control` and at least one other named intervention.
  Each label matches `[A-Za-z][A-Za-z0-9_]*`; each path/hash remains producer-owned.
- `preplaced_instruction` is rejected when non-null because this branch preserves
  task semantics. Geometry and physics qualifications remain external evidence.

The original dish schema keeps its previous four-cell behavior and default prim.
This extension is a native prototype, not a new portable package contract.

Optional `layout_variants` expands each geometry into the same set of named
initial layouts. Each entry has an `id` and object-keyed `overrides`; only finite
three-component `position` and normalized four-component `orientation` lists are
accepted. Asset paths, scale, instruction, goals and robot entries cannot be
changed through this field. Variants are supported only by the scene-variants
schema. Their identifiers are appended to cell names and retained in manifests,
alongside the actual changed initial objects and pose overrides.

New manifests bind `build_config.json` by SHA-256. Installation rechecks this
binding when present and always rechecks the source-layout hash. Legacy manifests
without a build-config hash retain their existing compatibility path.

## Validation, failure paths and external effects

Source bindings and unsupported `@`/newline USD path characters are checked
before creating an output directory. I/O failures can leave a diagnostic partial
directory; retries should use a new directory rather than overwrite old output.

Installation checks source config, content layer, source wrapper and producer
overlay hashes; reconstructs the expected native task config; checks compiled
scene/wrapper/JSON/pickle hashes; and checks all destinations before copying.
Existing task directories/configs are rejected. This is local registration in
the explicitly supplied runtime root, not remote deployment, a model run or
runtime qualification. Testing uses temporary runtime roots.

## Plan review and evidence scope

- **Architecture:** task-local source-bound contracts in the EBench adapter;
  no simulator code in core layers, no conversion logic or model runner.
- **Completeness:** controlled object set and coordinate-frame checks, unchanged
  goals, paired initial states, optional instruction consistency, source and
  output fingerprints, no-overwrite behavior and explicit pending runtime state.
- **Risk:** preserve existing task names and assets; reject changed source/compiled
  content before registration. Native reset, image observations and stability
  remain downstream validation responsibilities, not inferred from static USD.

Applicable standards: ASSET-001/002/003, STATE-001/004/006, VAL-002/003/004.
No general standard changes are needed; this document defines the local adapter
contract and its limitations.

Evidence:
[geometry × progress](../records/2026-09-11-ebench-dish-intervention-suite.md),
[inertia-matched diagnostic](../records/2026-09-11-ebench-inertia-matched-task.md),
[remaining-instruction diagnostic](../records/2026-09-11-ebench-remaining-instruction.md).

## Existing-scene initial pose synchronization

Scene-variants builds may specify `initial_scene_pose_objects`, an explicit list
of ordinary object IDs already defined in the source scene. For these objects,
the compiler writes the final `initial_layout` position, quaternion and scale
into the native content layer as world-frame xform overrides, in addition to
metadata. The object-root xform stack resets parent inheritance; child geometry
and physics attributes remain inherited. This is layout authoring, not an asset
geometry/collider repair.

The option rejects dynamically spawned asset paths, articulation parts,
malformed poses and nonpositive scale. It is not enabled implicitly on historical
builds. The caller must verify that the IDs resolve to existing source objects;
CPU composition and native reset checks remain required. A metadata-only layout
edit does not prove that the runtime starts from the intended assembly.

Each cell records the selected IDs in `initial_scene_pose_objects`. Source
artifacts remain unchanged, and corrected tasks use new output directories and
identities. See the 2026-09-12 initial-scene pose alignment record for the i01
prototype result and compiler verification scope.

## Initial-metadata-only sources

Scene-variants builds also accept `source_kind: source_initial_metadata_only`.
The source contains a hash-bound `metadata` reference and `task_data`; it does
not require a `database` reference or demonstration endpoint arrays. This is for
original initial-layout edits where a trajectory database is unavailable or
unused. The suite manifest records `source_kind` explicitly.

This source kind is rejected for intervention builds with preplaced progress:
initial metadata cannot substitute for demonstrated endpoints. Demonstration
sources retain their existing metadata plus database hash checks. The caller
must still bind exported task_data to the original metadata and verify native
reset; compilation does not certify a policy trajectory or success.

## Source stage metadata

Set `preserve_source_stage_metadata: true` to explicitly copy the source stage's
authored metadata into each generated content root layer, including
`customLayerData`, units and up axis. This opt-in adapter path uses OpenUSD lazily;
the default JSON-only packaging path does not acquire a global USD dependency.
The source defaultPrim must agree with the configured root. The suite records
`source_stage_metadata_preserved`; historical outputs are not rewritten.

In this opt-in path, legacy unit/axis defaults are omitted when absent from the
source. Preservation includes the absence of these authored opinions. The flag
does not by itself certify arbitrary stage equivalence;
callers must compare composed stage metadata and protected properties for their
source. It does not verify runtime consumption of camera/render custom data.
New EBench controlled variants should use this option and retain a source versus
generated stage audit. See USD-007 and the 2026-09-13 stage-metadata record.

# Source-bound native EBench intervention suites

Status: task-specific native adapter prototype. This is not the portable
`scenario-package/v0.2` contract and does not provide episode execution.

## Boundaries and inputs

`scenario_forge.adapters.ebench.intervention_suite` owns compilation of four
native dish intervention cells. ConvertAsset owns geometry, materials and
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

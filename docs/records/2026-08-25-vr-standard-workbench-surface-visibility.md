# VR standard-workbench surface visibility

Future VR scene generation now hides the standard workbench's composed
`Surface/Source/mesh`. The rule is implemented in the shared VR presentation
finalizer rather than repeated as an absolute-path patch in individual task
generators. It supports canonical and legacy double-wrapper composition paths.

Only USD visibility is changed. The mesh remains active and its transforms,
material and `physics:collisionEnabled` opinion are preserved. The policy is
VR-only; eBench output and the ConvertAsset source-bound package are unchanged.
Missing or ambiguous surface paths fail generation when the declared table is
`scientific_workbench_ebench_table_static_support`.

The common VR exporter records the result in `parity_manifest.json`. Custom
multi-entry generators must finalize each USD independently; the stir-bar r5
generator now does this for both frozen and editable-liquid entrypoints. Per
the rollout decision, existing output directories and ZIP files were not
rebuilt.

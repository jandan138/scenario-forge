# EBench initial-layout sources without trajectory databases

The EEOS one-shot control B plan includes retained source metadata whose LMDB
is absent (first observed at soap_to_dish instance 006). The requested scene edit
uses only initial layouts. Requiring a demonstration database for this build
would either block a valid source use or encourage an incorrect trajectory claim.

Added explicit `source_initial_metadata_only` support to scene-variants builds.
Metadata hashes remain required. The same kind is rejected for preplaced
intervention builds. Historical demonstration-source behavior is unchanged;
the suite manifest now records its source kind. No source assets were modified.

The targeted adapter suite passes 13 tests, including metadata-only compilation,
rejection for preplacement, and rejection of a changed metadata hash. Full
`make check` output is retained at `/tmp/sf-metadata-only-check.log`; its final
status must be checked before claiming the full repository check passed.

EEOS B recompile outputs are at
`/cpfs/user/zhuzihou/dev/embodied-eval-os/outputs/ebench_evolution/comparison_compilation_20260912_v2/control_b_r2/`.
Earlier partial `control_b/` outputs are retained. The 240 frozen slots were not
changed or replaced. Compilation and static composition do not certify rendered
appearance, physical settling, native evaluation or portability.

Standards: USD-007 and VAL-001/002/003. The design reference and USD source-scope
guidance were synchronized; other asset, material and runtime rules are unchanged.

Final validation: `make check` exited 0; 1015 tests passed, 1 skipped, Ruff and
package/Phase 10.x smoke checks passed. The log and receipt are retained under
EEOS `outputs/ebench_evolution/comparison_compilation_20260912_v2/validation/`.
This does not qualify the generated tasks' native policy runtime.

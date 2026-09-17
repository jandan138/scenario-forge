# EBench controlled variants: source stage metadata

The shop source scene has customLayerData with cameraSettings/renderSettings.
Its generated content wrappers omitted this field even though metadata poses
and composed edited-object origins matched. The EEOS audit retained that failure;
no affected shop episode had been run.

Added the explicit preserve_source_stage_metadata option to compile_suite. It
copies source-authored stage metadata after writing each content root layer,
validates the source default prim, and records adoption in the suite manifest.
OpenUSD is imported only for this optional adapter operation. The legacy path
and historical artifacts remain available; callers must still audit source-absent
fields against legacy wrapper defaults and verify actual runtime behavior.

The regression test failed with 1.0 instead of source metersPerUnit 0.01, then
passed for source units, Y up-axis and nested render custom data in all four cells.
All14 intervention-suite tests passed. Full make check completed successfully:
1022 tests passed, 1 skipped; lint, package smoke and Phase10x smoke passed.
The log and compiler snapshot are retained under EEOS outputs/ebench_evolution/
comparison_compilation_20260913_stage_v3/validation. Shop r3 passed its35-cell
full composed-content check after restoring registered transform fields and
normalizing flatten-generated documentation. This is source-specific USD
validation, not native renderer/physics qualification.

Standards: USD-007 and VAL-002; design contract and standard updated together.
No changes to model policies, original USD sources, runtime dependencies or
already running apple experiments.

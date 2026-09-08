# Titration VR r1.6: one receiver liquid mesh and material

## Change

r1.6 consumes the retained r1.5 handoff. The receiver's four geometrically
identical phase meshes and their materials are replaced by:

- `/World/obj_receiver_flask/VisualLiquid/Solution` (Mesh)
- `/World/obj_receiver_flask/VisualLiquid/Looks/Water` (Material)
- `/World/obj_receiver_flask/VisualLiquid/Looks/Water/Shader` (Shader)

The mesh retains the source geometry, normals, material parameters and initial
visibility. Its old static `titration:phase` property is removed. The StirBar
subtree and all hardware/physical prims are unchanged. ConvertAsset dependency
files are retained byte-for-byte.

Only `_sync_receiver()` changes in the embedded controller: it resolves the
unique shader through `titration:receiverLiquidShader`, writes the calculated
RGB to `inputs:glass_color`, and updates the station's `titration:indicator_phase`.
It neither switches visibility nor creates or replaces geometry or materials.
The mathematical flow/color policy, reset function, completion latch and all
other controller functions are unchanged from r1.5.

The two receiver relationships remain the integration interface, each now
with exactly one target. The four old phase-mesh and material paths are removed;
consumers that hardcoded them must use the relationships or the new paths.
The station retains its four logical indicator phases. The recipe declares
`visual_mode: single_material`, `visual_paths` and `shader_paths`; `phase_paths`
is removed. The policy version remains `linear_deadzone_v1`.

## Behavior and teaching guide

Flow remains zero at ≤5°, then increases linearly to 30/11 mL/s at 90°.
At 90° transition starts at 5 s and pale pink starts at 5.5 s. At 45° the full
pale window remains 1.5 s. Closing within the pale volume interval for 3 s
latches success until reset. Later operation can still deepen the color.

`COLOR_GUIDE_CN.md` now explains a single shader, includes live/offline reader
examples, and retains the numerical interpolation tutorial. Its source is
`docs/operations/titration-r16-color-guide.md`. The generator copies it into
the handoff; r1.5 and its guide are retained separately.

## Verification and delivery

Regression tests first fail on missing r1.6 behavior, then verify unique geometry
and material, MDL binding, absence of dangling targets, identical physical
content, and actual execution of the embedded receiver function through all
color boundaries and reset. An AST comparison requires every other embedded
controller function to remain identical to r1.5.

The shared runtime and rendering tools resolve receiver relationships for both
four-material and single-material packages. r1.6 cold starts additionally
check the same single visible mesh and bound shader on every prescribed-joint
step, including reset and post-success overshoot. Finalization rejects old
multi-material evidence even if it reports success.

Fresh Isaac Sim 4.5 runtime reports and static four-state render snapshots must
match the final scene SHA. Visual review compares the matching r1.5 cameras;
these snapshots are not runtime or robot recordings. Physical audit, `make check`,
ZIP dependency closure, CRC and SHA remain required.

Output root:
`outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_6_20260907/`.

Generate with `python -m scripts.generate_traditional_titration_vr_r16`;
validate with `python -m scripts.validate_traditional_titration_vr_r1`;
render with `python -m scripts.render_titration_liquid_comparison --linear-states`;
finalize with `python -m scripts.finalize_traditional_titration_vr_r16`.
The latter three commands take the existing `--root` and report/output arguments.

## Final result

Three fresh Isaac Sim 4.5 cold starts passed, including single mesh/material
persistence throughout all steps, on scene SHA
`18c805b11bff9633c065955300a677b32cab8d7810fef605f335ead2a8b30012`.
The 52 physical prims match r1.5. Dependency files are byte-identical.

`make check` passed: 940 tests passed, one skipped; all 15 final focused tests
also passed. Twelve 1920×1080 matching-camera snapshots have mean absolute
RGB differences below 0.574 on a 0–255 scale relative to r1.5. Local visual
review accepts the consolidation, with the existing dark-reflection caveat;
it is not an independent review and the frames are static snapshots.

The revised guide reader was checked against the actual single-material Stage.
ZIP closure has no missing or external dependencies; CRC and SHA passed.
The current VR delivery head advances to r1.6; r1.5 is retained as source.

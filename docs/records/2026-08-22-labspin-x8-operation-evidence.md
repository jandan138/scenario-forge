# 2026-08-22 LABSPIN X8 Operation Evidence

## Context

Scenario Forge received an exported centrifuge bundle and consumed new
ConvertAsset source-bound packages rather than adding simulator-specific
physics repairs locally.

## Change

`build_labspin_x8_robot_validation_bundle.py` produces non-canonical GenManip
validation bundles for the native tube and existing 15 mL compatibility tube.
The centrifuge and tube placements are authored on `obj_` root prims.  The
bundles reuse the frozen Lift2/table/background runtime and contain no episode
runner or benchmark-reporting implementation.

The delivery at
`outputs/scientific_workbench_labspin_x8_operation_evidence_20260822/` contains
three passing Isaac 4.1 MP4s and machine-readable evidence.  Native and existing
15 mL insertion videos show scripted lid open, physical free-drop seating and
lid close.  A third clip shows a visible low-speed balanced-pair rotor run.

## Validation and claim boundary

- Bundle unit test: pass.
- Native-tube insert: pass, `1.984 mm` bottom error.
- Existing 15 mL insert: pass, `3.249 mm` bottom error.
- Low-speed pair: pass; both tubes retained.
- Lift2 contact lane: blocked.  The left arm measured a partial `18.69°` lid
  opening, but the initialized right-gripper tube grasp did not retain the tube.
  The failed MP4 is not part of the delivery videos; JSON diagnostics are kept.

No robot-policy, full Lift2 open/insert, Task 10, benchmark or rated-speed claim
is made.


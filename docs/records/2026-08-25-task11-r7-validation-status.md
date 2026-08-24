# 2026-08-25 Task11 r7 validation status

## Candidate

Task11 r7 is generated at
`outputs/scientific_workbench_task11_vr_r7_20260825`. It consumes the
ConvertAsset split-grasp tube and keeps the centrifuge, rack, liquid sets,
table, and background package-owned. The selected workcell layout is:

- centrifuge: `(0.0, -0.1, 0.755)` m;
- mixed rack: `(-0.4, -0.3, 0.755)` m;
- target slot: `slot_15ml_r00_c02`.

The exact scene is wrapped for unchanged GenManip consumption under
`adapters/ebench/genmanip`. The adapter supplies the root `/physicsScene` ABI
and preserves the Lift2/table episode entries; it does not reauthor asset
physics.

## Results

- r6/r7 device mechanics independently pass contact-driven OPEN, automatic lid
  opening, STOP, power-off, and rack insertion gates.
- the r7 producer tube passes a fixed physical close/lift/hold gate.
- EOS/GenManip can plan every phase when the Lift2 column is staged at 0.281 m
  for buttons and 0.46 m for tube manipulation.
- robot OPEN contact has reached the 2.5 mm button limit and opened the lid to
  approximately -1.361 rad in retained diagnostic attempts.
- a complete same-episode robot sequence has not passed: OPEN contact remains
  contact-sensitive, and current tube contact can push the cap laterally rather
  than retain it through axial extraction.

## Claim boundary

The r7 manifest remains a candidate with `task11_success=false`,
`robot_policy_success=false`, and `benchmark_success=false`. The success-only
packager intentionally refuses to promote it until one continuous canonical
Lift2 episode passes all predicates.

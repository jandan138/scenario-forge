# Task 11 r8 particle-free rich tabletop candidate

## Investigation

Task 11 r7 retained two GPU-PBD sets of 2,640 particles, omitted the five
standard Task 02 tabletop context objects, and consumed the split-grasp r7
target tube. The newest EOS `full_report.json` was an OPEN-stage error and its
MP4 was only 262 bytes; an earlier diagnostic had reached the 2.50 mm OPEN limit
and `-1.361 rad`, but those are not the same run and cannot establish a complete
episode.

The centrifuge collider review found one real device defect and one false
positive. The old lid `main_shell` extended approximately 68 mm behind the
visible lid, while the base left/right thickness asymmetry matched the visual
housing exactly. ConvertAsset r6 therefore refits only the lid and requalifies
the device mechanics.

During r8 static validation, the split-grasp target tube moved approximately
86.8 mm out of the rotor. The older admitted `target_tube_r2` moved only
approximately 8.1 mm and settled to about 1.0 mm motion in the final second in
the same particle-free scene. Because this delivery targets a scene-qualified,
robot-unvalidated package, r8 uses the stable insertion-qualified tube. The
split-grasp tube remains available for later robot-specific work.

## Implementation

`scripts/generate_scientific_workbench_task11_vr_r8.py` consumes the promoted
ConvertAsset r6 centrifuge and stable target tube, restores the Task 02 context
amber bottle, tip box, wash bottle, clear bottle, and pipette carousel, and
keeps every tabletop object under an `obj_*` root with local XY randomization
of `+/- 0.01 m`.

The two PBD sets and `/World/fluid_runtime` are removed. The target and balance
tubes each own a blue `VisualLiquid` child with no collision, rigid body, mass,
particle API, or metric role. It rigidly follows the tube and is not a simulated
liquid. GPU dynamics remains enabled because Isaac Sim 4.1 requires it for the
tubes' dynamic SDF rigid collision; the scene contains zero particle systems
and no particle contact budget.

The exact scene is copied into the GenManip adapter. Its wrapper references the
copy through package-relative USD paths, so both the VR entry and wrapped entry
remain valid after ZIP extraction away from the repository.

Output:

`outputs/scientific_workbench_task11_vr_r8_20260826/`

Candidate ZIP:

`handoff/scientific_workbench_task11_vr_r8_candidate.zip`

## Validation

- three independent Isaac Sim 4.1 eight-second cold runs: pass;
- particle-like prim count: zero;
- visual-liquid forbidden physics prim count: zero;
- centrifuge/table/rack and five context props: stable;
- primary tube displacement: `8.080 mm`; final-second motion: `1.014 mm`;
- OPEN physical contact: `2.50 mm`, lid opens/holds at `-1.3610 rad`;
- rotor OPEN interlock and STOP power-off: pass;
- before/after room, tabletop, device, open-rotor, and isolated-liquid renders:
  local visual QA pass;
- extracted ZIP VR stage: 36 layers, 17 assets, zero unresolved dependencies;
- extracted ZIP adapter stage: 37 layers, 17 assets, zero unresolved dependencies;
- GenManip package-local composition/config smoke: pass.

The local visual review confirms that the five context props occupy the table
wings without blocking the centrifuge or rack. A review-only session pose shows
the blue insert filling the transparent tube to approximately the 12 mL mark;
the delivered initial pose remains inside the closed centrifuge. The review was
local, not independent blind review.

## Claim boundary

The manifest status is `scene_qualified_robot_unvalidated`. Robot-free device
mechanics and scene stability are true. Full mechanical tube transfer,
canonical Task 11, Lift2 policy, benchmark, and task success remain false. The
candidate ZIP name and README preserve this boundary; no success ZIP is
generated.

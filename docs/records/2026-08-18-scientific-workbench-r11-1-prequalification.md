# Scientific Workbench Task 05 / Task 09 r11.1 prequalification

## Outcome

r11 remains the immutable dual-consumer handoff.  Scenario Forge compiled
independent r11.1 validation children for Tasks 05 and 09, retained their
eBench and VR exports, and added an external-oracle evidence contract with two
possible terminal states:

- `pass` requires exactly three fresh-process, cold-start, robot-contact-only
  EOS runs with every task stage and the native weighted score at `1.0`;
- `blocked` retains measured prequalification evidence and explicitly keeps
  task, policy, benchmark, and thermal claims false.

The current r11.1 candidates are blocked before the three-run promotion loop.
They are diagnostic packages, not replacements for r11.

## Adapter correction

The GenManip export now preserves every authoritative articulated-device named
frame, including frames parented to moving links.  It also emits no-pose-write
sentinel entries for articulation parts in `initial_layout`.  This prevents
GenManip's generic recovery path from treating moving links as absent objects
and deactivating them.  Simulator SDK imports remain outside pure package
layers, and GenManip itself was not modified.

## Task 05 measurement

The required right auxiliary-arm flask hold has no CuRobo IK solution in the
locked layout.  A bounded 108-candidate search crossed three X shifts, three Y
shifts, three grasp heights, and all four cardinal approach azimuths inside the
r11.1 5 cm layout limit; it produced zero right-arm solutions.  Swapping roles
is not a valid escape: the right arm also produced zero solutions for all 20
bounded stopper candidates.  The first physical attempt consequently stopped
at `hold_flask/right_pregrasp` before any object motion.

This is a layout and hand-assignment blocker, not a ConvertAsset defect.  A
future child must either raise the flask grasp point, change the robot/table
relationship, or authorize a different hand assignment; none is silently
applied to r11.1.

## Task 09 measurement

Scene loading and articulation retention pass.  The door, sample, dial, and
rocker probe poses are individually reachable.  Two independent blockers remain:

1. The current source-bound `door_grasp` frame is on the main-door convex-hull
   face rather than on a physically enclosing handle.  During the contact
   trial, the right fingers were commanded from 44 mm to zero but stopped at
   43.349/43.322 mm; the first pull left the door at
   `2.73e-14 rad`.  The robot moved, but no opening force was transferred.
2. The fixed left operating arm cannot reach the declared shelf target or any
   of 45 bounded front-shelf candidates.  The right arm reaches all 45, but
   using it would change the locked task hand assignment and require a handoff.

The oven r11 asset admission remains valid inside its original state-cycle and
support-geometry claim.  It did not claim robot-contact opening.  The next
asset-side action is a new ConvertAsset interaction revision that identifies a
door-coupled grasp feature and proves contact opening; consumers must not add a
local oven collider patch.

## Evidence

The release root is
`outputs/scientific_workbench_task05_task09_r11_1_20260818/`.  Each package
contains `evidence/task_interaction_ready.yaml` and a hash-bound copy of the EOS
diagnostic observations under `evidence/scripted_robot_oracle_blocked/`.

## Verification

- `make check CHECK_PYTHON=.../embodied-eval-os-py310/bin/python`: 706 tests
  passed, Ruff passed, package/workflow/suite smoke checks passed.
- Focused r11.1 adapter, generator, and evidence tests: 67 passed.
- `validate_package` passed for both retained r11.1 package roots after evidence
  binding.

## Claim boundary

This work proves package closure, articulated contract transport, runtime scene
initialization, bounded reachability results, and the recorded door-contact
failure.  It does not prove either task, a robot policy, an eBench benchmark
result, heating behavior, or real-world physical calibration.

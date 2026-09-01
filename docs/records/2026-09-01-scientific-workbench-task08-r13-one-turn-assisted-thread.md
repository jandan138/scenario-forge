# Scientific Workbench Task 08 r13 One-turn Assisted Thread

## Outcome

Task 08 now has a VR-oriented one-turn cap-closing interaction.  The operator
still picks, aligns, mates, and rotates the target red cap.  Once the target cap
enters the capture band, a USD-contained OmniGraph maps clockwise rotation to
7.6 mm axial descent.  At approximately 350 degrees the state becomes
`closed`; an embedded pose-follow lock preserves the cap/tube relative pose
after release and while the tube moves.

The visible fine thread is retained but does not participate in contact
solving.  ConvertAsset supplies hidden smooth collision wrappers; Scenario
Forge owns only the task contract, controller graph, evidence, and packaging.

## Package contract

- Target tube: `/World/obj_tube_01`
- Target cap: `/World/obj_cap_01`
- State machine: `free -> capture -> engaged -> closed`
- Direction: clockwise when viewed from above
- Effective lead and travel: 7.6 mm per turn / 7.6 mm
- Close threshold: approximately 350 degrees
- Capture: 6 mm radial error and 20 degree tilt
- Abort: 12 mm radial error or 35 degree tilt
- Retention: USD-embedded pose-follow lock

The controller is stored inline in the USD.  The generator does not import a
simulator SDK; `author_scientific_workbench_task08_r13_omnigraph.py` registers
the graph through the Isaac 4.1 adapter boundary.

## Evidence

Three independent Isaac Sim 4.1 cold starts passed the same protocol:

1. place the dynamic cap at the aligned capture pose;
2. command one clockwise turn;
3. release and hold for 1,200 physics updates; and
4. lift the kinematic tube by 5 cm.

All three runs reached about 350.076 degrees, closed at relative Z 0.1074 m,
held that value, and retained it after the lift.  No hard CUDA/PhysX errors were
recorded.  A 220-frame RayTracedLighting video shows the rotation, descent,
closed hold, and tube lift.

## Verification

- `python -m pytest -q tests/test_generate_scientific_workbench_task08_vr_r13.py tests/test_finalize_scientific_workbench_task08_vr_r13.py tests/test_generate_scientific_workbench_task08_vr_r12.py`
  — 6 passed.
- Three executions of
  `qualify_scientific_workbench_task08_vr_r13.py` — pass.
- Local human-style render QA — pass; not an independent reviewer.

## Claim boundary

`thread_interaction_ready` means the recorded assisted one-turn protocol is
ready for VR action collection.  It does not mean physical fine-thread contact,
robot policy success, full human episode success, benchmark success, or
calibrated screw torque.  Those claims remain false.

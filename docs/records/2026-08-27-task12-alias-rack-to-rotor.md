# Task 12 alias: rack-to-rotor centrifuge transfer

This temporary alias is intentionally isolated from the canonical task catalog,
where Task 12 remains oven unload/shutdown. Its scenario ID is
`scientific_workbench_task12_alias_centrifuge_rack_to_rotor` and its output is
`outputs/scientific_workbench_task12_alias_centrifuge_rack_to_rotor_vr_r1_20260827/`.

The scene reuses the Task 11 r9 centrifuge and single-rigid threaded red-cap
15 mL tubes. The blue visual-liquid target starts in rack slot
`slot_15ml_r00_c02`; rotor socket 18 is empty and socket 6 contains one empty
balance tube. Six empty 15 mL context tubes remain in rack row 1. Both 50 mL
tubes and their package dependency are removed.

The ordered alias task is OPEN contact, target-tube pick from the rack,
insertion and release into rotor socket 18, then STOP contact. The lid starts
locked and OPEN reaches `open_hold`; manual push-down close/latch remains
outside scope and is recorded false.

The GenManip adapter replaces inherited Task 02 text and empty goals with a
non-empty native position goal and a schema-valid v0.6 transport contract. Its
seven progress items total 1.0 and retain robot/task/benchmark success as false.

Three Isaac Sim 4.1 initial-scene cold starts qualify the no-50 mL layout. A
separate robot-free oracle uses physical OPEN/STOP contact and a kinematic
carrier FixedJoint for the tube transfer; it does not claim a Lift2 policy.
Rendering covers rack start, open empty target socket, isolated visual liquid,
and inserted rotor states.

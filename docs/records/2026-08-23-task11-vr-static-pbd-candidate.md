# 2026-08-23 Task 11 VR static PBD candidate

Scenario Forge now builds a VR-only static candidate for
`scientific_workbench_centrifuge_unload_shutdown`. The scene uses the Code
wet-lab room, LABSPIN X8, an 18+4 mixed rack, six 15 mL and two 50 mL context
tubes, plus a primary and opposite balance tube in rotor sockets 18 and 6.

Both rotor tubes contain separate 2640-particle sets sharing one particle
system. Three isolated Isaac Sim 4.1 runs advanced eight seconds each; both
sets retained 100%, below-floor counts were zero and no hard errors were
reported. The VR scene has `/World` as defaultPrim, twelve inline `obj_*`
subtrees, direct-open light and no embedded robot or robot contact overrides.

This is `static_candidate_only`. Button press, lid-open causality, observable
power-off state, robot transfer, complete Task 11 and benchmark success remain
unclaimed. Delivery ZIP:
`outputs/scientific_workbench_task11_vr_static_candidate_20260823/handoff/scientific_workbench_task11_vr_static_candidate.zip`.

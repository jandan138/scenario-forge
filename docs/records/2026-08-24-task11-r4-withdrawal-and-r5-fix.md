# 2026-08-24 Task 11 r4 withdrawal and r5 fix

Task 11 VR r4 is withdrawn from use. Its six 15 mL and two 50 mL rack-context
tubes were composed from independent dynamic body/cap roots. The 15 mL cap
collider was misaligned at the tube bottom, and the unqualified rack had no
socket-bottom support. Isaac 4.1 reproduced immediate centimetre-scale motion;
one cap moved about 0.92 m by frame 60. The r4 liquid-only gate did not observe
these roots and therefore supported an over-broad `static_stability` claim.

r5 consumes only pass producer manifests. Background tubes are single
visual-static closed objects; the task tube remains dynamic. The mixed rack r2
owns target-slot support and has three producer insertion runs. Scenario Forge
now runs the exact scene without kinematic overrides and tracks the device,
rack, eight background tubes, two dynamic tubes, and both particle sets.

All three r5 eight-second Isaac 4.1 runs passed. Background displacement was
zero, primary/balance tube settling was about 2.1/1.2 mm, both 2640-particle
sets retained 100%, below-floor counts were zero, and no hard errors were
recorded.

The replacement ZIP is
`outputs/scientific_workbench_task11_vr_r5_20260824/handoff/scientific_workbench_task11_vr_r5.zip`.
Robot policy and complete Task 11 success remain false.

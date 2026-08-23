# 2026-08-24 Task 11 r3 embedded-lid consumption

The VR-only Task 11 candidate now consumes the LABSPIN X8 r3 package. Object
materialization preserves the embedded behavior graph under
`/World/obj_centrifuge/__device_behavior`; its inline script resolves the
articulation from the graph parent, so no source-root absolute path survives.

The producer evidence covers button-drive-triggered opening to -1.35987 rad and
hold after release. Contact press, manual close/latch and rotor interlock remain
false. After the r3 replacement, both 2640-particle sets retained 100% with zero
below-floor particles and zero hard errors in three isolated Isaac 4.1
eight-second runs. The ignored delivery ZIP is
`outputs/scientific_workbench_task11_vr_static_candidate_20260823/handoff/scientific_workbench_task11_vr_static_candidate_r3.zip`.

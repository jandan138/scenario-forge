# 2026-08-24 Task 11 r4 VR handoff

Scenario Forge now consumes the ConvertAsset LABSPIN X8 r4 package for the
VR-only `scientific_workbench_centrifuge_unload_shutdown` candidate.

## Package shape

The generated package is
`outputs/scientific_workbench_task11_vr_r4_20260824/`. Its runtime entry is
`vr/scene.usd` and its VR configuration is `vr/task_config.py`. Twelve direct
`obj_*` roots are materialized into the scene while the room/table dependency
bundle remains package-local. The centrifuge behavior graph survives under
`/World/obj_centrifuge/__device_behavior` and resolves the articulation from
its graph parent.

The layout retains the mixed 18+4 rack, six background 15 mL tubes, two
background 50 mL tubes, a primary closed 15 mL tube in socket 18, and a
balancing closed 15 mL tube in opposite socket 6. Each task tube contains an
independent 2640-particle set on the shared particle system.

## Evidence

ConvertAsset r4 producer evidence qualifies rigid-contact OPEN and STOP,
automatic opening to about 78 degrees with hold, rotor-open interlock, and the
observable power-off transition in Isaac Sim 4.1.

Scenario Forge ran three isolated eight-second Isaac Sim 4.1 observations.
Both particle sets retained 100% in all runs, all below-floor counts were zero,
and all hard-error lists were empty. The combined report is
`vr/evidence/static_validation/report.json`.

## Handoff

The delivery ZIP is
`outputs/scientific_workbench_task11_vr_r4_20260824/handoff/scientific_workbench_task11_vr_r4.zip`.
It includes a Chinese README and a SHA-256 sidecar beside the archive.

## Claim boundary

The package qualifies the device controls and static PBD start state. It does
not qualify robot pick/place, manual contact close/latch, or complete Task 11
success. Scenario Forge still does not contain an episode runner or benchmark
reporting logic.

## Verification

```text
python -m pytest -q tests/test_generate_scientific_workbench_task11_vr_static.py \
  tests/test_package_scientific_workbench_task11_vr_r4.py
# 2 passed

make check
# full result recorded in the associated commit
```

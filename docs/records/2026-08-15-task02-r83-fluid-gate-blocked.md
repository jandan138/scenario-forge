# Task 02 r8.3 Fluid Gate Blocked

Date: 2026-08-15

## Product status

Task 02 r8.3 was not generated. ConvertAsset's corrected live-particle static
gate failed before Scenario Forge packaging, so producing an eBench or VR USD
would overstate the available physics claim.

The correction distinguishes Isaac Sim 4.1's authored
`physxParticle:simulationPoints` from the live `points` readback. Scenario
Forge's GPU-PBD handoff loader now requires every cold run to contain
`particle_readback_attribute: points`; older reports are rejected even when
their hashes and previous status say pass.

Corrected producer evidence:

- graduated cylinder: 43--45 / 548 retained across three cold runs;
- 325 mL beaker: 167--170 / 548 retained across three cold runs;
- bounded prescribed trajectory: blocked before any transferable pair could
  be promoted.

Evidence roots:

- `/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/graduated_cylinder_250ml_gpu_pbd_remesh_20260814_v3/static_admission_live_points_r3/`
- `/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/beaker_325ml_gpu_pbd_20260815/static_admission_live_points_r3/`
- `/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/task02_cylinder_to_beaker_gpu_pbd_transfer_20260815/`

## Boundary

Scenario Forge owns only the fail-closed package contract. It does not patch
colliders, tune PBD parameters, import Isaac Sim, or run episodes. Work may
resume only after ConvertAsset supplies new source-derived geometry that passes
three live-`points` static cold runs and the 50% prescribed-transfer gate.

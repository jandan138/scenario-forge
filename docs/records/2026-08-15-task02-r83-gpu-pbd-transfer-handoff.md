# Task 02 r8.3 GPU-PBD transfer handoff

Date: 2026-08-15

## Outcome

Scenario Forge now consumes the qualified ConvertAsset cylinder-to-beaker
transfer pair and emits a self-contained Task 02 r8.3 candidate for eBench and
VR. The eBench product was opened through GenManip, reset/recovered, and stepped
for 960 zero-action physics steps at 120 Hz (8 seconds) in Isaac Sim 4.1.

The generated product is:

```text
outputs/scientific_workbench_task02_r83_20260815/
```

Primary handoff files are `ebench/scene.usd`, `ebench/config.yaml`,
`vr/scene.usd`, and `vr/config.py`. The collected eBench scene keeps all USD
references inside its `source_bundle/`; provenance may retain producer source
paths, but the runtime dependency closure is package-relative.

## Producer evidence consumed

The new `load_gpu_pbd_transfer_pair_handoff` adapter accepts:

```text
/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/
  task02_cylinder_to_beaker_gpu_pbd_transfer_20260815_r6/
  final_package/task02_cylinder_to_beaker_gpu_pbd_transfer_pair_r1/
```

The package identifies candidate `c03`: zero lateral rim offset, 10 mm rim gap,
-115 degree tilt, and 3 second dwell. Its three independent cold runs delivered
518, 519, and 526 of 548 particles to the beaker (94.5%, 94.7%, and 96.0%), with
zero recorded spill, zero below-support particles, 85--87 FPS, and no hard
runtime errors. These results cover the producer's prescribed kinematic
trajectory, not a robot trajectory.

The adapter verifies the embedded and external manifest identities, component,
profile, report, initial-state and dependency-tree hashes, live `points`
readback, exact particle count, selected candidate, three cold runs, at least
50% target reception, at least 40 FPS, and absence of hard errors.

## Product integration

The r8.3 scene keeps the r7 robot, 2.0 x 0.8 x 0.755 m support table, room and
context dressing. It deactivates the former empty beaker and graduated cylinder,
then references the producer-owned transfer component at
`/World/_scene/fluid_runtime`. Scenario Forge owns only scene placement and the
runtime composition override needed to leave the source and target non-kinematic
for future robot work; it does not author vessel-specific collider or liquid
parameters.

The liquid-transfer metric remains declared but inactive. The product score
ceiling therefore remains 60%.

## Runtime and visual evidence

Product smoke evidence:

```text
outputs/scientific_workbench_task02_r83_20260815/
  evidence/product_smoke/report.json
```

The report records USD open, GenManip scene construction, reset/recovery and the
8 second zero-action run as passing. It records zero hard CUDA, GPU cooking, or
particle errors. Eight pre-existing GenManip robot-link contact/rest-offset
warnings remain non-blocking and were not suppressed or patched in Scenario
Forge.

The seven 1920 x 1080 views and their structural gate are under:

```text
outputs/scientific_workbench_task02_r83_20260815/
  ebench/evidence/initial_scene/
```

`visual_ready_gate.yaml` passed. Local human review found the workcell and task
objects correctly scaled and supported; the room-corner views intentionally make
the task small, while `workspace_closeup.png` and `task_object_closeup.png`
provide the inspection views. The task-directory page was audited in Chromium at
1440 x 1000, 900 x 1100 and 390 x 844: no request, console, broken-image, or
horizontal-overflow failure was observed, and the r7/r8 switch worked.

## Claim boundary

This release proves the producer's static container gates, prescribed cylinder-
to-beaker transfer feasibility, package-relative USD composition, initial visual
readiness, and eBench load/reset/8-second zero-action runtime. It does not prove
robot grasping, visible robot pouring, policy success, liquid metric correctness,
40+ FPS for the full eBench product, or benchmark success.

# Experimental PBD beaker pour

This temporary task remains outside the formal wet-experiment catalog and its
statistics. It exercises a producer-owned 3,600-particle PBD beaker scene with
the standard eBench Lift2 robot. Two independent packages are generated so a
consumer never has to switch table variants inside one USD:

- `source_workbench` (recommended): preserve the complete, wide source table;
- `ebench_workbench`: replace it upstream with the qualified eBench static-
  support table while keeping the task and robot-relative layout unchanged.

Generate each package from its matching qualified LabUtopia handoff:

```bash
PYTHONPATH=src python scripts/generate_experimental_pbd_beaker_pour.py \
  --variant source_workbench \
  --handoff-package /path/to/lab001_pbd_beaker_to_beaker_source_workbench_v3/package \
  --out outputs/experimental_pbd_beaker_to_beaker_pour_source_workbench_20260807_r1

PYTHONPATH=src python scripts/generate_experimental_pbd_beaker_pour.py \
  --variant ebench_workbench \
  --handoff-package /path/to/lab001_pbd_beaker_to_beaker_ebench_workbench_v3/package \
  --out outputs/experimental_pbd_beaker_to_beaker_pour_ebench_workbench_20260807_r1
```

The generator requires handoff schema
`labutopia.interactive_scene_handoff/v0.3`, qualified `native`, `genmanip`, and
`vr` endpoints, and a matching variant/package id. It writes:

- `scene/main.usda`: neutral/native composition;
- `adapters/ebench/genmanip/`: GenManip collected package at 600 Hz;
- `adapters/vr/scene.usd` and `task_config.py`: VR handoff at 60 Hz;
- `evidence/robot_table_clearance.yaml`: circular Lift2-base versus producer-
  certified table-AABB clearance;
- `evidence/tabletop_placement_policy.yaml`: 10 cm table-edge and robot-facing-
  half checks for both beakers.

Both beakers and all 3,600 authored PBD points move by the same producer-owned
translation. Scenario Forge consumes that layout; it does not author particle,
collider, mass, inertia, or PhysX fixes. The eBench-table variant additionally
requires the hash-bound ConvertAsset static-support package recorded by the
producer manifest.

Lift2 uses its neutral open-arm reset state for initial-scene evidence. No old
pregrasp joint vector is reused after moving the robot and vessels. The base is
outside the table with at least 5 cm clearance; vessel AABBs remain at least 10
cm from every table edge and in the robot-facing half. These are initial-layout
gates, not arm-reachability or motion-planning claims.

The primary success contract remains the staged geometric pour pose followed
by return to the initial source pose. Release is instruction-only and liquid
transfer is inactive until their scorers are separately qualified. The package
does not claim stable grasp, policy success, liquid-transfer success, or
benchmark success.

For initial-scene evidence, the renderer uses eight zero-action physics steps,
then renders without further physics advancement. A clean GenManip code copy
may point its ignored `saved/assets` path at the shared eBench asset store; use
a process-local `mesh_data` directory when the shared cache is full. CuRobo is
provided through the managed runtime's documented external source path. This
setup does not modify GenManip or its shared environment.

The old
`outputs/experimental_lab001_pbd_beaker_to_beaker_pour_20260806_r4` package is
rejected: its Lift2 base spawn `[0, 0, 0]` lies inside the source table XY AABB.
Its images and manifests remain historical diagnostic evidence only.

All variants are internal and non-redistributable. Do not extract their source
assets for public delivery.

# Task 02 r8 fluid prototype

Date: 2026-08-13

## Product result

Scenario Forge composes the ConvertAsset-owned r8 liquid component with the r7
modern wet-chemistry room, the 2000 × 800 × 755 mm workbench, and the existing
eBench/VR robot contracts.  The handoff is self-contained and preserves the
GenManip object names `obj_graduated_cylinder` and `obj_beaker`; GenManip itself
is unchanged.

Package:
`outputs/scientific_workbench_task02_r8_20260813`

Entrypoints:

- eBench: `ebench/scene.usd` with `ebench/config.yaml`
- eBench collected layout: `ebench/tasks/config.yaml`
- VR: `vr/scene.usd` with `vr/config.py`

## Runtime status

The package is a **blocked diagnostic prototype**.  Static USD composition opens
in Isaac Sim 4.1 and contains the room, table composition, two task objects, and
548 authored particles.  The real GenManip product smoke reaches
`scene_constructed` and then fails during PhysX initialization with a CUDA
illegal-memory-access error.  This is consistent with ConvertAsset's component
qualification blocker: the graduated cylinder visual-mesh
`convexDecomposition` is not GPU-compatible for PBD particle contact.

Liquid metrics remain inactive and the task score ceiling remains 60%.  The
package does not claim eight-second liquid retention, visible transfer, 40+ FPS,
robot policy success, or benchmark success.

## Visual evidence

`evidence/static_composition/scene_overview_0000.png` is a no-physics
composition preview.  It shows the room, table, robot, graduated cylinder, and
beaker together, but intentionally disables the failing particle runtime.  It
must not be used as liquid-simulation evidence.

The source USD/config handoff remains package-relative.  The preview-only layer
may contain local evidence references and is not an execution entrypoint.

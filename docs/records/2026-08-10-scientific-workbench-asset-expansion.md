# Scientific Workbench Asset Expansion

Date: 2026-08-10

## Outcome

Scenario Forge consumed a source-bound ConvertAsset library and compiled nine
portable packages under
`outputs/scientific_workbench_asset_expansion_20260810_r4/packages/`:

- five independent Task 7 glass-rod-stir packages using the example4, teaching
  research, modern wet chemistry, bioclean, and analytical-instrumentation
  Code-as-Room backgrounds;
- one Task 8 centrifuge-tube-cap canonical candidate;
- Task 4, Task 14, and Task 15 layout prototypes.

Every package has the same eBench Lift2 robot, static-support workbench, task
objects, world poses, and physics contract in its eBench and VR exports. Each is
self-contained and keeps USD/material/texture dependencies package-relative.

## Asset boundary

The new glass rod, 50 mL tube body and cap, k=1.25 tube rack, stir bar,
analytical balance, Petri dish, micro-spatula, and transparent beaker are consumed
through `convert_asset_package` bindings. Scenario Forge does not author their
scale, collider, mass, inertia, material repair, or asset-specific PhysX logic.

The eBench adapter now supports any qualified static or static-support object
through a generic package preload. GenManip's generic collider and rigid-body
creation are disabled for those objects. This is adapter transport, not a local
asset repair. The VR adapter now exports arbitrary task-object sets while
preserving the historical two-vessel dependency names for pour packages.

## Evidence

All nine packages passed:

- portable package closure;
- robot-facing tabletop placement;
- Isaac Sim 4.1 initial-scene load/reset;
- seven-view 1920 x 1080 rendering;
- automated and human visual review for embedding, floating task objects,
  support penetration, and missing task meshes.

The runtime used the existing EOS-managed Isaac Sim 4.1 + GenManip environment
and an existing CuRobo source path. No new environment was created and GenManip
was not modified.

The tube-rack package is bound to the ConvertAsset k=1.25 fit report, which
records 12 bottom contacts and no side penetration for the specified 50 mL tube
protocol. This does not establish robot insertion success.

## Product status and claim boundary

Task 7 is a full-score canonical candidate. Task 8 is capped at 0.70 until a
threaded-closure interaction exists. Task 4 is capped at 0.55 pending a vessel
closure; Task 14 is capped at 0.65 pending liquid-flow and contained-volume
metrics; Task 15 is capped at 0 because tare control, a dynamic micro-spatula,
and reagent/sample assets are absent.

All nine remain candidates because the fixed-base provisional IK result is
`not_run`. The repository writes a deterministic request but does not contain a
standard GenManip/CuRobo request runner, and Scenario Forge must not become an
episode runner. The evidence therefore does not claim reachability, grasp,
stirring, threaded closure, pouring, weighing, policy, or benchmark success.

## Validation

Focused package/schema/adapter tests:

```text
169 passed
```

The repository-wide check also passed:

```text
make check
609 passed; Ruff passed; package/workflow/layout/task/scene/eBench/suite smokes passed
```

The public task-directory page was reviewed in Chromium at 1440 x 1000 and
390 x 844. It had no broken images, console errors, or body overflow; the wide
table remained horizontally scrollable on mobile.

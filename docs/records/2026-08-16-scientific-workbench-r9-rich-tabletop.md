# 2026-08-16 Scientific Workbench r9 Rich Tabletop

## Outcome

Tasks 02, 07, and 08 now have seven immutable r9 scene packages that add
non-scoring, room-semantic tabletop context from
`refined_assets_on_table_no_operation.zip` while preserving the r7 task-object
poses and Lift2 robot contract. Task 02 has one modern-wet-chemistry package,
Task 07 has five fixed background packages, and Task 08 has one bioclean package.

The context is deliberately placed on the far left and right tabletop wings. It
does not enter the task graph, success predicates, or task-object list. The main
interaction corridor remains unchanged.

## Asset admission

ConvertAsset qualified six source-bound dynamic context objects in Isaac Sim 4.1:
amber and clear reagent bottles, a pipette carousel, a pipette-tip box, a wash
bottle, and a 100 mL graduated cylinder. Scenario Forge consumes those packages
through source bindings and adds no asset-specific collider, scale, mass, inertia,
or PhysX-warning suppression.

Standalone `/ObjectRoot` entry prims are not descendants of the room `/World`
entry. The GenManip adapter therefore references them into object wrappers without
trying to deactivate a nonexistent `/World/ObjectRoot` room child.

## Runtime and visual gates

All seven packages passed:

- package dependency closure and tabletop-placement validation;
- GenManip load, reset, recovery, and 960 zero-action physics steps;
- three-view 1920×1080 initial-scene rendering;
- local visual review of the overview, workspace, and task-object views.

The first Task 08 render exposed two closed context-tube caps separating during
the 960-step warmup. r9 replaced only those two non-scoring context instances with
the already qualified body-only 15 mL tube package. The real red task cap remains
separate and visible. The corrected Task 08 render passed the same runtime gate.

## Task 02 robot evidence

EOS ran three cold-start scripted Lift2 oracle trials against the exact r9 Task 02
package, without task-object transform writes or replay. All three passed the
five-stage hold, lift, align, pour, and return protocol:

| run | target particles | source particles | spill | below support | commanded lift |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 573 | 7 | 0 | 0 | 0.100054 m |
| 2 | 571 | 9 | 0 | 0 | 0.100013 m |
| 3 | 571 | 9 | 0 | 0 | 0.100007 m |

A separate same-protocol recording run placed 570 of 580 particles in the target,
with zero spill and zero particles below support. EOS retains workspace,
task-closeup, and combined robot-operation H.264 videos plus a keyframe atlas. The
formal evidence validator passed, and Scenario Forge hash-binds a copied evidence
tree under `evidence/robot_oracle/`.

This proves a scripted robot contact oracle for the recorded fixed protocol. It is
not learned-policy success, benchmark success, or qualification of the eBench
liquid metric; the package keeps `liquid_metrics_active: false` and a 60% scoring
ceiling.

## Handoff and page

The seven robot-free VR review scenes are delivered as one deterministic archive:

`outputs/scientific_workbench_tasks_02_07_08_r9_20260816/handoff/scientific_workbench_tasks_02_07_08_r9_rich_tabletop_20260816.zip`

Each package directory contains the USD, config, parity manifest, and package-local
dependencies. The task directory defaults to r9 for Tasks 02, 07, and 08 while
retaining the older release switches.


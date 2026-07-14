# Task Catalog and Readiness

Scenario Forge separates durable task intent from dated implementation readiness.
The catalog is a small, versioned product input; the readiness snapshot is evidence
about the assets and runtime available on one date.

## Catalog contract

`task-catalog/v0.1` records stable task IDs, source IDs, task level, execution mode,
step count, atomic skills, required asset roles, claim scope, and intended success
evidence. It does not contain local USD paths, ConvertAsset manifests, simulator
objects, rollout code, or a claim that any task is executable.

The current scientific-workbench catalog lives at
`configs/task_catalogs/scientific_workbench_phase1.yaml`. It is derived from the
detailed table in the 2026-07-14 task-design handoff. The source document declares
17 first-phase tasks, while the detailed table contains 19 candidate rows: `1..17`
plus `8a` and `8b`. The catalog preserves all source IDs and records the discrepancy
as unresolved. A later product decision may mark variants or replacements, but must
not silently renumber or delete rows.

The catalog is not a ScenarioSpec and is not directly compiled into a scenario
package. A selected task still needs an explicit ScenarioSpec, asset-source
resolution, layout, robot binding, predicates, and adapter export.

## Readiness snapshot

`task-readiness-snapshot/v0.1` records evidence-backed status for asset roles and
catalog tasks. It intentionally avoids one global `ready` boolean.

For assets it distinguishes:

- whether a usable context package or candidate identity exists;
- whether task-specific interactive affordances have been validated;
- pending affordances and concrete blockers.

For tasks it distinguishes:

- portable package compilation;
- downstream runtime reset;
- full oracle execution.

A successful simulator reset does not promote oracle readiness. Object identity,
the tracked rigid body, task frames, and downstream metric semantics must agree;
otherwise `oracle_status` is `blocked` even when package compilation and reset pass.

These states must not be promoted by inference. For example, the source-bound
DryingBox_03 package is accepted at the portable overlay/context-package boundary,
but current GenManip initialization recursively removes colliders below the
`room` prim. In that adapter placement it is visible context, not evidence of a
collision-active device, and it does not prove that a door or start button can be
manipulated and observed. Dynamic asset repair and interaction-ready packaging
remain upstream asset-owner responsibilities.

Snapshots are dated records, not mutable project-management truth. The current
snapshot lives under
`docs/records/evidence/2026-07-14-scientific-workbench-task-catalog/`.

## Selection rule

The first expansion tasks should be selected only after their required roles have
identified candidates and their claim can be expressed with supported predicates.
The selected set should cover more than one skill graph or asset combination. A
blocked task remains in the catalog with its original identity; Scenario Forge does
not generate placeholder assets or publish a format-correct package as executable.

# Task Catalog and Readiness

Scenario Forge separates durable task intent from dated implementation readiness.
The catalog is a small, versioned product input; the readiness snapshot is evidence
about the assets and runtime available on one date.

## Catalog contract

`task-catalog/v0.2` records stable task IDs, exact source fields, normalized
execution mode, step count, atomic skills, required asset roles, and every
Progress Score criterion. It also binds the catalog to the source document,
embedded sheet, revisions, range, and content hash. It does not contain local USD
paths, ConvertAsset manifests, simulator objects, rollout code, or a claim that
any task is executable.

The product authority is the `1. Task Design` section of the Feishu wiki and its
embedded task sheet. The checked-in source snapshot lives at
`configs/task_catalogs/sources/scientific_workbench_task_design.json`; the
generated catalog lives at
`configs/task_catalogs/scientific_workbench_phase1.yaml`. The current pinned
source contains 18 table rows. The document prose still says 17 tasks, so the
catalog records that inconsistency instead of silently deleting a row.

Refresh or check the snapshot explicitly:

```bash
python scripts/sync_scientific_workbench_task_catalog.py --check
python scripts/sync_scientific_workbench_task_catalog.py --write
```

These commands use the user's Feishu authorization. Normal compilation and CI
consume the pinned snapshot and remain offline.

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

Snapshots are dated evidence, not mutable project-management truth. The current
readiness snapshot lives at
`docs/records/evidence/2026-07-31-scientific-workbench-task-design-correction/readiness.yaml`.
The former PDF-derived v0.1 catalog remains beside it as archival evidence only.

## Selection rule

The first expansion tasks should be selected only after their required roles have
identified candidates and their claim can be expressed with supported predicates.
The selected set should cover more than one skill graph or asset combination. A
blocked task remains in the catalog with its original identity; Scenario Forge does
not generate placeholder assets or publish a format-correct package as executable.

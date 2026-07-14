# 2026-07-14 Scientific Workbench Task Catalog and Readiness

## Decision

The wet-experiment task-design handoff is now represented by a versioned
Scenario Forge task catalog and a separate dated readiness snapshot. The raw PDF is
not a compiler input and is not required in a generated scenario package.

## Source identity and ambiguity

The handoff source filename is `湿实验具身操作评测任务设计.pdf`, with SHA-256:

```text
3b7ebb2592a8dd612f37e0e934aa052284de772fd0e7fb80b7359afa57d82eca
```

The document states that the first phase contains 17 tasks. Its detailed candidate
table contains 19 rows because IDs `8a` and `8b` appear in addition to `1..17`.
Scenario Forge preserves all 19 candidate identities and records the count mismatch
as unresolved. This record does not choose which two rows, if any, are variants or
replacements.

## Current readiness

`wetlab_nonquant_pour_to_cylinder` is the only task with a compiled package and a
current exact-package runtime reset. Its five-stage oracle remains pending.

The DryingBox_03 source-bound ConvertAsset package is accepted for physical scene
context. Door opening/closing and start-button state are separate interaction
affordances and remain pending. Centrifuge, heating plate, vortex oscillator,
rotary evaporator, chromatography column, balance, stopper, tube/rack, funnel, and
other task-specific assets remain blocked or pending according to the snapshot.

This is intentionally not a claim that all assets named in LabUtopia are absent.
An object visible in a source USD is not yet a task-ready asset until its identity,
runtime closure, interaction prims, physical behavior, and success observation are
bound for the task.

## Artifacts

- Catalog: `configs/task_catalogs/scientific_workbench_phase1.yaml`
- Catalog schema: `task-catalog-v0.1.schema.json`
- Readiness: `docs/records/evidence/2026-07-14-scientific-workbench-task-catalog/readiness.yaml`
- Readiness schema: `task-readiness-snapshot-v0.1.schema.json`

The next implementation target remains the exact-package five-stage oracle for the
existing bimanual pour. In parallel, the catalog constrains the design of the thin
asset-source resolution and compile orchestration entry point.

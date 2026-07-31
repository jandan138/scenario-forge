# 2026-07-31 Scientific Workbench Task Design Authority Correction

## Outcome

The `1. Task Design` section of the Feishu wiki and its embedded sheet are now
the product authority. Scenario Forge pins their revisions, range, and content
hash in
[`../../configs/task_catalogs/sources/scientific_workbench_task_design.json`](../../configs/task_catalogs/sources/scientific_workbench_task_design.json)
and deterministically generates the v0.2 catalog and reference pages from that
snapshot.

The source currently contains 18 task rows. Its prose still says 17 tasks; that
discrepancy, the task 12 weight total of 0.90, and other row-level source
inconsistencies are preserved as warnings rather than silently repaired.

## Corrected identities

The previous tube-task prototypes were incorrectly described as tasks 7 and 11.
The live rows are:

- task 7: `scientific_workbench_glass_rod_stir`;
- task 10: `scientific_workbench_centrifuge_load_start`;
- task 11: `scientific_workbench_centrifuge_unload_shutdown`.

The two implemented integration cases are now explicitly non-canonical:

- `scientific_workbench_prototype_centrifuge_load_start`;
- `scientific_workbench_prototype_bimanual_rack_insert`.

Historical `wetlab_*` output directories are retained unchanged as regression
evidence. They are not canonical task packages and must not be handed to eBench
under task 7, 10, or 11.

## Readiness consequence

No formal package is currently claimed for live task 7, 10, or 11:

- task 7 lacks a qualified glass rod and beaker stirring interaction;
- task 10 lacks the specified setting button and the full lid-open sequence;
- task 11 lacks a lid-open button, shutdown button, and observable off-state.

The existing centrifuge, test tube, and rack deliveries remain valid for the
affordances they actually proved. They are shared partial inputs, not evidence
that the Feishu tasks are complete. The exact producer request is
[`../operations/scientific-workbench-live-task-7-10-11-asset-admission-request.yaml`](../operations/scientific-workbench-live-task-7-10-11-asset-admission-request.yaml).

## Reproducibility

Use:

```bash
python scripts/sync_scientific_workbench_task_catalog.py --check
```

to compare the checked-in snapshot and generated artifacts with the live Feishu
source. Normal repository checks remain offline and validate the pinned data.

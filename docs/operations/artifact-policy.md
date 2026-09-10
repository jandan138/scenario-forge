# Artifact Policy — Maintenance Entry

The current formal rules are maintained in the standards library:

- [VAL-005: Git and large artifacts](../standards/validation-and-delivery.md#val-005)
- [VAL-006: current deliveries and historical retention](../standards/validation-and-delivery.md#val-006)

This path remains available for existing links. The rules formerly published
here moved on 2026-09-08 without changing their meaning; do not maintain another
copy of the policy in this file.

## Finding artifacts

Use [current task heads](../../configs/artifact_retention/current_task_heads.v1.json)
to locate a task/variant's complete directory and canonical handoff ZIP.
Use [external artifact indexes](../../external_artifacts/README.md) for externally
stored material and the associated dated records for hashes and restoration
checks. A filename's largest revision number is not a substitute for the index.

## Maintenance procedure

Before retention work, resolve the task family, variant and source dependencies;
apply the classifications in VAL-006 and record the decision and evidence.
The standards migration itself does not authorize an archival or cleanup run.
Policy changes follow the [standards maintenance workflow](../standards/maintenance.md).

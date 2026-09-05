# Generated Artifact Retention Review

Scenario Forge now records current local task-package heads in
`configs/artifact_retention/current_task_heads.v1.json`. The registry keeps one
head per task and meaningful delivery variant, with both its full output tree
and canonical handoff ZIP. It deliberately keeps candidate or blocked
validation status separate from benchmark or robot-policy success claims.

The external storage operation at
`/cpfs/user/zhuzihou/ops/storage-cleanup/` gained a fail-closed retention
inventory and an approval-digest archive path. The review spans Scenario Forge,
ConvertAsset outputs and tmp trees, and EmbodiedEval OS outputs, while keeping
their OSS namespaces separate. Unclassified paths default to `HOLD`; approved
archive paths remain subject to process, path-type, secret, hashing, restore,
quarantine, and repository-validation gates.

At this record's pre-delete checkpoint, no generated directory has been
removed. The immutable v3 review files are:

- `inventory-retention-review-20260905-v3.json`;
- `RETENTION-REVIEW-2026-09-05-v3.md`;
- approval SHA-256
  `cac467cf95073eca0162b5233b3703e3819b42ed05094b40c673582a3255bde8`.

The proposed archive set is 18.92 GiB: 12.56 GiB from Scenario Forge, 2.46 GiB
from ConvertAsset outputs, 3.66 GiB from ConvertAsset tmp, and 0.24 GiB from
EmbodiedEval OS outputs. This is storage-retention evidence only; it does not
change or upgrade any task, asset, runtime, robot-policy, or benchmark claim.

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

- `inventory-retention-review-20260905-v6.json`;
- `RETENTION-REVIEW-2026-09-05-v6.md`;
- approval SHA-256
  `95f01b800ab94da12156b9c145418c41c4cc5f983a3d1329fce13853a51092ab`.

The proposed archive set is 18.46 GiB: 13,483,260,265 bytes from Scenario Forge,
2,143,433,948 bytes from ConvertAsset outputs, 3,932,477,196 bytes from
ConvertAsset tmp, and 262,855,016 bytes from EmbodiedEval OS outputs. One
changing Scenario Forge `.working` directory and 51 ConvertAsset experiment
directories containing runtime symlinks are explicitly held outside the
archive set. All four approved subsets passed the non-mutating preflight. This
is storage-retention evidence only; it does not
change or upgrade any task, asset, runtime, robot-policy, or benchmark claim.

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

The initial review below describes the pre-delete checkpoint. Execution is
now complete for the safe approved subset; see the execution result below.
The immutable v6 review files are:

- `inventory-retention-review-20260905-v6.json`;
- `RETENTION-REVIEW-2026-09-05-v6.md`;
- approval SHA-256
  `95f01b800ab94da12156b9c145418c41c4cc5f983a3d1329fce13853a51092ab`.

The proposed archive set is 18.46 GiB: 13,483,260,265 bytes from Scenario Forge,
2,143,433,948 bytes from ConvertAsset outputs, 3,932,477,196 bytes from
ConvertAsset tmp, and 262,855,016 bytes from EmbodiedEval OS outputs. One
Scenario Forge `.working` directory and 51 ConvertAsset experiment
directories containing runtime symlinks are explicitly held outside the
archive set. All four approved subsets passed the non-mutating preflight. This
is storage-retention evidence only; it does not
change or upgrade any task, asset, runtime, robot-policy, or benchmark claim.

## Execution result

Six batches completed with immutable OSS copies, count/byte/hash verification,
restored samples, quarantine validation, and local deletion. The net result
excludes two assets subsequently restored as cross-repository test inputs.

| Root | Removed directories | Net removed bytes |
| --- | ---: | ---: |
| Scenario Forge outputs | 53 | 12,864,423,143 |
| ConvertAsset outputs | 75 | 2,065,101,524 |
| ConvertAsset tmp | 350 | 3,932,477,196 |
| EOS outputs | 6 | 262,855,016 |
| Total | 484 | 19,124,856,879 |

The original approval remains unchanged. Fifteen approved candidates were
retained as explicit execution exceptions: Task 08 r12 is the physical-thread
branch, twelve directories are retained producer/generator inputs, and two
ConvertAsset packages were restored after cross-repository regression checks
identified dependencies. Those two packages are the original fixed-benchtop
oven and titration station r1. Their complete restored contents matched the
original SHA-256 manifests. All exceptions and their reasons are in
[`archive-index-20260905.json`](../../external_artifacts/archive-index-20260905.json).

The current generator chains have **not** all been decoupled from older
outputs. That refactor remains necessary before removing the retained build
inputs. The large retained background/source sets are also outside this
approved deletion subset. This is not a claim that only task heads remain on
disk.

Validation after cleanup:

- Scenario Forge: `make check`, 910 passed; Ruff, package smoke, Phase 10.x passed.
- ConvertAsset: clean committed validation checkout, 1155 passed / 8 skipped;
  the original dirty paper worktree's content fingerprint stayed unchanged.
- EOS: smoke, 4929 passed / 10 skipped, core leakage check passed.
- Full restores: Task 02 (175 files), threaded tube asset (51 files), EOS
  evidence (4 files), plus the two restored inputs (14 and 50 files).
  Every file SHA-256 matched; the restored Task 02 VR scene opened with 2780 prims.

The interrupted second Scenario Forge batch was recovered by checking every
remaining quarantined file against the already verified manifest, then
finishing deletion and uploading its completion record. No quarantine remains.
The temporary ConvertAsset validation worktree was removed. Existing unrelated
worktrees and source archives were not removed.

## Find and restore

The human-readable result is
`/cpfs/user/zhuzihou/ops/storage-cleanup/reports/approved-v6-result.md`.
The tracked archive index records original paths, exact case-sensitive OSS
URIs, file counts, tree hashes, batch IDs and manifest locations.

```bash
python3 /cpfs/user/zhuzihou/ops/storage-cleanup/restore_artifact.py task02 --list
python3 /cpfs/user/zhuzihou/ops/storage-cleanup/restore_artifact.py \
  scientific_workbench_task02_r85_20260816 --dest /tmp/restored-task02-r85
```

The destination must not exist. Restore checks the full file set and every
SHA-256. Batch metadata and SHA manifests are retained on OSS in each project's
`artifact-history-v1/_manifests/<batch>/completion/` prefix. A recovery-tooling
snapshot and consolidated index were also uploaded and checked at:

```text
aliyun-beijing-internal:pjlab-bjpai-zhuzihou-assets/archives/scenario-forge/artifact-history-v1/_manifests/retention-v6-final-20260905
```

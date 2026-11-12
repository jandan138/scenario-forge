# Task 12/task 18 repair-round OSS evidence backup

User date: 2026-10-29. The host UTC clock at execution reported 2026-10-28;
individual receipts preserve that observed UTC rather than inventing timestamps.

The user requested research of the EmbodiedEval OS OSS archive workflow and
execution of this round's backup without interrupting ongoing water-bath/silver
repair. Read-only review covered EEOS `evidence-oss-archive.md`,
`r-evidence-oss-retention.md`, its storage policy and archive, metadata snapshot,
and restore scripts. The useful pattern is one immutable archive per completed
attempt, receipt-linked native output, per-file identity, full remote readback,
and explicit restoration. Its deletion permission, 100 GiB quota admission rule,
and four-worker scheduling are specific to its old R-study and were not adopted.
No EEOS files or cleanup jobs were changed.

The current rclone backend advertises MD5 only. A bounded read-only probe of the
new Scenario Forge experiment prefix succeeded with an empty listing. Uploads
therefore use additive immutable generations and explicit full-read SHA-256
verification. The external tools and current index are under
`/cpfs/user/zhuzihou/dev/scientific-round2-repair-20261026/bath/repair_20261028/archive_oss`.
See [the runbook](../operations/scientific-experiment-oss-backup.md) for the OSS
prefix, closure rules, single-worker supervision and restore command.

## Verified pilot

The isolated query run `query_20261028T120547_706453Z` was selected using its
completed status/exit-code record and an actual process check on
`dsw-536365-78bdb944c8-q99ff` at `10.150.164.127`. The old `dsw-4090` SSH alias
points to another host and was not used for closure attribution or modified.

- Source: two regular files, 228,756 bytes (`report.json`, `query_stage.usda`).
- Archive: 44,859 bytes, SHA-256
  `f0e0b94708b40649cedaa8f291272386baff2b220fd17ee6be2360d8ff3586e8`.
- Generation: `units/pilot-beaker-query-v1/20261028T173214Z-0760696bef/`.
- Archive, manifest and verification receipt were all read back from OSS in full.
- `run/report.json` was actually downloaded/restored under
  `/tmp/scenario-forge-restore-acceptance-20261028`, with verified SHA-256;
  `archive_oss/restore_acceptance.json` records the check.
- All original files remain. This proves a recoverable backup of a static query;
  it does not establish dynamic containment, repair success or final delivery.

The first native batch covers closed C1/C2/F1/F2 and contact runs, with native
videos and metadata. Exact verified counts and bytes are in `archive_oss/index.json`;
queued or packing units are not counted as verified. No-result historical attempts
and current integration runs remain HOLD until explicit closure is available.
The service continues discovering closed units within this round's owned tree.

## Standards and validation

Applicable rules: VAL-001/003/004 preserve qualification and evidence identity;
VAL-002 requires packing/restore checks; VAL-005 keeps large evidence and tools
outside core package layers; VAL-006 preserves current heads and history; the
maintenance workflow requires this dated record and matching operations guidance.
规范无需变更：本次只是已授权实验产物的私有备份，未改变场景制作规则、包/API、
任务资格、当前交付头或历史包字节，也未给予删除授权。

Four external tests were first run failing for the missing implementation, then
passed: traversal rejection, symlink exclusion, changed-source rejection, and
restore refusal for symlinks/different existing files. The actual OSS pilot adds
end-to-end upload, full readback and recovery evidence. No simulator revalidation
is claimed or needed for unchanged source scene bytes.

Repository `make check` passed: 1,255 tests passed, one skipped; Ruff,
boundary/schema/examples and the Phase 10.x suite passed. The retained log is
`archive_oss/make_check.log`; `acceptance_checks.json` records its SHA-256 and the
byte-for-byte pilot restore comparison. Existing unrelated worktree changes were
not edited or staged.

An additional failing-then-passing test rejects manifest unit IDs containing path
traversal before local staging or OSS key construction. The final external test
count is five; this external-tool change does not change repository package tests.

## First batch and continued discovery

At the 2026-10-28 18:00 UTC handoff, all nine native units in the frozen first
batch plus the pilot were verified: 59,044 regular files, 12,212,545,184 source
bytes and 8,727,526,731 compressed archive bytes. These are backed-up bytes, not
freed space. Zero original files were deleted.

The archive worker then reached idle and the transition supervisor verified its
process identity, stopped only that archive worker, and started the expanded
worker under the same lock. Four additional tooling/query/metadata snapshots
also completed, bringing the as-of index to 14 verified units, 63,525 files,
12,268,845,170 source bytes and 8,735,140,367 archive bytes. Snapshot units may
intentionally overlap source files; these sums are not a deduplicated footprint.
The independent controlled-visual probe was packing; the NOT_READY candidate
and remaining closed receipt units remained queued. Discovery also recognized
new `normal_final_20261029` receipts as HOLD while still incomplete.

`archive_oss/handoff_snapshot.json` binds the worker, counts, current HOLD list,
validation and remote index. The fully read-back immutable index at this point
was `indexes/20261028T175940Z-ebd83460a7.json`, SHA-256
`9a3d2d40844b691f05fac8147645d002971d21b98497ef9d333559afab7859ea`.
Current progress remains in the local index/status; this record does not claim
the remaining queue or active experiments have completed.

## Independent progress and native restore review

At 2026-10-28 18:25:32 UTC (2026-10-29 02:25:32 Beijing), the live
index contained 24 fully verified units: 118,983 regular files,
22,379,668,303 source bytes and 16,237,568,568 compressed archive bytes.
The single archive worker was reading back another upload; unresolved failures
were zero. These are additive as-of snapshots and may overlap; no source bytes
were freed and no GPU jobs were stopped.

The implementer also restored an actual native `result_info.json` from a
1,042,436,983-byte archived C1 mixed-6 run and compared its bytes to the retained
local original. SHA-256 matched
`52a83b889fd910d37709fdd8c8c43ae5bda10e8efcf5af5c727c5e3ebfb236e2`.
Its original score 0.85, SR 0 and 7,000 steps were preserved. This validates
recovery of that archived evidence; it does not turn the failed episode into
a successful task or establish final candidate qualification.

The exact read-back index and review evidence are located in
`archive_oss/root_archive_progress_review_20261029.json` and
`archive_oss/root_native_restore_review.json`. New reviews written after an
archive's snapshot are not silently claimed to be present in the older object.
Final evidence packaging must bind its own immutable snapshot.

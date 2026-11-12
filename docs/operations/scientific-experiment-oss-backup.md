# Scientific experiment evidence backups

This runbook covers the task 12/task 18 repair round rooted at
`/cpfs/user/zhuzihou/dev/scientific-round2-repair-20261026/bath/repair_20261028`
(`R` below). The user authorized private OSS backup while experiments continue.
The latest explicit user authorization permits local eviction of already verified, closed raw payloads. Inputs, source assets, current candidate/head trees and small reports remain protected; original archive receipts stay byte-identical. This is an external evidence workflow, not a
Scenario Forge episode runner, package API, or replacement for task acceptance.

Independent versioned tools live under `R/archive_oss/local_eviction/source_payload_20261029`; the original `R/archive_oss/tools/archive_round.py` remains frozen. `worker_launch.json` identifies the active version, process, script SHA and log; a pending version is not active until its static-boundary handoff completes. It uses only
Python's standard library, the installed rclone, and read-only SSH process checks.
It does not import simulator SDKs, change runtime inputs, restart GPU jobs, or
apply a storage quota gate. Do not run the EmbodiedEval OS R-study cleanup script:
its old authorization to delete payloads does not apply to this round.

## Location and ownership

The configured remote is `aliyun-beijing-internal:`. The private destination is:

```text
oss://pjlab-bjpai-zhuzihou-assets/archives/scenario-forge/scientific-experiments/task12-task18-repair-20261028-v1/
  units/<unit-id>/<utc-and-random-generation>/evidence.tar.gz
  units/<unit-id>/<utc-and-random-generation>/manifest.json
  units/<unit-id>/<utc-and-random-generation>/remote_verified.json
```

This is a separate namespace for experiment evidence. It does not change
`artifact-history-v1` for superseded task packages, current task heads, original
inputs, or any existing project's archive. Each transfer is additive and immutable;
there is no `sync`, purge or remote deletion. User-authorized local raw-payload eviction is a separate, SHA-gated operation documented below.

Automatic discovery remains scoped to R. Explicitly admitted closed output leaves under the parent round2 experiment project use a separately checked owned-project root. Other-task units use the independent `round2-closed-outputs-20261029-v1` OSS prefix. Admission binds each original receipt to its actual runtime hostname; closure queries that host rather than substituting another machine. Only owned `evidence/runs` and `saved/eval_results` leaves are allowed; whole runtime/source trees, delivery/review copies and current task heads remain protected. The scanner does not follow symlinks, enter shared
runtime/assets trees, copy credentials, caches, environments, or models. A native
output directory is admitted only through a completed receipt's `result_path`
whose resolved directory is within the unit's explicitly admitted scope. Symlinks are recorded without copying their
targets. The archive is evidence, not a self-contained simulator environment;
external input paths and original input hashes remain provenance references.

## Admission and validation

A native unit needs an explicit receipt end time, result object and owned native
result file, plus a successful check that corresponding runtime processes are
absent on the receipt's actual host. No-result/aborted attempts stay HOLD until
explicit termination/cleanup evidence is reviewed. File age alone never admits a
unit. Scores, failures and `acceptance_eligible` retain their original meaning.
Pending integration and normal-demonstration runs remain HOLD until closed.
A controlled visual probe with an explicit end/exit receipt is a separate visual
unit, not a native robot run. Static candidate snapshots retain their NOT_READY
identity. Other fixture trees without reviewed closure evidence remain HOLD.

Each unit includes the complete run directory and its receipt-linked native
output directory, including available four-camera videos and `meta_record.pkl`.
The manifest records original roots, run/task/config/result identity, timestamps,
file sizes and SHA-256, skipped symlinks, archive hash and closure evidence. Hashes
are computed from the bytes passed to tar. Full source membership, size, mtime and
SHA-256 are checked after packing and again after remote verification. A changing
source cannot receive a verified receipt.

The worker first performs an rclone dry-run, uploads with `--immutable` and
`--s3-no-check-bucket`, then fully reads each OSS object back and checks SHA-256.
It does not interpret multipart ETag as SHA-256. Proxy environment variables are
unset only for rclone subprocesses. One worker and 16 MiB/s network bandwidth
limit keep the backup separate from simulation work.

Small code/control records can be copied with `snapshot_metadata.py`. Their
provenance explicitly says point-in-time; a copied live status is not final.
Metadata snapshots do not authorize source deletion. Current inputs remain untouched; separately authorized raw-output eviction follows the gates below.

## Operations and restore

Use the external script with `discover`, `archive --dry-run`, `archive`, or `watch`.
The manifest override is `--manifest <file>` and unit selection is `--unit <id>`.
A single-instance lock is held at
`/tmp/scenario-forge-scientific-archive-20261028/worker.lock`.
Check `R/archive_oss/worker_launch.json` and `status.json` before starting anything.
A heartbeat every ten seconds distinguishes packing/uploading/verifying/idle/error;
`last_progress_at` advances only after a verified unit. A failure never restarts
GPU work or releases local data. `index.json`, `receipts/`, `candidates.json`, and
`failures/` retain local locators, verified totals and HOLD/error details.
`remote_index_latest.json` points to a fully verified immutable OSS index snapshot.
The nine-unit first batch is preserved in `batch1_manifest.json`;
`transition_at_idle.py` changes the archive worker only after that batch reaches
idle/error and checks the old process identity before signaling it. The expanded
worker keeps the same single-instance lock. Status
and worker logs also live under the `/tmp` directory above.

For the verified pilot, first list the selection:

```bash
python3 "$R/archive_oss/tools/archive_round.py" restore \
  --receipt "$R/archive_oss/receipts/pilot-beaker-query-v1.json" \
  --destination /tmp/scientific-evidence-review \
  --only run/report.json --dry-run
```

Repeat without `--dry-run` to download and extract. Omit `--only` for all regular
files. The restore checks the downloaded manifest/archive and each selected file,
rejects traversal and symlinks, and refuses to overwrite different existing data.
Choose a fresh directory. Recorded symlinks are not recreated automatically.

The pilot and current limits are recorded in
[the dated evidence record](../records/2026-10-29-scientific-experiment-oss-backup.md).

## Native sequences and the v2 handoff

A receipt containing `sequence_results` is admitted as a `native_sequence`, never as only its top-level final `result_path`. Empty, malformed or unfinished sequences stay HOLD. The unit contains `run`, every `native_000`/`native_001`/... root and `worker_logs` from the exact owning `runtime/logs/<run-id>/worker` directory. Per-segment result/path/task/case/episode ownership, client completion, native artifacts and finalize-payload markers are checked; the roots must be disjoint and free of symlink escape. Worker proof bytes are packed alongside their hashes.

The new `native-seq-v2-<hash>` IDs leave old single-segment objects and receipts intact. Unit closure rechecks server/client/worker/runID process absence and source membership/hashes before packing and after remote readback. A changing source is a real failure; preserve its dated logs rather than counting it as verified.

The 2026-10-29 handoff used a bounded exact-identity supervisor and waited for no active packing, upload or readback at a static idle/error boundary. It stopped only old worker522735 and started worker1123356 on the existing lock. Three priority units (8 native segments) completed actual dry-runs, full uploads/readbacks and stability checks before that same PID continued normal v2 watch. The acceptance snapshot was61 verified units/0 unresolved failures; HOLD entries were excluded. These are dated observations, not fixed target counts.

A real full restore of the cross-task unit recovered211 files, including its first native segment and raw worker logs, with all source SHA matches. Evidence and current operation notes are under `R/archive_oss/native_sequence_v2_preparation_20261029/handoff_20261028T1930`. The[dated handoff record](../records/2026-10-29-task12-task18-native-sequence-archive-handoff.md) binds the transfer/restore records. Keep one archive worker, preserve the shared lock, and use a fresh destination for restoration. Archive verification does not promote failed C1 results or any scene/task qualification.

## Closed diagnostic attempts without native results

A missing native `result_path` does not make a terminated diagnostic disposable. Preserve its original receipt and failure status. Review the original controller terminal record or explicit owned-process termination record, then check the current corresponding PID, PGID, runID and NVML identities on the actual runtime host. Active identities, missing termination evidence, unreaped identities or unavailable resource checks remain HOLD. This is an ownership/retention decision, not a successful native run.

For a confirmed closed diagnostic, freeze a finite selected subset into a new read-only snapshot: original failure logs/JSON/images, fixture, source code and binding copies, an explicit closure sidecar, actual resource-observation proof and a source/hash manifest. Do not admit an evolving whole parent directory. Do not follow shared symlinks or label changed current bytes as the original version. List omitted references and keep the originals. Never backfill the original receipt's end, result or SR.

Register the immutable subset as an appended `closed_diagnostic_snapshot` manual unit, with its original receipt locator and explicit closure basis. This resolves the original scanner HOLD only through reviewed diagnostic admission. Upload/readback completion is still required before counting the snapshot as verified. The existing watch worker can consume appended units without restart; keep the same lock and bandwidth limit.

The 2026-10-29 batch classified and archived twelve such snapshots, including all five source-init v2–v6 calibrations, then restored an actual failed source-v2 snapshot and confirmed its STARTING/no-end/STOPPED/exit-15 fields remained intact. At that completion snapshot, the existing worker had 73 verified units, 0 archive HOLD and 0 unresolved failures, while C1 remained rejected and 39 initialization jobs remained HOLD. See the [closed-diagnostic evidence record](../records/2026-10-29-task12-task18-closed-diagnostic-snapshots.md) and `R/archive_oss/closed_diagnostics_20261029/archive_acceptance.json`.

## Verified local payload eviction

The later user instruction to clear OSS-archived data supersedes the earlier local-retention policy. A local payload may be unlinked only after its unit has a persistent verified remote receipt, the downloaded manifest SHA matches that receipt, the run is closed, the exact file SHA still matches, its inode is single-link and unchanged during hashing, and current input/readers protections permit it. There is no recursive directory deletion. Mutated files, hardlinks, unverified files and active inputs remain local with explicit skip reasons.

Protection includes every inputs/input_sources path, canonical assets/config/taskdata/core, frozen diagnosis/runtime_base, the rollback payload_complete_v2 closure and all current tube_band05_guard_iso33_v1 content. c1_sample_vmax6_guard_iso33_v1 inputs/tools/candidates/runtime_prefix2000 remain protected; only its explicitly closed runs/native_runs can enter the new backup→full-readback→eviction sequence. Current command/file dependencies are resolved separately from historical output locators.

Generated NPZ/NPY, MP4/RRD, raw worker observer JSONL, large raw trace JSON and generated frame PNG/JPEG can be payloads. Extension alone does not make JSON/JSONL a small report. Receipts, summaries, hashes, certificates, contact sheets, scripts and metadata inputs are retained. New closed fixture/generation outputs require new owned closure admission and a real immutable upload/full readback before rolling eviction.

The authoritative source registry is `R/archive_oss/local_eviction_registry.json`, pointing to per-file tombstones and `restore_any_evicted.py`. Each deleted file keeps its archive unit, manifest object/SHA, member path and content SHA. Restore to a fresh destination; explicit local eviction is not an unfinished native run. The eviction-aware worker preserves verified archive locators and does not alter prior receipt bytes.

Source counters distinguish logical bytes unlinked from allocated blocks unlinked, exclude hardlink ambiguity, and are not deduced from overlapping archive source_bytes or shared-pool df changes. Staging tar counters are separate. After full remote readback and receipt persistence, the small staging watcher may remove only matching, unread compressed evidence.tar.gz copies; it keeps manifests/receipts/logs and cannot select KEEP_LOCAL canonical.pack. Git object copies were only inventoried: current 0644 packs fail the read-only hardlink gate, so no Git byte/path/history/HEAD/mode was changed and no Git savings are claimed.

Current per-batch evidence lives under `R/archive_oss/local_eviction/source_payload_20261029`, including dry-run lists, deletion audits, dependency protection snapshots, remaining-coverage lists and full file-type/Git-inode inventories. A low HOLD count or a verified-unit count is not a claim that the entire 174G parent experiment tree has been archived. Unregistered and owner-unconfirmed outputs remain listed and untouched.

## Closed client output evidence

Native `result_path` units do not implicitly cover separate `client_results` trees. The independent tools and admission evidence in `R/archive_oss/client_output_closure_20261029` bind each client leaf through its original receipt, the original client's printed results-directory parameter or explicit receipt field, and every raw `steps.jsonl` record's full benchmark/run/task/case/episode identity. An ordinary client unit also requires the original controller end, original receipt/proof/steps hashes, and fresh observations on the receipt's actual host. Matching PID, PGID, runID, NVML identity or an open client file rejects closure. Task heads, resolved inputs, current T1 and source/asset trees remain protected.

The immutable client prefix is `round2-client-outputs-20261029-v1` in the same project OSS namespace. Each `closed-client-output-v1-*` unit contains only the owned client leaf and its finite binding/proof snapshot. Source actions, mode/state/clock fields and merged videos are original evidence; reconstruction does not authorize deleting unarchived bytes. The first private v7 pilot was rejected by the prior prefix allowlist before upload; its failure log/stage remains evidence. Private v8 explicitly allows this client prefix while rejecting parent, other-bucket and arbitrary-suffix paths. Worker transitions retain the same lock and wait for a static idle/error boundary with no transfer.

Missing controller end remains a rejection in the ordinary client contract. A separately confirmed failed diagnostic may instead use an independently appended finite snapshot under the existing closed-diagnostic protocol: require the original receipt SHA, its already remote-verified explicit termination sidecar and manifest membership, original external termination bytes, exact task metadata hash, original client parameter and all raw step episode IDs, plus a fresh actual-host process/NVML/FD check. Preserve the missing end/result/SR fields. Record original client bytes and newly created duplicate snapshot bytes separately when evicting them.

After full remote readback and source stability, only exact archived client payload SHA matches may be removed. Each new client deletion keeps the original source path, archive unit, manifest SHA/object, member and content SHA. The shared `restore_any_evicted.py` also reads these client audits; restore to a fresh destination. Original archive/native receipts remain unchanged. `new_client_eviction_progress.json` counts this batch separately from the prior 63,507,049,057 B source batch; frozen-copy and compressed staging counters remain separate. The existing persistent staging watcher continues without interrupting uploads.

## Unique deletion accounting

`R/archive_oss/accounting_reconciliation_20261029/immutable_20261029T094703Z` preserves the independently reviewed 807-tar accounting and path rows. Keep its hashes and bytes immutable; use `accounting_latest.json` or a new dated snapshot for later unlinks. Watcher lifetime totals already include earlier cumulative values and later deltas. Root's initial staging total includes its two restored tar copies; agent restores and frozen raw snapshot copies are separate. Sum only disjoint actual unlink paths, not archive source_bytes or shared backing-filesystem df changes. The [dated reconciliation record](../records/2026-10-29-round2-retention-accounting.md) binds current totals, remaining input/failure-evidence retention and the shared restore registry.

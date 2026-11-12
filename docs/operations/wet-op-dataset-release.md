# WET-OP dataset release operations

The 2026-11-07 release is executed through `ssh genmanip-2gpu` (`10.150.170.198`). Read the [task record](../records/2026-11-07-wet-op-private-migration-and-hf-release.md) for scope and evidence. Apply ASSET-002 and VAL-001–007 in [validation and delivery](../standards/validation-and-delivery.md). Do not use the private project root as a public upload root.

## Locations

| Purpose | Target-host path |
| --- | --- |
| Private project | `/cpfs/shared/wet_op_bench/GenManip-Sim` |
| Train staging | `/cpfs/shared/wet_op_bench/releases/huggingface/WET-OP-Bench-Train` |
| Single validation staging | `/cpfs/shared/wet_op_bench/releases/huggingface/WET-OP-Bench-Validation` |
| State and receipts | `/cpfs/shared/wet_op_bench/_operations/release_20261107` |
| Scripts and native image evidence | `/cpfs/user/zhuzihou/dev/scenario-forge/external_artifacts/wet_op_release_20261107` |

The source repository and training directory remain untouched. Do not remove old shared data as part of this release. CPFS membership is owned by the user and was already configured.

## Queue and recovery

`status.json` describes the copy stage; its timestamp changes at stage boundaries, not on every file. Check `rsync` process activity and destination byte growth before treating it as stalled. `private_integrity.json` records full selected-data SHA-256 comparison; `private_hashes.jsonl` holds the individual hashes.

`train_pipeline.json` progresses from `COPY_WAIT_AND_INTEGRITY` through `DATA_CARD`, `PUBLICATION`, and `PUBLISHED_VERIFIED`. A failure changes it to `FAILED_REQUIRES_REVIEW` and preserves the failing stage log. Never bypass a failed integrity check to start uploading. Inspect `pipeline_copy_wait_and_integrity.log`, `train_check_progress.json`, and `train_integrity.json` for detail.

`hf_train.json` and `hf_validation.json` are the authoritative publication receipts. `UPLOADING` or `VERIFYING_REMOTE` is not completion. Only `PUBLISHED_VERIFIED` records successful remote tree, sizes, content hashes and sample-download verification. Each receipt records the exact final revision. The dataset card also remains marked as uploading until these checks finish.

`publish.py Train` / `publish.py Validation` use explicit per-dataset staging roots, resumable Hugging Face upload state, and a private creation receipt. They refuse an unexpected preexisting repository. The token is loaded from a private credential file, never from an argument or committed config. Keep `.cache` outside uploads. To resume after a network error, retain staging and its upload cache, restore connectivity, then rerun only the failed publication step with the release virtual environment.

The new host needed a temporary SSH reverse-forward proxy to reach Hugging Face. The release processes use loopback proxy port 28792, forwarded to the controller's existing proxy. A detached `proxy_supervisor.py` process restarts the SSH tunnel on disconnect and exits when the pipeline reaches a terminal state. Its heartbeat is `external_artifacts/wet_op_release_20261107/proxy_monitor.json`. If the supervisor itself stops, restart it with a detached session before resuming uploads. Do not change machine-wide proxy or Git settings.

## Public validation scope

The published dataset contains only task-01 `validation_mixed_1/000`. Original scene appearance and initial state are retained; `public_validation` is a portable directory name. No LMDB, trajectory records, private holdout episodes, historical logs, or evaluation results belong in this dataset.

Runtime checks must use an isolated saved tree so private assets cannot hide missing dependencies. USD dependency discovery does not enumerate transitive MDL imports or robot-planner configuration reads; include those in native checks. Native simulation can write mesh caches under `saved/assets/mesh_data`: keep generated caches in private operations storage, not the public payload.

Team-authored data/assets use MIT. Preserve original notices for bundled material software. The NVIDIA tabletop shader remains an official remote dependency with a pinned content hash. The cuRobo planner configuration carries its original NVIDIA research/evaluation license; do not describe that software as MIT. No simulator SDK is bundled.

The accepted check is initialization plus 20 hold steps and paired four-camera image review. It is not a successful pouring rollout, a validation score, or qualification of every private task. The overhead view shows both task vessels; individual fixed cameras provide partial views.

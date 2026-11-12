# Private migration independent-runtime audit

Status: in progress; no independence acceptance yet.

The user selected current-host auditing, allowing the installed Isaac/CUDA base environment, and full initialization coverage plus representative complete replays. Strict mount isolation remains deferred: the current host rejects unshare/bwrap namespaces and has no Landlock ABI. Do not equate path scanning or successful execution with strict isolation.

Target: `/cpfs/shared/wet_op_bench/GenManip-Sim`. Private scripts, environment, inventory and evidence: `/cpfs/shared/wet_op_bench/_operations/independence_20261108`. The source project and Hugging Face repositories are unchanged by this audit.

A frozen inventory contains 961 configuration/episode cases. Static text scanning identified 432 legacy-path candidates, including historical provenance records; these are candidates, not 432 proven runtime dependencies. Native USD/MDL closure and runtime attribution are still outstanding.

The former acceptance wrapper explicitly imported the client from another project under `/mnt/data/zhuzihou`; its driver/evidence also depended on Scenario Forge. New copies of the driver and probe now reside on the target CPFS and use the target client submodule. A clean non-system-site-packages client venv was installed there, using the existing Python distribution as an allowed base runtime. EvalClient import and gmp CLI initialization passed; package resolution points inside the new CPFS environment. The full dependency lock and baseline-runtime path audit remain pending.

A two-GPU task01 test/validation pilot has been launched, including 20 hold steps and a second reset. Its status is `pilot_status.json`; native errors and images must be reviewed before expanding coverage. The full 961-case queue and representative complete replay comparisons have not yet been launched. No successful pilot may be promoted to full-project acceptance.

Rules: ASSET-002, VAL-001–008. No general standard changes are justified: this work applies existing closure, runtime-scope and replay-calibration rules. No simulator runner is added to Scenario Forge core. Remaining work includes dependency classification and closure, full coverage with explicit episode selection, calibrated old/new representative replay, visual/log review, and a target-local runbook with final evidence.

## Pilot diagnosis and retry

Both initial pilot lanes completed initial reset, four-camera captures and 20 hold steps. They failed in the probe's second-reset assertion because EvalClient.reset allocates the next queued task; it does not restart the currently assigned episode. The returned observation was None, which the probe incorrectly indexed. This is a harness error, not evidence of missing scene assets.

The failed attempt remains recorded in `pilot_status_first_attempt.json`. A retry now closes the first client, submits a separate private repeat job for the same configuration and episode, and checks fresh initialization. The receipt explicitly distinguishes fresh-job initialization from same-worker warm reset. Warm-reset qualification remains outstanding and is not silently replaced by this retry. Full 961-case coverage and representative replay have not started.

## Explicit worker reset and full native queue

A new target-local `worker_case.py` uses the production IsaacWorker.reset(seed, config) interface. It checks the requested episode, performs two resets on the same worker, and executes 20 hold steps after each reset. Both resets returned timestep 0 and advanced to 20 for the task01 probe. All frozen cases declare Lift2 R5a; the action mapping explicitly rejects any different joint/gripper shape.

The first direct attempt emitted a headless GL interop startup error. A second attempt disabled GL interop through the same environment setting used in the prior host wrapper and completed in 91.2 seconds. The implementer inspected reset0 and second-reset-after20 overhead images; both vessels and the robot are visible with no obvious material fallback. This is a limited view review, not independent/all-camera qualification.

Static USD traversal completed 476 unique scene entries with zero missing entrypoints or resolved file dependencies outside the migrated project. It reported 56 unresolved OmniGlass.mdl search names requiring SDK/runtime classification. This scan does not enumerate all MDL imports or Python/config runtime reads.

`representatives.json` contains 189 grouped cases and reference candidates. Their replay protocols are NOT yet qualified; no full-replay result is asserted.

The two-lane `full_native_queue.py` was launched on the target host. It attempts all 961 cases, with persistent per-case receipts, 20-minute process limits, input fingerprints, and at most one additional attempt for failures not identified as missing-file/import/assertion errors. Its terminal state is FULL_NATIVE_FINISHED_REQUIRES_REVIEW, not global acceptance. Review and representative replay are not automatically implemented by this queue. Full native execution was started before completion of the remaining replay orchestration to use available GPUs; this is a deviation from the initial plan to connect every stage before launching the long queue.

Source and HF contents remain unchanged. Outstanding work: queue failure-injection tests, stricter initial-state/metric-reset comparison, runtime file-access attribution, MDL closure classification, representative replay protocol and runner, source baseline isolation from writes, full log/visual review, and final acceptance/runbook. No general standards change is justified.

The first full-queue launch failed before simulation because the Ray socket path exceeded AF_UNIX's 107-byte limit. The queue now hashes temporary directory labels into a short `/tmp/wi/<hash>` path, and restart only skips successful unchanged cases. The initial failure status and per-attempt logs are preserved. After restart both GPU lanes reached Simulation App Startup Complete and began scene loading. Particle sampling and other warnings remain subject to per-case review; process/receipt success is not engine-error or visual acceptance.

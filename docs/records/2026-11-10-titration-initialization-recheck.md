# Titration initialization recheck

Status: eight controlled repeats completed and log-reviewed; root cause and whole-migration acceptance remain unproven.

Two original native sweep failures are cases 390 (`task_10_titration_experiment/unseen_instruction_9/000`) and 753 (`task_10_titration_experiment/validation_mixed_1/000`). Both failed on their first reset, after Scene.post_initialize and during episode layout recovery/warmup, before any probe action. Invalid PhysX transforms spread through the Lift2 articulation; the first observation contained non-finite joints/gripper values and was rejected. They did not fail specifically on the second reset.

The target configuration, episode metadata and scene entrypoint hashes equal the old-source files; configuration and metadata also equal the frozen audit inventory. Other original cases sharing these scene entrypoints completed native checks (1/2 and 3/4 cases respectively), but they are not identical-state repeats and cannot independently establish intermittency.

Repeat protocol: two original cases on their original GPU assignment in parallel, both with GPU assignments swapped, then each case alone on GPU 0 and GPU 1. Total eight fresh-process runs, each with its own Ray/Kit cache paths and the same production worker reset interface; each run performs two resets and 20 hold steps after each reset. No scene, physics, input metadata or task logic changes. Shared SDK/driver caches and the installed runtime remain present; this is not strict host isolation or hardware cold boot.

Scripts and private evidence reside in `/cpfs/shared/wet_op_bench/_operations/independence_20261108`: `diagnose_titration.py`, `titration_diagnosis.json`, `titration_input_identity.json` and per-attempt logs/receipts. `summarize_titration.py` requires all eight results and checks startup/driver plus worker logs, retaining warnings separately from errors and invalid transforms. Original full-sweep results are not overwritten.

Standards: VAL-001/002/003/004/008. No general rule changes: a successful rerun establishes non-reproduction within its conditions, not a causal fix, universal simulator stability, or complete task success. Remaining migration acceptance work is separate.

## Result

All eight runs passed the short native recheck: both initial and same-worker second resets returned valid observations and advanced from timestep 0 to 20. Full driver/startup plus worker logs showed no error-level messages, invalid PhysX transforms, assertion failures or tracebacks after excluding identifiable stderr progress bars. Warnings remain (102 matched warning lines per trial across the inspected logs, potentially duplicated between log sinks); this is not a warning-free claim.

Each failed case passed four fresh-process trials covering both physical GPUs, parallel runs and single-card controls. The observed original failures are therefore intermittent across these executions; no stable GPU-specific or concurrency-specific trigger was observed. This does not identify whether the cause is PhysX internals, scene constraints/contact conditioning, or initialization order. No physics or scene parameter was changed, and original failure receipts remain intact.

The implementer inspected each case's original-GPU repeat overhead image after the second reset and 20 hold steps (`diag390.jpg`, `diag753.jpg` in the local task artifacts). The robot and apparatus are visible without obvious exploded/missing robot geometry. This was not an independent or complete multi-camera visual review.

A separate full-sweep log scan covered 961 cases and found error-pattern matches in 515 cases, including collision rest-offset errors in 477, non-root articulation velocity-setting errors in 365, tracebacks across attempts in 22, and invalid PhysX transforms in the original two failures. Categories overlap; counts do not imply 515 failed native runs. Contact-offset messages account for the scan's OTHER_ERROR grouping. These recurring errors must not be reclassified as harmless/intermittent solely because these two NaN cases passed repeats. Report: `full_native_log_audit.json`.

Final diagnosis receipt: `titration_diagnosis_summary.json` (8/8 short native rechecks passed). Original sweep remains 959 completed / 2 failed, augmented by this separate repeat evidence; no historical results were overwritten.

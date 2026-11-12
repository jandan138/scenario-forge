# Collected-files migration operations

On `genmanip-2gpu`, inspect `/cpfs/shared/wet_op_bench/_operations/collected_20261112/status.json` and driver.log. The locked migrate.py process sequences dependency copying, full hashes, collected copying, link rebasing, analysis increments, media-path checks and analysis regressions. Do not delete sources or overwrite unexpected destination directories.

The independent controller watcher is `external_artifacts/wet_op_collected_20261112/watch_browser.py`; its heartbeat/result is watch_status.json and its log is watch_browser.log. It waits for file/media readiness, launches a loopback target preview and SSH forward, runs browser_audit.cjs, compares all 12 target screenshots with source baselines, copies evidence into the target operations directory and closes its own preview services. A failed watcher must not be treated as successful browser review.

Read delivery_checks.json, analysis_incremental.json and browser_receipt.json. Source-conflict copies are preserved under analysis_source_conflicts; they are not silently merged into the active verified analysis reader. Use the existing migration_v2 analysis configuration. Two historical video browsers keep their original data/content; only the two target-side filesystem links are rebased.

The frozen scope is documented in [the task record](../records/2026-11-12-collected-files-supplemental-migration.md). No training duplication, HF publication, old-source cleanup or evaluation-runtime switching is part of this operation.

For video seeking, use a server supporting HTTP Range requests. The delivered private `range_preview.py` helper binds 127.0.0.1:19542 and serves the new CPFS root. Basic `python -m http.server` can display initial frames yet stall seeking for some files; this is not evidence of a damaged copy. The final browser receipt includes successful actual playback and seek tests for all 12 audited combinations.

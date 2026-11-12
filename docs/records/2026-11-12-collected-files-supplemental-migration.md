# Collected-files supplemental migration

Status: supplemental migration verified; source retained.

The user approved copying collected_files_20261016 plus its two external symlink dependencies, and checking sci_bench_analyse for source increments. No old source is deleted, no running evaluation is switched, no HF content is changed, and the existing training publication copy is retained without another training copy.

Target root: `/cpfs/shared/wet_op_bench`. The collected directory contains 8,236 ordinary files (78,067,488,603 bytes) and two absolute source-side links under task01-14_video_browser. Their dependencies are the historical OpenWAM resume64 run and gpt6_all14_mixed run. Total selected ordinary-file bytes: 182,512,388,029; preflight existing target allocation: 2,196,190,819,840 bytes. None of the three target directory paths existed at preflight.

The target-host process copies dependencies first, verifies inventory and per-file SHA-256, installs them, copies and verifies collected files, then rewrites only the two target-side links as relative references to the installed dependencies. Source link values and target mappings are recorded separately. Analysis increments compare against the original 20261111 snapshot: new/source-only changes are copied, while conflicting source versions are archived in private operations and the verified target reader is preserved.

Private state/scripts: `/cpfs/shared/wet_op_bench/_operations/collected_20261112`. Raw copy uses `_incoming/collected_20261112`. Controller scripts and browser evidence: `external_artifacts/wet_op_collected_20261112/`.

After file transfer, check_delivery.py validates every embedded browser episode video path resolves inside new CPFS, decodes one available video per model per browser, and reruns analysis tests/report generation. A detached controller watcher then renders target pages with the same Playwright 1.62.1 / Chromium revision 1234 used for source baselines. The existing browser installation was reused; no existing browser binary was removed. Preview services bind loopback only and are stopped after checks.

Source baseline automation passed 12 route/viewport/model combinations: both browsers, each model, desktop 1440×1000, tablet 820×1180 and mobile 390×844. The implementer inspected desktop and mobile samples; videos, task lists and metric sections were readable. This is not an independent review. Target checks and screenshot comparison are pending. Pixel-identical target/source screenshots may establish preservation of the reviewed baseline; any difference remains pending visual review rather than automatically accepted.

Final phases are distinct: FILES_VERIFIED_BROWSER_REVIEW_PENDING versus COLLECTED_MIGRATION_VERIFIED. The latter requires target browser functional checks and exact screenshot equivalence to the reviewed source baseline; conflicts in analysis increments remain recorded, not overwritten. No claim is made that a copied source can never receive future writes.

Standards: VAL-002/003/005/006 and maintenance workflow. No generic rules, simulator physics, package contracts, or benchmark metrics changed. Script compilation and node syntax checks passed. This supplemental copy does not close the separate old/new simulator behavior-equivalence work.


## Final checks

All three payload directories were installed after inventory/SHA-256 validation: 90,497,346,051 bytes for the OpenWAM dependency, 13,947,553,375 bytes for the GPT dependency and 78,067,488,603 bytes for the collected directory. Analysis increment inspection found no new source changes to apply. Both historical browsers resolve all 1,500 episode video paths inside new CPFS; per-model video samples and analysis regressions/report generation passed.

All 12 target browser route/viewport/model combinations passed functional loading checks. Six screenshots were pixel-identical to source, while six differed in only approximately 0.01–0.06% of pixels confined to the video/player region. The implementer inspected target desktop/mobile samples and the later playback capture; no migration-related page/content defect was observed. The original pixel differences remain preserved in the evidence.

An additional actual-playback/seek test initially timed out using Python's basic HTTP preview. A Range-capable loopback preview resolved that test-server limitation: all 12 combinations played beyond 0.3 seconds and successfully sought to 1 second, with valid video dimensions and no page errors. The video and HTML payloads were not modified. range_preview.py is retained as a usable private preview helper; preview services and SSH forwards started for verification were stopped.

Final state: COLLECTED_MIGRATION_VERIFIED, with BROWSER_PLAYBACK_AND_VISUAL_REVIEW_PASSED. Acceptance followed explicit playback and visual review rather than declaring non-identical screenshots identical. No claim of exhaustive human review of every video or independent reviewer qualification is made.

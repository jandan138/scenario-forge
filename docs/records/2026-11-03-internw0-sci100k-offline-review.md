> Superseded delivery and findings: see [the physics / USD v2 review](2026-11-03-internw0-physics-usd-v2-review.md). The user rejected the two liquid candidates; six operation-failure examples are outside the review scope. The former HTML is retained only under the v2 revision’s `history/withdrawn_v1/` directory. The body below is the historical v1 record.

# InternW0 scientific evaluation: offline video review

## Delivery

Batch: `internw0_sci100k_sim40ebb0_20261031T181626Z`.

- Single-file HTML (sole delivery path): `/mnt/data/zhuzihou/GenManip-Sim/saved/reviews/scientific_experiments/internw0_sci100k_sim40ebb0_20261031T181626Z/download/internw0_review_selfcontained.html`.
- Size: **165,128,231 bytes**.
- SHA-256: `a4119ec629b2085bf0969c46fa5af0d221a82a8a6d51cef37a43fb64161510e9`.

The HTML embeds all 680 original result JSON records, 9 complete original
videos from 8 selected episodes, 26 issue evidence images, and 560 episode
overview images. Embedded videos retain the source bytes; none were transcoded.
Unselected videos are not embedded. Their source paths and review scope remain
in the coverage table. The report needs only the HTML file when opened offline.

The earlier report records were located in
[the OpenWAM review](2026-10-23-openwam-offline-video-review.md) and
[the pi05 review](2026-10-26-pi05-data20261020-offline-review.md).
Their report layout and offline player were reused; their findings and
user-confirmed issue assertions were not transferred to this batch.

## Source and actual review coverage

The matching batch was found directly in mounted storage, without SSH or an
OSS download:

`/mnt/data/chenjiantong/GenManip-Sim/saved/eval_results/scientific_experiments/internw0_sci100k_sim40ebb0_20261031T181626Z`.

There are 20 tasks: T01–T14 have 40 episodes each and z1–z6 have 20 each.
All 2,720 camera files were present and nonempty. The 680 main-view videos
contain 2,656,066 decoded frames and total 24.593268 hours. All main-view video
and result JSON hashes were checked against the inventory and copied scores.
All 680 score arithmetic checks passed; this does not establish semantic
correctness of the evaluator.

Every episode received visual screening. **152 episodes have complete 1fps
timeline review records; the other 528 were screened at eight uniform time
points including the first and last frames.** The full 3,112-page 1fps atlas
was generated, but it was not all visually inspected. Partial timeline pages
and exact sampled frame indices are recorded per episode. The existing,
source-bound 40-episode T03 review was retained; the current assistant performed
the additional screening and candidate review without delegated reviewers.

Candidates were checked with source-resolution frames, selected other views,
complete 1fps timelines for the retained representative episodes, and selected
31-frame native-rate intervals. Main-view screening does not establish full
four-camera semantic review. Video seconds are not simulation seconds.

## Findings and evidence boundaries

Two liquid appearance candidates remain **suspected**: persistent outward
liquid geometry near a measuring cylinder mouth in z1/mixed_1, and persistent
upward splash-shaped transparent geometry in z3/mixed_2. Neither is presented
as a confirmed solver failure or a root-cause diagnosis.

Six visible operation failure/stall examples are separately categorized:
off-target pouring in T02/mixed_3, failed weighing-boat placement followed by
bare-pan dosing in T14/mixed_4, unfinished oven closure in T08/mixed_10,
unfinished centrifuge closure in T07/mixed_1, prolonged lack of progress in
z2/mixed_10, and prolonged manipulation near the left container without
evaporation-dish placement in z6/mixed_14. These are not counted as physics
faults. Selected-example counts are not incidence estimates.

Closer views did not support the proposed synchronous recoloring of spilled
liquid in T13/unseen_prospect_8. Early frames also disproved the initial
"no action throughout despite partial credit" interpretation for the selected
T12 and z4 candidates. These rejected interpretations are documented in the
report and `rejected_candidates.json` rather than registered as faults.

No semantic mis-scoring was confirmed. Final JSON records lack stage-trigger
frames, and no original abnormal-termination logs were obtained for this batch.
The report does not invent runtime failures from current source code or robot
state thresholds. Transparent materials, camera framing, occlusion, and sparse
screening limit detection of brief events.

## Reproduction and acceptance

The review root is the canonical HTML's parent directory's parent. It contains
`inventory.json`, `scan_summary.json`, `reviewer/`, `evidence/`, `coverage.csv`,
`issues.json`, `SOURCE_VERIFICATION.json`, `PAYLOAD_VALIDATION.json`,
`SELFCONTAINED_MANIFEST.json`, and `browser_selfcontained/audit.json`.
Rebuild with `python tools/build_report.py --final` from that root, with the
recorded source videos available. Verify with `python tools/verify_payload.py`
and `python tools/audit_selfcontained.py`.

The final browser audit copies only the HTML into an isolated directory and
disables network access. Chromium verified all nine embedded videos: metadata,
issue-time seeking, advancing playback, and end seeking. All 26 issue images
and 560 overview images decoded. Score/image dialogs, search, task/status/type
filters, and issue navigation passed. Desktop 1440×1000, tablet 768×1024, and
mobile 390×844 screenshots cover the header, issue cards, coverage table, and
player. Long metric JSON was compacted in cards while keeping the original
JSON dialog; the coverage table scrolls horizontally on narrow screens.
There were no external requests or JavaScript errors. Audit hashes bind the
checks to the delivered HTML. Browser processes started by the audit exit.

`make check` passed: **1,255 tests passed, 1 skipped**, lint, package smoke,
Phase 10.x smoke, and whitespace validation. No package/schema/adapter behavior
changed, so no new package test was introduced. Media payload checks directly
compare decoded embedded bytes and scores to their sources.

## Duplicate-copy cleanup

The user selected cleanup of duplicate copies while retaining the existing
personal review directory. Delivery files, shortcut copies, and symlinks must
not be created directly under `/mnt/data`. The personal-directory HTML above
is the sole delivery entry. The delivery manifest and local README now use it.

The root-level duplicate and three explicitly inventoried isolated-browser
HTML copies were removed: **4 files, 660,512,360 logical bytes**. Their recorded
allocated file blocks totaled **660,529,152 bytes**. The three temporary
directories were removed only after becoming empty. Each file was checked for
identity, size, SHA-256, single-link ownership, stability, and open readers;
the two older audit copies were matched to their recorded older HTML hash.
Shared-filesystem free-space observations are kept separately and are not used
to attribute unrelated storage changes to this cleanup.

The canonical HTML's bytes and SHA-256 remain unchanged. Source videos, scores,
evidence images, scan data, intermediate products, and browser caches were
retained. Prior delivery metadata and browser audit evidence were preserved
under the review's `browser_selfcontained/history/` directory.

The browser audit previously leaked its isolated HTML when browser startup
failed; a controlled failure reproduced this before the fix. Its lifecycle
now removes the owned temporary HTML and empty directory on successful audit,
partial-copy failure, browser startup failure, and failure after browser start.
Unexpected extra files prevent recursive removal and are reported. Browser
process termination and log closure remain protected by `finally` blocks.

`tools/check_audit_cleanup.py` exercises the three failure paths, including a
real Chromium process for the post-start failure; all passed without temporary
HTML or a live owned browser process remaining. The complete offline browser
audit was rerun successfully against the unchanged canonical HTML. Per-run
cleanup receipts and failure diagnostics remain in `browser_selfcontained/`.
`CLEANUP_RECEIPT.json` records exact removed paths, hashes, byte counts, and
verification results; `REVIEW_PROVENANCE.json` binds the updated files.
The cleanup uses targeted external-tool checks; the earlier core `make check`
result above is retained rather than represented as a new test run.

## Repository and standards scope

The HTML, source media, review tools, and large evidence stay outside the repo.
Only this dated evidence record is added here. No runner, model adapter,
leaderboard, or reporting package is introduced into Scenario Forge.

The validation/delivery guidance and maintenance workflow were consulted;
VAL-001/002/003/004/005/007 are applied within this recorded-video evidence
scope. No scene, asset, task state, scoring contract, or simulator runtime was
changed or revalidated. Therefore no general scene-authoring rule or design
contract changes, and no standards/runbook synchronization is required beyond
this evidence record. Historical task packages remain unchanged.

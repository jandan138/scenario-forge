# InternW0 physics / USD review v2

This record supersedes the current delivery and finding assertions in the
[earlier InternW0 review](2026-11-03-internw0-sci100k-offline-review.md).
The user clarified that this review covers physical abnormalities and USD/asset
errors. Policy performance and operation failures are outside its scope.
The two former liquid candidates were rejected by the user and withdrawn;
the six operation-failure examples were removed from the active finding list.
The previous HTML is retained once as an explicitly withdrawn historical file.

The scope follows the earlier
[OpenWAM](2026-10-23-openwam-offline-video-review.md) and
[pi05](2026-10-26-pi05-data20261020-offline-review.md) reviews. Their findings
are not transferred to this batch. Falling, tipping, spilling, transparent
outlines, unsuccessful grasps, and stalls do not alone establish a physics or
USD defect. A visible anomaly would not by itself establish its USD root cause.

## Delivery

Accepted single-file HTML:

`/mnt/data/zhuzihou/GenManip-Sim/saved/reviews/scientific_experiments/internw0_sci100k_sim40ebb0_20261031T181626Z/revisions/physics_usd_v2/download/internw0_physics_usd_review_selfcontained.html`.

- Size: **1,059,948 bytes**.
- SHA-256: `ef08ce4e5776560f35ce25608714a5c25034764881dd8ff267c665277e2a8817`.
- Coverage: **680/680 episodes, 3,112/3,112 timeline pages**.
- Valid findings: **0 physics, 0 USD/asset errors** within the recorded scope.
- The prior two liquid candidates remain withdrawn; operation failures are excluded.

Revision root:

`/mnt/data/zhuzihou/GenManip-Sim/saved/reviews/scientific_experiments/internw0_sci100k_sim40ebb0_20261031T181626Z/revisions/physics_usd_v2`.

The sole current HTML belongs in that revision's `download/` directory.
No delivery copy, shortcut, or symlink is created directly under `/mnt/data`.
The parent review README and delivery metadata point to the revision. Former
metadata and the single withdrawn HTML remain under `history/withdrawn_v1/`.
Source media, full timeline atlases, and review tools stay outside this repo.

## Evidence and coverage

The batch is directly available in mounted storage at
`/mnt/data/chenjiantong/GenManip-Sim/saved/eval_results/scientific_experiments/internw0_sci100k_sim40ebb0_20261031T181626Z`.
No SSH transfer or OSS download was needed. There are 680 episodes in 20 tasks
and 2,720 camera files. The main-camera videos contain 2,656,066 decoded frames
and total 24.593268 hours. Original main-video and result JSON SHA-256 hashes
were recomputed and matched to the frozen inventory. Auxiliary cameras were
checked for existence and byte counts, with selected views visually examined.

The review retains source-bound complete timeline records for 152 episodes /
397 pages and completes the other 528 episodes / 2,715 pages through the
user-authorized parallel review. The coverage unit is each episode's full
1fps timeline plus its last frame. Previously generated pages or eight-point
overviews are not counted as visual review. The coverage gate compares the
exact expected and viewed page sets per episode, rejects duplicate episode
records, and stops the builder on incomplete coverage. Its incomplete state
was exercised before final assembly.

The final ownership map is `assignments/FINAL_OWNERSHIP.json`; initial manifests
are planning history. The final reviewer records are:

| Reviewer | Episodes | Pages | Records |
| --- | ---: | ---: | --- |
| Retained complete timelines | 152 | 397 | `baseline/retained_full_timeline_reviews.json` |
| Primary: T10, remaining T14, last 13 T07 episodes | 92 | 358 | `primary.json`, `primary_t14.json`, `primary_t07_tail.json` |
| A: remaining T02, T04, T06, completed T07 prefix | 107 | 504 | `agent_a.json` |
| B: T08, T09, T11, z5, z6, remaining z2, z4, first 14 T07 tail episodes | 211 | 1,089 | `agent_b.json`, `agent_b_extra.json`, `agent_b_z4.json`, `agent_b_t07_tail.json` |
| C: T12, T13, remaining z1 and z3 | 118 | 764 | `agent_c.json`, `agent_c_extra.json` |
| Total | 680 | 3,112 | `COVERAGE_VALIDATION.json` |

All new reviewer records are under the revision's `reviewer/` directory.
A's checkpoint also retains four partial T07 pages; B independently reviews
those pages within the reassigned complete episodes. They are counted only
once in the complete-episode coverage totals above.
Three gripper-state threshold flags in T10/mixed_1 were checked using selected
native-frame neighborhoods in all four views: indices 14, 1422, and 1530,
offsets -5, -3, -1, 0, 1, 3, 5, and 8. The 12 contact sheets did not support
registration of joint divergence, component separation, or penetration.
`state_flag_review.json` records those observations and their limits.

## Verification and limits

Reproduction commands, run from the revision directory:

```sh
python tools/verify_sources.py
python tools/build_report.py
python tools/verify_payload.py
python tools/check_audit_cleanup.py
python tools/audit_selfcontained.py
```

The checks bind coverage, payload, and browser acceptance to the delivered
HTML SHA-256. Payload validation compares all 680 embedded raw result records
with their originals and decodes all 20 task-index images. Result scores are
preserved as source records; score semantics are outside this review.
With no valid findings, there are no embedded problem videos. Task-index
images identify scenes and are not substitutes for the timeline review ledger.

The browser check copies only the HTML into an isolated temporary directory,
disables networking, and exercises task navigation, filtering, search,
empty results, reset, and source/raw-result dialogs. It captures header,
findings, task index, coverage, limits, and dialog states at 1440×1000,
768×1024, and 390×844. Separate failure injection checks cover partial-copy,
browser-startup, and post-start failure cleanup. Browser processes and owned
temporary HTML copies must be gone after each run. Persistent browser binaries
and source media are retained.

All five commands passed. The final offline browser audit reported 20 decoded
images, no external requests, no JavaScript errors, and no document overflow
at all three sizes. All 18 final screenshots were actually inspected with
`view_image`; there were no blocking visual defects. Narrow-screen statistic
wrapping and the mobile dialog close button were adjusted, then the HTML,
payload check, browser audit, and screenshot inspection were repeated.
`audit/visual_acceptance.json` records the final screenshot hashes.
The three cleanup failure cases passed and the successful final audit's
temporary directory was removed. `DELIVERY.json` is accepted;
`RETRACTIONS.json` points to the accepted replacement. Parent current-entry
metadata now contains an empty active finding list and points to v2.

Full 1fps timeline coverage is not visual inspection of every native frame or
every auxiliary camera. Brief contacts and occluded events may be missed.
The historical run's bound USD snapshot, contact truth, and abnormal-termination
logs were unavailable. No simulator was run and no source asset, task state,
score, or video was changed. An empty finding list is not a certification that
all assets and runtime physics are correct.

This change adds only dated evidence documentation to Scenario Forge; it adds
no runner, model adapter, leaderboard, or benchmark reporting package.
Core package/schema/adapter behavior is unchanged, so v2 validation uses the
external report checks and documentation whitespace checks. The earlier
record's `make check` result belongs to that earlier work and is not reported
as a new v2 test run.

## Standards and synchronization

The standards entry, validation/delivery topic, and maintenance workflow were
consulted. Repository baseline HEAD is
`4f1b6a69c711773119fd5870c47e8093a1d105b7`; the existing dirty standards
working files are not represented as a clean released standards version.
VAL-001/002/003/004/005/007 apply within this recorded-video evidence scope;
VAL-006's historical/current distinction is preserved by the withdrawn archive
and this new record. No scene, asset, runtime, or core contract is changed or
revalidated. **规范无需变更**: no general scene-authoring rule changed.
The synchronized items are the external report, current delivery metadata,
scope/retraction records, rebuild guidance, provenance, this dated record, and
an explicit supersession notice on the old record. The old body remains
historical evidence rather than being silently rewritten.

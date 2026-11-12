# Task12 / task18 integrated candidate progress

This is an intermediate evidence record, not acceptance or deployment. The
external work root `R` is
`/cpfs/user/zhuzihou/dev/scientific-round2-repair-20261026/bath/repair_20261028`.
Times below retain the actual UTC receipts; their Beijing calendar date is
October 29. Earlier trials and rejected candidates remain in the
[October 28 record](2026-10-28-task12-task18-repair-reopened.md).

## Current decision: C1 rejected after a new counterexample

The first integrated cold candidate/reference pair exposed a physical failure
in C1 that the earlier pilot runs did not. Candidate commands/timebase and input
hashes pass, and the native result remains 7,000 steps / score 0.15 / SR 0.
Normal demonstration successes below remain scoped historical evidence; they
do not override this failure or earn final credit for a later physics version.

The main implementer independently checked particles 203, 256, 590 and 617:
their actual 1371–1372 source-relative endpoints move from the liquid cavity
to the exterior, with intersections through both actual glass surfaces. This
is stronger than a coarse side/rim label or temporary entry into glass. The
bound source-mesh witnesses are in
`R/control/root_four_source_outer_exit_counterexamples_20261029.json`.
The investigator's complete path review identifies 62 of the 67 coarse
nonmouth cases with confirmed source outer-surface exits; particle 359 passes
through the outer rounded bottom at 1453–1454. These remain source-geometry
native-tick witnesses, not cooked-force or hidden-substep certificates.

The tube's final negative Z is not independently evidence of table tunneling.
The dense trajectory contains steps 1417–1420 with the entire tube beyond the
front table edge, followed by falling below the slab; no sampled glass vertices
entered the source slab. The initial release also has an upward COM proxy
excursion, so later falling does not alone establish normality of that earlier
motion. Exact particle/pose/contact evidence and limits remain in
`integration/c1_final_queue_v1/coldpilot_candidate_exit_paths_v2.json`.

Further C1 normal cold jobs, the larger paired matrix and the 39-entry
initialization batch are paused at the queue level while repair continues.
Completed/active runs are retained. The new work isolates rounded-bottom
containment: the tube's authored SDF band/margin remain 0.00035 despite resolution
512; the existing beaker precision fix did not modify those values. A separate
calibrated source SDF query and a fresh private dynamic candidate are being
prepared. These values are intentional historical authoring, not a newly
asserted unit error. No new parameter is adopted without containment validation.

## Frozen candidate and first normal cold runs

Integrated C1 retains the original geometry, offsets, particle counts, 120 Hz,
reaction times and native metric. Its five scalar changes from the frozen base
are sample mass 6 g, bath mass multiplied by 0.9, beaker body SDF resolution
512, narrow band 0.05, and bath isosurface grid spacing 0.0033 m. The last is a
surface-rendering setting. The verified script lifecycle guard is integrated
separately; it is not a physics or scoring change.

The first instrumented cold runs have completed with native score 1 / SR 1:

| Task / independent validation case | Executed commands | Sample / bath minimum retention | Released rack support |
|---|---:|---|---|
| Phi `aligned_return_seen1_20261028` | 3,582 | 100% / 100% | 95 steps after release; maximum displacement 0.031529 mm |
| Phi `aligned_return_seen10_20261028` | 3,322 | 100% / 99.4397% | 96 steps after release; maximum displacement 0.017396 mm |
| Phi `aligned_return_seen4_20261029` | 3,062 | 99.7833% / 100% | 90 steps after release; maximum displacement 0.035545 mm |
| Silver `aligned_return_silver_20261028` | 5,742 | 100% / 100% | 105 steps after release; maximum displacement 0.067340 mm |

The Silver run executed 5,722 exact source commands and 20 explicitly derived
tail commands; do not relabel its executed length as 5,722. These runs have
same-tick particle observations, no observed exterior wall/bottom exits, no
bath body-core intrusion, complete four-camera decoding and zero error-level
engine log findings in the recorded full-log scope. Warnings remain recorded.
The corresponding `cold1_qualification.json` files are under
`R/normal_final_20261029/<case>/`.

The main implementer independently inspected sampled rack-return images. Silver
frames 5555–5630 show approach/seating; 5639–5741 show open fingers retreating
while the tube remains upright. This independent review covers that sampled
window, not every frame or the entire visible reaction. Its source hashes and
limits are in `R/control/root_silver_cold1_return_review_20261029.json`.
The final ledger contains provisional candidate evidence only: one cold run
does not satisfy three layouts or three cold runs per layout.

Phi seen1 subsequently passed a second independent cold run. Silver mixed5's
original normal action received native score 1 at deposition 0.9641, consistent
with its unchanged metadata threshold `progress_thre=0.95`; it was rejected for
the stronger complete-reaction goal. A separately named version inserts 360
native stable-held commands (three seconds) after source command 2,000 and
preserves all original action segments. Its first run completes the original
36.785358-second reaction and returns successfully. These later receipts are
also limited to the now-rejected C1 version and do not establish final delivery.

Phi seen10 has 13 of 2,320 bath particles first leaving through the opening
during withdrawal, with six outside the inner profile at termination. All six
trace to those mouth events; the reviewed 2908–2918 source-mesh window has no
segment hits, solid membership or ambiguity. This is bounded mouth splash,
not zero loss. The root review also preserves 209 root-path `xformOpOrder`
warnings among 276 warnings; their cause is not established and they are not
silently declared harmless. See
`R/control/root_phi_seen10_cold1_review_20261029_v2.json`.

Accepted source reports are copied into SHA-addressed immutable files under
`R/control/qualification_snapshots/` before ledger binding. The first seen10
report received warning links after initial binding; its original binding and
the explicit refresh remain recorded. This requires evidence binding refresh,
not a physical rerun. Further supplements use separate review versions.

Other layouts and paired reported cases remain under execution and review.
Small apparent liquid departures must be classified from the same particle's
first exit and actual source geometry; a later radial position does not prove
a wall leak. Confirmed exterior leaks remain blockers.

## Lifecycle and evidence presentation

Native short natural-done task switches have run; positive-reaction reset
validation is a separate full first-task execution followed by native successor
tasks. Known SDK null-database cleanup diagnostics and an absent `/Camera`
deletion diagnostic remain preserved and narrowly classified. Neither short
switch success nor this classification establishes error-free platform cleanup,
full physical regression, or repair of robot ejection.

The immutable self-contained report draft is
`R/reviews/final_delivery_draft_20261029/snapshot_20261028T181651Z/waterbath_silver_candidate_selfcontained.html`.
Its SHA-256 is
`9566ab362d643f53b71016dc3166ec0f7524f6a31949713737e61baeff8129c6`.
Six embedded video clips passed full decoding and source binding checks. The
report implementer exercised 30 playback/seek cases across five browser widths;
the main implementer independently inspected the desktop normal section.
This proves presentation within those scopes. It does not qualify the candidate,
and its Silver capability example predates the newer cold1 result above. Refresh
to a new immutable version rather than overwrite this reviewed snapshot.

## Personal repository staging

The 392-file, 1,244,900,780-byte frozen asset closure has been copied and checked
by SHA-256 into:

```text
/mnt/data/zhuzihou/GenManip-Sim/tmp/deliveries/task12-task18-c1-20261029-candidate-not-ready/
```

All runtime files currently sit under `payload/saved/assets/scene_usds/` in the
two task trees. `asset_staging_manifest.json` binds every copied file to the
frozen source. No live `saved/` or `configs/` installation was overwritten.
Normal YAML/task data, remaining qualification, full-package rollback inventory
and final ZIP are still pending. This directory explicitly remains NOT_READY; it is not an
accepted delivery and must not be installed as one. No core, SDK, public robot,
metric, LeRobot, colleague repository, Feishu or remote Git changes were made.

The asset rollback subset is now prepared separately: comparison against frozen
base `f67879b5` finds 40 replaced scene roots and 352 unchanged dependency files,
with no new paths in that baseline comparison. The 40 original roots are in
`R/integration/c1_asset_rollback_preparation_20261029/`, with a matching private
copy under the candidate's `rollback_assets/`. The rollback ZIP passed CRC and
actual extraction/SHA checks for all 40 files; its SHA-256 is
`faae89e8243291796b4e809e50b495690f7be4dff6e05f0d11aca2d52733d78e`.
This is an asset inverse against that stated frozen base, not a backup of any
newer colleague worktree or a completed rollback for future YAML/task data.
Nothing has been installed or rolled back live.

## Complete initialization coverage preparation

`R/integration/c1_all40_init_preparation_20261029` binds 30 original task
YAML/metadata/action sources and ten Silver stock seen-stage entries without
borrowed task metadata. Static source and payload checks plus 15 external CPU
contract tests pass. The strengthened private source-stage helper records live
composed USD parameters, 30 measured native ticks, finite particle/rigid state,
two nonblank evidence images and the complete startup-to-close raw log. It has
not yet earned GPU runtime qualification. Its guard check establishes the graph
prim and embedded-source identity, not successful graph execution or reaction.
The initial GPU allocation remains inactive until the current task releases it.

The diagnostic source-stage tool subsequently completed a real single-pilot
check, with its scope kept separate from C1 qualification. Initial attempts
exposed an SDK import-warning classification, a checkpoint lost after default
fast shutdown, and a crash when forcing graceful SDK unload. Each failed attempt
remains recorded. The final tool saves its simulation checkpoint before the
supported default fast shutdown; an external controller independently verifies
actual process exit, GPU release and the complete raw log. A missing Pillow
dependency in an earlier controller was corrected by offline verification of
retained data, without rerunning that simulation or rewriting its rejection.

The camera diagnosis also found that the composed stage uses meters, while its
new evidence camera retained the default near clip of 1. The beaker center is
only 0.816815 meters away along the camera direction, so a nonblank room image
hid the target apparatus. The v6 pilot changes only the private evidence camera
to near/far 0.01/100 and uses a CPU interpreter with verified image dependencies.
Its actual first/last images show the beaker and stirrer; 30 native ticks, 31
finite-state samples and independent exit-0/NVML-empty process closure pass.
The full log has zero hard findings and 37 retained warnings. Root evidence is
`R/control/source_init_postprocess_reviews/seen1_v6_attempt5_visual_and_tool_review.json`.
This qualifies the diagnostic tool/camera protocol only. C1 remains rejected
and the 39-entry batch remains on hold pending a new physical candidate.

An API-reading correction is also preserved explicitly:
`R/control/root_physics_schema_metadata_correction_20261029.json`. Local usd-core
without PhysxSchema filters unknown APIs from `GetAppliedSchemas`; raw
`apiSchemas` confirms the original Physx APIs on table, tube and glass. The
earlier omission in that local view is not missing authoring and must not become
a repair variable. Existing USD-008 already covers this distinction. The actual
source-mesh outer-leak witnesses are unaffected.

## Standards and remaining work

Applicable rules are MAT-001/003, USD-008/009 and
VAL-001/002/003/004/005/006/008. The camera evidence adds the scoped USD-009
recommendation to check target visibility and clipping in stage units; its
particular clipping values are not defaults. No design contract, schema or
package API changed. Physical measurements remain task-specific. Operations guidance is synchronized
with the evidence locations. Documentation UTF-8, final newline and trailing
whitespace checks apply; they do not replace runtime acceptance.

Repository `make check` completed successfully after the integration documentation
work: 1,255 tests passed, one skipped, Ruff and package/Phase 10.x smoke passed,
and `git diff --check` passed. The exact log is
`R/control/make_check_integration_20261029.log`; external initializer tests are
separate from those repository tests. Later documentation-only supplements are
checked directly without relabeling this run as new simulator evidence.

The full goal remains open: six normal layouts with three cold successes each,
14 reported cases with their required paired repetitions, 30 original task-mapped
and ten stock source-stage initializations, real task switches, plain receiver
validation, final closure/hash/rollback/package and final self-contained evidence.
The [OSS backup record](2026-10-29-scientific-experiment-oss-backup.md) separately
documents additive backup and actual recovery; backup does not alter task scores
or release readiness.

## Follow-up: velocity control rejected; isolated tube-band trial

The SampleSystem-only maxVelocity 3→6 candidate passed three independent
70-second static probes and the 33-second controlled motion, but failed the
exact first 2,000 original mixed-6 commands. Particle 669 crosses the actual
closed-bottom triangle 303 at 1441–1442; its entire earlier recorded history
never approaches the mouth. The velocity change is therefore rejected, with
no full-7,000-step or final-delivery credit. The certificate and original
partial-run termination/media scope are bound by
`R/c1_sample_vmax6_guard_iso33_v1/experiment_result_20261029_v1.json`.

An isolated calibrated tube SDF query has also completed in the target Isaac
4.1 runtime. Original raw author APIs and explicit API application give
identical results. Expanding only the fine band improves the four observed
1371 cavity-point distance errors; it neither proves dynamic containment nor
fixes every material-midpoint approximation. Query limits remain in
`R/control/tube_bottom_sdf_query_20261029/review_v1.json`.

The next independent candidate is
`R/tube_band05_guard_iso33_v1`: only Tube GlassShell narrow-band thickness
changes from 0.00035 to 0.05. Sample maxVelocity remains 3, margin remains
0.00035, resolution remains 512, and all other C1 properties/APIs remain
unchanged. Three cold static probes complete 8,400 native 120-Hz ticks each
with both liquids retained. The main implementer separately checks the live
parameter readbacks, per-tick envelope records and one actual final image;
`R/control/root_tube_band05_static_review_20261029.json` records that scope.
Controlled motion is running; original-command and complete acceptance
remain pending. This is a single-attribute hypothesis test, not a new
general SDF default or a claim that the physical problem is solved.

The user subsequently explicitly authorized deleting already OSS-verified
local evidence. That instruction supersedes the earlier backup-only preference
for those files. Deletion uses per-file archive/SHA and runtime-input protection;
original receipts and recovery locators remain. Current factual counts live in
`R/archive_oss/local_eviction/`, not in the earlier no-deletion snapshots.

## T1 follow-up at 09:50 UTC: normal success and paired regression

The tube-band candidate has now passed the controlled-motion gate and three
full original-command pilots. These are candidate results, not release approval.
The first formal mixed-6 reference/candidate pair also completed 7,000 commands
on the same physical GPU: actual score/SR is 0.15/0 and 0.85/0 respectively.
Neither result is task success. The reference loses sample particles through
the opening; the candidate retains both liquids in this repetition. The pair
compares five physical scalar changes together and does not isolate causality
to tube-band thickness. The other 27 pairs remain pending at this checkpoint.

Normal demonstrations make separate progress: Phi seen1 now has three
instrumented cold successes. Phi seen10, Silver unseen6 and the explicitly
adapted Silver mixed5 hold360 each have one. Their original reaction durations
are retained; native SR/score is 1/1 and actual fingers release after rack
support. Small opening splashes are retained in the evidence: one sample
particle in Phi seen1 cold3 and 21 bath particles in Phi seen10 cold1 have
opening-origin paths. Their bound follow-up audits do not find actual source
glass-wall crossings. This is not a zero-loss claim. The main implementer's
additional receipt/hash/threshold and sampled visual review is
`R/control/root_T1_three_more_qualification_bindings_20261029.json`;
the earlier Silver unseen6 review remains separately bound. Other layouts,
remaining cold repetitions and task18 plain-receiver compatibility are pending.
The plain Phi seen1 run does not supply quantitative particle-retention credit.

All 40 T1 initializer entries have CPU preparation/readback in the actual
Isaac 4.1 USD version: 30 original task mappings and ten stock source stages
without borrowed task metadata. The independent scope check is
`R/control/root_T1_init40_cpu_preparation_review_20261029.json`.
There is still no GPU-initialization credit for these 40 entries. The new
normal and matrix lanes do not authorize silent scene substitution or removal
of the three reported rigid-contact checks.

The final ledger keeps `selected_physics` unset and delivery NOT_READY.
No runtime core, SDK, public robot, Chen directory, Feishu document or LeRobot
dataset changes are made by this checkpoint. Standards need no further change:
these are additional source-bound results within MAT-001/003 and VAL-001/002/003/004/008,
not general PBD or SDF parameter recommendations.

At 10:00 UTC, Phi seen4 cold1 also completes 3,062 commands with SR/score 1/1,
the full original 19.476356506347656-second reaction, both liquids retained and
90 ticks after release. Its binding review is
`R/control/root_T1_seen4_qualification_bindings_20261029.json`.
This brings the scoped T1 quantitative normal count to seven of 18; the third
Silver layout and further cold repetitions remain active. Actual remote NVML
now identifies workers on all four GPUs: matrix on 0/3, normal on 1/2.
These process observations are a dated snapshot, not future liveness proof.

At 11:27 UTC, quantitative normal qualifications reach 12/18; the additional
receipt identities are bound in `R/control/root_T1_progress_20261029T1127.json`.
Five of the 56 matrix jobs have formal reviews. Both mixed-6 repetitions are
complete: reference/candidate scores are 0.15/0.85 in repeat one and 0.85/0.85
in repeat two, with SR0 throughout. The second reference also retains both
liquids. This reference variation must remain visible and prevents interpreting
the first pair as a deterministic causal repair. The UI1 reference separately
has confirmed source-mesh closed-wall sample exits; its candidate is finishing
native export and still awaits full boundary and original-issue review.

## T1 rejected: confirmed bath-floor escape

The UI1 candidate review subsequently confirms Bath particles 83/373 crossing
the source inner floor at native535–536, remaining inside the 3 mm solid floor
for nine sampled ticks, then crossing the outer floor at544–545. The endpoints
later lie outside the cup body. Source winding, enabled collision inventory,
unit scale and native/USD/DC owner transforms were checked; this is not merely
an inner-profile or near-mouth label. The original native result remains
7,000 steps, score0.85/SR0. The hard proof SHA is
`5f8445217dc653b06ea7b20ca55805b75dbb47d1cf4f5e0c13c5f9f3f3762ed8`,
located by `T/matrix56_batch_case_lanes_v1/GLOBAL_T1_STOP.json`, with
`T = R/tube_band05_guard_iso33_v1`. T1 is rejected for release.

The normal collection eventually completes18/18 scoped successes, separately
bound by `T/normal18_completion_v1.json`; those results remain valid only for
their own trajectories. Matrix execution ends at7/56 full native runs and five
formal ordinary/reference-negative reviews. Initializer work reaches21/40
scoped acceptances, without reaction or global-containment credit.

Root's14:23UTC audit finds all four GPUs empty. A coordination gap also needs
preservation: the matrix's nested `GLOBAL_T1_STOP.json` was not recognized by
other owners' filename-only stop checks, so normal/init work continued after
the matrix stop. Root publishes canonical top-level
`T/T1_STOP_CONFIRMED_BOTTOM_ESCAPE_20261029.json`, stops every later old-T1
dispatch and resumes targeted CPU repair diagnosis. Completed receipts are not
rewritten. Root's independent18-receipt and hard-proof bindings are
`R/control/root_T1_rejected_normal18_scoped_20261029T1423.json`.
The earlier12–18hour throughput estimate is withdrawn pending a repaired
candidate. No core, SDK, public robot, Chen installation or Feishu changes occur.

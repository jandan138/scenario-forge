# WET-OP private migration and dataset release

Status: complete. Private migration accepted within the documented native-check scope; both public datasets verified.

The authorized private destination is `/cpfs/shared/wet_op_bench/GenManip-Sim`, transferred through `genmanip-2gpu` (`10.150.170.198`). The source `/mnt/data/chenjiantong/GenManip-Sim` remains unchanged. CPFS access was configured by the user; this task does not change or attest the cloud access list.

The private copy retains source commit `9151623253bf9db737ad0d696b50f3a95821591b`, independent Git history and client submodule `61202ccc1419d1e1427ea750bfdeb44309862386`. Its local branch is `migration/wet-op-private-20261107`. The selection retains `saved/assets` and 959 task directories referenced by test, validation and holdout_test YAML configurations. Historical results, logs, client outputs and repair/backup caches are excluded. New acceptance logs belong to this migration and are kept separately from old source logs. The source is not cleaned up or switched to a different branch.

Public release targets are two sibling dataset repositories: `InternRobotics/WET-OP-Bench-Train` and `InternRobotics/WET-OP-Bench-Validation`. Only their explicit staging roots under `/cpfs/shared/wet_op_bench/releases/huggingface` may be uploaded. The private project root must never be uploaded wholesale.

Training source is `/mnt/data/chenjiantong/wet_op_bench/lerobot_train_dataset`: 14 independent LeRobot v2.1 task roots, 500 episodes each. Preserve episode indices and data/meta/videos layout. No duplicate large archive is produced.

Validation is exactly `scientific_experiments/task_01_pour_flask_to_cylinder/validation_mixed_1/000`. The publication copy removes LMDB and recording bookkeeping, retaining original task_data and instruction. Its scene folder is renamed from `unseen_scene_1` to `public_validation`; background, geometry, physical parameters and material values are unchanged. Other validation episodes and all test/holdout data stay private.

The user attests that all model and scene assets are internally authored by the AI Lab team. Team-owned published data/assets use standard MIT, copyright 2026 Intern Robotics. NVIDIA material and planner software are distinct runtime dependencies: permissive MDL modules retain original notices; the EULA Plastic_Thick_Translucent shader is referenced at its official NVIDIA URL, not redistributed. Its SHA-256 is `e6fc7403fce0da94912d3aa2ced0638a2aafb4c9cd504a745743f4273b7dc333`. The cuRobo planner configuration retains its upstream notice and installed LICENSE, including the research/evaluation limitation; it is not relicensed as MIT.

## Verification and evidence

Applicable standards: ASSET-002, VAL-001 through VAL-007. This changes packaging and deployment, not core package/schema/adapter behavior. Standards need no general rule change: the existing closure, immutable-source and evidence-scope rules cover the work. No simulator code is added to Scenario Forge core.

Operational scripts and raw evidence are under `external_artifacts/wet_op_release_20261107/`. Private state, file hashes and upload receipts are in `/cpfs/shared/wet_op_bench/_operations/release_20261107/` on the target host. Tokens live outside all staging roots in a mode-0600 credential file and are never included in reports.

The first isolated public native probe found transitive MDL imports missing from USD-only dependency discovery and a required R5a planner configuration missing from the package. This failed attempt is retained. Original files were added with upstream notices, followed by new static and native checks. No visual substitution or source scene edits were used to conceal these failures.

Acceptance covers byte-level migration checks, public allowlist/dependency checks, original-versus-public scene semantics, native initialization and short hold steps with four cameras. It does not attest full policy performance, trajectory success, or all task configurations. A legacy broken asset-authoring symlink in the source is recorded separately; no fabricated target is introduced.

Final measured counts, native/visual outcomes and HF revisions will be appended after verification.

## Verified checkpoint at 13:04 UTC

- Private selected assets/tasks: all 18,826 files matched source/destination SHA-256; source and destination Git worktrees are clean and the client submodule remains pinned. The original unused legacy articulation JSON link remains broken as in the source.
- Task-01 original validation and test reset/20-step probes completed. Public validation completed an isolated reset/20-step probe; its full startup/worker/server/client log review found no substantive errors. Progress bars written to stderr are recorded separately from errors. Existing headless-window/Open3D warnings remain in raw logs.
- The implementer reviewed 16 paired original/public images (four cameras at reset and after 20 steps). Scene appearance is preserved. This is not an independent review. Camera cropping and incomplete receiver visibility are inherited limitations.
- Public validation is verified at [Hugging Face](https://huggingface.co/datasets/InternRobotics/WET-OP-Bench-Validation), revision `5ad001b6ce30f0de162d24faa316a611dde84c40`. All 84 local publication files were checked against remote sizes and LFS SHA-256 / Git blob hashes; a metadata sample was downloaded from the pinned payload revision. Upload caches and runtime-generated mesh caches are excluded.
- The holdout probe completed steps/images but emitted an MDL database transaction error. A fresh cold-start probe is pending; this first result is not described as error-free.
- Training copy is still running. Source preflight checked first/last episode indices and one video decode for each of the 14 tasks. Full destination hashes, all episode indices, video references, and public upload remain pending in the serial pipeline.
- `make check` passed: 1,259 tests passed, 1 skipped; Ruff, Phase 10.x suite and diff-whitespace checks also passed. No core package/schema/adapter code was changed.

## Private acceptance and visual correction

The second holdout cold start (`release_holdout_20261107b`) completed initialization and 20 hold steps with no substantive error lines in the full checked logs. The earlier MDL transaction error is retained as a non-reproduced event, not presented as a proven causal fix. `private_acceptance.json` now records the selected-file integrity result and native task-01 test/validation/holdout probes. These probes do not cover every one of the 959 private configuration directories.

The first review contact sheet pasted full-resolution images into smaller cells and inadvertently showed crops. Corrected full-frame contact sheets plus the original 1280×960 overhead image were reviewed: both task vessels are visible in the overhead camera, with partial views from individual fixed cameras. The earlier wording about incomplete receiver visibility across the scene was too broad. The public README was corrected without changing payload files or scene state. Full-frame test and final holdout images were also reviewed; no blank camera or missing-material fallback is visible.

The legacy broken link is not the loader's default: `genmanip/utils/loader/scene.py` loads `assets/objects/articulation_data.json` unless a configuration overrides `articulation_data_path`. A tracked-config search found no such override and no `articulation_data_1` reference. The broken legacy link is retained unchanged; this finding is scoped to the migrated version and configured splits.

## Training publication started

Training copy completed at 13:27:11 UTC. All 35,056 source payload files matched SHA-256 (541,374,148,261 bytes); 7,000 episodes / 19,654,550 frames passed all episode/frame index and referenced-video checks, with 56 successful sample video decodes. The training dataset card, MIT license and manifest were then created.

`InternRobotics/WET-OP-Bench-Train` was created publicly by this release and is uploading with resumable state. Upload concurrency was raised from 6 to 12 workers via a publication-only resume; completed local checks were not rerun or bypassed. At the 13:38 UTC checkpoint, upload reporting showed approximately 4.6 GB pre-uploaded and 2.7 GB committed. These are partial progress values, not a complete published dataset. The receipt remains `UPLOADING` until remote verification succeeds.

The detached controller-side proxy supervisor and target-side publication pipeline are active. After upload, `publish.py` performs remote file-tree, size, hash and sample-download checks. `finish_release.py` then verifies both dataset receipts and writes final documentation and `release_status.json`. Any pipeline exception is recorded as `FAILED_REQUIRES_REVIEW`; source data are never deleted by this workflow.


## Completed release 502d07401d1da7d9bf766f70ee5b039d389019fc

Completed at 2026-11-08T02:44:32.851698+00:00.

- Training: 35056 payload files, 541374148261 bytes, 14 tasks / 7,000 episodes. Full source/destination SHA-256 checks, all episode/frame index checks, video-reference checks and 56 sampled video decodes passed.
- Train repository: https://huggingface.co/datasets/InternRobotics/WET-OP-Bench-Train, final revision `502d07401d1da7d9bf766f70ee5b039d389019fc`.
- Validation repository: https://huggingface.co/datasets/InternRobotics/WET-OP-Bench-Validation, final revision `178cbcc0724a8a72ab15323a9a32b04275e8a06a`. Exactly one episode, no LMDB or recorded trajectories.
- Both repositories passed remote file-tree, size and content-hash checks plus pinned-revision sample downloads. Source data remain unchanged; private test/holdout data were not published.
- Final machine-readable receipt: `/cpfs/shared/wet_op_bench/_operations/release_20261107/release_status.json`. The first failed/errored native attempts remain in private evidence.

## 2026-11-08 final tail repair

At 02:41 UTC, 35,058 of 35,059 training publication files were committed; one 18,897,815-byte video remained (`task_09_solid_weighing/videos/chunk-000/video.right_camera_view/episode_000020.mp4`). Prior upload logs included Hugging Face HTTP 429 rate-limit retries. The active tail upload was no longer advancing, despite the API being reachable.

The stalled publisher was stopped and resumed with a targeted single-file upload followed by the existing full remote verifier. No source data or upload scope changed. The remaining file uploaded successfully; all 35,059 publication files then passed remote tree, size and content-hash verification and the pinned-revision sample download. Final Train revision: `502d07401d1da7d9bf766f70ee5b039d389019fc`. The overall release completed at approximately 02:44 UTC, and the publication pipeline recorded `PUBLISHED_VERIFIED`.

A fresh remote validation-repository listing on 2026-11-08 confirmed exactly the approved task-01 `validation_mixed_1/000` metadata entry, with no test or holdout paths. Its receipt is `validation_remote_scope_20261108.json`. Training remote-tree equality against the checked local manifest confirms no extra test, holdout, or validation payload was included in Train.

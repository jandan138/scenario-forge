# WET-OP instruction-to-metric semantic alignment — 2026-11-13

Applied the reviewed instruction-to-metric alignment patch (`docs/tmp/wet_op_instruction_alignment_review.html`, 149 updated templates across 6 demonstration tasks and 1 zero-shot task) across `/cpfs/shared/wet_op_bench/` on `genmanip-2gpu` (`10.150.170.198`) and synchronized the two private Hugging Face dataset repositories. `/mnt/data/chenjiantong/GenManip-Sim`, `origin/feature/pioneer`, and historical showcase files under `collected_files_20261016/paper_demo/` were left untouched.

## Scope and exact counts

- **Affected tasks (7 of 20)**: `task_01_pour_flask_to_cylinder`, `task_02_pour_liquid_and_stir`, `task_03_magnetic_beaker_stirrer`, `task_04_pour_liquid_with_funnel`, `task_09_solid_weighing`, `task_13_blue_bottle_reaction`, and zero-shot `task_z3_boat_pour_stir`. All remaining 13 tasks were verified unchanged.
- **Training dataset (`/cpfs/shared/wet_op_bench/releases/huggingface/WET-OP-Bench-Train`)**:
  - Updated `69` rows across 6 `<task>/meta/tasks.jsonl` files and `1,770` episode rows across 6 `<task>/meta/episodes.jsonl` files.
  - Updated the corresponding `12` entries in `WET-OP-Bench-Train/manifest.jsonl` (`sha256: 679e8591ccbc766c2a5173f4dfc236531306e0c17d5b02752ad4a8f2252ea2b5`).
  - Parquet (`task_index: int64`) and MP4 files required zero modification.
- **Private evaluation sets (`/cpfs/shared/wet_op_bench/GenManip-Sim`)**:
  - Updated `221` of `959` `saved/tasks/scientific_experiments/<task>/<case>/000/meta_info.pkl` files (`153` `test` + `34` `validation` + `34` `holdout_test`), updating both `language_instruction` and `task_data["instruction"]` atomically in `test` → `validation` → `holdout_test` order.
  - Verified the remaining `738` `meta_info.pkl` files retained byte-identical SHA-256 digests (`before_all_959_meta_hashes.json`), and verified `goal`, `initial_layout`, `initial_scene_graph`, `camera_data`, and `initial_particle_states` are byte-identical before and after on all `221` updated files.
  - Updated `34` case entries (`instruction`, `source_metadata_sha256`, `metadata_sha256`) in `configs/batches/holdout_test.json` and committed locally on `migration/wet-op-private-20261107` (`bee185b3b42faf6cecbe8dd663f93e22da6f77bf`).
- **Public single-episode validation staging (`/cpfs/shared/wet_op_bench/releases/huggingface/WET-OP-Bench-Validation`)**:
  - Updated `saved/tasks/scientific_experiments/task_01_pour_flask_to_cylinder/validation_mixed_1/000/meta_info.pkl` (`sha256: 92d77878b0211a8960998d35466efb2574933d639525769b81c185c25473f53e`) and `manifest.jsonl` (`sha256: a0ff700c244f4c8f8deef2f09988f3b7d94994a5ce65230ddd4a61262ac827ee`).

## Private Hugging Face synchronization

| Repository | Privacy (`before` → `after`) | Previous revision | New revision | Committed files | Remote siblings verified |
| --- | --- | --- | --- | ---: | ---: |
| `InternRobotics/WET-OP-Bench-Train` | `private: True` → `True` | `502d07401d1da7d9bf766f70ee5b039d389019fc` | `bcec8e3dd7975be4ab12bc045119e83226d22a34` | 13 | 35,060 |
| `InternRobotics/WET-OP-Bench-Validation` | `private: True` → `True` | `178cbcc0724a8a72ab15323a9a32b04275e8a06a` | `07e73c41e9f6a5a764a1608a036dd3ab4311c072` | 2 | 85 |

Both repositories passed remote file-count, file-size, LFS/blob hash, privacy preservation, and pinned-revision sample download SHA-256 verification.

## Backup, rollback, and standards synchronization

- Pre-change backups of all `237` modified files (`14,785,377` bytes), `patch_spec.json`, `before_after_hashes.json`, `hf_sync_receipt.json`, and dry-run-by-default `rollback.py` are stored under `/cpfs/shared/wet_op_bench/_operations/instruction_alignment_20261113/` on `genmanip-2gpu`.
- All 41 GenManip-Sim unit tests (`python -m unittest discover -s tests/unit -v`) and LeRobot Parquet ↔ `tasks.jsonl` ↔ `episodes.jsonl` consistency checks passed.
- Applicable standards: VAL-002, VAL-003, VAL-005, and VAL-006. This change aligns natural-language task descriptions with existing evaluation rubric clauses without altering scene USD layers, physics parameters, asset contracts, or Scenario Forge core schemas; `docs/standards/` requires no rule change.
